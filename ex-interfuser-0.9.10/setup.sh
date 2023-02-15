#!/bin/bash

set -euo pipefail

mkdir -p results models data

if [ ! -h models/interfuser ]; then
    echo "Creating symlink to models"
    ln -s $(realpath ../models/interfuser) models/interfuser
fi

# if ../scripts/check-interfuser.sh; then
#     echo "Models already exist, skipping download"
# else
#     echo "Downloading models"
#     ../scripts/download-interfuser.sh
# fi
