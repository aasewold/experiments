from dataclasses import dataclass
from typing import Generic, TypeVar


_T = TypeVar('_T')


@dataclass
class Measurement(Generic[_T]):
    ts: float   # timestamp in milliseconds
    value: _T
