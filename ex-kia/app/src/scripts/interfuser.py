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
def if_process_output(step, agent, action):
    # target = pred_wp[0] + pred_wp[1]
    # angle = atan2(target[1], target[0]) * 180 / np.pi
    
    print(f'{step}: {action}')


def if_main(trip: str):
    run_agent(trip, if_setup_agent, if_process_image, if_process_output)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        with profile.scope('main', dump=True):
            if_main(*sys.argv[1:])
