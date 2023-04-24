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


@click.group()
def cli():
    pass


@cli.command()
@click.argument("dataset-datetime")
@click.option(
    "--destination-dir",
    type=click.Path(exists=True),
    default="/data/datasets/interfuser",
)
@click.option(
    "--idun-datasets-path",
    type=click.Path(),
    default="~/work/thesis/datagen-interfuser/output",
)
def sync(dataset_datetime, destination_dir, idun_datasets_path):
    destination = Path(destination_dir) / dataset_datetime
    idun_dataset_path = f"{idun_datasets_path}/{dataset_datetime}/data/"
    click.echo(f"Syncing dataset from {IDUN}:{idun_dataset_path} to {destination}...\n")
    os.system(
        f'rsync -avzhP --include="*.tar.gz" --exclude="*" {IDUN}:{idun_dataset_path} {destination}'
    )


def process_job_tarball(job_tarball_path):
    weather_number_search = re.search("w[0-9]{1,2}", str(job_tarball_path))
    if weather_number_search is None:
        click.echo(f"Could not find weather number in {job_tarball_path}")
        sys.exit(1)

    weather_number = weather_number_search.group()[1:]
    weather_dir = Path(job_tarball_path).parent / f"weather-{weather_number}/data"
    weather_dir.mkdir(parents=True, exist_ok=True)
    os.system(
        f"tar --skip-old-files -xf {job_tarball_path} -C {weather_dir} --strip-components=1"
    )


def process_weather_tarball(tarball_path: Path):
    destination = Path(tarball_path).parent

    error = False

    try:
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=destination)

    except EOFError:
        error = True
        shutil.rmtree(destination / tarball_path.name.replace(".tar.gz", ""))

    tarball_path.unlink()

    return tarball_path.name if error else None


@cli.command(
    help="Extracts the dataset from the tarballs and creates a dataset index file."
)
@click.argument("dataset-path", type=click.Path(exists=True, path_type=Path))
def extract(dataset_path: Path):
    job_tarball_paths = list(dataset_path.glob("*.tar.gz"))

    process_map(
        process_job_tarball,
        job_tarball_paths,
        max_workers=CPU_COUNT,
        desc="Untaring slurm job tarballs",
    )

    dataset_index_path = dataset_path / "dataset_index.txt"

    if dataset_index_path.exists():
        shutil.copy(dataset_index_path, dataset_index_path.with_suffix(".bak"))
        dataset_index_path.unlink()

    for weather_dir in dataset_path.glob("weather-*"):
        data_dir = weather_dir / "data"

        if (data_dir / "checkpoint.json").exists():
            (data_dir / "checkpoint.json").unlink()

        weather_tarball_paths = list(data_dir.glob("*.tar.gz"))

        results = process_map(
            process_weather_tarball,
            weather_tarball_paths,
            max_workers=CPU_COUNT,
            desc=f"Processing {weather_dir.name}",
        )

        failed_extractions = [r for r in results if r is not None]

        click.echo(
            f"Failed to fully extract {len(failed_extractions)} tarballs: {failed_extractions}"
        )

        routes_removed = []

        for route_dir in data_dir.iterdir():
            if not route_dir.is_dir():
                continue

            num_frames = len(list((route_dir / "C2_tricam60").iterdir()))

            if num_frames < 10:
                routes_removed.append(route_dir.name)
                shutil.rmtree(route_dir)
                continue

            relative_route_dir = route_dir.relative_to(dataset_path)
            with open(dataset_index_path, "a") as f:
                f.write(f"{relative_route_dir}/ {num_frames}\n")

        click.echo(
            f"Removed {len(routes_removed)} routes with less than 10 frames: {routes_removed}"
        )

    click.echo("\nDONE\n")
    click.echo(f"Converted dataset stored at {dataset_path}")


if __name__ == "__main__":
    cli()
