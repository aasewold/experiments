#!/bin/bash

source ../../common/utils.sh

export CARLA_VERSION="0.9.14"
export INTERFUSER_COMMIT=$(get_commit_hash_interfuser "0.9.14")
export MODEL_PATH=../models/interfuser
export SAVE_PATH="/work/viz-interfuser/$(date +%Y-%m-%d-%H-%M-%S)"

mkdir -p "${SAVE_PATH:1}"

docker compose -p eval-interfuser-kia -f interfuser.docker-compose.yml run -it --rm --build --user $UID interfuser python3 -m src.scripts."$@"
