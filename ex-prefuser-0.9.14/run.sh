#!/bin/bash

source ../common/utils.sh

run_in_screen "ex-prefuser-0.9.14" \
    "docker compose up --build --abort-on-container-exit"
