#!/bin/bash
DIR="$(dirname "$0")"
source ${DIR}/../../common/utils.sh

MODEL_PATH="$1"; shift
CARLA_VERSION="0.9.10"
TRANSFUSER_VERSION="experiments/0.9.10"

if [ -z "${MODEL_PATH}" ]; then
    echo "Usage: $0 <model_path>"
    exit 1
fi

if [ ! -d "${MODEL_PATH}" ]; then
    echo "Model path ${MODEL_PATH} does not exist"
    exit 1
fi

CONTEXT_PATH=.context

if [ -d "${CONTEXT_PATH}" ]; then
    echo "Context path ${CONTEXT_PATH} already exists"
    if [ "$MODEL_PATH" = "$(cat ${CONTEXT_PATH}/.source)" ]; then
        echo "Model path ${MODEL_PATH} already in context"
    else
        echo "Cleaning existing context"
        rm -r "${CONTEXT_PATH}"
    fi
fi

if [ ! -d "${CONTEXT_PATH}" ]; then
    mkdir "${CONTEXT_PATH}"
    echo "${MODEL_PATH}" > "${CONTEXT_PATH}/.source"

    # Copy model files into build context
    mkdir "${CONTEXT_PATH}/models"
    rsync -avhP "${MODEL_PATH}/" "${CONTEXT_PATH}/models/"
fi

echo Build context:
find .context -type f

TRANSFUSER_COMMIT="$(get_commit_hash ${TRANSFUSER_VERSION})"

docker build \
    --build-arg CARLA_VERSION=${CARLA_VERSION} \
    --build-arg TRANSFUSER_COMMIT=${TRANSFUSER_COMMIT} \
    -t transfuser-leaderboard-agent \
    -f ${DIR}/Dockerfile.master \
    .context
