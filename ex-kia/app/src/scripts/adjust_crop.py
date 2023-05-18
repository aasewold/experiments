import sys
from contextlib import suppress
from pathlib import Path
from typing import Any, List, Tuple

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

from src import profile
from src.measurements.collection import MeasurementCollection
from src.nap.kia.camera import make_camera, CameraData

from .transfuser import tf_process_image


def main(trip: str):
    dir = Path(f"/dataset/{trip}")
    camera_paths = sorted(dir.glob("*.h264"))
    # get selected cameras from user
    for i, path in enumerate(camera_paths):
        print(f"{i}: {path}")
    print("Select cameras to use (comma separated):")
    selected_cameras = [camera_paths[int(x)] for x in '6,2,7'.split(',')] #input().split(",")]

    with profile.scope("setup", dump=False):
        cameras = [make_camera(path) for path in selected_cameras]
    
    collection = MeasurementCollection(cameras)
    collection.synchronize()

    camera_index = 0
    mode = 'move'

    crops = [
        (40, 30, 1.33),
        (0, 0, 1.21),
        (-228, 38, 1.33)
    ]

    step = 10

    while True:
        images = [camera.value for camera in cameras]
        img = make_image(images, crops)
        img.save('/work/crop.png')

        print(f'camera: {camera_index}')
        print(f'crop: {crops[camera_index]}')
        print(f'mode: {mode}')
        print(f'step: {step}')

        print('> ', end='')
        cmd = sys.stdin.read(1)
        print(cmd)

        if cmd == 'r':
            if mode == 'move':
                mode = 'resize'
            else:
                mode = 'move'
    
        if cmd in [str(i) for i in range(len(cameras))]:
            camera_index = int(cmd)

        if cmd == 'q':
            step //= 10
        if cmd == 'e':
            step *= 10
        step = max(1, step)

        if cmd == 'p':
            for camera in cameras:
                camera.advance_n(step)
            collection.synchronize()
        
        x, y, s = crops[camera_index]
        if mode == 'move':
            if cmd == 'w':
                y += step
            if cmd == 'a':
                x += step
            if cmd == 's':
                y -= step
            if cmd == 'd':
                x -= step
        if mode == 'resize':
            if cmd == 'a':  
                s /= 1.1
            if cmd == 'd':
                s *= 1.1
        crops[camera_index] = (x, y, s)  # type: ignore


def make_image(cameras: List[CameraData], crops: List[Tuple[int, int, float]]):
    images = []
    for cam, transform in zip(cameras, crops):
        img = tf_process_image(cam.frame, transform)
        img = img[160:320, 320:640]
        images.append(img)
    combined = np.hstack(images)[:,:,::-1]
    return Image.fromarray(combined)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        with profile.scope("main", dump=True):
            main(*sys.argv[1:])
