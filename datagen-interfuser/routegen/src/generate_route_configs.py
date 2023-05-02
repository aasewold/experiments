import csv
import yaml
import os


# ---------------------------------- routes ---------------------------------- #

routes = {}

# town 01
# routes["training_routes/routes_town01_tiny.xml"] = "scenarios/town01_all_scenarios.json"
# routes["training_routes/routes_town01_short.xml"] = "scenarios/town01_all_scenarios.json"
# routes["additional_routes/routes_town01_long.xml"] = "scenarios/town01_all_scenarios.json"

# town 02
# routes["training_routes/routes_town02_tiny.xml"] = "scenarios/town02_all_scenarios.json"
# routes["training_routes/routes_town02_short.xml"] = "scenarios/town02_all_scenarios.json"
# routes["additional_routes/routes_town02_long.xml"] = "scenarios/town02_all_scenarios.json"

# town 03
# routes["training_routes/routes_town03_tiny.xml"] = "scenarios/town03_all_scenarios.json"
# routes["training_routes/routes_town03_short.xml"] = "scenarios/town03_all_scenarios.json"
# routes["additional_routes/routes_town03_long.xml"] = "scenarios/town03_all_scenarios.json"

# town 04
# routes["training_routes/routes_town04_tiny.xml"] = "scenarios/town04_all_scenarios.json"
# routes["training_routes/routes_town04_short.xml"] = "scenarios/town04_all_scenarios.json"
# routes["additional_routes/routes_town04_long.xml"] = "scenarios/town04_all_scenarios.json"

# town 05
routes["training_routes/routes_town05_tiny.xml"] = "scenarios/town05_all_scenarios.json"
routes["training_routes/routes_town05_short.xml"] = "scenarios/town05_all_scenarios.json"
routes["training_routes/routes_town05_long.xml"] = "scenarios/town05_all_scenarios.json"

# town 06
routes["training_routes/routes_town06_tiny.xml"] = "scenarios/town06_all_scenarios.json"
routes["training_routes/routes_town06_short.xml"] = "scenarios/town06_all_scenarios.json"
routes["additional_routes/routes_town06_long.xml"] = "scenarios/town06_all_scenarios.json"

# town 07
routes["training_routes/routes_town07_tiny.xml"] = "scenarios/town07_all_scenarios.json"
routes["training_routes/routes_town07_short.xml"] = "scenarios/town07_all_scenarios.json"

# town 10
routes["training_routes/routes_town10_tiny.xml"] = "scenarios/town10_all_scenarios.json"
routes["training_routes/routes_town10_short.xml"] = "scenarios/town10_all_scenarios.json"


# --------------------------------- weathers --------------------------------- #
# 0: "ClearNoon": carla.WeatherParameters.ClearNoon,
# 1: "ClearSunset": carla.WeatherParameters.ClearSunset,
# 2: "CloudyNoon": carla.WeatherParameters.CloudyNoon,
# 3: "CloudySunset": carla.WeatherParameters.CloudySunset,
# 4. "WetNoon": carla.WeatherParameters.WetNoon,
# 5: "WetSunset": carla.WeatherParameters.WetSunset,
# 6: "MidRainyNoon": carla.WeatherParameters.MidRainyNoon,
# 7: "MidRainSunset": carla.WeatherParameters.MidRainSunset,
# 8: "WetCloudyNoon": carla.WeatherParameters.WetCloudyNoon,
# 9: "WetCloudySunset": carla.WeatherParameters.WetCloudySunset,
# 10: "HardRainNoon": carla.WeatherParameters.HardRainNoon,
# 11: "HardRainSunset": carla.WeatherParameters.HardRainSunset,
# 12: "SoftRainNoon": carla.WeatherParameters.SoftRainNoon,
# 13: "SoftRainSunset": carla.WeatherParameters.SoftRainSunset,
# 14: "ClearNight": carla.WeatherParameters(5.0,0.0,0.0,10.0,-1.0,-90.0,60.0,75.0,1.0,0.0),
# 15: "CloudyNight": carla.WeatherParameters(60.0,0.0,0.0,10.0,-1.0,-90.0,60.0,0.75,0.1,0.0),
# 16: "WetNight": carla.WeatherParameters(5.0,0.0,50.0,10.0,-1.0,-90.0,60.0,75.0,1.0,60.0),
# 17: "WetCloudyNight": carla.WeatherParameters(60.0,0.0,50.0,10.0,-1.0,-90.0,60.0,0.75,0.1,60.0),
# 18: "SoftRainNight": carla.WeatherParameters(60.0,30.0,50.0,30.0,-1.0,-90.0,60.0,0.75,0.1,60.0),
# 19: "MidRainyNight": carla.WeatherParameters(80.0,60.0,60.0,60.0,-1.0,-90.0,60.0,0.75,0.1,80.0),
# 20: "HardRainNight": carla.WeatherParameters(100.0,100.0,90.0,100.0,-1.0,-90.0,100.0,0.75,0.1,100.0),

WEATHER_CONFIG_INDEXES = [0, 2, 4, 6, 7, 11, 12, 14, 17, 20]


# ------------------------------ generate yamls ------------------------------ #


d = {}
d[
    "waypoint_disturb"
] = 0.2  # in meters, a way of data augumentaion that randomly distrub the planned waypoints
d["waypoint_disturb_seed"] = 2020
d["destory_hazard_actors"] = True
d["save_skip_frames"] = 10  # skip 10 frames equals fps = 2
d["rgb_only"] = False

if not os.path.exists("build/output/yamls"):
    os.mkdir("build/output/yamls")

for i in WEATHER_CONFIG_INDEXES:
    d["weather"] = i
    with open("build/output/yamls/weather-%d.yaml" % i, "w") as fw:
        yaml.dump(d, fw)


# -------------------------- generate route configs -------------------------- #

with open("build/output/route_configs.csv", "w") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "route",
            "scenario",
            "weather_config_index",
        ],
    )

    configs = []

    for i in WEATHER_CONFIG_INDEXES:
        for route in routes:
            configs.append(
                {
                    "route": route,
                    "scenario": routes[route],
                    "weather_config_index": i,
                }
            )

    writer.writerows(configs)
