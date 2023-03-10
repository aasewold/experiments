#!/bin/bash

COMMON="$(dirname "$BASH_SOURCE")"

run_in_screen() {
    screen -S "$1" -- \
        sh -ic "
            echo 'Running in SCREEN - Press Ctrl+A then Ctrl+D to detach'
            $2
            echo 'Still running in SCREEN - Press Ctrl+D to exit'
            exec bash
        "
}

get_commit_hash() {
    curl -s "https://api.github.com/repos/aasewold/transfuser/commits/$1" \
        | jq -r .sha \
        | head -c 8
}

setup_transfuser() (
    set -euo pipefail

    mkdir -p results models

    if [ ! -h models/prefuser ]; then
        echo "Creating symlink to models"
        ln -s $(realpath ../models/prefuser) models/prefuser
    fi

    if ../scripts/check-prefuser.sh; then
        echo "Models already exist, skipping download"
    else
        echo "Downloading models"
        ../scripts/download-prefuser.sh
    fi
)

run_transfuser() (
    MODEL_PATH="models/$MODEL_NAME"
    if [ ! -d "$MODEL_PATH" ]; then
        echo "Directory $MODEL_PATH does not exist"
        exit 1
    fi

    TRANSFUSER_COMMIT="$(get_commit_hash "$TRANSFUSER_COMMIT")"
    CARLA_VERSION_SUBST="$(echo "$CARLA_VERSION" | tr . _)"

    screen_name="ex-${MODEL_NAME}-${CARLA_VERSION}"
    compose_name="ex_${MODEL_NAME}_${CARLA_VERSION_SUBST}"

    RESULT_PATH="results/${MODEL_NAME}"
    mkdir -p "$RESULT_PATH"

    export CARLA_VERSION
    export TRANSFUSER_COMMIT
    export MODEL_PATH="$(realpath "$MODEL_PATH")"
    export RESULT_PATH="$(realpath "$RESULT_PATH")"

    run_in_screen "$screen_name" \
        "docker compose -p $compose_name -f $COMMON/transfuser.docker-compose.yml up --build"
)
