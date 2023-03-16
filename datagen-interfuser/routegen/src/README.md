# Interfuser Datagen

## Dataset
The data is generated with ```leaderboard/team_code/auto_pilot.py``` in 8 CARLA towns using the routes and scenarios files provided at ```leaderboard/data``` on CARLA 0.9.14

The collected dataset is structured as follows:
```
- TownX_{tiny,short,long}: corresponding to different towns and routes files
    - routes_X: contains data for an individual route
        - rgb_{front, left, right, rear}: multi-view camera images at 400x300 resolution
        - seg_{front, left, right}: corresponding segmentation images
        - depth_{front, left, right}: corresponding depth images
        - lidar: 3d point cloud in .npy format
        - birdview: topdown segmentation images required for training LBC
        - 2d_bbs_{front, left, right, rear}: 2d bounding boxes for different agents in the corresponding camera view
        - 3d_bbs: 3d bounding boxes for different agents
        - affordances: different types of affordances
        - measurements: contains ego-agent's position, velocity and other metadata
        - other_actors: contains the positions, velocities and other metadatas of surrounding vehicles and the traffic lights
```

## Data Generation
### Data Generation with multiple CARLA Servers
In addition to the dataset, we have also provided all the scripts used for generating data and these can be modified as required for different CARLA versions. The dataset is collected by a rule-based expert agent in differnet weathers and towns.

#### Running CARLA Servers
```bash
# start 14 carla servers: ip [localhost], port [20000 - 20026]
cd carla
CUDA_VISIBLE_DEVICES=0 ./CarlaUE4.sh --world-port=20000 &
CUDA_VISIBLE_DEVICES=1 ./CarlaUE4.sh --world-port=20002 &
...
CUDA_VISIBLE_DEVICES=7 ./CarlaUE4.sh --world-port=20026 &
```

Instructions for setting up docker are available [here](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker). Pull the docker image of CARLA 0.9.14 ```docker pull carlasim/carla:0.9.14```.

Docker 18:
```
docker run -it --rm -p 2000-2002:2000-2002 --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=0 carlasim/carla:0.9.14 ./CarlaUE4.sh
```

Docker 19:
```Shell
docker run -it --rm --net=host --gpus '"device=0"' carlasim/carla:0.9.14 ./CarlaUE4.sh
```

If the docker container doesn't start properly then add another environment variable ```-e SDL_AUDIODRIVER=dsp```.

#### Run the Autopilot
Generate scripts for collecting data in batches.
```bash
cd dataset
python init_dir.py
cd ..
cd data_collection
python generate_yamls.py # You can modify fps, waypoints distribution strength ...

# If you don't need all weather, you can modify the following script
python generate_bashs.py
python generate_batch_collect.py 
cd ..
```

Run batch-run scripts of the town and route type that you need to collect.
```bash
bash data_collection/batch_run/run_route_routes_town01_long.sh
bash data_collection/batch_run/run_route_routes_town01_short.sh
...
bash data_collection/batch_run/run_route_routes_town07_tiny.sh
```

**Note1:** If you don't need all 14 kinds of weather in your dataset, you can modify the above code and scripts.

**Note2:** We also provide 7 kinds of night weather conditions in `leaderboard/team_code/auto_pilot.py`, you can modify the above code and scripts to collect the night dataset.
