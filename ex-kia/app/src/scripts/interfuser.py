import sys
from contextlib import suppress

import numpy as np
from PIL import Image

from src import profile
from src.scripts.transfuser import run_agent


def if_setup_agent():
    from team_code.interfuser_agent import InterfuserAgent
    agent = InterfuserAgent("leaderboard/team_code/interfuser_config.py")
    return agent


@profile.func
def if_get_extra_data(step, agent, action):
    # Taken from interfuser_controller.py
    wp = agent.prev_waypoints.copy()
    wp[:, 1] *= -1
    wp[:, [0, 1]] = wp[:, [1, 0]]
    
    meta = agent.meta_infos

    desired_speed = float(meta[0].split('target_speed: ')[1])
    
    aim = (wp[0] + wp[1]) / 2
    angle = np.arctan2(aim[1], aim[0])
    steer = np.degrees(angle) / 90
    
    return {
        'wp': wp,
        'desired_speed': desired_speed,
        'angle_rad': angle,
        'raw_steer': steer,
    }


def if_main(trip: str):
    run_agent(trip, if_setup_agent, if_get_extra_data)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            if_main(*sys.argv[1:])
