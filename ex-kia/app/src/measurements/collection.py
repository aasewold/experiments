from typing import Any, Optional, Tuple, List, Generic, TypeVar

from logging import getLogger
_log = getLogger(__name__)

from src import profile
from .measurement import Measurement
from .source import MeasurementSource, SourceEmpty


_T = TypeVar('_T')


class MeasurementCollection(Generic[_T]):
    """Provides synchronized access to a collection of measurements from multiple sensors."""

    def __init__(self, sources: List[MeasurementSource[_T]]) -> None:
        self._sources = tuple(sources)

    @property
    def current(self) -> Tuple[Measurement[_T], ...]:
        return tuple(source.current for source in self._sources)
    
    @property
    def min_ts(self) -> float:
        return min(source.ts for source in self._sources)
    
    @property
    def max_ts(self) -> float:
        return max(source.ts for source in self._sources)
    
    @profile.func
    def advance(self):
        for source in self._sources:
            with profile.ctx(f'sensor.{id(source)}.{str(source)}'):
                source.advance()
    
    @profile.func
    def synchronize(self, to: Optional[float] = None):
        if to is None:
            ts = self.max_ts
        else:
            ts = to

        for source in self._sources:
            with profile.ctx(f'sensor.{id(source)}.{str(source)}'):
                source.advance_to(ts)

        details = '\n'.join(f'\t{str(source):40s}: {source.ts:.3f} (diff={source.ts - ts:+.3f})' for source in self._sources)
        _log.info('Synchronized sources to %.3f range=%.3f:\n%s', ts, self.max_ts - self.min_ts, details)

    def iter_sync(self):
        while True:
            try:
                self.advance()
                self.synchronize()
            except SourceEmpty:
                break
            yield self.current
