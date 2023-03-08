#!/bin/bash

script_dir=$(dirname "$0")

echo "Training on multiple GPUs"

NVIDIA_GPUS="$(nvidia-smi -L)"
NUM_GPUS="$(echo "$NVIDIA_GPUS" | wc -l)"
CUDA_GPUS="$(echo "$NVIDIA_GPUS" | cut -d ' ' -f 2 | tr -d ':' | head -c -1 | tr '\n' ',')"
echo "Found ${NUM_GPUS} GPUs: ${CUDA_GPUS}"
echo "${NVIDIA_GPUS}"

export CUDA_VISIBLE_DEVICES="$CUDA_GPUS"
export OMP_NUM_THREADS=$(nproc)
export OPENBLAS_NUM_THREADS=1

export PYTHONPATH=/transfuser/team_code_transfuser:$PYTHONPATH

exec torchrun \
    --nnodes=1 \
    --nproc_per_node=$NUM_GPUS \
    --max_restarts=0 \
    --rdzv_id=123456780 \
    --rdzv_backend=c10d \
    $script_dir/train.py "$@"
