#!/usr/bin/env python3
"""
Generate raw candidate images for a pack spec, thermally safe, into a
staging folder -- NOT packaged, NOT published. These get uploaded to the
Folio Proofing review queue separately (only Claude can do that, via the
Artifact tool) and only bundled into a pack once enough are approved.

Exit codes: 0 = ran to completion (either finished every entry, or
stopped cleanly at this run's safety cap -- rerun the same command to
continue, already-finished images are skipped). 3 = ComfyUI stopped
responding; do NOT immediately rerun in a loop, check the machine first.

Usage:
    export COMFYUI_HOST=100.104.162.124
    python3 generate_review_candidates.py --spec content-pipeline/products/volume-6.json \
        --out content-pipeline/_review_incoming/volume-6
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import sys

from safe_generate import generate_one_safe, MachineUnreachableError, RunCapReached, RunCapCounter

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path to a products/volume-N.json spec")
    parser.add_argument("--out", required=True, help="Staging directory for raw candidate images")
    args = parser.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)
    slug = os.path.splitext(os.path.basename(args.spec))[0]

    os.makedirs(args.out, exist_ok=True)
    manifest_path = os.path.join(args.out, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else []
    done_ids = {m["id"] for m in manifest}

    cap = RunCapCounter()
    exit_code = 0
    for entry in spec["images"]:
        if entry["id"] in done_ids:
            print(f"=== {entry['id']} already generated, skipping ===")
            continue
        try:
            cap.check()
        except RunCapReached as exc:
            print(f"\n=== {exc} ===")
            break
        print(f"\n=== generating {slug}: {entry['id']} ===")
        try:
            raw_path = generate_one_safe(entry["prompt"], f"{slug}_{entry['id']}", args.out, timeout=600)
        except MachineUnreachableError as exc:
            print(f"\n=== {exc} — stopping entirely, do not auto-retry ===")
            exit_code = 3
            break
        except Exception as exc:
            print(f"  !! {entry['id']} failed ({exc}) — skipping, continuing with the rest of the batch")
            continue
        manifest.append({"id": entry["id"], "prompt": entry["prompt"], "path": raw_path, "theme": spec["theme"],
                          "pack_name": spec["name"], "slug": slug, "price": spec.get("price", "£10"),
                          "target_count": len(spec["images"])})
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    print(f"\n=== {slug}: {len(manifest)}/{len(spec['images'])} candidates generated so far ===")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
