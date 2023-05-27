import itertools
import os
import sys
import typing as t
import typing_extensions as te
import logging as log
from pathlib import Path

import numpy as np
import numpy.ma as ma
import numpy.typing as npt
import matplotlib.pyplot as plt
import tqdm

from src import profile
from src.util import lerp, point_to_line_dist
from src.measurements.source import BufferedSource, SingleBufferSource, SourceEmpty
from src.nap.kia.canbus import make_can
from src.nap.kia.gps import make_avg_gps, GpsData

dpi = 100

trim_ms = 10 * 1000

ts_max_diff = 100  # ms
gps_ts_max_diff = 50  # ms

wp_timed_max_speed = 4  # m/s

WORK_PATH = Path("/work")
OUT_PATH = Path(os.environ["OUT_PATH"])
SAVE_PATH = Path(os.environ["SAVE_PATH"])


InputDict = te.TypedDict(
    "InputDict",
    {
        "gps_carla": t.Tuple[float, float],
        "yaw_rad": float,
        "speed_mps": float,
    }
)
ActionDict = te.TypedDict(
    "ActionDict",
    {
        "steer": float,
        "throttle": float,
        "brake": float,
    }
)
ExtraDict = te.TypedDict(
    "ExtraDict",
    {
        "wp": np.ndarray,
        "desired_speed": float,
        "angle_rad": float,
        "raw_steer": float,
    }
)
Record = t.Tuple[float, int, InputDict, ActionDict, ExtraDict]
LatLonDict = te.TypedDict("LatLonDict", {"lat": float, "lon": float})
SaveFile = te.TypedDict(
    "SaveFile",
    {
        "gps0": t.Tuple[float, float],
        "records": t.List[Record],
        "trip": str,
        "global_plan_gps": t.List[t.Tuple[LatLonDict, t.Any]],
    }
)


def get_path(run: str):
    # Strip leading parts until we get a relative path that exists
    path = Path(run)
    for skip in range(len(path.parts)):
        parts = path.parts[skip:]
        test_path = Path("/").joinpath(*parts)
        if test_path.is_dir():
            return test_path
    raise ValueError(f'Could not find path for "{run}"')


def parse_model(model: str) -> te.Literal['transfuser', 'interfuser']:
    if model == 'transfuser':
        return 'transfuser'
    elif model == 'interfuser':
        return 'interfuser'
    else:
        raise ValueError(f'"{model}" is not a known model')


def smooth(arr: np.ndarray, window: int = 5):
    window += 1 - window % 2
    return ma.convolve(arr, np.ones(window) / window, mode="same")


def pearson(x, y):
    return ma.corrcoef(x, y)[0, 1]


def trim_records(records: t.List[Record]):
    """Remove the first and last few seconds of the records."""
    start_ts = records[0][0]
    end_ts = records[-1][0]
    start_ts += trim_ms
    end_ts -= trim_ms
    return [
        record
        for record in records
        if start_ts <= record[0] <= end_ts
    ]


@profile.func
def transform_wps(wps_raw: np.ndarray, NE0: np.ndarray, yaw: float):
    """Transform the WP predictions from the car's frame to a global frame."""
    rot = np.array([
        [np.cos(yaw), -np.sin(yaw)],
        [np.sin(yaw), np.cos(yaw)],
    ])
    return np.array([NE0 + rot @ wp for wp in wps_raw])


@profile.func
def find_closest_wps(gps: BufferedSource[GpsData], wp: np.ndarray):
    # Find the closest GPS point
    closest_index = 0
    closest_NE = gps.value.NE
    closest_dist = np.linalg.norm(wp - closest_NE)
    break_dist = 2 * closest_dist

    for i in itertools.count(1):
        try:
            peek_NE = gps.peek(i).value.NE
        except SourceEmpty:
            break
        dist = np.linalg.norm(wp - peek_NE)
        if dist < closest_dist:
            closest_dist = dist
            closest_index = i
            closest_NE = peek_NE
        elif dist > break_dist:
            break

    # Now, we can try to find the points before and after the closest point
    # and measure the distance to the line segments between them.

    lines = []

    if closest_index > 0:
        before_NE = gps.peek(closest_index - 1).value.NE
        lines.append((before_NE, closest_NE))

    try:
        after_NE = gps.peek(closest_index + 1).value.NE
        lines.append((closest_NE, after_NE))
    except SourceEmpty:
        pass

    # TODO: fix interpolation of closest_NE
    return min(
        (point_to_line_dist(wp, line) for line in lines),
        default=closest_dist
    ), closest_NE


@profile.func
def find_timed_wps(gps: BufferedSource[GpsData], wp: np.ndarray, time_sec: float):
    time_ms = gps.ts + time_sec * 1e3
    i = 0

    # Advance i until we're past the time we're looking for
    try:
        while gps.peek(i).ts < time_ms:
            i += 1
    except SourceEmpty:
        return None
    
    lerp_NE = lerp(
        time_ms,
        gps.peek(i - 1).ts,
        gps.peek(i).ts,
        gps.peek(i - 1).value.NE,
        gps.peek(i).value.NE,
    )
    dist = np.linalg.norm(wp - lerp_NE)
    return dist, lerp_NE


@profile.func
def find_spaced_wps(gps: BufferedSource[GpsData], wp: np.ndarray, dist: float):
    i = 0

    # Advance i until we're past the distance we're looking for
    try:
        while np.linalg.norm(gps.peek(i).value.NE - gps.value.NE) < dist:
            i += 1
    except SourceEmpty:
        return None
    
    lerp_NE = lerp(
        dist,
        np.linalg.norm(gps.peek(i - 1).value.NE - gps.value.NE),
        np.linalg.norm(gps.peek(i).value.NE - gps.value.NE),
        gps.peek(i - 1).value.NE,
        gps.peek(i).value.NE,
    )
    dist = np.linalg.norm(wp - lerp_NE)
    return dist, lerp_NE


def main(trip: str, run: str, count: t.Optional[int]):
    path = get_path(run)
    if path.parts[-3] != trip:
        raise ValueError(f'"{trip}" is not in "{run}"')

    model = parse_model(path.parts[-2])
    model_run = path.parts[-1]

    (OUT_PATH / ('model-' + model)).touch()
    (OUT_PATH / ('run-' + model_run)).symlink_to(run, target_is_directory=True)

    trip_path = Path("/dataset") / trip
    records_path = path / "records.npz"

    log.info(f"Loading records from: {records_path}")
    data = t.cast(SaveFile, np.load(records_path, allow_pickle=True))
    gps0 = data["gps0"]
    records = data["records"]
    log.info(f"Loaded {len(records)} records")

    records = trim_records(records)
    log.info(f"Trimmed 2*{trim_ms} ms down to {len(records)} records")

    gps = BufferedSource(
        make_avg_gps(
            trip_path / "gnss50_vehicle.bin",
            trip_path / "gnss52_vehicle.bin",
            max_ts_diff_ms=gps_ts_max_diff,
            gps0=gps0,
        )
    )
    can = SingleBufferSource(make_can(trip_path / "can_vehicle1.bin"))

    if model == 'transfuser':
        wp_metric = 'timed'
    elif model == 'interfuser':
        wp_metric = 'spaced'
    else:
        raise ValueError(f'Unknown model: "{model}"')

    T = []
    steer = []
    speed = []
    throttle = []
    brake = []
    waypoint_dists: t.List[t.List[t.Union[ma.MaskedArray, np.floating]]] = []

    if count is not None:
        records = records[:count]

    for ts, step, input, action, extra in tqdm.tqdm(records):
        with profile.ctx('advance'):
            gps.advance_to(ts)
            can.advance_to(ts)

        ts_diff = abs(gps.ts - can.ts)
        if ts_diff > ts_max_diff:
            log.warning(
                "Skipping frame at %d due to large time difference %.2f",
                step + 1,
                ts_diff,
            )
            continue

        tf_steer = extra["raw_steer"] * 180 / np.pi
        tf_speed = extra["desired_speed"] * 3.6
        tf_throttle = action["throttle"]
        tf_brake = action["brake"]

        wps_NE = transform_wps(extra["wp"], NE0=gps.value.NE, yaw=input["yaw_rad"])
        exp_wps: t.List[t.Tuple[float, npt.ndarray]] = []

        if wp_metric == 'timed':
            speed_mps = can.value[1].speed / 3.6
            if speed_mps > wp_timed_max_speed:
                # Reduce lookahead when we're driving faster than the agents
                # are trained for.
                wp_time_scale = wp_timed_max_speed / speed_mps
            else:
                wp_time_scale = 1
            times = wp_time_scale * 0.5 * np.arange(1, len(wps_NE) + 1)
            exp_wps = [find_timed_wps(gps, wp, dt) for wp, dt in zip(wps_NE, times)]

        elif wp_metric == 'spaced':
            wp_space_offset = 3.5
            spaces = wp_space_offset + np.arange(len(wps_NE))
            exp_wps = [find_spaced_wps(gps, wp, space) for wp, space in zip(wps_NE, spaces)]
        
        elif wp_metric == 'closest':
            exp_wps = [find_closest_wps(gps, wp) for wp in wps_NE]

        # Strip away trailing None values
        exp_wps = list(itertools.takewhile(lambda x: x is not None, exp_wps))
        
        # Store the distances, and fill with masked values in
        # case we suddenly get a varying number of waypoints.
        for i, exp_wp in enumerate(exp_wps):
            while len(waypoint_dists) <= i:
                waypoint_dists.append([ma.masked] * len(T))
            waypoint_dists[i].append(exp_wp[0])
        for j in range(len(exp_wps), len(waypoint_dists)):
            waypoint_dists[j].append(ma.masked)

        T.append(ts / 1000)
        steer.append((tf_steer, can.value[1].steer * -1))
        speed.append((tf_speed, can.value[1].speed))
        throttle.append((tf_throttle, can.value[1].throttle))
        brake.append((tf_brake, can.value[1].brake))

        if False:
        # if 480 < T[-1] - T[0] < 490:
        # if 800 <= step <= 900 or 1100 <= step <= 1200:
            fut_gps = np.array([gps.peek(i).value.NE for i in range(1, 10)])
            exp_wpts = np.array([exp_wp[1] for exp_wp in exp_wps])
            plt.figure(figsize=(12, 12))
            plt.scatter(gps.value.NE[1], gps.value.NE[0], label='Car')
            plt.scatter(fut_gps[:, 1], fut_gps[:, 0], label='GPS', s=np.linspace(3, 1, len(fut_gps)))
            plt.scatter(exp_wpts[:, 1], exp_wpts[:, 0], label='Expected WPs')
            plt.scatter(wps_NE[:, 1], wps_NE[:, 0], label='Predicted WPs')
            plt.plot
            plt.legend()
            plt.savefig(OUT_PATH / f'wp_{step}.png', dpi=dpi)

    T = np.array(T) - T[0]
    speed = np.array(speed)
    steer = np.array(steer)
    throttle = np.array(throttle)
    brake = np.array(brake)

    # Mask steering when standing still
    steer = ma.array(steer)
    steer[speed < 1] = ma.masked

    # Corr coefficients
    corr_steer = pearson(steer[:, 0], steer[:, 1])
    corr_speed = pearson(speed[:, 0], speed[:, 1])
    corr_throttle = pearson(throttle[:, 0], throttle[:, 1])
    corr_brake = pearson(brake[:, 0], brake[:, 1])


    ## Plotting

    # Smoothing
    steer[:, 0] = smooth(steer[:, 0], 5)
    speed[:, 0] = smooth(speed[:, 0], 5)

    # Normalize GT to (-1, 1), and scale predictions to best fit
    steer[:, 1] = steer[:, 1] / np.max(np.abs(steer[:, 1]))
    steer_nz = np.abs(steer[:, 0]) > 0.01
    steer[:, 0] *= np.mean(np.abs(steer[steer_nz, 1]) / np.abs(steer[steer_nz, 0]))

    # Steer and speed
    plt.figure(figsize=(10, 10))
    plt.subplot(2, 1, 1)
    plt.title(f"Steer (corr: {corr_steer:.2f})")
    plt.plot(T, steer[:, 0], label="Agent")
    plt.plot(T, steer[:, 1], label="Ground truth")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Angle [normalized]")
    plt.minorticks_on()
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.title(f"Speed (corr: {corr_speed:.2f})")
    plt.plot(T, speed[:, 0], label="Agent")
    plt.plot(T, speed[:, 1], label="Ground truth")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Speed [km/h]")
    plt.minorticks_on()
    plt.grid()

    plt.tight_layout()
    plt.savefig(OUT_PATH / "steer,speed.png", dpi=dpi)

    # Waypoint distances
    plt.figure(figsize=(12, 6))
    plt.title(f"Waypoint error")
    for i, wp_dists in enumerate(waypoint_dists):
        percents = [50, 95, 99]
        wp_dists = ma.array(wp_dists)
        percentiles = np.nanpercentile(wp_dists.filled(np.nan), percents)
        fmt_percentiles = ', '.join(f'{p}%: {d:.2f}' for p, d in zip(percents, percentiles))
        plt.plot(T, wp_dists, label=f"WP{i+1} percentiles: {fmt_percentiles}", zorder=2-i/100)
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Distance [m]")
    plt.minorticks_on()
    plt.grid()
    
    plt.tight_layout()
    plt.savefig(OUT_PATH / "waypoint_dists_full.png", dpi=dpi)

    # Waypoint distances (outliers removed)
    plt.figure(figsize=(12, 6))
    plt.title(f"Waypoint error")
    for i, wp_dists in enumerate(waypoint_dists):
        percents = [50, 95, 99]
        wp_dists = ma.array(wp_dists)
        percentiles = np.nanpercentile(wp_dists.filled(np.nan), percents)
        fmt_percentiles = ', '.join(f'{p}%: {d:.2f}' for p, d in zip(percents, percentiles))
        plt.plot(T, wp_dists, label=f"WP{i+1} percentiles: {fmt_percentiles}", zorder=2-i/100)
        plt.ylim(0, percentiles[-1] * 1.1)
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Distance [m]")
    plt.minorticks_on()
    plt.grid()
    
    plt.tight_layout()
    plt.savefig(OUT_PATH / "waypoint_dists_99th.png", dpi=dpi)

    # Throttle and brake
    # Normalize GTs to (0, 1)
    throttle[:, 1] /= np.max(throttle[:, 1])
    brake[:, 1] /= np.max(brake[:, 1])

    plt.figure(figsize=(10, 10))
    plt.subplot(2, 1, 1)
    plt.title(f"Throttle (corr: {corr_throttle:.2f})")
    plt.plot(T, throttle[:, 0], label="Agent")
    plt.plot(T, throttle[:, 1], label="Ground truth")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Throttle")
    plt.minorticks_on()
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.title(f"Brake (corr: {corr_brake:.2f})")
    plt.plot(T, brake[:, 0], label="Agent")
    plt.plot(T, brake[:, 1], label="Ground truth")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Brake")
    plt.minorticks_on()
    plt.grid()

    plt.tight_layout()
    plt.savefig(OUT_PATH / "throttle,brake.png", dpi=dpi)


if __name__ == "__main__":
    trip = sys.argv[1]
    run = sys.argv[2]
    if len(sys.argv) > 3:
        count = int(sys.argv[3])
    else:
        count = None

    with profile.scope('main', dump=True):
        main(trip, run, count)
