# Experiments

This repository contains code for reproducing the experiments described in our master's thesis. See README in each folder for usage instructions.

Short overview of the folders:
- `common`: Contains scripts and Dockerfiles shared by multiple experiments.
- `datagen-*`: Used to generate datasets for the training.
- `train-*`: Used to train the models.
- `models`: Contains the trained TransFuser and InterFuser models.
- `ex-[transfuser|interfuser]-[0.9.10|0.9.14]`: Used to evaluate trained models in CARLA benchmarks. 
- `ex-kia`: Used to evaluate trained models on real-world data.
- `ex-transfuser-leaderboard`: Used to submit TransFuser models for evaluation on the CARLA Leaderboard.
