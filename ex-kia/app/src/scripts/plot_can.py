import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from src.nap.kia.canbus import make_can


if __name__ == '__main__':
    path = Path(sys.argv[1])
    gen = make_can(path)

    throttle = []
    speed = []
    wheel_speed = []
    brake = []
    steer = []

    print(gen.current.ts)

    for measurement in gen:
        ts = measurement.ts
        msg, state = measurement.value
        if msg.is_brake:
           brake.append((ts, -msg.get_brake())) 
        if msg.is_throttle:
            throttle.append((ts, msg.get_throttle()))
        if msg.is_speed:
            speed.append((ts, msg.get_speed()))
        if msg.is_wheel_speed:
            wheel_speed.append((ts, sum(msg.get_wheel_speed()) / 4))
        if msg.is_steer:
            steer.append((ts, msg.get_steer()))

    print(len(throttle), len(speed), len(brake), len(steer), len(wheel_speed))

    throttle = np.array(throttle)
    speed = np.array(speed)
    brake = np.array(brake)
    steer = np.array(steer)
    wheel_speed = np.array(wheel_speed)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
    ax1.plot(*throttle.T, label='throttle', c='blue')
    ax1.plot(*brake.T, label='brake', c='green')
    ax2.plot(*wheel_speed.T, label='speed')
    ax3.plot(*steer.T, label='steer')
    ax1.legend(); ax1.grid()
    ax2.legend(); ax2.grid()
    ax3.legend(); ax3.grid()
    plt.savefig('/work/can.png', dpi=600, bbox_inches='tight')
