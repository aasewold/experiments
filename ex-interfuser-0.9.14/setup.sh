#!/bin/bash

source ../common/utils.sh

if [ ! -h models ]; then
    echo "Creating symlink to models"
    ln -s $(realpath ../models) models
fi

setup_interfuser
