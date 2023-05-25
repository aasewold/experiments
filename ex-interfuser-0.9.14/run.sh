#!/bin/bash

source ../common/utils.sh

CARLA_VERSION=0.9.14

select_model "../models"
select_sensor_config
select_evaluation

run_interfuser
