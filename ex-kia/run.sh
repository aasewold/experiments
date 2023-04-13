#!/bin/bash

source ../common/utils.sh

export CARLA_VERSION=0.9.14
export TRANSFUSER_COMMIT="$(get_commit_hash experiments/${CARLA_VERSION})"
export MODEL_PATH=./models/prefuser
export DATASET_PATH=/data/ad/recordings_DW

docker compose run --build -it --rm transfuser "$@"
