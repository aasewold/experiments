from contextlib import suppress
from itertools import count
from pathlib import Path
import sys

from src import profile
from src.measurements import MeasurementCollection
from src.measurements import SingleBufferSource
from src.nap.kia.camera import make_camera, CameraData
from src.nap.kia.gps import make_gps, GpsData


def main(trip: str):
    dir = Path(f'/dataset/{trip}')

    with profile.scope('setup', dump=False):
        cam_c1 = make_camera(dir / 'C1_front60Single.h264')
        cam_c2 = make_camera(dir / 'C2_tricam60.h264')
        cam_c3 = make_camera(dir / 'C3_tricam120.h264')
        cam_c4 = make_camera(dir / 'C4_rearCam.h264')
        gps = make_gps(dir / 'gnss50_vehicle.bin')
        
        # The SingleBufferSource will cause the camera to synchronize to the frame closest in time
        # to the GPS timestamp. The alternative is to just use the camera source itself,
        # in which case you will get the first frame after the GPS timestamp.
        #   Also, MeasurementCollection should probably be named SourceCollection,
        # but whatever. It's used to synchronize multiple sources together.
        cameras = MeasurementCollection([
            SingleBufferSource(c)
            for c in [cam_c1, cam_c2, cam_c3, cam_c4]
        ])

    for _ in count():
        with profile.ctx('advance'):
            # Advance to the next GPS frame,
            gps.advance()
            # Then synchronize the cameras to that frame
            cameras.synchronize(to=gps.ts)

        # gps.value is GpsData
        # cam_c1.value is CameraData

        with profile.ctx('process'):
            print(f'GPS: {gps.ts:.3f} {gps.value.lat:.3f} {gps.value.lon:.3f} {gps.value.alt:.1f}')
            print(f'Cam C1: {cam_c1.ts:.3f} {cam_c1.value.frame.shape}')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        # This profiling code is just used to record and print where your code spends time.
        with profile.scope('main', dump=True):
            main(*sys.argv[1:])
