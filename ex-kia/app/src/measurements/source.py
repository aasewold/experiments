from typing import Any, Iterable, Iterator, Protocol, TypeVar

from .measurement import Measurement


_T = TypeVar('_T')


class MeasurementSource(Protocol[_T]):
    @property
    def current(self) -> Measurement[_T]:
        ...

    def advance(self):
        ...

    @property
    def ts(self) -> float:
        return self.current.ts

    @property
    def value(self) -> Any:
        return self.current.value

    def advance_n(self, n: int):
        for _ in range(n):
            self.advance()
    
    def advance_to(self, ts: float):
        while self.ts < ts:
            self.advance()

    def __iter__(self):
        while True:
            try:
                self.advance()
            except StopIteration:
                break
            yield self.current


class IteratorSource(MeasurementSource[_T]):
    _iterator: Iterator[Measurement[_T]]
    _current: Measurement[_T]

    def __init__(self, iterator: Iterator[Measurement[_T]]) -> None:
        self._iterator = iterator
        self._current = next(iterator)
    
    @property
    def current(self) -> Measurement[_T]:
        return self._current

    def advance(self):
        self._current = next(self._iterator)


class NamedSource(MeasurementSource[_T]):
    _name: str
    _inner: MeasurementSource[_T]

    def __init__(self, name: str, inner: MeasurementSource[_T]) -> None:
        self._name = name
        self._inner = inner
    
    @property
    def current(self) -> Measurement[_T]:
        return self._inner.current
    
    def advance(self):
        self._inner.advance()
    
    def __str__(self) -> str:
        return f'{self._name}'


class SingleBufferSource(MeasurementSource[_T]):
    _inner: MeasurementSource[_T]
    _prev: Measurement[_T]
    _is_prev: bool

    def __init__(self, inner: MeasurementSource[_T]) -> None:
        super().__init__()
        self._inner = inner
        self._prev = inner.current
        self._is_prev = False
    
    @property
    def current(self) -> Measurement[_T]:
        if self._is_prev:
            return self._prev
        else:
            return self._inner.current
    
    def advance(self):
        if self._is_prev:
            self._is_prev = False
        else:
            self._prev = self._inner.current
            self._inner.advance()

    def reverse(self):
        if self._is_prev:
            raise ValueError('Cannot reverse twice in a row')
        self._is_prev = True

    def advance_to(self, ts: float):
        prev_diff = abs(self.ts - ts)
        while self.ts < ts:
            self.advance()
            diff = abs(self.ts - ts)
            if diff > prev_diff:
                self.reverse()
                break
            prev_diff = diff

    def __str__(self) -> str:
        return f'{self._inner} (buffered)'


class GroupedSource(IteratorSource[Iterable[_T]]):
    _inner: MeasurementSource[_T]

    def __init__(self, inner: MeasurementSource[_T]) -> None:
        self._inner = inner
        super().__init__(self._group_generator())
    
    def _group_generator(self) -> Iterator[Measurement[Iterable[_T]]]:
        inner = self._inner
        exhausted = False

        def iter_group(ts: float):
            nonlocal exhausted
            while inner.ts == ts:
                yield inner.value
                try:
                    inner.advance() 
                except StopIteration:
                    exhausted = True
                    return
        
        while not exhausted:
            ts = inner.ts
            yield Measurement(ts, iter_group(ts))
    
    def __str__(self) -> str:
        return f'{self._inner} (grouped)'