#!/bin/bash
# Runs generate_review_candidates.py to completion, respawning after each
# safety-cap-limited chunk (default 10 images/run) with an extra rest
# between chunks on top of the per-image cooldown already inside the
# script. Stops immediately -- does not respawn -- if ComfyUI stops
# responding (exit code 3), instead of hammering a possibly overheated
# machine all night. This is the overnight-safe entry point; don't use
# generate_review_candidates.py directly for a big batch, only for one
# capped chunk.
set -u

SPEC="$1"
OUT="$2"
CHUNK_REST_SECONDS="${CHUNK_REST_SECONDS:-180}"

export PATH="/Users/dev/.local/node/bin:$PATH"
export COMFYUI_HOST="${COMFYUI_HOST:-100.104.162.124}"
cd /Users/dev/projects/faraway-folio

while true; do
  echo ""
  echo "########## chunk starting at $(date) ##########"
  python3 content-pipeline/generate_review_candidates.py --spec "$SPEC" --out "$OUT"
  code=$?
  echo "########## chunk finished at $(date), exit code $code ##########"

  if [ "$code" -eq 3 ]; then
    echo "ComfyUI unreachable -- stopping the whole batch, not retrying automatically."
    break
  fi

  # Done when the manifest has as many entries as the spec's image list.
  total=$(python3 -c "import json; print(len(json.load(open('$SPEC'))['images']))")
  have=$(python3 -c "import json,os; p='$OUT/manifest.json'; print(len(json.load(open(p))) if os.path.exists(p) else 0)")
  echo "progress: $have/$total"
  if [ "$have" -ge "$total" ]; then
    echo "All candidates generated."
    break
  fi

  echo "resting ${CHUNK_REST_SECONDS}s between chunks..."
  sleep "$CHUNK_REST_SECONDS"
done
