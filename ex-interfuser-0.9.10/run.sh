#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"
CARLA_VERSION=0.9.10.1
INTERFUSER_COMMIT=main

PS3='Select evaluation: '
options=("town05" "42routes" "longest6" "Quit")
select eval in "${options[@]}"
do
    case $eval in
        "town05")
            break
            ;;
        "42routes")
            break
            ;;
        "longest6")
            break
            ;;
        "Quit")
            exit 0
            ;;
        *) echo "invalid option $REPLY";;
    esac
done

export EVALUATION=$eval

run_interfuser
