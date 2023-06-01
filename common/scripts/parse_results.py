#!/usr/bin/env python3
"""
Parse results from evaluation runs.
Run the script with a path to a directory, and optionally a list of filters.
The script will find all runs within the directory, and print the results.

Filters are checked for substring match agains each run, and are combined
by logical and. Filters separated by ',' are combined by logical or.
Negate filters by prefixing them with a slash.

Example: ./common/scripts/parse_results.py . transfuser longest6 /old
"""

import sys
import json
import typing as t
import itertools
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultKey:
    carla_version: str
    benchmark: str
    agent: str
    weights: str
    actors: str

    def __str__(self):
        res = ""
        res += f"{self.carla_version} "
        res += f"{self.benchmark:<8} "
        res += f"(a={self.actors})".ljust(8)
        res += f":  {self.agent} {self.weights}"
        return res


@dataclass(frozen=True)
class Result:
    run: str
    p_current: int
    p_total: int
    values: t.Tuple[float, ...]
    ignored: bool

    @property
    def complete(self) -> bool:
        return bool(self.values) and self.p_current == self.p_total

    @property
    def DS(self) -> float:
        return self.values[0]
    
    @property
    def RC(self) -> float:
        return self.values[1]
    
    @property
    def IS(self) -> float:
        return self.values[2]
    
    def __str__(self):
        name = f"{self.run:>20} ({self.p_current:>2}/{self.p_total:>2}): "
        if self.complete:
            vals = ' '.join(f"{v:>5.2f}" for v in self.values[3:])
            score = f"{self.DS:>5.0f}% {self.RC:>5.0f}% {self.IS:>6.0%} | {vals}"
        else:
            score = 'incomplete'
        if self.ignored:
            score += ' (ignored)'
        return name + score
               


def main(topdir: Path, *filters: str):
    if not topdir.is_dir():
        print(f'"{topdir}" is not a directory')
        sys.exit(1)
    jsons = list(topdir.absolute().rglob("*.json"))
    results = list(filter(None, map(process_json, jsons)))
    print_results(results, filters)


def process_json(path: Path):
    try:
        if 'results' not in path.parts:
            return None

        k = parse_key(path)
        v = parse_results(path)
        return k, v
    except TypeError as e:
        print(f"Failed to parse {path}: {e}")
        return None


def parse_key(path: Path):
    benchmark = path.stem.split('fuser_')[-1]
    ir = path.parts.index('results')
    weights = path.parts[ir + 1]
    _, agent, carla_version = path.parts[ir - 1].split('-')
    actors = find_actor_amount(path)
    return ResultKey(carla_version, benchmark, agent, weights, actors)


def parse_results(path: Path) -> Result:
    run = path.parts[-2]
    with path.open() as f:
        data = json.load(f)
        p_current, p_total = data['_checkpoint']['progress'] or (0, 0)
        values = tuple(map(float, data['values']))
    ignored = path.with_name('ignore').exists()
    return Result(run, p_current, p_total, values, ignored)


def find_actor_amount(path: Path) -> str:
    path = path.with_name('log.txt')
    if not path.exists():
        return '?'
    
    amounts: t.Set[str] = set()
    with path.open() as f:
        for line in f:
            if line.startswith("ACTOR_AMOUNT="):
                amounts.add(line.split('=')[1].strip())
    if len(amounts) > 1:
        raise ValueError(f"Found multiple actor amounts in {path}: {amounts}")
    if len(amounts) == 0:
        return '?'
    return amounts.pop()


def average_results(results: t.List[Result]) -> Result:
    return Result('avg', 0, 0, tuple(sum(x) / len(x) for x in zip(*map(lambda x: x.values, results))), False)


def print_results(results: t.List[t.Tuple[ResultKey, Result]], filters: t.Tuple[str]):
    all_matches: t.List[Result] = []
    num_tot = 0

    if not 'ignored' in filters:
        num_ignored = len(list(filter(lambda x: x[1].ignored, results)))
        results = list(filter(lambda x: not x[1].ignored, results))
    else:
        num_ignored = 0

    results = sorted(results, key=lambda x: str(x[0]))
    for key, group in itertools.groupby(results, lambda x: x[0]):
        key_str = str(key)
        items = sorted([r for _, r in group], key=lambda x: x.run)
        num_tot += len(items)

        items = list(filter(lambda x: check_filters(f'{key_str}|{x}', filters), items))
        if not items:
            continue

        print(f"{key}:")
        for result in items:
            print(f"\t{result}")

        complete_items = [r for r in items if r.complete]
        if len(complete_items) > 1:
            print(f"\t{average_results(complete_items)}")
        
        all_matches.extend(complete_items)
    
    num_match = len(all_matches)
    print(f"\nMatched {num_match} of {num_tot} runs ({num_ignored} ignored)")
    if num_match > 1:
        print(f"Average of all matches:")
        print(f"\t{average_results(all_matches)}")


def check_filters(key: str, filters: t.Tuple[str]):
    if not filters:
        return True
    
    for f in filters:
        match = False
        for f in f.split(','):
            neg = f.startswith('/')
            if neg:
                f = f[1:]
            if neg and f not in key:
                match = True
            if not neg and f in key:
                match = True
        if not match:
            return False

    return True


if __name__ == "__main__":
    if not sys.argv[1:]:
        print(f"Usage: {sys.argv[0]} <path> [filters...]\n{__doc__}")
        sys.exit(1)
    main(Path(sys.argv[1]), *sys.argv[2:])
