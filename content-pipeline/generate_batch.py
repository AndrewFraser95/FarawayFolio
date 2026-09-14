#!/usr/bin/env python3
"""
Generate a batch of ready-to-post content for Faraway Folio.

Each entry in prompts.json is one POST with 4 images (a themed set, e.g. a
carousel/multi-photo post). For each post, generates all 4 images and writes
one ready-to-post caption file to a dated folder on this Mac.

Images are left on the Windows ComfyUI machine (not copied to this Mac) — the
Mac often runs clamshell/headless, so uploads happen from the PC instead. Each
image's filename is prefixed with its post id and image number
(e.g. FarawayFolio_slow-mornings-1_00001_.png .. -4_00001_.png), so it's obvious
on the PC which images belong to which post and in what order. Captions are
zipped (preserving <date>/<post-id>/caption.txt structure) and sent to the PC
via Tailscale Taildrop, so everything ends up grouped together there.

Usage:
    export COMFYUI_HOST=100.104.162.124
    python3 generate_batch.py --count 3 --out ./queue
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import date

FILENAME_PREFIX = "FarawayFolio"
TAILDROP_PEER = os.environ.get("COMFYUI_TAILDROP_PEER", "andygaming")

HERE = os.path.dirname(os.path.abspath(__file__))


def find_tailscale_bin():
    found = shutil.which("tailscale")
    if found:
        return found
    app_path = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
    return app_path if os.path.exists(app_path) else None


def send_captions_via_taildrop(batch_dir, batch_label):
    """Zip the whole batch folder (preserving <theme-id>/caption.txt structure) and
    Taildrop it to the Windows ComfyUI machine, so captions end up grouped by batch
    right alongside the matching images instead of stranded on this headless Mac."""
    tailscale_bin = find_tailscale_bin()
    if not tailscale_bin:
        print("  (warning: tailscale binary not found, skipping caption Taildrop)")
        return False

    zip_path = os.path.join("/tmp", f"faraway-folio-captions-{batch_label}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(batch_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                arcname = os.path.join(batch_label, os.path.relpath(full_path, batch_dir))
                zf.write(full_path, arcname)

    result = subprocess.run([tailscale_bin, "file", "cp", zip_path, f"{TAILDROP_PEER}:"], capture_output=True, text=True)
    os.remove(zip_path)
    if result.returncode != 0:
        print(f"  (warning: Taildrop send failed: {result.stderr.strip()})")
        return False
    print(f"  Sent captions to {TAILDROP_PEER} via Taildrop as faraway-folio-captions-{batch_label}.zip")
    print(f"  (unzip on the PC to get {batch_label}/<theme>/caption.txt grouped per batch)")
    return True


def load_prompts():
    with open(os.path.join(HERE, "prompts.json")) as f:
        return json.load(f)


def free_comfyui_memory():
    """The Windows GPU (RTX 3060 Ti, 8GB VRAM) can end up starved of VRAM/RAM after
    heavy runs, causing intermittent VAEDecode failures (HostBuffer.read_file_slice).
    Ask ComfyUI to unload models and free memory before each generation."""
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


def main():
    parser = argparse.ArgumentParser(description="Generate a batch of Faraway Folio content.")
    parser.add_argument("--count", type=int, default=len(load_prompts()), help="How many prompts to run (in order)")
    parser.add_argument("--out", default=os.path.join(HERE, "queue"), help="Base output directory for caption files")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds to wait per generation")
    args = parser.parse_args()

    prompts = load_prompts()[: args.count]
    batch_dir = os.path.join(args.out, date.today().isoformat())
    os.makedirs(batch_dir, exist_ok=True)

    # Free memory once up front (clears anything left over from a previous run),
    # but NOT before every generation — that would force a full model reload each time.
    free_comfyui_memory()

    results = []
    for post in prompts:
        post_dir = os.path.join(batch_dir, post["id"])
        os.makedirs(post_dir, exist_ok=True)

        image_ok = []
        for i, prompt_text in enumerate(post["images"], start=1):
            filename_prefix = f"{FILENAME_PREFIX}_{post['id']}-{i}"
            cmd = [
                sys.executable,
                os.path.join(HERE, "comfyui_bridge.py"),
                "--workflow", os.path.join(HERE, "workflow_api.json"),
                "--prompt", prompt_text,
                "--filename-prefix", filename_prefix,
                "--no-download",
                "--timeout", str(args.timeout),
            ]

            ok = False
            for attempt in (1, 2):
                print(f"\n=== Generating: {post['id']} image {i}/4 (attempt {attempt}) ===")
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(result.stdout)
                ok = result.returncode == 0 and "Generated 0 image" not in result.stdout and "image(s), left on the ComfyUI machine" in result.stdout
                if ok:
                    break
                print(result.stderr)
                print(f"  generation failed for {post['id']} image {i}, freeing memory and retrying...")
                free_comfyui_memory()
                time.sleep(3)
            image_ok.append(ok)

        with open(os.path.join(post_dir, "caption.txt"), "w") as f:
            f.write(post["caption"] + "\n")

        results.append({"id": post["id"], "ok": all(image_ok), "dir": post_dir})

    print("\n=== Batch summary ===")
    for r in results:
        status = "OK" if r["ok"] else "FAILED"
        print(f"  [{status}] {r['id']} -> {r['dir']} (4 images left on ComfyUI PC, prefix {FILENAME_PREFIX}_{r['id']}-N)")

    batch_label = date.today().isoformat()
    send_captions_via_taildrop(batch_dir, batch_label)


if __name__ == "__main__":
    main()
