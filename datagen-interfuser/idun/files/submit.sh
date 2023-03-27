#!/bin/bash

set -euo pipefail

# Check Lustre quotas
lfs quota -u $USER /cluster
echo

if [ -z "$RESUME" ]; then
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
    echo "Starting new run in $output_dir"
else
    # Resume from existing output directory
    output_dir=output/$RESUME
    if [ ! -d $output_dir ]; then
        echo "Resume directory $output_dir does not exist" >&2
        exit 1
    fi

    cp job.slurm datagen.sh $output_dir
    echo "Resuming from $output_dir"
fi

cd $output_dir


if [ -z "$ROUTES" ]; then
    # Calculate the correct number of nodes, one for each route file
    routes_file=input/route_configs.csv
    num_routes=$(wc -l < $routes_file)
    ROUTES="1-$num_routes"
fi

echo "Running routes $ROUTES"
sed "s/#SBATCH --array=.*/#SBATCH --array=$ROUTES/" -i job.slurm


# Submit the job
mkdir -p logs
sbatch \
    -o logs/slurm-%A_%a.out \
    -e logs/slurm-%A_%a.out \
    job.slurm
