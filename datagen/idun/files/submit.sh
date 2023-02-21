#!/bin/bash

set -euo pipefail

routes_file=input/routes.csv
num_routes=$(wc -l < $routes_file)

output_dir_name=$(date +%Y-%m-%d_%H-%M-%S)
output_dir=output/$output_dir_name
mkdir -p $output_dir

(
    cd output
    ln -sf $output_dir_name latest
)

job_in=job.slurm
job_out=$output_dir/job.slurm

sed "s/#SBATCH --array=.*/#SBATCH --array=1-$num_routes/" < $job_in > $job_out

cd $output_dir
sbatch job.slurm
