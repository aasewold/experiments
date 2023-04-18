from itertools import count
from pathlib import Path

from logging import getLogger
from typing import Any, Tuple, Dict, List
_log = getLogger(__name__)

import matplotlib.pyplot as plt

import numpy as np
from numpy.typing import NDArray
from scipy import signal

from src import profile
from src.measurements import MeasurementCollection
from src.measurements import SingleBufferSource
from .camera import make_camera, CameraData
from .lidar import make_lidar, LidarData
from .gps import make_gps, GpsData


class DiffPlotter:
    _data: Dict[str, Tuple[NDArray[Any], List[float], List[float]]]

    def __init__(self):
        self._data = {}
    
    def append(self, name: str, ts: float, data: NDArray[Any]):
        if name not in self._data:
            self._data[name] = (data, [], [])
        
        prev = self._data[name][0]
        
        self._data[name] = (data, self._data[name][1], self._data[name][2])
        self._data[name][1].append(ts)
        self._data[name][2].append(np.sqrt(np.mean((data - prev)**2)))
    
    def save(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        for name, (_, ts, diff) in self._data.items():
            ax.plot(ts, diff, label=name)
        fig.legend()
        ax.grid()
        ax.minorticks_on()
        fig.savefig(f'diff.png', dpi=300)

        # for name, (_, ts, diff) in self._data.items():
        #     with open(f'diff_{name}.csv', 'w') as f:
        #         f.write('ts,diff\n')
        #         for t, d in zip(ts, diff):
        #             f.write(f'{t},{d}\n')

    def merge(self, into: str, *series: str):
        if into not in self._data:
            self._data[into] = (np.empty(0), [], [])
        
        ts = 0
        value = 0
        for s in series:
            ts += self._data[s][1][-1]
            value += self._data[s][2][-1]
        ts /= len(series)

        self._data[into][1].append(ts)
        self._data[into][2].append(value)

    def analyze_lag(self, series1: str, series2: str):
        ts1, diff1 = self._data[series1][1:]
        ts2, diff2 = self._data[series2][1:]
        diff1 = np.array(diff1)
        diff2 = np.array(diff2)

        corr = signal.correlate(diff1, diff2, mode='full')
        lags = signal.correlation_lags(len(diff1), len(diff2), mode='full')
        lag = lags[np.argmax(corr)]

        ms1 = ts1[lag] - ts1[0]
        ms2 = ts2[lag] - ts2[0]
        print(f'{series1} - {series2} lag: {lag}, ms1: {ms1:.3f}, ms2: {ms2:.3f}')


def iter_data():
    dir = Path('/data/ad/recordings_DW/Trip001')

    with profile.scope('setup', dump=False):
        cam_c1 = make_camera(dir / 'C1_front60Single.h264')
        cam_c2 = make_camera(dir / 'C2_tricam60.h264')
        cam_c3 = make_camera(dir / 'C3_tricam120.h264')
        cam_c4 = make_camera(dir / 'C4_rearCam.h264')
        lidar = make_lidar(dir / 'OS-2-128-992029000682-1024x10.pcap', 
            ts_offset=1632131008789.2532,
        )
        
        sensors = [lidar, cam_c1, cam_c2, cam_c3, cam_c4]
        sensors = [SingleBufferSource[Any](s) for s in sensors]

        collection = MeasurementCollection(sensors)
        plotter = DiffPlotter()

    for _ in count():
        collection.advance()
        collection.synchronize()
        lid, c1, c2, c3, c4 = collection.current

        with profile.ctx('plot'):
            plotter.append('lidar', lid.ts, lid.value.ranges / 10000)
            plotter.append('cam_c1', c1.ts, c1.value.frame)
            plotter.append('cam_c2', c2.ts, c2.value.frame)
            plotter.append('cam_c3', c3.ts, c3.value.frame)
            plotter.append('cam_c4', c4.ts, c4.value.frame)
            plotter.merge('cam', 'cam_c1', 'cam_c2', 'cam_c3', 'cam_c4')
            plotter.save()
            plotter.analyze_lag('lidar', 'cam')
