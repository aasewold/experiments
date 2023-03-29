#!/bin/bash

source ../common/utils.sh

export DATASET_PATH="$1"; shift
export RESUME_PATH="$1"; shift


export CARLA_VERSION=0.9.14
export INTERFUSER_COMMIT="$(get_commit_hash_interfuser 0.9.14)"

if [ ! -d "$DATASET_PATH" ]; then
    echo "Dataset path does not exist: $DATASET_PATH"
    exit 1
fi

echo "DATASET_PATH: $DATASET_PATH"
echo "RESUME_PATH: $RESUME_PATH"

run_in_screen "train-interfuser" \
    "docker compose up --build"
