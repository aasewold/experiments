#!/usr/bin/env python3

import os
import csv
from pathlib import Path

routes = Path('/routes/routes')
scenarios = Path('/routes/scenarios')
empty_scenario = scenarios / 'empty.json'
out_csv = Path('/routes/routes.csv')

pairs = []

all_scenarios = set(scenarios.rglob('*.json'))

for route in routes.rglob('*.xml'):
    rel = route.relative_to(routes)
    json = rel.with_suffix('.json')
    scenario = scenarios / json

    if scenario.exists():
        pass
    elif empty_scenario.exists():
        print(f'Missing scenario for {route}, using empty')
        scenario = empty_scenario
    else:
        print(f"Missing scenario for {route}, and empty.json doesn't exist")
        continue

    all_scenarios.discard(scenario)
    pairs.append((str(route), str(scenario)))

if all_scenarios:
    print('Unused scenarios:')
    for scenario in all_scenarios:
        print(f'  {scenario}')

with open(out_csv, 'w') as f:
    writer = csv.writer(f, lineterminator=os.linesep)
    for route, scenario in pairs:
        writer.writerow([route, scenario])
