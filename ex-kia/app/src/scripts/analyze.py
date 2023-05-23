import itertools
import os
import sys
import typing as t
import typing_extensions as te
import logging as log
from pathlib import Path

import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import tqdm

from src import profile
from src.util import point_to_line_dist
from src.measurements.source import BufferedSource, SingleBufferSource, SourceEmpty
from src.nap.kia.canbus import make_can
from src.nap.kia.gps import make_avg_gps, GpsData

trim_ms = 10 * 1000
ts_max_diff = 100  # ms
gps_ts_max_diff = 50  # ms

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
def transform_wps(wps_NE: np.ndarray, NE: np.ndarray, yaw: float):
    """Transform the WP predictions from the car's frame to a global frame."""
    rot = np.array([
        [np.cos(yaw), -np.sin(yaw)],
        [np.sin(yaw), np.cos(yaw)],
    ])
    return np.array([NE + rot @ wp for wp in wps_NE])


@profile.func
def find_wp_dist(gps: BufferedSource[GpsData], wp: np.ndarray):
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

    return min(
        (point_to_line_dist(wp, line) for line in lines),
        default=closest_dist
    )


def main(trip: str, run: str, count: t.Optional[int]):
    path = get_path(run)
    if path.parts[-3] != trip:
        raise ValueError(f'"{trip}" is not in "{run}"')
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

    T = []
    steer = []
    speed = []
    throttle = []
    brake = []
    waypoint_dists: t.List[t.List[float]] = []

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

        wps_NE = transform_wps(extra["wp"], NE=gps.value.NE, yaw=input["yaw_rad"])
        wp_dists = [find_wp_dist(gps, wp) for wp in wps_NE]
        for i, wp_dist in enumerate(wp_dists):
            while len(waypoint_dists) <= i:
                waypoint_dists.append([ma.masked] * len(T))
            waypoint_dists[i].append(wp_dist)
        for j in range(len(wp_dists), len(waypoint_dists)):
            waypoint_dists[j].append(ma.masked)

        T.append(ts / 1000)
        steer.append((tf_steer, can.value[1].steer * -1))
        speed.append((tf_speed, can.value[1].speed))
        throttle.append((tf_throttle, can.value[1].throttle))
        brake.append((tf_brake, can.value[1].brake))

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
    steer[:, 0] *= np.mean(steer[steer_nz, 1] / steer[steer_nz, 0])

    # Steer and speed
    plt.figure(figsize=(10, 10))
    plt.subplot(2, 1, 1)
    plt.title(f"Steer (corr: {corr_steer:.2f})")
    plt.plot(T, steer[:, 0], label="TF")
    plt.plot(T, steer[:, 1], label="GT")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Angle [normalized]")
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.title(f"Speed (corr: {corr_speed:.2f})")
    plt.plot(T, speed[:, 0], label="TF")
    plt.plot(T, speed[:, 1], label="GT")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Speed [km/h]")
    plt.grid()

    plt.tight_layout()
    plt.savefig(OUT_PATH / "steer,speed.png", dpi=1000)

    # Waypoint distances
    plt.figure(figsize=(12, 6))
    plt.title(f"Waypoint error")
    for i, wp_dists in enumerate(waypoint_dists):
        percents = [50, 95, 99]
        percentiles = np.percentile(wp_dists, percents)
        fmt_percentiles = ', '.join(f'{p}%: {d:.2f}' for p, d in zip(percents, percentiles))
        plt.plot(T, wp_dists, label=f"WP{i+1} percentiles: {fmt_percentiles}", zorder=2-i/100)
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Distance [m]")
    plt.grid()
    
    plt.tight_layout()
    plt.savefig(OUT_PATH / "waypoint_dists.png", dpi=1000)

    # Throttle and brake
    plt.figure(figsize=(10, 10))
    plt.subplot(2, 1, 1)
    plt.title(f"Throttle (corr: {corr_throttle:.2f})")
    plt.plot(T, throttle[:, 0], label="TF")
    plt.plot(T, throttle[:, 1], label="GT")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Throttle")
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.title(f"Brake (corr: {corr_brake:.2f})")
    plt.plot(T, brake[:, 0], label="TF")
    plt.plot(T, brake[:, 1], label="GT")
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Brake")
    plt.grid()

    plt.tight_layout()
    plt.savefig(OUT_PATH / "throttle,brake.png", dpi=1000)


if __name__ == "__main__":
    trip = sys.argv[1]
    run = sys.argv[2]
    if len(sys.argv) > 3:
        count = int(sys.argv[3])
    else:
        count = None

    with profile.scope('main', dump=True):
        main(trip, run, count)
