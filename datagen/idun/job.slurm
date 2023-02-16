#! /usr/bin/bash
#SBATCH --job-name="carla-datagen"
#SBATCH --partition=GPUQ
#SBATCH --account=share-ie-idi
#SBATCH --time=05:00:00

#SBATCH --ntasks=1
#SBATCH --gres=gpu:1

#SBATCH --array=1-1

echo "Jobbnummer: ${SLURM_JOB_ID}"
echo "Task-id innad i array: ${SLURM_ARRAY_TASK_ID}"

SIFDIR=$HOME/work/thesis/datagen/sif
CONFDIR=$HOME/work/thesis/datagen/config

WORKDIR=${SLURM_SUBMIT_DIR}/jobs/${SLURM_ARRAY_JOB_ID}
mkdir -p $WORKDIR
cd $WORKDIR

if [ $SLURM_ARRAY_TASK_ID -eq $SLURM_ARRAY_TASK_MIN ]; then
        touch jobinfo
        echo "job : $SLURM_ARRAY_JOB_ID" >> jobinfo 
        echo "jobs: $SLURM_ARRAY_TASK_COUNT" >> jobinfo
        echo "date: $(date +'%Y-%m-%d_%H-%M-%S')" >> jobinfo
fi

export DATASET_PATH="data/$SLURM_ARRAY_TASK_ID"
mkdir -p $DATASET_PATH
cd $DATASET_PATH
echo "Generating data into $DATASET_PATH"

export CARLA_PORT=$((51000+$SLURM_ARRAY_TASK_ID))
export CARLA_TM_PORT=$((61000+$SLURM_ARRAY_TASK_ID))
echo "Running CARLA on port $CARLA_PORT"

echo Starting server
singularity exec \
        --nv \
        $SIFDIR/carla.sif \
                /home/carla/CarlaUE4.sh \
                        -RenderOffScreen \
                        -carla-rpc-port=$CARLA_PORT \
                        -carla-streaming-port=0 \
                        &
CARLA_PID=$!


ROUTELINE=$(sed "${SLURM_ARRAY_TASK_ID}q;d" $CONFDIR/routes.csv)
ROUTE=$(echo $ROUTELINE | cut -d, -f1)
SCENARIO=$(echo $ROUTELINE | cut -d, -f2)

echo "Route: $ROUTE"
echo "Scenario: $SCENARIO"

sleep 30
echo Starting client

SAVE_PATH=$(realpath .)
singularity run \
        --nv \
        --bind $SAVE_PATH:/results \
        $SIFDIR/transfuser.sif \
        /transfuser/leaderboard/scripts/datagen.sh \
                    /transfuser/carla /transfuser /results \
                    localhost $CARLA_PORT $CARLA_TM_PORT \
                    $ROUTE $SCENARIO


echo Killing $CARLA_PID
kill $CARLA_PID

echo Bye
