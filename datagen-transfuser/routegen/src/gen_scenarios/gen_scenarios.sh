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

mkdir -p ${RESULTS_DIR}/scenarios

cp -f ${DIR}/empty.json ${RESULTS_DIR}/scenarios/empty.json

python3 ${DIR}/gen_scenario_1_3.py --save_dir=${RESULTS_DIR}/scenarios
python3 ${DIR}/gen_scenario_4.py --save_dir=${RESULTS_DIR}/scenarios
python3 ${DIR}/gen_scenario_7_8_9.py --save_dir=${RESULTS_DIR}/scenarios
python3 ${DIR}/gen_scenario_10.py --save_dir=${RESULTS_DIR}/scenarios
