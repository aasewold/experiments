from typing import Tuple, Dict, List
from dataclasses import dataclass
from pathlib import Path
from logging import getLogger
import subprocess
import numpy as np
from numpy.typing import NDArray
import queue
import ffmpeg
import threading

from src import profile
from src.measurements import Measurement, IteratorSource, NamedSource


@dataclass
class CameraData:
    frame: NDArray[np.uint8]


def make_camera(path: Path, resolution: Tuple[int, int] = (1920, 1208)):
    log = getLogger('camera.' + path.stem)

    w, h = resolution

    log.info(f'Reading camera {path} at {w}x{h}')
    
    video_cmd = (
        ffmpeg
        .input(str(path))
        .video
        .output('pipe:', format='rawvideo', pix_fmt='bgr24', s=f'{w}x{h}')
        .compile()
    )

    video = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    data_queue = queue.Queue(maxsize=2)
    def _read():
        while True:
            in_bytes = video.stdout.read(w * h * 3)  # type: ignore
            if not in_bytes:
                break
            data_queue.put(in_bytes)
        log.info('Reader thread exiting')
        data_queue.put(None)
    thread = threading.Thread(target=_read, daemon=True)
    thread.start()

    timestamp_path = str(path) + '.timestamps'
    try:
        timestamps = open(timestamp_path, 'r')
    except Exception:
        log.error(f'Could not open timestamps file {timestamp_path}')
        raise
    
    def generator():
        try:
            while True:
                with profile.ctx('camera wait'):
                    in_bytes = data_queue.get()

                if not in_bytes:
                    break

                with profile.ctx('camera decode'):
                    frame = (
                        np
                        .frombuffer(in_bytes, np.uint8)
                        .reshape([h, w, 3])
                    )

                with profile.ctx('camera process'):
                    ts_line = timestamps.readline().strip()
                    ts_ms = int(ts_line.split()[-1]) / 1e3

                yield Measurement(ts_ms, CameraData(frame / 255.0))

        finally:
            log.info('Killing ffmpeg')
            video.kill()
            video.wait()

    return NamedSource(
        name=path.stem,
        inner=IteratorSource(generator())
    )
