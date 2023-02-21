#!/bin/bash

echo hey

export CARLA_ROOT=$1; shift
export WORK_DIR=$1; shift
export SAVE_PATH=$1; shift
export CARLA_HOST=$1; shift
export CARLA_PORT=$1; shift
export CARLA_TM_PORT=$1; shift
export SCENARIOS=$1; shift
export ROUTES=$1; shift

export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg
export SCENARIO_RUNNER_ROOT=${WORK_DIR}/scenario_runner
export LEADERBOARD_ROOT=${WORK_DIR}/leaderboard
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}

export REPETITIONS=1
export CHALLENGE_TRACK_CODENAME=MAP
export CHECKPOINT_ENDPOINT=${SAVE_PATH}/checkpoint.json
export TEAM_AGENT=${WORK_DIR}/team_code_autopilot/data_agent.py
export DEBUG_CHALLENGE=0
export RESUME=1
export DATAGEN=1

python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator_local.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--resume=${RESUME} \
--host=${CARLA_HOST} \
--port=${CARLA_PORT} \
--trafficManagerPort=${CARLA_TM_PORT}
