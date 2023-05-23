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


def if_process_image(img, unused):
    pil = Image.fromarray(img)
    pil = pil.resize((800, 600), Image.BILINEAR)
    img = np.asarray(pil)
    return img


@profile.func
def if_get_extra_data(step, agent, action):
    # Taken from interfuser_controller.py
    wp = agent.prev_waypoints
    meta = agent.meta_infos

    desired_speed = float(meta[0].split('target_speed: ')[1])
    
    aim = (wp[1] + wp[0]) / 2
    aim[1] *= -1
    angle = np.pi/2 - np.arctan2(aim[1], aim[0])
    steer = np.degrees(angle) / 90
    
    return {
        'wp': wp,
        'desired_speed': desired_speed,
        'angle_rad': angle,
        'raw_steer': steer,
    }


def if_main(trip: str):
    run_agent(trip, if_setup_agent, if_process_image, if_get_extra_data)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            if_main(*sys.argv[1:])
