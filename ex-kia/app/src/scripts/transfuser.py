from collections import deque
import logging
import os
from typing import Tuple

_log = logging.getLogger(__name__)

import sys
import enum
import itertools
import datetime
from contextlib import suppress
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pymap3d
import rich
from rich.table import Table
from PIL import Image

from src import profile
from src.measurements.source import BufferedSource, SourceEmpty
from src.measurements.collection import MeasurementCollection
from src.nap.kia.gps import make_avg_gps
from src.nap.kia.camera import make_camera
from src.nap.kia.lidar import make_lidar
from src.nap.kia.canbus import make_can
from .make_mov import make_movie

from team_code_transfuser.submission_agent import HybridAgent
from srunner.scenariomanager.timer import GameTime


WORK_PATH = Path('/work')
OUT_PATH = Path(os.environ['OUT_PATH'])
SAVE_PATH = Path(os.environ['SAVE_PATH'])


class RoadOption(enum.Enum):
    UNUSED = 0


def main(trip: str):
    _log.info('Loading global plan')
    plan_path = '/plan/plan.csv'
    csv = np.genfromtxt(plan_path, delimiter=',', names=True)
    gps_lat0 = csv['lat'][0]
    gps_lon0 = csv['lon'][0]
    csv = csv[1:]
    carla_lat = csv['carla_lat']
    carla_lon = csv['carla_lon']
    global_plan_gps = [
        ({ 'lat': lat, 'lon': lon }, RoadOption.UNUSED)
        for lat, lon in zip(carla_lat, carla_lon)
    ]

    _log.info('Preparing input data')
    input_data_gen = gen_input_data(
        Path('/dataset') / trip,
        gps_lat0=gps_lat0, gps_lon0=gps_lon0
    )

    _log.info('Loading agent')
    agent = HybridAgent('/model')
    agent.config.action_repeat = 1

    # Don't use set_global_plan to avoid route downsampling
    agent._global_plan = global_plan_gps

    # Disable GPS denoising
    def _gps_keep_last(*_):
        while len(agent.gps_buffer) > 1:
            agent.gps_buffer.popleft()
    agent.update_gps_buffer = _gps_keep_last

    agent.tick = profile.func(agent.tick)
    agent.run_step = profile.func(agent.run_step, name='agent.run_step')

    tf_actions = []
    gt_actions = []

    try:
        for ts, step, input_data, output_data in input_data_gen:
            GameTime._init = True
            GameTime._last_frame = step
            GameTime._carla_time = ts / 1000
            GameTime._current_game_time = ts / 1000
            GameTime._platform_timestamp = datetime.datetime.now()

            print_input_data(step, input_data)

            action = agent.run_step(input_data, step)

            print_agent_data(step, agent, action)

            tf_actions.append((-360 * action.steer, action.throttle, action.brake))
            gt_actions.append((output_data.steer, output_data.throttle, output_data.brake))

    except KeyboardInterrupt:
        pass

    tf_actions = np.array(tf_actions).T
    gt_actions = np.array(gt_actions).T
    np.savez(OUT_PATH / 'actions.npz', tf=tf_actions, gt=gt_actions)
    plot_actions(tf_actions, gt_actions)

    with profile.ctx('make movie'):
        make_movie(SAVE_PATH, OUT_PATH / 'movie.mp4')


def plot_actions(tf_actions, gt_actions):
    smoothing = np.ones(50) / 50
    for i, name in enumerate(['steer', 'throttle', 'brake']):
        plt.subplot(3, 1, i + 1)
        plt.title(name)
        smooth_tf = np.convolve(tf_actions[i], smoothing, mode='same')
        plt.plot(smooth_tf, label=f'TF')
        plt.plot(gt_actions[i], label=f'GT')
        plt.legend()
        plt.grid()
    plt.savefig(OUT_PATH / 'tf.png', dpi=600, bbox_inches='tight')


def make_input_data(step: int):
    with profile.ctx('make fake input data'):
        ex_lidar = [step, np.zeros((100, 4), dtype=float)]
        ex_rgb = [step, np.zeros((1208, 1920, 4), dtype=np.uint8)]
        ex_gps = [step, [0, 0, 0]] # lat, lon, alt?
        ex_speed = [step, { 'speed': 0 }]
        ex_imu = [step, [ 0 ]] # yaw probably

        return {
            'lidar': ex_lidar,
            'rgb_left': list(ex_rgb),
            'rgb_front': list(ex_rgb),
            'rgb_right': list(ex_rgb),
            'rgb_back': list(ex_rgb),
            'gps': ex_gps,
            'speed': ex_speed,
            'imu': ex_imu,
        }


def gen_input_data(path: Path, *, gps_lat0: float, gps_lon0: float):

    gps50_path = path / 'gnss50_vehicle.bin'
    gps52_path = path / 'gnss52_vehicle.bin'

    lidar_path, = path.glob('*.pcap')
    if not lidar_path.with_suffix('.offset').exists():
        _log.error(f'Please write the LiDAR offset in milliseconds to {lidar_path}')
        sys.exit(1)
    lidar_offset = int(lidar_path.with_suffix('.offset').read_text())

    with profile.scope('setup', dump=True):
        gps = BufferedSource(make_avg_gps(gps50_path, gps52_path))
        can_0 = make_can(path / 'can_vehicle1.bin')
        cam_left = make_camera(path / 'C7_L2.h264')
        cam_right = make_camera(path / 'C8_R2.h264')
        cam_front = make_camera(path / 'C3_tricam120.h264')
        lidar = make_lidar(lidar_path, first_ts=lidar_offset + cam_front.ts)

        to_sync = [lidar, cam_left, cam_right, cam_front]

        collection = MeasurementCollection([gps, can_0, lidar, cam_left, cam_right, cam_front])
        collection.synchronize()

    def _generator():
        est_yaw = 0
        est_speed = 0
        behind_gps_buf = deque([])
        ahead_gps_buf = deque([])

        for step in itertools.count():
            try:
                with profile.ctx('advance'):
                    for source in to_sync:
                        with profile.ctx(str(source)):
                            source.advance()
                
                ts = max(source.ts for source in to_sync)
                collection.synchronize(to=ts)
            except SourceEmpty:
                break

            input_data = make_input_data(step)

            with profile.ctx('gps'):
                N, E, _ = pymap3d.geodetic2ned(gps.value.lat, gps.value.lon, 0, gps_lat0, gps_lon0, 0)
                carla_lat = N / 111324.60662786
                carla_lon = E / 111319.490945
                
                # Find points behind and ahead of us within distance (0.5, 1) meters
                NE = np.array((N, E))
                gps_min_dist = 0.5
                gps_max_dist = 1

                behind_gps_buf = []
                for i in range(-1, -gps.index, -1):
                    peek_gps = gps.peek(i)
                    peek_NE = pymap3d.geodetic2ned(peek_gps.value.lat, peek_gps.value.lon, 0, gps_lat0, gps_lon0, 0)[:2]
                    peek_dist = np.linalg.norm(peek_NE - NE)
                    if peek_dist < gps_min_dist:
                        continue
                    if peek_dist > gps_max_dist:
                        break
                    behind_gps_buf.append(peek_NE)

                ahead_gps_buf = []
                for i in itertools.count(1):
                    try:
                        peek_gps = gps.peek(i)
                    except SourceEmpty:
                        break
                    peek_NE = pymap3d.geodetic2ned(peek_gps.value.lat, peek_gps.value.lon, 0, gps_lat0, gps_lon0, 0)[:2]
                    peek_dist = np.linalg.norm(peek_NE - NE)
                    if peek_dist < gps_min_dist:
                        continue
                    if peek_dist > gps_max_dist:
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

            input_data['gps'][1] = [carla_lat, carla_lon, 0]
            input_data['imu'][1] = [est_yaw]
            input_data['speed'][1] = { 'speed': est_speed }

            ## RGB
            input_data['rgb_left'][1] = prepare_image(cam_left.value.frame, (40, 30, 1.33))
            input_data['rgb_front'][1] = prepare_image(cam_front.value.frame, (0, 0, 1.21))
            input_data['rgb_right'][1] = prepare_image(cam_right.value.frame, (-228, 38, 1.33))

            ## Lidar
            lidar_data = lidar.value.cartesian.reshape(-1, 3)
            lidar_data[:,[0,1]] = lidar_data[:,[1,0]]
            lidar_data[:, 2] -= 0.8
            input_data['lidar'][1] = lidar_data 

            ## Output data
            output_data = can_0.value[1]

            yield gps.ts, step, input_data, output_data
    
    return profile.iterable('gen_input_data', _generator())


@profile.func
def print_input_data(step, input_data):
    print(f'{step}:')
    print('gps:', np.array(input_data['gps'][1][:2]) * [111324.60662786, 111319.490945])
    print('speed:', input_data['speed'][1]['speed'] * 3.6)
    print('imu:', input_data['imu'][1][0] * 180 / np.pi)


@profile.func
def print_agent_data(step, agent, action):
    pred_wp = agent.pred_wp
    route = agent._route_planner.route

    # target = pred_wp[0] + pred_wp[1]
    # angle = atan2(target[1], target[0]) * 180 / np.pi
    
    print(f'{step}: {action}')
    print(pred_wp)

    table = Table(show_header=True)
    table.add_column('N')
    table.add_column('E')
    for (lat, lon), _ in itertools.islice(route, 3):
        table.add_row(str(lat), str(lon))
    rich.print(table)


def prepare_image(img, transform: Tuple[int, int, float]):
    pil = Image.fromarray(img)
    ox, oy, s = transform
    x = pil.width//2 + ox
    y = pil.height//2 + oy
    w = int(pil.width * s)
    h = int(pil.height * s)
    box = (x - w//2, y - h//2, x + w//2, y + h//2)
    pil = pil.crop(box)
    pil = pil.resize((960, 480), Image.BILINEAR)
    img = np.asarray(pil)
    return img


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            main(*sys.argv[1:])
