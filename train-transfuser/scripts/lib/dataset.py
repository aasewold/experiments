from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class Dataset:
    path: Path
    subsets: list['DatasetSubset']

    @staticmethod
    def load(path: Path) -> 'Dataset':
        return Dataset(
            path=path, 
            subsets=[
                DatasetSubset.load(subset_path)
                for subset_path in path.iterdir()
                if subset_path.is_dir()
            ]
        )


@dataclass(frozen=True)
class DatasetSubset:
    path: Path
    routes: list['DatasetRoute']

    @staticmethod
    def load(path: Path) -> 'DatasetSubset':
        return DatasetSubset(
            path=path, 
            routes=[
                DatasetRoute.load(route_path)
                for route_path in path.iterdir()
                if route_path.is_dir()
            ]
        )


@dataclass(frozen=True)
class DatasetRoute:
    path: Path

    _date_sep_index: ClassVar[int] = 5

    @property
    @cache
    def name(self) -> str:
        return '_'.join(self.path.name.split('_')[:-self._date_sep_index])

    @property
    @cache
    def date(self) -> str:
        return '_'.join(self.path.name.split('_')[-self._date_sep_index:])
    
    @property
    @cache
    def num_frames(self) -> int:
        return min(self.count_frames().values())
    
    @property
    def has_consistent_frame_count(self) -> bool:
        return len(set(self.count_frames().values())) == 1
    
    @cache
    def count_frames(self) -> dict[Path, int]:
        return {
            path: len(list(path.iterdir()))
            for path in self.sensor_paths
        }

    @property
    def sensor_paths(self) -> list[Path]:
        return [
            path
            for path in self.path.iterdir()
            if path.is_dir()
        ]

    @staticmethod
    def load(path: Path) -> 'DatasetRoute':
        return DatasetRoute(path=path)