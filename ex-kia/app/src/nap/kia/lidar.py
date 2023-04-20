from dataclasses import dataclass
from pathlib import Path
from logging import getLogger

import numpy as np
from numpy.typing import NDArray

from ouster.client import Scans, SensorInfo, ChanField, XYZLut
from ouster.pcap import Pcap

from src import profile
from src.measurements import Measurement, IteratorSource, NamedSource


@dataclass
class LidarTimesync:
    camera_epoch: int = 0
    lidar_epoch: int = 0
    lidar_scaler: float = 1


@dataclass
class LidarData:
    timestamps: NDArray[np.float64]
    ranges: NDArray[np.uint32]
    cartesian: NDArray[float]


def make_lidar(pcap_path: Path, ts_offset: float = 0):
    log = getLogger('lidar.' + pcap_path.stem)

    metadata_path = pcap_path.with_suffix('.json')
    log.info(f'Reading lidar metadata from {metadata_path}')
    with open(metadata_path, 'r') as f:
        metadata = SensorInfo(f.read())
    
    data = Pcap(str(pcap_path), metadata)
    scans = Scans(data)
    lut = XYZLut(metadata)

    def generator():
        try:
            for scan in profile.iterable('lidar read', scans):
                if not scan.complete():
                    log.debug('Skipping incomplete scan')
                    continue

                with profile.ctx('lidar process'):
                    ts_ms = scan.timestamp / 1e6 + ts_offset
                    ranges = scan.field(ChanField.RANGE)
                    cartesian = lut(ranges)

                yield Measurement(ts_ms[0], LidarData(ts_ms, ranges, cartesian))

        finally:
            log.info('Killing pcap')
            scans.close()
    
    return NamedSource(
        name=pcap_path.stem,
        inner=IteratorSource(generator())
    )
