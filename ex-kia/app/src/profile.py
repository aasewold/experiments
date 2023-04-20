from collections import defaultdict
from dataclasses import dataclass
import time
from typing import Any, Dict, Tuple, List, Callable, Iterable, TypeVar
from contextlib import contextmanager
from functools import wraps

from rich import print
from rich.table import Table


@dataclass
class _Stats:
    count: int = 0
    tot_ns: int = 0


DataDict = Dict[Tuple[str, ...], _Stats]

_data: DataDict = defaultdict(_Stats)
_ctx: List[str] = []


@contextmanager
def ctx(name: str):
    _ctx.append(name)
    path = tuple(_ctx)
    entry = _data[path]
    start = time.monotonic_ns()
    try:
        yield
    finally:
        end = time.monotonic_ns()
        ns = end - start
        entry.count += 1
        entry.tot_ns += ns
        _ctx.pop()


_F = TypeVar('_F', bound=Callable[..., Any])
def func(f: _F) -> _F:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Dict[str, Any]):
        with ctx(f.__name__):
            return f(*args, **kwargs)
    return wrapper  # type: ignore


_T = TypeVar('_T')
def iterable(name: str, iterable: Iterable[_T]) -> Iterable[_T]:
    iterator = iter(iterable)
    while True:
        with ctx(name):
            val = next(iterator)
        yield val


@contextmanager
def scope(name: str, *, dump: bool = False):
    global _data
    old_data = _data
    _data = defaultdict(_Stats)
    try:
        yield
    finally:
        if dump:
            _dump(_data, title=f'Profile: {name}')
        _data = old_data


def _dump(data: DataDict, title: str):
    table = Table(title=title)
    table.add_column('Path', justify='left')
    table.add_column('Count', justify='right')
    table.add_column('Time (ms, total)', justify='right')
    table.add_column('Time (ms, per call)', justify='right')
    for path, stats in data.items():
        disp = ' -> '.join(path)
        table.add_row(disp, str(stats.count), f'{stats.tot_ns / 1e6:.2f}ms', f'{stats.tot_ns / stats.count / 1e6:.2f}ms')
    print(table)
