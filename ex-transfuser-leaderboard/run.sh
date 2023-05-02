#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"; shift
MODEL_TAG="transfuser-leaderboard-agent"

echo Building image for model "$MODEL_NAME" to tag "$MODEL_TAG"
./scripts/make-docker.sh "$MODEL_NAME" "$MODEL_TAG"

echo "Submitting evaluation for model $MODEL_NAME"
alpha benchmark:submit --split 3 "$MODEL_TAG"
