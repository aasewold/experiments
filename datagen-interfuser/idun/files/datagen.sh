#!/bin/bash

export CARLA_ROOT=$1; shift
export WORK_DIR=$1; shift
export YAML_ROOT=$1; shift
export SAVE_PATH=$1; shift
export CARLA_HOST=$1; shift
export CARLA_PORT=$1; shift
export CARLA_TM_PORT=$1; shift
export ROUTES=$1; shift
export SCENARIOS=$1; shift
export WEATHER_CONFIG_INDEX=$1; shift


export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:${WORK_DIR}/leaderboard
export PYTHONPATH=$PYTHONPATH:${WORK_DIR}/leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:${WORK_DIR}/scenario_runner

export LEADERBOARD_ROOT=${WORK_DIR}/leaderboard

export CHECKPOINT_ENDPOINT=${SAVE_PATH}/checkpoint.json
export TEAM_CONFIG=${YAML_ROOT}/weather-${WEATHER_CONFIG_INDEX}.yaml
export TRAFFIC_SEED=42
export CARLA_SEED=42
export SCENARIOS=${LEADERBOARD_ROOT}/data/${SCENARIOS}
export ROUTES=${LEADERBOARD_ROOT}/data/${ROUTES}
export CHALLENGE_TRACK_CODENAME=SENSORS
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs
export TEAM_AGENT=${LEADERBOARD_ROOT}/team_code/auto_pilot.py # agent
export RESUME=True
export ACTOR_AMOUNT=town

mkdir -p $(dirname ${CHECKPOINT_ENDPOINT})
mkdir -p ${SAVE_PATH}

python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--record=${RECORD_PATH} \
--resume=${RESUME} \
--port=${CARLA_PORT} \
--host=${CARLA_HOST} \
--trafficManagerPort=${CARLA_TM_PORT} \
--carlaProviderSeed=${CARLA_SEED} \
--trafficManagerSeed=${TRAFFIC_SEED} \
--timeout=5
