#!/bin/bash

export CARLA_ROOT=carla
export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:scenario_runner

export LEADERBOARD_ROOT=leaderboard
export CHALLENGE_TRACK_CODENAME=SENSORS
export PORT=2000 # same as the carla server port
export TM_PORT=2500 # port for traffic manager, required when spawning multiple servers/clients
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs

export TEAM_CONFIG=leaderboard/team_code/interfuser_config.py # model checkpoint, not required for expert
export SAVE_PATH=data/eval # path for saving episodes while evaluating
export RESUME=True

if [ -f "models/autopilot" ]; then
    export TEAM_AGENT=leaderboard/team_code/auto_pilot.py # agent
    export CHALLENGE_TRACK_CODENAME=MAP
    unset SAVE_PATH
else
    export TEAM_AGENT=leaderboard/team_code/interfuser_agent.py # agent
fi

if [ -z "$EVALUATION" ]; then
    echo "EVALUATION is not set, please set it to one of the following:"
    echo "  - town05"
    echo "  - longest6"
    echo "  - 42routes"
    exit 1
fi

if [ "$EVALUATION" = "town05" ]; then
    export ROUTES=leaderboard/data/evaluation_routes/routes_town05_long.xml
    export SCENARIOS=leaderboard/data/scenarios/town05_all_scenarios.json
    export CHECKPOINT_ENDPOINT=results/town05.json
elif [ "$EVALUATION" = "longest6" ]; then
    export ROUTES=leaderboard/data/longest6/longest6.xml
    export SCENARIOS=leaderboard/data/longest6/eval_scenarios.json
    export CHECKPOINT_ENDPOINT=results/longest6.json
    export LONGEST_6_EVAL=True
else
    export ROUTES=leaderboard/data/42routes/42routes.xml
    export SCENARIOS=leaderboard/data/42routes/42scenarios.json
    export CHECKPOINT_ENDPOINT=results/42routes.json
fi


logfile=results/log.txt

echo "Starting at $(date +"%Y-%m-%d %H:%M:%S")" >> $logfile

echo "EVALUATION: $EVALUATION" >> $logfile
echo "ROUTES: $ROUTES" >> $logfile
echo "SCENARIOS: $SCENARIOS" >> $logfile
echo "CHECKPOINT_ENDPOINT: $CHECKPOINT_ENDPOINT" >> $logfile

echo >> $logfile
echo "Environment:" >> $logfile
env | sort >> $logfile
echo "---------------------" >> $logfile
echo >> $logfile



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
--port=${PORT} \
--timeout=60 \
--trafficManagerPort=${TM_PORT} \
    2>&1 | tee -a "$logfile"
RET="${PIPESTATUS[0]}"

echo >> $logfile
echo "Finished at $(date +"%Y-%m-%d %H:%M:%S")" >> $logfile
echo >> $logfile

exit $RET
