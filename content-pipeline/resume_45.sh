#!/bin/bash
set -uo pipefail
export COMFYUI_HOST=100.104.162.124
cd /Users/dev/projects/faraway-folio
echo "########## Resuming volume-4 at $(date) ##########"
python3 content-pipeline/generate_product_pack.py --volume content-pipeline/products/volume-4.json
echo "########## Finished volume-4 at $(date) ##########"
echo "########## Starting volume-5 at $(date) ##########"
python3 content-pipeline/generate_product_pack.py --volume content-pipeline/products/volume-5.json
echo "########## Finished volume-5 at $(date) ##########"
echo "########## Both volumes complete at $(date) ##########"
