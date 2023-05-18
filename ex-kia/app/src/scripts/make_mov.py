import sys
import subprocess
from pathlib import Path
from typing import Optional


def make_movie(data_folder: Path, movie_path: Optional[Path] = None):
    if movie_path is None:
        movie_path = data_folder / "movie.mp4"
    
    if (data_folder / '0.jpg').exists():
        fmt = '%d'
    elif (data_folder / '0000.jpg').exists():
        fmt = '%04d'
    else:
        raise ValueError(f"Couldn't guess number format in {data_folder}")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-framerate", "30",
        "-i", f"{data_folder}/{fmt}.jpg",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        f"{movie_path}",
    ], check=True)


if __name__ == "__main__":
    make_movie(*map(Path, sys.argv[1:]))
