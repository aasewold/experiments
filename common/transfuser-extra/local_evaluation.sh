export CARLA_ROOT="carla"
export WORK_DIR="."

export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$(echo ${CARLA_ROOT}/PythonAPI/carla/dist/carla-*-py3.7-linux-x86_64.egg)
export SCENARIO_RUNNER_ROOT=${WORK_DIR}/scenario_runner
export LEADERBOARD_ROOT=${WORK_DIR}/leaderboard
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}

export TEAM_CONFIG=/model

export REPETITIONS=1
export CHALLENGE_TRACK_CODENAME=SENSORS
export DEBUG_CHALLENGE=0
export RESUME=1
export DATAGEN=0

if [ -f "/model/autopilot" ]; then
    export TEAM_AGENT=${WORK_DIR}/team_code_autopilot/autopilot.py
    export CHALLENGE_TRACK_CODENAME=MAP
    unset SAVE_PATH
else
    export TEAM_AGENT=${WORK_DIR}/team_code_transfuser/submission_agent.py
fi

if [ -z "$EVALUATION" ]; then
    echo "EVALUATION is not set, please set it to one of the following:"
    echo "  - longest6"
    echo "  - town05"
    echo "  - 42routes"
    exit 1
fi

if [ "$EVALUATION" = "town05" ]; then
    export ROUTES=${WORK_DIR}/leaderboard/data/town05_long/routes_town05_long.xml
    export SCENARIOS=${WORK_DIR}/leaderboard/data/town05_long/town05_all_scenarios.json
    export CHECKPOINT_ENDPOINT=/results/town05.json
elif [ "$EVALUATION" = "42routes" ]; then
    export ROUTES=${WORK_DIR}/leaderboard/data/42routes/42routes.xml
    export SCENARIOS=${WORK_DIR}/leaderboard/data/42routes/42scenarios.json
    export CHECKPOINT_ENDPOINT=/results/42routes.json
else
    export ROUTES=${WORK_DIR}/leaderboard/data/longest6/longest6.xml
    export SCENARIOS=${WORK_DIR}/leaderboard/data/longest6/eval_scenarios.json
    export CHECKPOINT_ENDPOINT=/results/longest6.json
fi

logfile=/results/log.txt

echo "Starting at $(date +"%Y-%m-%d %H:%M:%S")" >> $logfile

echo >> $logfile
echo "EVALUATION: $EVALUATION" >> $logfile
echo "ROUTES: $ROUTES" >> $logfile
echo "SCENARIOS: $SCENARIOS" >> $logfile
echo "CHECKPOINT_ENDPOINT: $CHECKPOINT_ENDPOINT" >> $logfile

echo >> $logfile
echo "Environment:" >> $logfile
env | sort >> $logfile
echo "---------------------" >> $logfile
echo >> $logfile

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
    2>&1 | tee -a "$logfile"
RET="${PIPESTATUS[0]}"

echo >> $logfile
echo "Finished at $(date +"%Y-%m-%d %H:%M:%S")" >> $logfile
echo >> $logfile

exit $RET
