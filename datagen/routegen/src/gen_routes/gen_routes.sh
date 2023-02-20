#!/bin/bash

set -e

export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg
export SCENARIO_RUNNER_ROOT=${WORK_DIR}/scenario_runner
export LEADERBOARD_ROOT=${WORK_DIR}/leaderboard
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}

DIR=$(dirname "$0")

python3 ${DIR}/gen_routes_for_scen_1_3_4.py \
--save_dir=${RESULTS_DIR}/routes \
--scenarios_dir=${RESULTS_DIR}/scenarios/Scenario1/ \
--road_type=curved 

python3 ${DIR}/gen_routes_for_scen_1_3_4.py \
--save_dir=${RESULTS_DIR}/routes \
--scenarios_dir=${RESULTS_DIR}/scenarios/Scenario3/ \
--road_type=curved 

python3 ${DIR}/gen_routes_for_scen_1_3_4.py \
--save_dir=${RESULTS_DIR}/routes \
--scenarios_dir=${RESULTS_DIR}/scenarios/Scenario4/ \
--road_type=junction 

python3 ${DIR}/gen_routes_for_scen_7_8_9.py \
--save_dir=${RESULTS_DIR}/routes \
--scenarios_dir=${RESULTS_DIR}/scenarios/

python3 ${DIR}/gen_routes_for_scen_10.py \
--save_dir=${RESULTS_DIR}/routes \
--scenarios_dir=${RESULTS_DIR}/scenarios/Scenario10/

python3 ${DIR}/gen_routes_lane_change.py \
--save_dir=${RESULTS_DIR}/routes
