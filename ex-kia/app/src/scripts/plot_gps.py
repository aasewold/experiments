import sys
from contextlib import suppress
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
from cartopy.io.img_tiles import OSM

from src import profile
from src.nap.kia.gps import make_avg_gps


def load_gps_data(path):
    gps = make_avg_gps(
        path / 'gnss50_vehicle.bin',
        path / 'gnss52_vehicle.bin',
        max_ts_diff_ms=50,
    )

    ts = []
    pos = []

    for m in gps:
        ts.append(m.ts)
        pos.append((m.value.lat, m.value.lon, m.value.alt))
    
    ts = np.array(ts)
    coords = np.array(pos)
    return ts, coords


def plot_gps_data(ts, gps_coords):
    imagery = OSM()

    lat, lon, alt = gps_coords.T
    world_coords = imagery.crs.transform_points(ccrs.Geodetic(), lon, lat, alt)
    world_coords = world_coords[:, :2]

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection=imagery.crs)
    ax.add_image(imagery, 15)

    c = np.array(ts)
    c = (c - c.min()) / (c.max() - c.min())

    ax.scatter(*world_coords.T, s=1, c=c, marker='.', lw=0)

    px_coords_q = []
    def on_draw(event):
        px_coords = ax.transData.transform(world_coords)
        width, height = fig.canvas.get_width_height()
        px_coords[:, 1] = height - px_coords[:, 1]
        px_coords_q.append(((width, height), px_coords))

    fig.canvas.mpl_connect('draw_event', on_draw)

    return fig, world_coords, px_coords_q


def save_gps_fig(fig, path):
    fig.savefig(path, dpi=1000, bbox_inches='tight', pad_inches=0)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            
            path = Path(sys.argv[1])
            ts, gps_coords = load_gps_data(path)
            fig, world_coords, px_q = plot_gps_data(ts, gps_coords)
            save_gps_fig(fig, f'{path.stem}.png')
            px_coords, = px_q
