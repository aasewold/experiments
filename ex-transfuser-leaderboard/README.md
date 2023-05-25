# Experiments with TransFuser on CARLA Leaderboard

This folder is used to evaluate a TransFuser model on the official CARLA Leaderboard. Currently only CARLA version 0.9.10 is supported.

Usage:
    
```bash
./run.sh <model_path>
```


The `run.sh` script will build a Docker image for the given model and submit the model for evaluation on the CARLA Leaderboard.
