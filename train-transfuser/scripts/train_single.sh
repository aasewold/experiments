#!/bin/bash

script_dir=$(dirname "$0")

echo "Training on a single GPU"

export PYTHONPATH=/transfuser/team_code_transfuser:$PYTHONPATH
exec python $script_dir/train.py "$@"
