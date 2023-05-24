#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"
CARLA_VERSION=0.9.10.1
INTERFUSER_COMMIT=main

select_evaluation

run_interfuser
