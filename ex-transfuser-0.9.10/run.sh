#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"
CARLA_VERSION=0.9.10.1
TRANSFUSER_COMMIT=experiments/0.9.10

select_evaluation

run_transfuser
