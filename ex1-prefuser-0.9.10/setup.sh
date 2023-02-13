#!/bin/bash

set -euo pipefail

mkdir -p results models/transfuser

wget https://s3.eu-central-1.amazonaws.com/avg-projects/transfuser/models_2022.zip
md5sum -c <<< "b6ca3dcdfe97a8758469177765e81a31 *models_2022.zip" || { echo "MD5 mismatch" >&2; exit 1; }

unzip -j models_2022.zip 'models_2022/transfuser/*' -d models/transfuser
rm models_2022.zip
