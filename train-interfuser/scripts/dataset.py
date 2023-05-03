import json
import os
import re
import shutil
import sys
import tarfile
from pathlib import Path

import click
from tqdm.contrib.concurrent import process_map

CPU_COUNT = os.cpu_count()

IDUN = "idun-login1.hpc.ntnu.no"


@click.group(
    context_settings=dict(max_content_width=120),
)
def cli():
    pass


@cli.command(help="Sync tarballs from IDUN")
@click.argument("dataset-datetime")
@click.option(
    "--destination-dir",
    type=click.Path(exists=True),
    default="/data/datasets/interfuser",
    show_default=True,
)
@click.option(
    "--idun-datasets-path",
    type=click.Path(),
    default="~/work/thesis/datagen-interfuser/output",
    show_default=True,
)
def sync(dataset_datetime, destination_dir, idun_datasets_path):
    destination = Path(destination_dir) / dataset_datetime
    idun_dataset_path = f"{idun_datasets_path}/{dataset_datetime}/data/"
    click.echo(f"Syncing dataset from {IDUN}:{idun_dataset_path} to {destination}...\n")
    os.system(
        f'rsync -avzhP --include="*.tar.gz" --exclude="*" {IDUN}:{idun_dataset_path} {destination}'
    )


def _process_job_tarball(job_tarball_path: Path):
    weather_number_search = re.search("w[0-9]{1,2}", str(job_tarball_path))
    if weather_number_search is None:
        click.echo(f"Could not find weather number in {job_tarball_path}")
        sys.exit(1)

    weather_number = weather_number_search.group()[1:]
    weather_dir = job_tarball_path.parent / f"weather-{weather_number}/data"
    weather_dir.mkdir(parents=True, exist_ok=True)
    os.system(
        f"tar --skip-old-files -xf {job_tarball_path} -C {weather_dir} --strip-components=1"
    )
    job_tarball_path.rename(f"{job_tarball_path}.done")


def _process_weather_tarball(tarball_path: Path):
    destination = tarball_path.parent

    error = False

    try:
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=destination)

    except EOFError:
        error = True
        shutil.rmtree(destination / tarball_path.name.replace(".tar.gz", ""))

    tarball_path.unlink()

    return tarball_path.name if error else None


@cli.command(help="Extracts the dataset tarballs to weather folders")
@click.argument("dataset-path", type=click.Path(exists=True, path_type=Path))
def extract(dataset_path: Path):
    job_tarball_paths = list(dataset_path.glob("*.tar.gz"))

    process_map(
        _process_job_tarball,
        job_tarball_paths,
        max_workers=CPU_COUNT,
        desc="Untaring slurm job tarballs",
    )

    for weather_dir in dataset_path.glob("weather-*"):
        data_dir = weather_dir / "data"

        if (data_dir / "checkpoint.json").exists():
            (data_dir / "checkpoint.json").unlink()

        weather_tarball_paths = list(data_dir.glob("*.tar.gz"))

        results = process_map(
            _process_weather_tarball,
            weather_tarball_paths,
            max_workers=CPU_COUNT,
            desc=f"Processing {weather_dir.name}",
        )

        failed_extractions = [r for r in results if r is not None]

        click.echo(
            f"Failed to fully extract {len(failed_extractions)} tarballs: {failed_extractions}"
        )

    click.echo("\nDONE\n")
    click.echo(f"Converted dataset stored at {dataset_path}")


def _get_blocked_stats(route_dir):
    frames = len(os.listdir(os.path.join(route_dir, "measurements")))
    stop = 0
    max_stop = 0
    last_actors_num = 0
    res = []
    for i in range(frames):
        json_data = json.load(
            open(os.path.join(route_dir, "measurements", "%04d.json" % i))
        )
        actors_data = json.load(
            open(os.path.join(route_dir, "actors_data", "%04d.json" % i))
        )
        actors_num = len(actors_data)
        light = json_data["is_red_light_present"]
        speed = json_data["speed"]
        brake = json_data["should_brake"]
        if speed < 0.1 and len(light) == 0 and brake == 1:
            stop += 1
            max_stop = max(max_stop, stop)
        else:
            if stop >= 10 and actors_num < last_actors_num:
                res.append((route_dir, i, stop))
            stop = 0
        last_actors_num = actors_num
    if stop >= 10:
        res.append((route_dir, frames - 1, stop))
    return res


camera_names = [
    "C1_front60Single",
    "C2_tricam60",
    "C3_tricam120",
    "C4_rearCam",
    "C8_R2",
    "C5_R1",
    "C6_L1",
    "C7_L2",
]
data_dirs = {camera_name: "%04d.jpg" for camera_name in camera_names}
data_dirs["measurements"] = "%04d.json"
data_dirs["lidar"] = "%04d.npy"
data_dirs["affordances"] = "%04d.npy"
data_dirs["actors_data"] = "%04d.json"


def _rm_blocked_data(task):
    route_dir, end_id, length = task
    for i in range(end_id - length + 6, end_id - 3):
        for key in data_dirs:
            os.remove(os.path.join(route_dir, key, data_dirs[key] % i))


def _fix_indices(route_dir):
    for folder in data_dirs:
        temp = data_dirs[folder]
        files = os.listdir(os.path.join(route_dir, folder))
        fs = []
        for file in files:
            fs.append(int(file[:4]))
        fs.sort()
        for i in range(len(fs)):
            if i == fs[i]:
                continue
            try:
                os.rename(
                    os.path.join(route_dir, folder, temp % fs[i]),
                    os.path.join(route_dir, folder, temp % i),
                )
            except Exception as e:
                click.echo(e)


@cli.command(help="Remove data where ego is blocked over many frames")
@click.argument("dataset-path", type=click.Path(exists=True, path_type=Path))
def rm_blocked_data(dataset_path: Path):
    blocked_stats_file = Path("blocked_stat.txt")

    all_routes = []
    num_total_frames = 0

    for path in dataset_path.glob("weather-*/data/*"):
        all_routes.append(path)
        num_total_frames += len(os.listdir(path / "measurements"))

    results = process_map(
        _get_blocked_stats,
        all_routes,
        max_workers=CPU_COUNT,
        desc=f"Getting blocked stats",
    )

    num_blocked_frames = 0

    with open(blocked_stats_file, "w") as f:
        for result in results:
            if len(result) == 0:
                continue
            for stats in result:
                f.write("%s %d %d\n" % stats)
                num_blocked_frames += stats[2]

    click.echo(
        f"Found {num_blocked_frames} blocked frames out of {num_total_frames} total frames ({num_blocked_frames / num_total_frames * 100:.2f}%)"
    )

    if not click.confirm("\nDo you want to remove blocked data?"):
        return

    blocked_data_tasks = []

    with open(blocked_stats_file, "r") as f:
        for line in f:
            route, last_frame, num_frames_blocked = line.split()
            blocked_data_tasks.append((route, int(last_frame), int(num_frames_blocked)))

    process_map(
        _rm_blocked_data,
        blocked_data_tasks,
        max_workers=CPU_COUNT,
        desc=f"Removing blocked data",
    )

    processed_routes = set(task[0] for task in blocked_data_tasks)

    process_map(
        _fix_indices,
        processed_routes,
        max_workers=CPU_COUNT,
        desc=f"Fixing indices",
    )


@cli.command(help="Create dataset index")
@click.argument("dataset-path", type=click.Path(exists=True, path_type=Path))
def create_index(dataset_path: Path):
    dataset_index_path = dataset_path / "dataset_index.txt"

    if dataset_index_path.exists():
        dataset_index_path.unlink()

    routes_removed = []

    with open(dataset_index_path, "w") as f:
        for route_dir in dataset_path.glob("weather-*/data/*"):
            if not route_dir.is_dir():
                continue

            route_type = route_dir.name.split("_")[2]

            num_frames = len(list((route_dir / "C2_tricam60").iterdir()))
            min_frames = 10 if route_type == "tiny" else 50

            if num_frames < min_frames:
                routes_removed.append(route_dir.name)
                shutil.rmtree(route_dir)
                continue

            relative_route_dir = route_dir.relative_to(dataset_path)
            f.write(f"{relative_route_dir}/ {num_frames}\n")

    click.echo(
        f"Removed {len(routes_removed)} routes with less than 10 frames: {routes_removed}"
    )
    click.echo(f"Dataset index stored at {dataset_index_path}")


if __name__ == "__main__":
    cli()
