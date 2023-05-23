import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Tuple, TypeVar, List
import numpy as np
import numpy.typing as npt
import pymap3d

from src import profile
from src.util import cached_property
from src.measurements import Measurement, IteratorSource, NamedSource


def _avg_none(args: Iterable[Optional[float]]) -> Optional[float]:
    vals = [a for a in args if a is not None]
    if vals:
        return sum(vals) / len(vals)
    else:
        return None


@dataclass
class GpsData:
    index: int
    lat: float
    lon: float
    alt: float
    speed: Optional[float]
    course: Optional[float]
    hdop: Optional[float]
    vdop: Optional[float]
    gps0: Optional[Tuple[float, float]] = None

    @classmethod
    @profile.func
    def average(cls, datas: List['GpsData']) -> 'GpsData':
        return cls(
            index=datas[0].index,
            lat=sum(d.lat for d in datas) / len(datas),
            lon=sum(d.lon for d in datas) / len(datas),
            alt=sum(d.alt for d in datas) / len(datas),
            speed=_avg_none(d.speed for d in datas),
            course=_avg_none(d.course for d in datas),
            hdop=_avg_none(d.hdop for d in datas),
            vdop=_avg_none(d.vdop for d in datas),
            gps0=next((d.gps0 for d in datas if d.gps0 is not None), None),
        )
    
    def is_zero(self) -> bool:
        return self.lat == 0 and self.lon == 0 and self.alt == 0
    
    @cached_property
    @profile.func
    def NED(self) -> npt.NDArray[np.float64]:
        if self.gps0 is None:
            raise ValueError('gps0 is None')
        return np.array(pymap3d.geodetic2ned(self.lat, self.lon, 0, *self.gps0, 0))

    @property
    def NE(self) -> npt.NDArray[np.float64]:
        return self.NED[:2]


_I = TypeVar('_I')
_O = TypeVar('_O')

def _maybe(callable: Callable[[_I], _O]) -> Callable[[Optional[_I]], Optional[_O]]:
    def fn(arg: Optional[_I]) -> Optional[_O]:
        if arg is None:
            return None
        return callable(arg)
    return fn

# Example GPS data:
# GPS[0] - 1632734433978185 lat: 63.41962726 lon: 10.401724 alt: 86.47
# GPS[1] - 1632734433978185 lat: 63.41962726 lon: 10.401724 alt: 86.47
# GPS[0] - 1632734434279185 lat: 63.41962724 lon: 10.40172408 alt: 86.5 course: 0 speed: 0.01028888889 hdop: 0.9 vdop: 1.5
# GPS[1] - 1632734434279185 lat: 63.41962724 lon: 10.40172408 alt: 86.5 course: 0 speed: 0.01028888889 hdop: 0.9 vdop: 1.5


re_int = r'\d+'
re_float = r'\d+(?:\.\d+)?'
re_gps = re.compile(rf'GPS\[({re_int})\] - ({re_int}) lat: ({re_float}) lon: ({re_float}) alt: ({re_float})(?: course: ({re_float}) speed: ({re_float}) hdop: ({re_float}) vdop: ({re_float}))?')

def make_gps(path: Path):
    def generator():
        with path.open('rt') as f:
            for line in f:
                match = re_gps.match(line)
                if match:
                    index, ts, lat, lon, alt, *rest = match.groups()

                    index = int(index)
                    ts = int(ts) / 1000.0
                    lat = float(lat)
                    lon = float(lon)
                    alt = float(alt)
                    course, speed, hdop, vdop = map(_maybe(float), rest)

                    yield Measurement(ts, GpsData(index, lat, lon, alt, speed, course, hdop, vdop))
    
    return NamedSource(
        name=path.stem,
        inner=IteratorSource(generator())
    )
