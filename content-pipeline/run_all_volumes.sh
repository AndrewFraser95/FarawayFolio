#!/bin/bash
set -uo pipefail

export PATH="/Users/dev/.local/node/bin:$PATH"
export COMFYUI_HOST=100.104.162.124

cd /Users/dev/projects/faraway-folio

for vol in volume-2 volume-3 volume-4 volume-5; do
  echo ""
  echo "########## Starting $vol at $(date) ##########"
  python3 content-pipeline/generate_product_pack.py --volume "content-pipeline/products/${vol}.json"
  echo "########## Finished $vol at $(date) ##########"
done

echo ""
echo "########## All volumes complete at $(date) ##########"
