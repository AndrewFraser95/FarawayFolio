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
import subprocess
import sys
import time
import urllib.request

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


def generate_one(prompt_text, filename_prefix, out_dir, timeout):
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        sys.executable,
        os.path.join(HERE, "comfyui_bridge.py"),
        "--workflow", os.path.join(HERE, "workflow_api.json"),
        "--prompt", prompt_text,
        "--filename-prefix", filename_prefix,
        "--out", out_dir,
        "--timeout", str(timeout),
    ]
    for attempt in (1, 2):
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0 and "Saved 1 image" in result.stdout:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.endswith(".png") or line.endswith(".jpg"):
                    return line
        print(result.stderr)
        print(f"  attempt {attempt} failed, freeing memory and retrying...")
        free_comfyui_memory()
        time.sleep(3)
    raise RuntimeError(f"Generation failed after retries for {filename_prefix}")


def build_pack(spec_path, out_dir):
    with open(spec_path) as f:
        spec = json.load(f)

    slug = os.path.splitext(os.path.basename(spec_path))[0]  # e.g. "volume-2"
    pack_dir = os.path.join(out_dir, f"gumroad-pack-{slug}")
    print_dir = os.path.join(pack_dir, "print")
    wallpaper_dir = os.path.join(pack_dir, "wallpaper")
    raw_dir = os.path.join(pack_dir, "_raw")
    os.makedirs(print_dir, exist_ok=True)
    os.makedirs(wallpaper_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    free_comfyui_memory()

    results = []
    for i, entry in enumerate(spec["images"], start=1):
        num = f"{i:02d}"
        print_jpg = os.path.join(print_dir, f"{num}-{entry['id']}.jpg")
        wallpaper_jpg = os.path.join(wallpaper_dir, f"{num}-{entry['id']}-wallpaper.jpg")

        if os.path.exists(print_jpg) and os.path.exists(wallpaper_jpg):
            print(f"\n=== {slug}: {entry['id']} ({i}/{len(spec['images'])}) — already done, skipping ===")
            results.append(entry["id"])
            continue

        # A raw PNG may already exist from a prior interrupted run (e.g. ComfyUI
        # finished generating it but the download/packaging step never ran).
        existing_raw = [f for f in os.listdir(raw_dir) if f.startswith(f"{slug}_{entry['id']}_")]
        if existing_raw:
            print(f"\n=== {slug}: {entry['id']} ({i}/{len(spec['images'])}) — reusing existing raw image ===")
            raw_path = os.path.join(raw_dir, existing_raw[0])
        else:
            print(f"\n=== {slug}: {entry['id']} ({i}/{len(spec['images'])}) ===")
            try:
                raw_path = generate_one(entry["prompt"], f"{slug}_{entry['id']}", raw_dir, timeout=600)
            except Exception as exc:
                print(f"  !! {entry['id']} failed ({exc}) — skipping for now, continuing with the rest of the pack")
                continue

        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", raw_path, "--out", print_jpg],
                        check=True, capture_output=True)

        # Read actual dimensions to compute a correct centered 9:16 crop width.
        dim = subprocess.run(["sips", "-g", "pixelHeight", "-g", "pixelWidth", raw_path],
                              check=True, capture_output=True, text=True).stdout
        height = int([l for l in dim.splitlines() if "pixelHeight" in l][0].split(":")[1].strip())
        crop_width = round(height * 9 / 16)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                         "-c", str(height), str(crop_width), raw_path, "--out", wallpaper_jpg],
                        check=True, capture_output=True)

        results.append(entry["id"])

    readme_path = os.path.join(pack_dir, "README.txt")
    with open(readme_path, "w") as f:
        f.write(f"{spec['name']}\n{spec['theme']}\n\n")
        f.write("Thanks for downloading.\n\n")
        f.write("WHAT'S INSIDE\n")
        f.write("- print/       high-resolution images (2:3 ratio), ready to print\n")
        f.write("- wallpaper/   the same scenes, cropped to 9:16 for phone lock screens/wallpapers\n\n")
        f.write("PRINT SIZES\n")
        f.write("The 2:3 ratio matches standard frame sizes: 4x6in, 8x12in, 12x18in, 16x24in.\n")
        f.write("For best quality, don't print larger than 16x24in from these files.\n\n")
        f.write("Enjoy, and tag @farawayfolio if you share where you put them.\n")

    zip_path = os.path.join(out_dir, f"Faraway-Folio-{spec['name'].split(', ')[-1].replace(' ', '-')}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    subprocess.run(["zip", "-r", zip_path, f"gumroad-pack-{slug}/print", f"gumroad-pack-{slug}/wallpaper",
                     f"gumroad-pack-{slug}/README.txt"], cwd=out_dir, check=True, capture_output=True)

    print(f"\n=== {spec['name']} complete: {len(results)} images ===")
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
