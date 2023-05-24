#!/bin/bash

SCRIPT=$1; shift
export TRIP=$1; shift

source ../../common/utils.sh

export CARLA_VERSION="0.9.14"
export INTERFUSER_COMMIT=$(get_commit_hash_interfuser "experiments/0.9.14")

select_model "../../models"

export RUN="$(date +%Y-%m-%d-%H-%M-%S)"
export RUN_PATH="work/out/$TRIP/$SCRIPT/$RUN"
mkdir -p "$RUN_PATH/viz"

export METADATA_TEXT_COLOR="255,255,255"

docker compose -p eval-interfuser-kia -f interfuser.docker-compose.yml run -it --rm --build --user $UID interfuser python3 -m src.scripts.$SCRIPT $TRIP "$@"
