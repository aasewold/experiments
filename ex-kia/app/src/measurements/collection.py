from typing import Any, Optional, Tuple, List

from logging import getLogger
_log = getLogger(__name__)

from src import profile
from .measurement import Measurement
from .source import MeasurementSource


class MeasurementCollection:
    """Provides synchronized access to a collection of measurements from multiple sensors."""

    def __init__(self, sources: List[MeasurementSource[Any]]) -> None:
        self._sources = tuple(sources)

    @property
    def current(self) -> Tuple[Measurement[Any], ...]:
        return tuple(source.current for source in self._sources)
    
    @profile.func
    def advance(self):
        for source in self._sources:
            with profile.ctx(f'sensor.{id(source)}.{str(source)}'):
                source.advance()
    
    @profile.func
    def synchronize(self, to: Optional[float] = None):
        if to is None:
            ts = max(source.ts for source in self._sources)
        else:
            ts = to

        min_ts, max_ts = ts, ts

        for source in self._sources:
            with profile.ctx(f'sensor.{id(source)}.{str(source)}'):
                source.advance_to(ts)
            min_ts = min(min_ts, source.ts)
            max_ts = max(max_ts, source.ts)

        details = '\n'.join(f'\t{str(source):40s}: {source.ts:.3f} (diff={source.ts - ts:+.3f})' for source in self._sources)
        _log.info('Synchronized sources to %.3f range=%.3f:\n%s', ts, max_ts - min_ts, details)

    def __iter__(self):
        while True:
            self.advance()
            yield self.current
