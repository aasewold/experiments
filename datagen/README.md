# Data generation

This folder contains tools for generating TransFuser datasets.


## On IDUN

Run

```sh
make job CARLA_VERSION=0.9.14 TRANSFUSER_COMMIT=d8fc8d7
```
and wait. This will:
- build CARLA and Transfuser docker images
- convert those to Singularity/Apptainer .sif-images
- rsync those to IDUN
- submit a Slurm job to generate data
