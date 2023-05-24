#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"

choose_0_9_14_experiment

CARLA_VERSION=0.9.14
INTERFUSER_COMMIT=$COMMIT

select_evaluation

run_interfuser
