#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"/../..

echo "Please download the model pth.tar file from http://43.159.60.142/s/p2CN"
echo "and place it in the models/interfuser directory."
echo "Then press enter to continue."
read

cd models/interfuser
md5sum -c <<< "0b5f0d41887bccedc91e826e88b89a3a *interfuser.pth.tar" || { echo "MD5 mismatch";  >&2; exit 1; }

echo "Download complete"
