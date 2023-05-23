from collections import deque
import logging
import os
from typing import Any, Callable, Dict, Tuple

_log = logging.getLogger(__name__)

import sys
import enum
import itertools
import datetime
from contextlib import suppress
from pathlib import Path

import numpy as np
from PIL import Image

from src import profile
from src.measurements.source import BufferedSource, SingleBufferSource, SourceEmpty
from src.measurements.collection import MeasurementCollection
from src.nap.kia.gps import make_avg_gps
from src.nap.kia.camera import make_camera
from src.nap.kia.lidar import make_lidar
from .make_mov import make_movie

from srunner.scenariomanager.timer import GameTime


WORK_PATH = Path("/work")
OUT_PATH = Path(os.environ["OUT_PATH"])
SAVE_PATH = Path(os.environ["SAVE_PATH"])


class RoadOption(enum.Enum):
    UNUSED = 0


def run_agent(
    trip: str,
    setup_agent: Callable[[], Any],
    process_image: Callable[[np.ndarray, Any], np.ndarray],
    get_extra_data: Callable[[int, Any, Any], Dict[str, Any]],
):
    _log.info("Loading global plan")
    plan_path = "/plan/plan.csv"
    csv = np.genfromtxt(plan_path, delimiter=",", names=True)
    gps0 = (csv["lat"][0], csv["lon"][0])
    csv = csv[1:]
    carla_lat = csv["carla_lat"]
    carla_lon = csv["carla_lon"]
    global_plan_gps = [
        ({"lat": lat, "lon": lon}, RoadOption.UNUSED)
        for lat, lon in zip(carla_lat, carla_lon)
    ]

    _log.info("Preparing input data")
    input_data_gen = gen_input_data(
        Path("/dataset") / trip,
        gps0=gps0,
        process_image=process_image,
    )
    input_data_iter = iter(input_data_gen)

    _log.info("Loading agent")
    agent = setup_agent()

    # Don't use set_global_plan to avoid route downsampling
    agent._global_plan = global_plan_gps

    agent.tick = profile.func(agent.tick)
    agent.run_step = profile.func(agent.run_step, name="agent.run_step")

    records = []

    def save_records():
        _log.info("Saving records")
        np.savez(OUT_PATH / "_records.npz", records=records, gps0=gps0, global_plan_gps=global_plan_gps, trip=trip)
        (OUT_PATH / "_records.npz").rename(OUT_PATH / "records.npz")

    try:
        while True:
            print("--")
            ts, step, input_data = next(input_data_iter)

            GameTime._init = True
            GameTime._last_frame = step
            GameTime._carla_time = ts / 1000
            GameTime._current_game_time = ts / 1000
            GameTime._platform_timestamp = datetime.datetime.now()

            print_input_data(step, input_data)

            action = agent.run_step(input_data, step)
            extra = get_extra_data(step, agent, action)

            action_dict = {
                "steer": action.steer,
                "throttle": action.throttle,
                "brake": action.brake,
            }
            record_input = {
                "gps_carla": input_data["gps"][1][:2],
                "yaw_rad": input_data["imu"][1][0],
                "speed_mps": input_data["speed"][1]["speed"],
            }
            record = (ts, step, record_input, action_dict, extra)
            records.append(record)

            save_exp = np.floor(np.log10(len(records)))
            save_interval = max(10**save_exp, 10)
            if len(records) % save_interval == 1:
                save_records()

    except (StopIteration, KeyboardInterrupt):
        pass

    save_records()

    with profile.ctx("make movie"):
        make_movie(SAVE_PATH, OUT_PATH / "movie.mp4")


def make_input_data(step: int):
    with profile.ctx("make fake input data"):
        ex_lidar = [step, np.zeros((100, 4), dtype=float)]
        ex_rgb = [step, np.zeros((1208, 1920, 4), dtype=np.uint8)]
        ex_gps = [step, [0, 0, 0]]  # lat, lon, alt?
        ex_speed = [step, {"speed": 0}]
        ex_imu = [step, [0]]  # yaw in radians

        return {
            "lidar": ex_lidar,
            "rgb": list(ex_rgb),
            "rgb_left": list(ex_rgb),
            "rgb_front": list(ex_rgb),
            "rgb_right": list(ex_rgb),
            "rgb_back": list(ex_rgb),
            "gps": ex_gps,
            "speed": ex_speed,
            "imu": ex_imu,
        }


def gen_input_data(
    path: Path,
    *,
    gps0: Tuple[float, float],
    process_image: Callable[[np.ndarray, Any], np.ndarray],
):
    gps_ts_max_diff = 50  # ms
    ts_max_diff = 100  # ms

    gps50_path = path / "gnss50_vehicle.bin"
    gps52_path = path / "gnss52_vehicle.bin"

    (lidar_path,) = path.glob("*.pcap")
    if not lidar_path.with_suffix(".offset").exists():
        _log.error(f"Please write the LiDAR offset in milliseconds to {lidar_path}")
        sys.exit(1)
    lidar_offset = int(lidar_path.with_suffix(".offset").read_text())

    with profile.scope("setup", dump=True):
        gps = BufferedSource(
            make_avg_gps(gps50_path, gps52_path, max_ts_diff_ms=gps_ts_max_diff, gps0=gps0)
        )
        cam_left = SingleBufferSource(make_camera(path / "C7_L2.h264"))
        cam_right = SingleBufferSource(make_camera(path / "C8_R2.h264"))
        cam_front = SingleBufferSource(make_camera(path / "C3_tricam120.h264"))
        lidar = SingleBufferSource(
            make_lidar(lidar_path, first_ts=lidar_offset + cam_front.ts)
        )

        collection = MeasurementCollection[Any](
            [gps, lidar, cam_left, cam_right, cam_front]
        )
        collection.synchronize()

    def _generator():
        est_yaw = 0
        est_speed = 0

        step = -1

        while True:
            try:
                gps.advance()
                collection.synchronize(to=gps.ts)
            except SourceEmpty:
                break

            ts_diff = collection.max_ts - collection.min_ts
            if ts_diff > ts_max_diff:
                _log.warning(
                    "Skipping frame at %d due to large time difference %.2f",
                    step + 1,
                    ts_diff,
                )
                continue

            step += 1
            input_data = make_input_data(step)

            with profile.ctx("process gps"):
                NE = gps.value.NE
                carla_lat = NE[0] / 111324.60662786
                carla_lon = NE[1] / 111319.490945

                # Find points behind and ahead of us within distance (0.5, 1) meters
                gps_min_dist = 0.5
                gps_max_dist = 1
                gps_min_pts = 3

                behind_gps_buf = []
                for i in range(-1, -gps.index, -1):
                    peek_NE = gps.peek(i).value.NE
                    peek_dist = np.linalg.norm(peek_NE - NE)
                    if peek_dist < gps_min_dist:
                        continue
                    if peek_dist > gps_max_dist and len(behind_gps_buf) >= gps_min_pts:
                        break
                    behind_gps_buf.append(peek_NE)

                ahead_gps_buf = []
                for i in itertools.count(1):
                    try:
                        peek_NE = gps.peek(i).value.NE
                    except SourceEmpty:
                        break
                    peek_dist = np.linalg.norm(peek_NE - NE)
                    if peek_dist < gps_min_dist:
                        continue
                    if peek_dist > gps_max_dist and len(ahead_gps_buf) >= gps_min_pts:
                        break
                    ahead_gps_buf.append(peek_NE)

                # Calculate the yaw from the GPS buffers
                if behind_gps_buf and ahead_gps_buf:
                    fut_avg = np.mean(ahead_gps_buf, axis=0)
                    prev_avg = np.mean(behind_gps_buf, axis=0)
                    dN, dE = fut_avg - prev_avg
                    est_yaw = np.arctan2(dE, dN)

                # # Use the values from the GPS if they are available
                # # Or not, they are noisy
                # if gps.value.course is not None:
                #     est_yaw = gps.value.course * np.pi / 180

                if gps.value.speed is not None:
                    est_speed = min(3, gps.value.speed / 3.6)

                input_data["gps"][1] = [carla_lat, carla_lon, 0]
                input_data["imu"][1] = [est_yaw]
                input_data["speed"][1] = {"speed": est_speed}

            ## RGB
            with profile.ctx("process rgb"):
                input_data["rgb_left"][1] = process_image(
                    cam_left.value.frame, (40, 30, 1.33)
                )
                input_data["rgb_front"][1] = process_image(
                    cam_front.value.frame, (0, 0, 1.21)
                )
                input_data["rgb_right"][1] = process_image(
                    cam_right.value.frame, (-228, 38, 1.33)
                )
                # InterFuser compatability
                input_data["rgb"] = input_data["rgb_front"]

            ## Lidar
            with profile.ctx("process lidar"):
                lidar_data = lidar.value.cartesian.reshape(-1, 3).copy()
                lidar_data[:, [0, 1]] = lidar_data[:, [1, 0]]
                lidar_data[:, 2] -= 0.7
                input_data["lidar"][1] = lidar_data

            yield gps.ts, step, input_data

    return profile.iterable("gen_input_data", _generator())


@profile.func
def print_input_data(step, input_data):
    print(f"{step}:")
    print("gps:", np.array(input_data["gps"][1][:2]) * [111324.60662786, 111319.490945])
    print("speed:", input_data["speed"][1]["speed"] * 3.6)
    print("imu:", input_data["imu"][1][0] * 180 / np.pi)


def tf_setup_agent():
    from team_code_transfuser.submission_agent import HybridAgent

    agent = HybridAgent("/model")
    agent.config.action_repeat = 1
    # Disable GPS denoising
    agent.gps_buffer = deque(maxlen=1)
    return agent


def tf_process_image(img, transform: Tuple[int, int, float]):
    pil = Image.fromarray(img)
    ox, oy, s = transform
    x = pil.width // 2 + ox
    y = pil.height // 2 + oy
    w = int(pil.width * s)
    h = int(pil.height * s)
    box = (x - w // 2, y - h // 2, x + w // 2, y + h // 2)
    pil = pil.crop(box)
    pil = pil.resize((960, 480), Image.BILINEAR)
    img = np.asarray(pil)
    return img


@profile.func
def tf_get_extra_data(step, agent, action):
    # Taken from model.py
    wp = agent.pred_wp[0].data.cpu().numpy()
    wp[:, 0] += agent.config.lidar_pos[0]

    desired_speed = np.linalg.norm(wp[0] - wp[1]) * 2

    aim = (wp[0] + wp[1]) / 2
    angle = np.arctan2(aim[1], aim[0])
    steer = np.degrees(angle) / 90.0

    return {
        "wp": wp,
        "desired_speed": desired_speed,
        "angle_rad": angle,
        "raw_steer": steer,
    }


def tf_main(trip: str):
    run_agent(trip, tf_setup_agent, tf_process_image, tf_get_extra_data)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        with profile.scope("main", dump=True):
            tf_main(*sys.argv[1:])
