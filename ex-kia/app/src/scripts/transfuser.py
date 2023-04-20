from collections import deque
import logging

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

from src import profile
from src.measurements.source import IteratorSource, NamedSource, SingleBufferSource
from src.measurements.collection import MeasurementCollection
from src.nap.kia.gps import make_gps
from src.nap.kia.camera import make_camera
from src.nap.kia.lidar import make_lidar
from src.nap.kia.canbus import make_can

from team_code_transfuser.submission_agent import HybridAgent
from srunner.scenariomanager.timer import GameTime



class RoadOption(enum.Enum):
    UNUSED = 0
    

def main(data_path: str):
    
    _log.info('Loading global plan')
    csv = np.genfromtxt('/work/plan.csv', delimiter=',', names=True)
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
        Path(data_path),
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

    for ts, step, input_data, output_data in input_data_gen:

        GameTime._init = True
        GameTime._last_frame = step
        GameTime._carla_time = ts / 1000
        GameTime._current_game_time = ts / 1000
        GameTime._platform_timestamp = datetime.datetime.now()

        print_input_data(step, input_data)

        action = agent.run_step(input_data, step)

        print_agent_data(step, agent, action)


def make_input_data(step: int):
    with profile.ctx('make fake input data'):
        ex_lidar = [step, np.zeros((100, 4), dtype=float)]
        ex_rgb = [step, np.zeros((1208, 1920, 4), dtype=np.uint8)]
        ex_gps = [step, [0, 0, 0]] # lat, lon, alt?
        ex_speed = [step, { 'speed': 0 }]
        ex_imu = [step, [ 0 ]] # yaw probably

        return {
            'lidar': ex_lidar,
            'rgb_left': ex_rgb,
            'rgb_front': ex_rgb,
            'rgb_right': ex_rgb,
            'rgb_back': ex_rgb,
            'gps': ex_gps,
            'speed': ex_speed,
            'imu': ex_imu,
        }


def gen_input_data(path: Path, *, gps_lat0: float, gps_lon0: float):

    gps_path, = list(path.rglob('*gnss50*.txt'))
    # lidar_path, = list(path.rglob('*.pcap'))

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

    with profile.scope('setup', dump=True):
        gps = NamedSource(name=gps_path.stem, inner=SingleBufferSource(IteratorSource(gps_wrapper())))
        # can_0 = make_can(path / 'can_vehicle0.bin')
        cam_c1 = make_camera(path / 'C1_front60Single.h264')
        cam_c2 = make_camera(path / 'C2_tricam60.h264')
        cam_c3 = make_camera(path / 'C3_tricam120.h264')
        # cam_c4 = make_camera(path / 'C4_rearCam.h264')
        # lidar = make_lidar(lidar_path)

        to_sync = [cam_c1, cam_c2, cam_c3]

        collection = MeasurementCollection([gps, cam_c1, cam_c2, cam_c3])
        collection.synchronize()

    def _generator():
        est_yaw = 0
        est_speed = 0
        prev_gps = deque([], maxlen=100)

        for step in itertools.count():
            with profile.ctx('advance'):
                for source in to_sync:
                    with profile.ctx(str(source)):
                        source.advance()
            
            ts = max(source.ts for source in to_sync)
            collection.synchronize(to=ts)

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

            if gps.value.speed is not None:
                est_speed = gps.value.speed

            input_data['gps'][1] = [carla_lat, carla_lon, 0]
            input_data['imu'][1] = [est_yaw]
            input_data['speed'][1] = { 'speed': est_speed }

            ## RGB
            input_data['rgb_left'][1] = crop(cam_c1.value.frame)
            input_data['rgb_right'][1] = crop(cam_c2.value.frame)
            input_data['rgb_front'][1] = crop(cam_c3.value.frame)

            ## Lidar
            # lidar_data = lidar.value.cartesian.reshape(-1, 3)
            # lidar_data[:,[0,1]] = lidar_data[:,[1,0]]
            # input_data['lidar'][1] = lidar_data 

            ## Output data
            output_data = {
                # 'steer': can_0.value[1].steer,
                # 'throttle': can_0.value[1].throttle,
                # 'brake': can_0.value[1].brake,
            }

            yield gps.ts, step, input_data, output_data
    
    return profile.iterable('gen_input_data', _generator())


@profile.func
def print_input_data(step, input_data):
    print(f'{step}:')
    print('gps:', np.array(input_data['gps'][1][:2]) * [111324.60662786, 111319.490945])
    print('speed:', input_data['speed'][1]['speed'])
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


def crop(img, w=960, h=480):
    ph, pw = img.shape[:2]
    return img[(ph - h) // 2:(ph + h) // 2, (pw - w) // 2:(pw + w) // 2]


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            main(*sys.argv[1:])
