#!/bin/bash

SCRIPT=$1; shift
export TRIP=$1; shift

source ../../common/utils.sh

export CARLA_VERSION="0.9.14"
export TRANSFUSER_COMMIT=$(get_commit_hash "experiments/kia")
export MODEL_PATH=../models/transfuser-2023-03-17-epoch41/
# export MODEL_PATH=../models/prefuser/

export RUN="$(date +%Y-%m-%d-%H-%M-%S)"
export RUN_PATH="work/out/$TRIP/$SCRIPT/$RUN"
mkdir -p "$RUN_PATH"

docker compose run -it --rm --build --user $UID transfuser python3 -m src.scripts.$SCRIPT $TRIP "$@"
