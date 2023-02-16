#!/usr/bin/env python3

import os
import sys
import csv
from pathlib import Path

routes = Path(sys.argv[1])
scenarios = Path(sys.argv[2])
out_csv = Path(sys.argv[3])
strip_prefix = sys.argv[4]

pairs = []

all_scenarios = set(scenarios.rglob('*.json'))

def removeprefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

for route in routes.rglob('*.xml'):
    rel = route.relative_to(routes)
    json = rel.with_suffix('.json')
    scenario = scenarios / json
    all_scenarios.discard(scenario)
    if scenario.exists():
        route = removeprefix(str(route), strip_prefix)
        scenario = removeprefix(str(scenario), strip_prefix)
        pairs.append((route, scenario))
    else:
        print(f'Missing scenario for {route}')

if all_scenarios:
    print('Unused scenarios:')
    for scenario in all_scenarios:
        print(f'  {scenario}')

with open(out_csv, 'w') as f:
    writer = csv.writer(f)
    for route, scenario in pairs:
        writer.writerow([route, scenario])
