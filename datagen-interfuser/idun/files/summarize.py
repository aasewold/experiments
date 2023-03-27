#!/usr/bin/env python3

import json
import sys
import re
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel

regex_scen = [r'Scen[a-z]*(\d+)', r'([lr][lr])']
regex_town = [r'Town([0-9][0-9][a-zA-Z]*)']
regex_route = [r'route(\d+)']
regex_array_id = [r'data/(\d+)']


def find(regex: List[str], string: str) -> Optional[str]:
    for r in regex:
        m = re.search(r, string)
        if m:
            return m.group(1)
    return None


class Route(BaseModel):
    num_frames: int = 0
    status: Optional[dict] = None


class Town(BaseModel):
    routes: Dict[int, Route]
    num_frames: int = 0
    checkpoint: Optional[Path] = None
    status: Optional[dict] = None
    slurm_job: Optional[str] = None


class Scenario(BaseModel):
    towns: Dict[str, Town]
    num_frames: int = 0


class Result(BaseModel):
    scenarios: Dict[str, Scenario]
    num_frames: int = 0


def sorter(entry):
    m_scen, m_town, m_route, path = entry
    return (
        m_scen or '',
        m_town or '',
        m_route or '',
    )


def walk(path: Path):
    entries = []
    for p in path.iterdir():
        m_scen = find(regex_scen, p.name)
        m_town = find(regex_town, p.name)
        m_route = find(regex_route, p.name)
        if m_scen:
            entries.append((m_scen, m_town, m_route, p))
        if p.is_dir() and m_route is None:
            entries.extend(walk(p))
    entries.sort(key=sorter)
    return entries


def main():
    dataset_dir = Path(sys.argv[1])

    result: Result = Result(scenarios={})
    entries = walk(dataset_dir)

    for m_scen, m_town, m_route, path in entries:
        if m_scen not in result.scenarios:
            result.scenarios[m_scen] = Scenario(towns=[])
        scenario = result.scenarios[m_scen]
        
        if not m_town:
            continue

        if m_town not in scenario.towns:
            slurm_job = find(regex_array_id, str(path))
            scenario.towns[m_town] = Town(routes=[], slurm_job=slurm_job)
        town = scenario.towns[m_town]

        if not m_route:
            checkpoint = path / 'checkpoint.json'
            if checkpoint.exists():
                town.checkpoint = checkpoint
            continue

        if m_route in town.routes:
            raise RuntimeError(f'Route {m_route} already exists in scenario {m_scen} town {m_town}')

        num_frames = sum(1 for _ in (path / 'lidar').iterdir())
        town.routes[int(m_route)] = Route(num_frames=num_frames)
    
    for scenario in result.scenarios.values():
        for town in scenario.towns.values():
            for route in town.routes.values():
                result.num_frames += route.num_frames
                scenario.num_frames += route.num_frames
                town.num_frames += route.num_frames
    
    for scenario in result.scenarios.values():
        for town in scenario.towns.values():
            if town.checkpoint:
                with town.checkpoint.open('r') as f:
                    data = json.load(f)['_checkpoint']
                    town.status = {
                        'status': data['global_record'].get('status'),
                        'progress': data['progress'],
                    }
                    records = data.get('records', [])
                    if records:
                        sorted_routes = sorted(town.routes.items(), key=lambda p: int(p[0]))
                        for (_, route), record in zip(sorted_routes, records):
                            route.status = {
                                'status': record.get('status'),
                                'meta': record.get('meta'),
                            }
    
    print(result.json(indent=2, sort_keys=True, exclude_none=True))


if __name__ == '__main__':
    main()
