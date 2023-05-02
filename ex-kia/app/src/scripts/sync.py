import sys
from contextlib import suppress
from itertools import count
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

from src import profile
from src.measurements.buffer import MeasurementBuffer
from src.nap.kia.camera import make_camera, CameraData
from src.nap.kia.lidar import make_lidar, LidarData
from src.nap.kia.gps import make_gps, GpsData


def main(trip: str):
    dir = Path(f"/dataset/{trip}")

    lidar_path, = dir.glob("*.pcap")
    if lidar_path.with_suffix(".offset").exists():
        lidar_offset = int(lidar_path.with_suffix(".offset").read_text())
    else:
        lidar_offset = 0

    with profile.scope("setup", dump=False):
        s_cam_c1 = make_camera(dir / 'C1_front60Single.h264')
        ts0 = s_cam_c1.ts
        s_lidar = make_lidar(lidar_path, first_ts=ts0)

    buf_cam = MeasurementBuffer[CameraData]()
    buf_lidar = MeasurementBuffer[LidarData]()

    buf_cam.append(s_cam_c1.current)
    buf_lidar.append(s_lidar.current)

    def fill_buffers(ts: float):
        while buf_cam.max_ts < ts:
            s_cam_c1.advance()
            buf_cam.append(s_cam_c1.current)

        while buf_lidar.max_ts < ts:
            s_lidar.advance()
            buf_lidar.append(s_lidar.current)

    ts = s_cam_c1.ts
    offset = lidar_offset

    step = 100
    
    while True:
        fill_buffers(max(ts, ts+abs(offset)))

        cam = buf_cam.get_closest(ts)
        lidar = buf_lidar.get_closest(ts - offset)
        
        print(f"ts   : {ts}\ncam  : {cam.ts}\nlidar: {lidar.ts}")

        lidar_data = lidar.value.cartesian.reshape(-1, 3).copy()
        lidar_data[:,[0,1]] = lidar_data[:,[1,0]]
        lidar_data[:, 1] *= -1
        lidar_data[:, 2] -= 0.7
        lidar_data = lidar_to_histogram_features(lidar_data)
        lidar_data = lidar_data.transpose(1, 2, 0)
        lidar_data = np.pad(lidar_data, ((0, 0), (0, 0), (0, 1)), constant_values=0)
        lidar_data = (lidar_data * 255).astype(np.uint8)

        img_cam = Image.fromarray(cam.value.frame).resize((640, 480))
        img_lidar = Image.fromarray(lidar_data).resize((640, 480))

        img = Image.new('RGB', (640, 960))
        img.paste(img_cam, (0, 0))
        img.paste(img_lidar, (0, 480))
        img.save('/work/sync.png')
        
        print('> ', end='')
        cmd = sys.stdin.read(1)
        print(cmd)
        if cmd == "q":
            break
        if cmd == 'w':
            offset += step
        if cmd == 's':
            offset -= step
        if cmd == 'a':
            ts -= step
        if cmd == 'd':
            ts += step
        if cmd == 'z':
            step /= 10
        if cmd == 'x':
            step *= 10

        print(f"ts={ts-ts0:.3f} offset={offset:.3f} step={step:.3f}")


def lidar_to_histogram_features(lidar):
    """
    Convert LiDAR point cloud into 2-bin histogram over 256x256 grid
    """
    def splat_points(point_cloud):
        # 256 x 256 grid
        pixels_per_meter = 8
        hist_max_per_pixel = 5
        x_meters_max = 16
        y_meters_max = 16
        xbins = np.linspace(-x_meters_max, x_meters_max, 32*pixels_per_meter+1)
        ybins = np.linspace(-y_meters_max, y_meters_max, 32*pixels_per_meter+1)
        hist = np.histogramdd(point_cloud[..., :2], bins=(xbins, ybins))[0]
        hist[hist>hist_max_per_pixel] = hist_max_per_pixel
        overhead_splat = hist/hist_max_per_pixel
        return overhead_splat

    below = lidar[lidar[...,2]<=-2.3]
    above = lidar[lidar[...,2]>-2.3]
    below_features = splat_points(below)
    above_features = splat_points(above)
    features = np.stack([above_features, below_features], axis=-1)
    features = np.transpose(features, (2, 0, 1)).astype(np.float32)
    features = np.rot90(features, -1, axes=(1,2)).copy()
    return features


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        with profile.scope("main", dump=True):
            main(*sys.argv[1:])
