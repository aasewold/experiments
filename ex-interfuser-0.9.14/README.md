# Experiments with InterFuser in CARLA version 0.9.14

This folder is used to evaluate a InterFuser model in CARLA version 0.9.14 on various benchmarks.

Usage:
    
```bash
./setup.sh
./run.sh
```

The `setup.sh` script will download and verify the pretrained InterFuser model. 

The `run.sh` script will ask you to select a model from the `../models` folder, the sensor configuration to use (original or Kia-like), and which benchmark to run before starting the evaluation. The results will be saved in the `results` folder.
