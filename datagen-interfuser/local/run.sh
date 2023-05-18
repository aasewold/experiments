#!/bin/bash

set -euo pipefail

source ../../common/utils.sh

OUTPUT_DIR_ROOT=/nap02data/work/aasewold/datagen/interfuser

RESUME=${RESUME:-}
NUM_JOBS=${NUM_JOBS:-3}

if [ -z "$RESUME" ]; then
    # Setup output directory
    output_dir_name=$(date +%Y-%m-%d_%H-%M-%S)
    output_dir=$OUTPUT_DIR_ROOT/$output_dir_name
    mkdir -p $output_dir
    (
        cd $OUTPUT_DIR_ROOT
        ln -Tsf $output_dir_name latest
    )
    echo "Starting new run in $output_dir"
else
    # Resume from existing output directory
    output_dir=$OUTPUT_DIR_ROOT/$RESUME
    if [ ! -d $output_dir ]; then
        echo "Resume directory $output_dir does not exist" >&2
        exit 1
    fi
    echo "Resuming from $output_dir"
fi

run_in_screen "interfuser-datagen-vcxr" \
    "cat files/input/route_configs.csv | parallel --line-buffer -j$NUM_JOBS ./job.sh $output_dir" 
