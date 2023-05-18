#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"/../..

cd models/interfuser || { echo "models/interfuser does not exist" >&2; exit 1; }

md5sum -c <<< "0b5f0d41887bccedc91e826e88b89a3a *interfuser.pth.tar" || { echo "MD5 mismatch" >&2; exit 1; }
