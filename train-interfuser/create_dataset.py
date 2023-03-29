import os
import sys
import re
import shutil
import tarfile
from pathlib import Path

from tqdm.contrib.concurrent import process_map

if len(sys.argv) != 2:
    print("Usage: python create_dataset.py <DATETIME>")
    sys.exit(1)

DATETIME = sys.argv[1]
IDUN = "idun-login1.hpc.ntnu.no"
IDUN_DATASET_PATH = f"~/work/thesis/datagen-interfuser/output/{DATETIME}/data/"

DATASET_PATH = Path(f"/data/datasets/interfuser/{DATETIME}")
DATASET_INDEX_PATH = DATASET_PATH / "dataset_index.txt"


CPU_COUNT = os.cpu_count()

print("\nSyncing dataset from idun")
os.system(
    f'rsync -avzhP --include="*.tar.gz" --exclude="*" {IDUN}:{IDUN_DATASET_PATH} {DATASET_PATH}'
)

print()

def process_job_tarball(job_tarball_path):
    weather_number = re.search("w[0-9]{1,2}", str(job_tarball_path)).group()[1:]
    weather_dir = DATASET_PATH / f"weather-{weather_number}/data"
    weather_dir.mkdir(parents=True, exist_ok=True)
    os.system(f"tar -xf {job_tarball_path} -C {weather_dir} --strip-components=1")


job_tarball_paths = list(DATASET_PATH.glob("*.tar.gz"))

process_map(
    process_job_tarball,
    job_tarball_paths,
    max_workers=CPU_COUNT,
    desc="Processing job tarballs",
)

print()

if DATASET_INDEX_PATH.exists():
    DATASET_INDEX_PATH.unlink()


def process_tarball(tarball_path_tuple):
    with tarfile.open(tarball_path_tuple[0], "r:gz") as tar:
        tar.extractall(path=tarball_path_tuple[1])
    tarball_path_tuple[0].unlink()


for weather_dir in DATASET_PATH.glob("weather-*"):

    data_dir = weather_dir / "data"

    if (data_dir / "checkpoint.json").exists():
        (data_dir / "checkpoint.json").unlink()

    for path in data_dir.iterdir():
        if path.is_dir():
            shutil.rmtree(path)

    tarballs = list(data_dir.glob("*.tar.gz"))
    tarball_path_tuples = [(tarball, data_dir) for tarball in tarballs]

    process_map(
        process_tarball,
        tarball_path_tuples,
        max_workers=CPU_COUNT,
        desc=f"Processing {weather_dir.name}",
    )

    for route_dir in data_dir.iterdir():
        num_frames = len(list((route_dir / "rgb_front").iterdir()))
        relative_route_dir = route_dir.relative_to(DATASET_PATH)
        with open(DATASET_INDEX_PATH, "a") as f:
            f.write(f"{relative_route_dir}/ {num_frames}\n")

print("\nDONE\n")