from typing import Generic, Optional, TypeVar, List, Dict

from .measurement import Measurement


_T = TypeVar('_T')


class MeasurementBuffer(Generic[_T]):
    _buffer: Dict[float, Measurement[_T]]

    def __init__(self):
        self._buffer = {}

    @property
    def min_ts(self) -> float:
        return min(self._buffer.keys(), default=0)
    
    @property
    def max_ts(self) -> float:
        return max(self._buffer.keys(), default=0)
    
    def __getitem__(self, ts: float) -> Measurement[_T]:
        return self._buffer[ts]
    
    def get(self, ts: float) -> Optional[Measurement[_T]]:
        """Get the measurement at the given timestamp or raises KeyError."""
        return self._buffer.get(ts, None)

    def get_range(self, start: float, end: float) -> List[Measurement[_T]]:
        """Get all measurements in the given range, inclusive of start and exclusive of end."""
        return [value for ts, value in self._buffer.items() if start <= ts < end]
    
    def get_closest(self, timestamp: float) -> Measurement[_T]:
        if not self._buffer:
            raise KeyError('No measurements in buffer.')
        key = min(self._buffer.keys(), key=lambda ts: abs(ts - timestamp))
        return self._buffer[key]

    def pop(self, ts: float) -> Measurement[_T]:
        """Get the measurement at the given timestamp and remove it from the buffer or raises KeyError."""
        return self._buffer.pop(ts)
    
    def append(self, measurement: Measurement[_T]):
        if measurement.ts <= self.max_ts:
            raise ValueError('Measurements must be added chronologically')
        self._buffer[measurement.ts] = measurement

    def prune(self, ts: float):
        """Remove all measurements older than the given timestamp."""
        keys = [key for key in self._buffer.keys() if key < ts]
        for key in keys:
            del self._buffer[key]