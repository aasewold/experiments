#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"
CARLA_IMAGE="mathiaswold/carla:0.9.14"
CARLA_VERSION=0.9.14
INTERFUSER_COMMIT=0.9.14

select_evaluation

run_interfuser
