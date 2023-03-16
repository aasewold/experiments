#! /usr/bin/bash
#SBATCH --job-name="carla-datagen-interfuser"
#SBATCH --partition=GPUQ
#SBATCH --account=share-ie-idi
#SBATCH --time=07-00:00:00

#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --constraint="V100|P100"

#SBATCH --array=1-1

time_start=$(date +%s)

echo Starting at $(date +'%Y-%m-%d_%H-%M-%S')
echo "job : $SLURM_ARRAY_JOB_ID"
echo "index: $SLURM_ARRAY_TASK_ID / $SLURM_ARRAY_TASK_COUNT"

SIF_DIR=$HOME/work/thesis/datagen/sif
INPUT_DIR=$PWD/input

YAMLS_DIR=$INPUT_DIR/yamls

ROUTELINE=$(sed "${SLURM_ARRAY_TASK_ID}q;d" $INPUT_DIR/route_configs.csv)
ROUTE=$(echo $ROUTELINE | cut -d, -f1)
SCENARIO=$(echo $ROUTELINE | cut -d, -f2)
WEATHER_CONFIG_INDEX=$(echo $ROUTELINE | cut -d, -f3 | tr -d $'\r')

echo "Route: $ROUTE"
echo "Scenario: $SCENARIO"
echo "Weather config index: $WEATHER_CONFIG_INDEX"

SAVE_ROOT=data/dataset
SAVE_NAME=${SLURM_ARRAY_TASK_ID}-$(basename $ROUTE .xml)

CHECKPOINT_ENDPOINT=${SAVE_ROOT}/weather-${WEATHER_CONFIG_INDEX}/results/${SAVE_NAME}.json

TAR_NAME=$SAVE_NAME.tar.gz
TAR_PATH=data/$TAR_NAME

echo "Checkpoint endpoint: $CHECKPOINT_ENDPOINT"

archive_data() (
    echo "Archiving files to $TAR_NAME"
    cd data
    tar -czf $TAR_NAME.tmp $SAVE_ROOT
    if [ $? -eq 0 ]; then
        echo "Archiving successful, removing $SAVE_ROOT"
        mv $TAR_NAME.tmp $TAR_NAME
        rm -r $SAVE_ROOT
    else
        echo "Archiving failed, keeping $SAVE_ROOT"
    fi
)

if [ -f $TAR_PATH ]; then
    echo "Data already exists at $TAR_NAME, skipping."
    exit 0
fi

if [ -f $TAR_PATH.tmp ]; then
    echo "Data generated, but archiving failed last time, retrying."
    rm $TAR_PATH.tmp
    archive_data
    exit 0
fi

mkdir -p $SAVE_ROOT
echo "Generating data into $SAVE_ROOT"

is_port_available() {
    local port=$1
    if ss -tulpn | grep -q ":$port "; then
        return 1
    fi
    if nc -z localhost $port; then
        return 1
    fi
    return 0
}

find_port() {
    local port=$(($1+$SLURM_ARRAY_TASK_ID))

    if ! is_port_available $port; then
        port=$((port+10000))
    fi

    local attempts=0
    while ! is_port_available $port; do
        port=$((port+1))
        attempts=$((attempts+1))
        if [ $attempts -gt 100 ]; then
            echo "Could not find available port" >&2
            exit 1
        fi
    done

    echo $port
}

attempt=0
while :; do

attempt=$((attempt+1))
echo Starting attempt $attempt

export CARLA_RPC_PORT=$(find_port 30000)
export CARLA_STREAMING_PORT=$(find_port 31000)
export CARLA_SECONDARY_PORT=$(find_port 32000)
export CARLA_TM_PORT=$(find_port 33000)
echo "Running CARLA on port $CARLA_RPC_PORT/$CARLA_STREAMING_PORT/$CARLA_SECONDARY_PORT/$CARLA_TM_PORT"

echo Starting server
singularity exec \
    --nv \
    $SIF_DIR/carla.sif \
        /home/carla/CarlaUE4.sh \
            -RenderOffScreen \
            -carla-rpc-port=$CARLA_RPC_PORT \
            -carla-streaming-port=$CARLA_STREAMING_PORT \
            -carla-secondary-port=$CARLA_SECONDARY_PORT \
    > >(gzip > logs/carla-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}-${attempt}.gz) \
    2>&1 \
    &
CARLA_PID=$!

echo Sleeping
sleep 30

echo
echo Starting client

SAVE_ROOT=$(realpath $SAVE_ROOT)
singularity run \
    --nv \
    --pwd /pwd \
    --bind $PWD:/pwd \
    --bind $YAMLS_DIR:/yamls \
    --bind $SAVE_ROOT:/results \
    $SIF_DIR/interfuser.sif \
    /bin/bash ./datagen.sh \
        /interfuser/carla /interfuser /yamls \
        /results $SAVE_NAME $CHECKPOINT_ENDPOINT \
        localhost $CARLA_RPC_PORT $CARLA_TM_PORT \
        $ROUTE $SCENARIO $WEATHER_CONFIG_INDEX 

echo Client exited with code $?

echo Killing $CARLA_PID
kill $CARLA_PID
wait $CARLA_PID

echo CARLA exited with code $?

# Check checkpoint.json status
python3 <<EOF
import sys
import json
import os

if not os.path.exists('$CHECKPOINT_ENDPOINT'):
    print('Checkpoint file not found', file=sys.stderr)
    sys.exit(1)
with open('$CHECKPOINT_ENDPOINT') as f:
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

archive_data

echo "Finished at $(date +'%Y-%m-%d_%H-%M-%S')"

time_end=$(date +%s)
duration=$((time_end-time_start))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))
seconds=$(( (duration % 3600) % 60 ))
echo "Runtime: $hours:$minutes:$seconds (hh:mm:ss)"
