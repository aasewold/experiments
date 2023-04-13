#!/usr/bin/env python3.9

import sys
import shutil
from pathlib import Path
from itertools import groupby
from lib.dataset import Dataset


def main():
    dataset = Dataset.load(Path(sys.argv[1]))
    for subset in dataset.subsets:
        routes = sorted(subset.routes, key=lambda route: route.name)
        route_groups = groupby(routes, key=lambda route: route.name)
        for route_name, route_group in route_groups:
            route_group = list(route_group)
            keep_route = max(route_group, key=lambda route: (route.num_frames, route.date))
            for route in route_group:
                if route != keep_route:
                    print(f'Discarding {route.path} with {route.num_frames}/{keep_route.num_frames} frames')
                    shutil.rmtree(route.path)


if __name__ == '__main__':
    main()
