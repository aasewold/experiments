#!/bin/bash

source ../../common/utils.sh

export CARLA_VERSION="0.9.14"
export TRANSFUSER_COMMIT=$(get_commit_hash "experiments/0.9.14")
export MODEL_PATH=../models/transfuser-2023-03-17-epoch41/
export SAVE_PATH="/work/viz/$(date +%Y-%m-%d-%H-%M-%S)"

docker compose run -it --rm --build --user $UID transfuser python3 -m src.scripts.transfuser "$@"
