#!/bin/bash

source ../common/utils.sh

export DATASET_PATH="$1"; shift

if [ ! -d "$DATASET_PATH" ]; then
    echo "Dataset path does not exist: $DATASET_PATH"
    exit 1
fi

run_in_screen "train-transfuser" \
    "docker compose up --build --abort-on-container-exit"
