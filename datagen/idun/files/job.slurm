#! /usr/bin/bash
#SBATCH --job-name="carla-datagen"
#SBATCH --partition=GPUQ
#SBATCH --account=share-ie-idi
#SBATCH --time=07-00:00:00
#SBATCH --constraint="A100|V100"

#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16000

#SBATCH --array=1-1

time_start=$(date +%s)

echo Starting at $(date +'%Y-%m-%d_%H-%M-%S')
echo "job : $SLURM_ARRAY_JOB_ID"
echo "index: $SLURM_ARRAY_TASK_ID / $SLURM_ARRAY_TASK_COUNT"

SIF_DIR=$HOME/work/thesis/datagen/sif
ROUTES_DIR=$PWD/input

ROUTELINE=$(sed "${SLURM_ARRAY_TASK_ID}q;d" $ROUTES_DIR/routes.csv)
ROUTE=$(echo $ROUTELINE | cut -d, -f1)
SCENARIO=$(echo $ROUTELINE | cut -d, -f2)
echo "Route: $ROUTE"
echo "Scenario: $SCENARIO"

SAVE_NAME=${SLURM_ARRAY_TASK_ID}-$(basename $ROUTE .xml)
SAVE_PATH=data/$SAVE_NAME

echo
echo "Purging modules"
module list
module purge
echo

mkdir -p $SAVE_PATH
echo "Generating data into $SAVE_PATH"

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

    local attempts=0
    while ! is_port_available $port; do
        port=$((2000+$RANDOM))
        attempts=$((attempts+1))
        if [ $attempts -gt 100 ]; then
            echo "Could not find available port" >&2
            exit 1
        fi
    done

    echo $port
}

check_checkpoint() {
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
        return 0
    fi
    return 1
}

attempt=0
while :; do

attempt=$((attempt+1))
echo "Starting attempt $attempt at $(date +'%Y-%m-%d_%H-%M-%S')"

if check_checkpoint; then
    echo "Checkpoint OK, skipping"
    break
fi

export CARLA_RPC_PORT=$(find_port 50000)
export CARLA_STREAMING_PORT=$(find_port 51000)
export CARLA_SECONDARY_PORT=$(find_port 52000)
export CARLA_TM_PORT=$(find_port 53000)
echo "Running CARLA on port $CARLA_RPC_PORT/$CARLA_STREAMING_PORT/$CARLA_SECONDARY_PORT/$CARLA_TM_PORT"

echo Starting server
singularity exec \
    --nv \
    $SIF_DIR/carla.sif \
        /home/carla/CarlaUE4.sh \
            -slurm-task-id=${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}-${attempt} \
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

SAVE_PATH=$(realpath $SAVE_PATH)
singularity run \
    --nv \
    --pwd /pwd \
    --bind $PWD:/pwd \
    --bind $ROUTES_DIR:/routes \
    --bind $SAVE_PATH:/results \
    $SIF_DIR/transfuser.sif \
    /bin/bash ./datagen.sh \
        /transfuser/carla /transfuser /results \
        localhost $CARLA_RPC_PORT $CARLA_TM_PORT \
        $ROUTE $SCENARIO

echo Client exited with code $?

echo Killing $CARLA_PID
pkill -9 -P $CARLA_PID
kill -9 $CARLA_PID
wait $CARLA_PID

echo "CARLA (apptainer) exited with code $?"

if check_checkpoint; then
    echo "Checkpoint OK, skipping"
    break
fi

echo Sleeping before next attempt
sleep 30

done

echo "Data generation finished successfully after $attempt attempt(s)"
echo "Finished at $(date +'%Y-%m-%d_%H-%M-%S')"

time_end=$(date +%s)
duration=$((time_end-time_start))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))
seconds=$(( (duration % 3600) % 60 ))
echo "Runtime: $hours:$minutes:$seconds (hh:mm:ss)"
