#! /usr/bin/bash
#SBATCH --job-name="carla-datagen"
#SBATCH --partition=GPUQ
#SBATCH --account=share-ie-idi
#SBATCH --time=05:00:00

#SBATCH --ntasks=1
#SBATCH --gres=gpu:1

#SBATCH --array=1-1

echo "date: $(date +'%Y-%m-%d_%H-%M-%S')"
echo "job : $SLURM_ARRAY_JOB_ID"
echo "index: $SLURM_ARRAY_TASK_ID / $SLURM_ARRAY_TASK_COUNT"

DATAGEN_ROOT=$HOME/work/thesis/datagen
SIFDIR=$DATAGEN_ROOT/sif
CONFDIR=$DATAGEN_ROOT/config

ROUTELINE=$(sed "${SLURM_ARRAY_TASK_ID}q;d" $CONFDIR/routes.csv)
ROUTE=$(echo $ROUTELINE | cut -d, -f1)
SCENARIO=$(echo $ROUTELINE | cut -d, -f2)
echo "Route: $ROUTE"
echo "Scenario: $SCENARIO"

SAVE_PATH=data/${SLURM_ARRAY_TASK_ID}-$(basename $ROUTE)
mkdir -p $SAVE_PATH
echo "Generating data into $SAVE_PATH"

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

sleep 30
echo Starting client

SAVE_PATH=$(realpath $SAVE_PATH)
singularity run \
        --nv \
        --bind $DATAGEN_ROOT:/datagen \
        --bind $ROUTES_PATH:/routes \
        --bind $SAVE_PATH:/results \
        $SIFDIR/transfuser.sif \
        /bin/bash /datagen/datagen.sh \
                /transfuser/carla /transfuser /results \
                localhost $CARLA_PORT $CARLA_TM_PORT \
                $ROUTE $SCENARIO


echo Killing $CARLA_PID
kill $CARLA_PID

echo Bye
