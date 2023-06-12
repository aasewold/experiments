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
import math
import statistics as stats
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from dataclasses import dataclass


agent_names = {
    'transfuser': 'TF',
    'interfuser': 'IF',
}

model_names = {
    'prefuser': 'Pre-trained',
    'printerfuser': 'Pre-trained',
    'autopilot': 'Expert agent',
    'interfuser-kia-ds': 'ds-kia',
    'if-ds-custom': 'ds-custom',
    'transfuser-2023-03-08-epoch41': 'ds-feb',
    'tf-orig-ds-41': 'ds-orig',
}


def nanavg(xs: t.Iterable[float]) -> float:
    try:
        return stats.mean(xs)
    except stats.StatisticsError:
        return math.nan


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
    records: t.List[t.Tuple[float, float, float]]
    values: t.Tuple[float, ...]
    ignored: bool

    @property
    def complete(self) -> bool:
        return bool(self.records) and self.p_current == self.p_total

    @property
    def DS(self) -> float:
        return self.values[0]
    
    @property
    def RC(self) -> float:
        return self.values[1]
    
    @property
    def IS(self) -> float:
        return self.values[2]

    @property
    def RD(self) -> float:
        return self.values[9]
    
    @property
    def num_records(self) -> int:
        return len(self.records)
    
    def __str__(self):
        name = f"{self.run:>20} ({self.num_records:>2}/{self.p_total:>2}): "
        if self.complete:
            vals = ' &'.join(f"{v:>5.2f}" for v in (self.values[3:9] + self.values[10:]))
            score = f"{self.DS:>3.0f}\\% & {self.RC:>3.0f}\\% & {self.IS*100:>3.0f}\\% &{vals}"
            if self.RD > 0:
                score += f" (RD: {self.RD:>.2f})"
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
    groups, num_ignored = filter_and_group_results(results, filters)
    print_groups(groups, num_ignored)
    plot_groups(groups)


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
        records = parse_records(data['_checkpoint']['records'])
        values = tuple(map(float, data['values']))
        values = get_primary_scores(records) + values[3:]
    ignored = path.with_name('ignore').exists()
    return Result(run, p_current, p_total, records, values, ignored)


def get_primary_scores(records):
    return tuple(map(nanavg, zip(*records)))


def parse_records(json_records: t.List[t.Dict[str, t.Any]]):
    bad_statuses = {"Failed", "Failed - Agent couldn't be set up", "Failed - Agent crashed", "Failed - Simulation crashed"}
    # List of (DS, RC, IS) tuples
    records: t.List[t.Tuple[float, float, float]] = []
    for row in json_records:
        if row['status'] in bad_statuses:
            continue
        if row['meta']['duration_game'] < 1:
            continue
        s_ds = row['scores']['score_composed']
        s_rc = row['scores']['score_route']
        s_is = row['scores']['score_penalty']
        records.append((s_ds, s_rc, s_is))
    return records


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


def agg_results(results: t.List[Result], fn: t.Callable, name: str) -> Result:
    records = list(itertools.chain.from_iterable(r.records for r in results))
    aux_values = tuple(fn(x) for x in zip(*map(lambda x: x.values, results)))
    return Result(name, 0, 0, records, aux_values, False)


def filter_and_group_results(results: t.List[t.Tuple[ResultKey, Result]], filters: t.Tuple[str]):
    groups: t.List[t.Tuple[ResultKey, t.List[Result]]] = []
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
        if items:
            groups.append((key, items))
    
    return groups, num_ignored


def print_groups(groups: t.List[t.Tuple[ResultKey, t.List[Result]]], num_ignored: int):
    all_matches: t.List[Result] = []
    num_tot = 0

    for key, items in groups:
        num_tot += len(items)

        print(f"{key}:")
        for result in items:
            print(f"\t{result}")

        complete_items = [r for r in items if r.complete]
        if len(complete_items) > 1:
            print(f"\t{agg_results(complete_items, stats.mean, 'avg')}")
        
        all_matches.extend(complete_items)
    
    num_match = len(all_matches)
    print(f"\nMatched {num_match} of {num_tot} runs ({num_ignored} ignored)")
    if num_match > 1:
        print(f"Average of all matches:")
        print(f"\t{agg_results(all_matches, stats.mean, 'avg')}")
        print(f"\t{agg_results(all_matches, stats.stdev, 'std')}")


def plot_groups(groups: t.List[t.Tuple[ResultKey, t.List[Result]]]):
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.set_title("Driving Scores")
    ax.set_ylabel("Driving Score")
    ax.grid(True)

    lines = []

    for key, items in groups:
        items = [r for r in items if r.complete]
        if not items:
            continue

        str_agent = agent_names.get(key.agent, key.agent)
        str_model = model_names.get(key.weights, key.weights)
        key_str = f"{str_agent}: {str_model}"
        # if True:
        if False:
            key_user = input(f"Enter label for \"{key}\", or 'skip': ")
            if key_user == 'skip':
                continue
            if key_user:
                key_str = key_user
        
        x = [key_str for r in items]
        y = [r.DS for r in items]
        sns.swarmplot(x=x, y=y, alpha=0.5, linewidth=0.5)

        mean = stats.mean(y)
        median = stats.median(y)
        std = stats.stdev(y)
        range = max(y) - min(y)
        lines.append(f'{key_str:<20} & {median:>5.1f} & {mean:>5.1f} & {std:>4.1f} & {range:>5.1f} \\\\\n')

    plt.setp(ax.get_xticklabels(), rotation=20, horizontalalignment='right')
    plt.savefig("parse_result_scores.png", bbox_inches='tight', dpi=300)
    with open('parse_results_data.txt', 'w') as f:
        f.write(' '.join(sys.argv) + '\n')
        f.write('Scores: agent, median, mean, std\n')
        f.writelines(lines)


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
