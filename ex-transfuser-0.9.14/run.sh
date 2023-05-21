#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"
CARLA_VERSION=0.9.14
TRANSFUSER_COMMIT=experiments/kia
export SAVE_PATH=/results/viz
export CARLA_IMAGE=mathiaswold/carla:0.9.14

run_transfuser
