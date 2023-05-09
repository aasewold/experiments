# Data generation

This folder contains tools for generating TransFuser datasets.

## Instructions

Generate route and scenario definitions with the following sequence.
Note that the simulator may get stuck and/or crash, so you might
have to clean up left-over Docker containers and restart generation.
    
```sh
cd routegen
make scenarios
make routes
make csv
make copy
```

## To Idun and beyond

Then we'd like to generate the dataset on Idun.
In theory, the following should be enough:

```sh
cd idun
make job CARLA_VERSION=0.9.14 TRANSFUSER_COMMIT=experiments/0.9.14
```
and wait. This will:
- build CARLA and TransFuser docker images
- convert those to Singularity/Apptainer .sif-images
- rsync those to Idun
- submit a Slurm job to generate data

All files are stored under `work/thesis/datagen` on Idun,
however this can be changed by modifying `$IDUN_WORKDIR` in the `Makefile`.