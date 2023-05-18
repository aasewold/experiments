from typing import Any, Iterable, Iterator, List, TypeVar
try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol

from .measurement import Measurement


_T = TypeVar('_T')


class SourceEmpty(Exception):
    pass


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
    def value(self) -> _T:
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
            except SourceEmpty:
                break
            yield self.current


class WrappingSource(MeasurementSource[_T]):
    _inner: MeasurementSource[_T]

    def __init__(self, inner: MeasurementSource[_T]) -> None:
        self._inner = inner
    
    @property
    def current(self) -> Measurement[_T]:
        return self._inner.current
    
    def advance(self):
        self._inner.advance()

    def advance_n(self, n: int):
        self._inner.advance_n(n)
    
    def advance_to(self, ts: float):
        self._inner.advance_to(ts)


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
        try:
            self._current = next(self._iterator)
        except StopIteration:
            raise SourceEmpty


class NamedSource(WrappingSource[_T]):
    _name: str

    def __init__(self, name: str, inner: MeasurementSource[_T]) -> None:
        super().__init__(inner)
        self._name = name
    
    def __str__(self) -> str:
        return f'{self._name}'


class SingleBufferSource(WrappingSource[_T]):
    _prev: Measurement[_T]
    _is_prev: bool

    def __init__(self, inner: MeasurementSource[_T]) -> None:
        super().__init__(inner)
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
        while self.ts < ts:
            self.advance()
        
        if not self._is_prev and (
            abs(self._prev.ts - ts) < abs(self.ts - ts)
        ):
            self.reverse()

    def __str__(self) -> str:
        return f'{self._inner} (buffered)'


class BufferedSource(WrappingSource[_T]):
    _buffer: List[Measurement[_T]]
    _index: int

    def __init__(self, inner: MeasurementSource[_T]) -> None:
        super().__init__(inner)
        self._buffer = []
        self._index = 0
        self._fill_to_index(self._index)
    
    @property
    def index(self) -> int:
        return self._index
    
    @property
    def current(self) -> Measurement[_T]:
        return self._buffer[self._index]
    
    def advance(self):
        self._index += 1
        self._fill_to_index(self._index)

    def advance_to(self, ts: float):
        while self.ts < ts:
            self.advance()
        if self._index > 0 and abs(self.peek(-1).ts - ts) < abs(self.ts - ts):
            self.reverse()
    
    def reverse(self):
        if self._index <= 0:
            raise ValueError('Cannot reverse beyond 0')
        self._index -= 1

    def peek(self, n: int) -> Measurement[_T]:
        self._fill_to_index(self._index + n)
        return self._buffer[self._index + n]

    def _fill_to_index(self, index: int):
        while len(self._buffer) <= index:
            self._inner.advance()
            self._buffer.append(self._inner.current)
        
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
                except SourceEmpty:
                    exhausted = True
                    return
        
        while not exhausted:
            ts = inner.ts
            yield Measurement(ts, iter_group(ts))
    
    def __str__(self) -> str:
        return f'{self._inner} (grouped)'