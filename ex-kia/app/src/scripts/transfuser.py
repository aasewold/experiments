from collections import deque
import logging
import os

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
from src.measurements.source import IteratorSource, NamedSource, SingleBufferSource, SourceEmpty
from src.measurements.collection import MeasurementCollection
from src.nap.kia.gps import make_gps
from src.nap.kia.camera import make_camera
from src.nap.kia.lidar import make_lidar
from src.nap.kia.canbus import make_can

from team_code_transfuser.submission_agent import HybridAgent
from srunner.scenariomanager.timer import GameTime


WORK_PATH = Path('/work')
OUT_PATH = Path(os.environ['OUT_PATH'])


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

    gps_path = path / 'gnss50_vehicle.bin'

    def gps_wrapper():
        """Wraps the GPS sensor with persistent speed and yaw values."""
        course = 0
        speed = 0
        for val in make_gps(gps_path):
            if val.value.course is not None:
                course = val.value.course
            if val.value.speed is not None:
                speed = val.value.speed
            val.value.course = course
            val.value.speed = speed
            yield val

    lidar_path, = path.glob('*.pcap')
    if lidar_path.with_suffix('.offset').exists():
        lidar_offset = int(lidar_path.with_suffix('.offset').read_text())
    else:
        lidar_offset = 0

    with profile.scope('setup', dump=True):
        gps = NamedSource(name=gps_path.stem, inner=SingleBufferSource(IteratorSource(gps_wrapper())))
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
        prev_gps = deque([])

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

            ## GPS
            N, E, _ = pymap3d.geodetic2ned(gps.value.lat, gps.value.lon, 0, gps_lat0, gps_lon0, 0)
            carla_lat = N / 111324.60662786
            carla_lon = E / 111319.490945
            
            # Keep the GPS history buffer one meter long
            NE = np.array((N, E))
            gps_dist = 1
            while (
                len(prev_gps) > 1 
                and np.linalg.norm(prev_gps[1] - NE) >= gps_dist
            ):
                prev_gps.popleft()
            
            # Calculate the yaw from the GPS position one meter ago
            if prev_gps:
                dN, dE = NE - prev_gps[0]
                est_yaw = np.arctan2(dE, dN)
            prev_gps.append(NE)

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
            input_data['rgb_left'][1] = crop(cam_left.value.frame)
            input_data['rgb_right'][1] = crop(cam_right.value.frame)
            input_data['rgb_front'][1] = crop(cam_front.value.frame)

            ## Lidar
            lidar_data = lidar.value.cartesian.reshape(-1, 3)
            lidar_data[:,[0,1]] = lidar_data[:,[1,0]]
            lidar_data[:, 2] -= 0.7
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
    
    print(f'{step}: {action}')
    print(pred_wp)

    table = Table(show_header=True)
    table.add_column('N')
    table.add_column('E')
    for (lat, lon), _ in itertools.islice(route, 3):
        table.add_row(str(lat), str(lon))
    rich.print(table)


def crop(img):
    pil = Image.fromarray(img)
    pil = pil.resize((960, 480), Image.BILINEAR)
    img = np.asarray(pil)
    return img


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            main(*sys.argv[1:])
