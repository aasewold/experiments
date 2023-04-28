from contextlib import suppress
from itertools import count
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib.pyplot as plt


from src import profile
from src.nap.kia.camera import make_camera, CameraData
from src.nap.kia.lidar import make_lidar, LidarData
from src.nap.kia.gps import make_gps, GpsData


def iter_data():
    dir = Path('/dataset/Trip066')

    with profile.scope('setup', dump=False):
        gps = make_gps(dir / 'gnss50_vehicle.bin')
        lidar = make_lidar(
            dir / '2023-04-25-13-01-38_OS-2-128-992029000682-1024x10.pcap',
            first_ts=gps.ts
        )
        # cam_c1 = make_camera(dir / 'C1_front60Single.h264')
    
    series = {}
    
    for sensor in [gps, lidar]:
        key = str(sensor)
        print('Reading', key)
        values = [frame.ts for frame in sensor]
        values = np.array(values)
        print(f'{key}: {values[0]} - {values[-1]}')
        series[key] = values
    
    for i, (key, data) in enumerate(series.items()):
        plt.plot(data, np.full(len(data), i+1), label=key)
    plt.legend()
    plt.savefig('/work/plot.png', dpi=600)

    lidar_data = series[str(lidar)]
    gps_data = series[str(gps)]
    # cam_data = series[str(cam_c1)]

    l = min(len(lidar_data), len(gps_data))
    lidar_vs_gps = np.polyfit(gps_data[-l:], lidar_data[-l:], 1)
    print(f'Lidar-GPS fit: {lidar_vs_gps}')

    # l = min(len(lidar_data), len(cam_data))
    # lidar_vs_cam = np.polyfit(cam_data[-l:], lidar_data[-l:], 1)
    # print(f'Lidar-cam fit: {lidar_vs_cam}')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            iter_data()
