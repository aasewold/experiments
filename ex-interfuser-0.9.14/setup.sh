#!/bin/bash

source ../common/utils.sh
setup_interfuser

mkdir -p data

if [ ! -h models/interfuser ]; then
    echo "Creating symlink to models"
    ln -s $(realpath ../models) models
fi
