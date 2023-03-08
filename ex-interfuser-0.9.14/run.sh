#!/bin/bash

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

source ../common/utils.sh

run_in_screen "ex-interfuser-0.9.14-$eval" \
    "docker compose up --build --abort-on-container-exit"

