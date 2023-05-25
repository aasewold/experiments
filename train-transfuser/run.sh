#!/bin/bash

source ../common/utils.sh

export DATASET_PATH="$1"; shift

export CARLA_VERSION=0.9.14
export TRANSFUSER_COMMIT="$(get_commit_hash experiments/${CARLA_VERSION})"

if [ ! -d "$DATASET_PATH" ]; then
    echo "Dataset path does not exist: $DATASET_PATH"
    exit 1
fi
export DATASET_PATH="$(realpath "$DATASET_PATH")"

run_in_screen "train-transfuser" \
    "docker compose up --build"
