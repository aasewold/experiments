#!/bin/bash

source ../common/utils.sh

CARLA_VERSION=0.9.14

select_model "../models"
choose_0_9_14_experiment
select_evaluation

run_interfuser
