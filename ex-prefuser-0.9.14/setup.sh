#!/bin/bash

set -euo pipefail

mkdir -p results models

if [ ! -h models/prefuser ]; then
    echo "Creating symlink to models"
    ln -s $(realpath ../models/prefuser) models/prefuser
fi

if ../scripts/check-prefuser.sh; then
    echo "Models already exist, skipping download"
else
    echo "Downloading models"
    ../scripts/download-prefuser.sh
fi
