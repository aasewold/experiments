import re
from dataclasses import dataclass
from pathlib import Path

from src.measurements import Measurement, IteratorSource, NamedSource
from .old_gps import GpsData


@dataclass
class NMEA_GGA:
    lat: float
    lon: float
    alt: float
    hdop: float


@dataclass
class NMEA_VTG:
    course: float
    speed_kmh: float


def parse_lat(s: str) -> float:
    dd = int(s[:2])
    mm = float(s[2:])
    return dd + mm / 60


def parse_lon(s: str) -> float:
    ddd = int(s[:3])
    mm = float(s[3:])
    return ddd + mm / 60


re_line = re.compile(r"\$(.+)\*[0-9A-F]{2} (\d+)")


def make_gps(path: Path):
    def generator():
        curr_gga = None
        curr_vtg = None

        with path.open("rt") as f:
            for line in f:
                match = re_line.match(line.strip())
                if match:
                    nmea, ts_us = match.group(1), int(match.group(2))
                    parts = nmea.split(",")

                    if parts[0] == "GPVTG":
                        try:
                            curr_vtg = NMEA_VTG(
                                course=float(parts[1]),
                                speed_kmh=float(parts[7]),
                            )
                        except ValueError:
                            pass

                    if parts[0] == "GPGGA":
                        try:
                            curr_gga = NMEA_GGA(
                                lat=parse_lat(parts[2])
                                * (-1 if parts[3] == "S" else 1),
                                lon=parse_lon(parts[4])
                                * (-1 if parts[5] == "W" else 1),
                                alt=float(parts[9]),
                                hdop=float(parts[8]),
                            )
                        except ValueError:
                            pass
                        else:
                            yield Measurement(
                                ts_us / 1000,
                                GpsData(
                                    index=0,
                                    lat=curr_gga.lat,
                                    lon=curr_gga.lon,
                                    alt=curr_gga.alt,
                                    speed=curr_vtg.speed_kmh if curr_vtg else None,
                                    course=curr_vtg.course if curr_vtg else None,
                                    hdop=curr_gga.hdop,
                                    vdop=None,
                                ),
                            )

    return NamedSource(name=path.stem, inner=IteratorSource(generator()))
