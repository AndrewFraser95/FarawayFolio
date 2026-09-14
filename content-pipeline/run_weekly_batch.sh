#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/node/bin:$PATH"
export COMFYUI_HOST="100.104.162.124"

cd "$HOME/projects/faraway-folio/content-pipeline"
python3 generate_batch.py --out ./queue --timeout 600
