#!/bin/bash
DIR="$(dirname "$0")"

# build docker image
docker build \
    --build-arg CARLA_VERSION=0.9.13 \
    --build-arg TRANSFUSER_COMMIT=experiments/0.9.14 \
    -t transfuser-leaderboard-agent \
    - \
    < ${DIR}/Dockerfile.master
