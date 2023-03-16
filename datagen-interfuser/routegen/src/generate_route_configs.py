import os
import csv

routes = {}
routes[
    "training_routes/routes_town01_short.xml"
] = "scenarios/town01_all_scenarios.json"
routes["training_routes/routes_town01_tiny.xml"] = "scenarios/town01_all_scenarios.json"
routes[
    "training_routes/routes_town02_short.xml"
] = "scenarios/town02_all_scenarios.json"
routes["training_routes/routes_town02_tiny.xml"] = "scenarios/town02_all_scenarios.json"
routes[
    "training_routes/routes_town03_short.xml"
] = "scenarios/town03_all_scenarios.json"
routes["training_routes/routes_town03_tiny.xml"] = "scenarios/town03_all_scenarios.json"
routes[
    "training_routes/routes_town04_short.xml"
] = "scenarios/town04_all_scenarios.json"
routes["training_routes/routes_town04_tiny.xml"] = "scenarios/town04_all_scenarios.json"
routes[
    "training_routes/routes_town05_short.xml"
] = "scenarios/town05_all_scenarios.json"
routes["training_routes/routes_town05_tiny.xml"] = "scenarios/town05_all_scenarios.json"
routes["training_routes/routes_town05_long.xml"] = "scenarios/town05_all_scenarios.json"
routes[
    "training_routes/routes_town06_short.xml"
] = "scenarios/town06_all_scenarios.json"
routes["training_routes/routes_town06_tiny.xml"] = "scenarios/town06_all_scenarios.json"
routes[
    "training_routes/routes_town07_short.xml"
] = "scenarios/town07_all_scenarios.json"
routes["training_routes/routes_town07_tiny.xml"] = "scenarios/town07_all_scenarios.json"
routes[
    "training_routes/routes_town10_short.xml"
] = "scenarios/town10_all_scenarios.json"
routes["training_routes/routes_town10_tiny.xml"] = "scenarios/town10_all_scenarios.json"
routes[
    "additional_routes/routes_town01_long.xml"
] = "scenarios/town01_all_scenarios.json"
routes[
    "additional_routes/routes_town02_long.xml"
] = "scenarios/town02_all_scenarios.json"
routes[
    "additional_routes/routes_town03_long.xml"
] = "scenarios/town03_all_scenarios.json"
routes[
    "additional_routes/routes_town04_long.xml"
] = "scenarios/town04_all_scenarios.json"
routes[
    "additional_routes/routes_town06_long.xml"
] = "scenarios/town06_all_scenarios.json"


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

    for i in range(14):
        for route in routes:
            configs.append(
                {
                    "route": route,
                    "scenario": routes[route],
                    "weather_config_index": i,
                }
            )

    writer.writerows(configs)
