#!/bin/bash

source ../common/utils.sh

MODEL_NAME="$1"
CARLA_VERSION=0.9.10.1
TRANSFUSER_COMMIT=experiments/0.9.10

export SAVE_PATH=/results/viz

PS3='Select evaluation: '
options=("town05" "42routes" "longest6" "Quit")
select eval in "${options[@]}"
do
    case $eval in
        "town05")
            export ACTOR_AMOUNT=120
            break
            ;;
        "42routes")
            export ACTOR_AMOUNT=town
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

run_transfuser
