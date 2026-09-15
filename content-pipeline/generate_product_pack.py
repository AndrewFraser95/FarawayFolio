#!/usr/bin/env python3
"""
Generate a full Gumroad product pack from a products/volume-N.json spec:
one HQ image per entry, a matching 9:16 wallpaper crop, converted to
high-quality JPEG, packaged with a README, and zipped.

Usage:
    export COMFYUI_HOST=100.104.162.124
    python3 generate_product_pack.py --volume content-pipeline/products/volume-2.json
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import sys
import urllib.request

from safe_generate import generate_one_safe, MachineUnreachableError, RunCapReached, RunCapCounter
from pack_builder import assemble_pack

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)


def free_comfyui_memory():
    host = os.environ.get("COMFYUI_HOST", "192.168.1.100")
    port = os.environ.get("COMFYUI_PORT", "8188")
    payload = json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{host}:{port}/free", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"  (warning: failed to free ComfyUI memory: {e})")


def build_pack(spec_path, out_dir):
    with open(spec_path) as f:
        spec = json.load(f)

    slug = os.path.splitext(os.path.basename(spec_path))[0]  # e.g. "volume-2"
    pack_dir = os.path.join(out_dir, f"gumroad-pack-{slug}")
    raw_dir = os.path.join(pack_dir, "_raw")
    os.makedirs(raw_dir, exist_ok=True)

    free_comfyui_memory()

    cap = RunCapCounter()
    images = []
    for i, entry in enumerate(spec["images"], start=1):
        # A raw PNG may already exist from a prior run -- reuse it rather than
        # regenerating (cheap to re-encode into print/wallpaper JPEGs either way).
        existing_raw = [f for f in os.listdir(raw_dir) if f.startswith(f"{slug}_{entry['id']}_")]
        if existing_raw:
            print(f"\n=== {slug}: {entry['id']} ({i}/{len(spec['images'])}) — reusing existing raw image ===")
            raw_path = os.path.join(raw_dir, existing_raw[0])
        else:
            try:
                cap.check()
            except RunCapReached as exc:
                print(f"\n=== {exc} ===")
                break
            print(f"\n=== {slug}: {entry['id']} ({i}/{len(spec['images'])}) ===")
            try:
                raw_path = generate_one_safe(entry["prompt"], f"{slug}_{entry['id']}", raw_dir, timeout=600)
            except MachineUnreachableError as exc:
                print(f"\n=== {exc} — stopping this run entirely ===")
                break
            except Exception as exc:
                print(f"  !! {entry['id']} failed ({exc}) — skipping for now, continuing with the rest of the pack")
                continue
        images.append({"id": entry["id"], "raw_path": raw_path})

    pack_dir, zip_path = assemble_pack(images, spec["name"], spec["theme"], slug, out_dir)

    print(f"\n=== {spec['name']} complete: {len(images)}/{len(spec['images'])} images ===")
    print(f"Pack dir: {pack_dir}")
    print(f"Zip: {zip_path}")
    return pack_dir, zip_path


def main():
    # Line-buffer stdout so progress is visible in real time when redirected to a
    # log file (e.g. nohup ... > log.txt &) instead of only appearing on exit.
    sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description="Generate a full Gumroad product pack from a spec JSON.")
    parser.add_argument("--volume", required=True, help="Path to a products/volume-N.json spec")
    parser.add_argument("--out", default=os.path.join(REPO_ROOT, "branding"), help="Base output directory")
    args = parser.parse_args()

    build_pack(args.volume, args.out)


if __name__ == "__main__":
    main()
