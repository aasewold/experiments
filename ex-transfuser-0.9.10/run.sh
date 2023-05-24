#!/bin/bash

source ../common/utils.sh

CARLA_VERSION=0.9.10.1
COMMIT=experiments/0.9.10

select_model "../models/"
select_evaluation

run_transfuser
