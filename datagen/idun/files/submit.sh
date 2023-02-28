#!/bin/bash

set -euo pipefail

# Check Lustre quotas
lfs quota -u $USER /cluster
echo

# Setup output directory
output_dir_name=$(date +%Y-%m-%d_%H-%M-%S)
output_dir=output/$output_dir_name
mkdir -p $output_dir
(
    cd output
    ln -Tsf $output_dir_name latest
)

# Copy all input data to output directory
cp job.slurm datagen.sh $output_dir
cp -r input $output_dir

cd $output_dir

# Calculate the correct number of nodes, one for each route file
routes_file=input/routes.csv
num_routes=$(wc -l < $routes_file)
sed "s/#SBATCH --array=.*/#SBATCH --array=1-$num_routes/" -i job.slurm

# Submit the job
mkdir logs
sbatch \
    -o logs/slurm-%A_%a.out \
    -e logs/slurm-%A_%a.out \
    job.slurm
