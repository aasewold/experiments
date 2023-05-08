import sys
import subprocess
from pathlib import Path
from typing import Optional


def make_movie(data_folder: Path, movie_path: Optional[Path] = None):
    if movie_path is None:
        movie_path = data_folder / "movie.mp4"
    subprocess.run([
        "ffmpeg",
        "-y",
        "-framerate", "30",
        "-i", f"{data_folder}/%d.jpg",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        f"{movie_path}",
    ], check=True)


if __name__ == "__main__":
    make_movie(*map(Path, sys.argv[1:]))
