#!/usr/bin/env python3
"""
Bundle a set of approved review-queue images into a Gumroad pack and
publish it live, given a small JSON description.

Second half of "approve in Folio Proofing -> pack goes live once full":
Claude reads the review queue (an Artifact-tool capability, not something
a script can call), and once a pack's approved-image count reaches its
target, writes the group out as JSON and runs this script to do the
actual packaging + Gumroad publish.

Input JSON shape:
    {
      "slug": "volume-6",
      "name": "Faraway Folio, Volume Six",
      "theme": "<one-line theme description for the README/listing>",
      "price": "10",
      "images": [{"id": "...", "path": "/abs/local/raw-or-print-image.png"}, ...]
    }

Usage:
    python3 pack_from_approved.py --input pack.json
Prints a JSON result: {"product_url": ..., "product_id": ...}
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import glob
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pack_builder import assemble_pack  # noqa: E402


def gumroad(*args, json_out=True):
    cmd = ["gumroad", *args, "--no-input", "--non-interactive"]
    if json_out:
        cmd.append("--json")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # The CLI prints a version-upgrade nag to stderr even on success, which can
        # mask the real JSON error (also on stdout) if stderr happens to be checked
        # first -- always show both so a real failure is never hidden behind the nag.
        raise RuntimeError(f"gumroad {' '.join(args)} failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    if json_out:
        return json.loads(result.stdout)
    return result.stdout


def build_description(theme, n):
    return (
        f"<p>{theme}: {n} quiet, warm-toned travel scenes.</p>"
        f"<p>Each image comes ready to print (high-resolution, standard print ratios) and as a cropped "
        f"wallpaper for your phone.</p>"
        f"<p><strong>What's included:</strong></p><ul>"
        f"<li>{n} high-resolution images, print-ready (2:3 ratio, suitable for standard frame sizes)</li>"
        f"<li>{n} phone wallpaper crops (9:16)</li>"
        f"<li>A quick-start note on print sizes</li></ul>"
        f"<p><strong>Format:</strong> instant digital download (ZIP), no physical item ships.</p>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    with open(args.input) as f:
        spec = json.load(f)

    images = [{"id": img["id"], "raw_path": img["path"]} for img in spec["images"]]
    out_dir = os.path.join(REPO_ROOT, "branding")
    pack_dir, zip_path = assemble_pack(images, spec["name"], spec["theme"], spec["slug"], out_dir)

    cover_candidates = sorted(glob.glob(os.path.join(pack_dir, "print", "*.jpg")))
    cover_image = cover_candidates[0]
    thumbnail_image = os.path.join(pack_dir, "_thumbnail.jpg")
    dim = subprocess.run(["sips", "-g", "pixelHeight", "-g", "pixelWidth", cover_image],
                          check=True, capture_output=True, text=True).stdout
    height = int([l for l in dim.splitlines() if "pixelHeight" in l][0].split(":")[1].strip())
    width = int([l for l in dim.splitlines() if "pixelWidth" in l][0].split(":")[1].strip())
    side = min(height, width)
    subprocess.run(["sips", "-c", str(side), str(side), cover_image, "--out", thumbnail_image],
                    check=True, capture_output=True)

    n = len(images)
    # Gumroad caps tags at 20 characters -- a long theme name breaks the create
    # call outright (caught live on Volume Eight: "english countryside manor",
    # 25 chars). Truncate at a word boundary rather than guessing it'll fit.
    theme_tag = spec["theme"].lower()
    if len(theme_tag) > 20:
        theme_tag = theme_tag[:20].rsplit(" ", 1)[0]
    tags = ["travel", "wall art", "printable", "digital download", "wallpaper", "aesthetic",
            "quiet luxury", theme_tag]
    create_args = [
        "products", "create",
        "--name", spec["name"],
        "--price", str(spec["price"]),
        "--currency", "gbp",
        "--file", zip_path,
        "--file-name", os.path.basename(zip_path),
        "--cover-image", cover_image,
        "--thumbnail", thumbnail_image,
        "--category", "design/wallpapers",
        "--description", build_description(spec["theme"], n),
        "--custom-summary", f"{n} aspirational {spec['theme'].lower()} travel scenes for your walls and your phone.",
    ]
    for tag in tags:
        create_args += ["--tag", tag]

    result = gumroad(*create_args)
    if not result.get("success"):
        raise RuntimeError(f"Create failed: {result}")
    product_id = result["product"]["id"]

    publish_result = gumroad("products", "publish", product_id)
    if not publish_result.get("success"):
        raise RuntimeError(f"Publish failed: {publish_result}")

    view_result = gumroad("products", "view", product_id)
    product = view_result["product"]

    print(json.dumps({
        "product_id": product_id,
        "product_url": product.get("short_url") or product.get("landing_url"),
        "pack_dir": pack_dir,
        "zip_path": zip_path,
    }, indent=2))


if __name__ == "__main__":
    main()
