from pathlib import Path
import struct
from dataclasses import dataclass, replace
from typing import Tuple

from src.measurements import Measurement, IteratorSource, NamedSource


# NVIDIA CAN format described here:
# https://forums.developer.nvidia.com/t/binary-can-file-format/154781/8

# KIA CAN protocol described here:
# https://github.com/commaai/opendbc/blob/d40e429914a8bc5c2c630726fe097f85f7108185/hyundai_kia_generic.dbc#L1523


@dataclass
class CANMessage:
    ts_us: int
    id: int
    payload_size: int
    data: bytes

    @property
    def is_steer(self) -> bool:
        return self.id == 0x2b0

    def get_steer(self) -> float:
        return struct.unpack('<h', self.data[:2])[0] / 10

    @property
    def is_throttle(self) -> bool:
        return self.id == 0x371

    def get_throttle(self) -> float:
        raw = (
            ((self.data[3] & 0b1000_0000) >> 7)
            | ((self.data[4] & 0b0111_1111) << 1)
        )
        return raw / 254
    
    @property
    def is_brake(self) -> bool:
        return self.id == 0x371

    def get_brake(self) -> float:
        return self.data[0] / 127
    
    @property
    def is_speed(self) -> bool:
        return self.id == 0x52a

    def get_speed(self) -> float:
        return self.data[0]
    
    @property
    def is_wheel_speed(self) -> bool:
        return self.id == 0x386

    def get_wheel_speed(self) -> Tuple[float, float, float, float]:
        raw = [
            self.data[i*2] | ((self.data[i*2+1] & 0b00111111) << 8)
            for i in range(4)
        ]
        speeds = [r / 32 for r in raw]
        return tuple(speeds)
    

@dataclass
class VehicleState:
    steer: float = 0
    throttle: float = 0
    brake: float = 0
    speed: float = 0
    wheel_speed: Tuple[float, float, float, float] = (0, 0, 0, 0)
    
    def update(self, message: CANMessage):
        copy = replace(self)
        if message.is_steer:
            copy.steer = message.get_steer()
        if message.is_throttle:
            copy.throttle = message.get_throttle()
        if message.is_brake:
            copy.brake = message.get_brake()
        if message.is_speed:
            copy.speed = message.get_speed()
        if message.is_wheel_speed:
            copy.wheel_speed = message.get_wheel_speed()
        return copy

    
def make_can(path: Path):
    def generator():
        with open(path, 'rb') as f:
            buf = f.read(32)
            magic, version = struct.unpack('<Ii', buf[:8])

            if magic != 0xc5eeeaf2:
                raise ValueError('Invalid magic number')

            if version == 1:
                max_payload_size = 8
            else:
                max_payload_size = 64

            state = VehicleState()

            buf = f.read(14)
            while buf:
                ts_us, id, payload_size = struct.unpack('<qIH', buf)
                if payload_size > max_payload_size:
                    raise ValueError('Invalid payload size', payload_size)
                data = f.read(max_payload_size)[:payload_size]

                message = CANMessage(ts_us, id, payload_size, data)
                state = state.update(message)
                yield Measurement(ts_us / 1000, (message, state))

                buf = f.read(14)
    
    return NamedSource(
        name=path.stem,
        inner=IteratorSource(generator()),
    )

