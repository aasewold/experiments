#!/bin/bash

source ../../common/utils.sh

export CARLA_IMAGE="mathiaswold/carla:0.9.14"
export CARLA_VERSION=0.9.14
export INTERFUSER_COMMIT=$(get_commit_hash_interfuser "0.9.14")

SAVE_ROOT=$1; shift
ROUTELINE=$1; shift

export ROUTES=$(echo $ROUTELINE | cut -d, -f1)
export SCENARIOS=$(echo $ROUTELINE | cut -d, -f2)
export WEATHER_CONFIG_INDEX=$(echo $ROUTELINE | cut -d, -f3 | tr -d $'\r')

export SAVE_PATH=$SAVE_ROOT/$PARALLEL_SEQ-w${WEATHER_CONFIG_INDEX}-$(basename $ROUTES .xml)

mkdir -p $SAVE_PATH

time_start=$(date +%s)
date_start=$(date +'%Y-%m-%d-%H-%M-%S')
echo Starting job ${PARALLEL_SEQ} at $date_start

exec >> $SAVE_ROOT/$PARALLEL_SEQ.out
exec 2>&1

echo "Route: $ROUTES"
echo "Scenario: $SCENARIOS"
echo "Weather config index: $WEATHER_CONFIG_INDEX"


echo "Generating data into $SAVE_PATH"
echo "----------------------------------------"

compose_name=interfuser-datagen-$date_start-job-$PARALLEL_SEQ

attempt=0
while :; do

attempt=$((attempt+1))
echo Starting attempt $attempt

docker compose -p $compose_name up --build --exit-code-from interfuser

EXIT_CODE=$?
echo "Docker compose exited with code $EXIT_CODE"

sleep 5

echo "Docker compose down..."
docker compose -p $compose_name down

echo "Sleeping for 10 seconds before restarting"

sleep 10

# Check checkpoint.json status
python3 <<EOF
import sys
import json
with open('$SAVE_PATH/checkpoint.json') as f:
    data = json.load(f)
checkpoint = data.get('_checkpoint', {})
progress = checkpoint.get('progress', [])
if len(progress) != 2:
    print('Invalid progress:', progress, file=sys.stderr)
    sys.exit(1)
if progress[0] != progress[1]:
    print('Progress mismatch:', progress, file=sys.stderr)
    sys.exit(1)
EOF

checkpoint_good=$?
if [ $checkpoint_good -eq 0 ]; then
    break
fi

done

echo "Data generation finished successfully after $attempt attempt(s)"
echo "Finished at $(date +'%Y-%m-%d_%H-%M-%S')"
time_end=$(date +%s)
duration=$((time_end-time_start))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))
seconds=$(( (duration % 3600) % 60 ))
echo "Runtime: $hours:$minutes:$seconds (hh:mm:ss)"
