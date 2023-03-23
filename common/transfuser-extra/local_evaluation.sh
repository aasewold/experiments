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
export CHECKPOINT_ENDPOINT=/results/transfuser_longest6.json
export ROUTES=${WORK_DIR}/leaderboard/data/longest6/longest6.xml
export SCENARIOS=${WORK_DIR}/leaderboard/data/longest6/eval_scenarios.json

export TEAM_AGENT=${WORK_DIR}/team_code_transfuser/submission_agent.py
export REPETITIONS=1
export CHALLENGE_TRACK_CODENAME=SENSORS
export DEBUG_CHALLENGE=0
export RESUME=1
export DATAGEN=0

echo "Starting at $(date +"%Y-%m-%d %H:%M:%S")" >> /results/log.txt

echo >> /results/log.txt
echo "Environment:" >> /results/log.txt
env >> /results/log.txt
echo "---------------------" >> /results/log.txt
echo >> /results/log.txt

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
    2>&1 | tee -a "/results/log.txt"
RET="${PIPESTATUS[0]}"

echo >> /results/log.txt
echo "Finished at $(date +"%Y-%m-%d %H:%M:%S")" >> /results/log.txt
echo >> /results/log.txt

exit $RET
