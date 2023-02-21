#!/bin/bash

set -euo pipefail

dir=$(dirname $0)

routes_file=$dir/config/routes.csv
num_routes=$(wc -l < $routes_file)

job_in=$dir/job.slurm
job_out=$dir/.job.slurm.tmp.n$num_routes
cp $job_in $job_out || { echo "$job_out already exists, please remove it."; exit 1; }

sed "s/#SBATCH --array=.*/#SBATCH --array=1-$num_routes/" -i $job_out

sbatch $job_out
rm $job_out
