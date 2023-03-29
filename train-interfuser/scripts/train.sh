DATASET_ROOT=/dataset/
OUTPUT_DIR=/output

NVIDIA_GPUS="$(nvidia-smi -L)"
NUM_GPUS="$(echo "$NVIDIA_GPUS" | wc -l)"
CUDA_GPUS="$(echo "$NVIDIA_GPUS" | cut -d ' ' -f 2 | tr -d ':' | head -c -1 | tr '\n' ',')"
echo "Found ${NUM_GPUS} GPUs: ${CUDA_GPUS}"
echo "${NVIDIA_GPUS}"

export CUDA_VISIBLE_DEVICES="$CUDA_GPUS"

cd interfuser

RESUME_ARG=""

if [ ! -z "$RESUME_PATH" ]; then
    RESUME_ARG="--resume $RESUME_PATH"
fi

python3 -m torch.distributed.launch --nproc_per_node=$NUM_GPUS \
    train.py $DATASET_ROOT --dataset carla \
    --train-towns 1 2 3 4 6 7 \
    --val-towns 5 \
    --train-weathers 0 1 6 7 12 17 20 \
    --val-weathers 2 4 11 14 \
    --model interfuser_baseline --sched cosine --epochs 25 --warmup-epochs 5 --lr 0.0005 --batch-size 16  -j 16 --no-prefetcher --eval-metric l1_error \
    --opt adamw --opt-eps 1e-8 --weight-decay 0.05  \
    --scale 0.9 1.1 --saver-decreasing --clip-grad 10 --freeze-num -1 \
    --with-backbone-lr --backbone-lr 0.0002 \
    --multi-view --with-lidar --multi-view-input-size 3 128 128 \
    --experiment interfuser_baseline \
    --pretrained \
    --output $OUTPUT_DIR \
    $RESUME_ARG

# Default:
#   --train-towns 1 2 3 4 6 7 10 \
#   --val-towns 5 \
#   --train-weathers 0 1 2 3 4 5 6 7 8 9\
#   --val-weathers 10 11 12 13 \
