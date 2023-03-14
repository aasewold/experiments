#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"/..

cd models/prefuser || { echo "models/prefuser does not exist" >&2; exit 1; }

md5sum -c <<< \
"bd190faff0c436fd4ec3576280f4d832 *args.txt
ee88734a6eada340572ebcdffb63a52b *model_seed1_39.pth
487c63268c6f58dca9469f5dfff7f642 *model_seed2_39.pth
ea76d0feacb86c87d59452d464ee58c0 *model_seed3_37.pth" || { echo "MD5 mismatch" >&2; exit 1; }
