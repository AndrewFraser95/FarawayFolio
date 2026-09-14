#!/usr/bin/env python3
"""
Create and publish a finished volume pack as a live Gumroad product.

Usage:
    python3 publish_volume_to_gumroad.py --volume content-pipeline/products/volume-2.json \
        --pack-dir branding/gumroad-pack-volume-2 --zip branding/Faraway-Folio-Volume-Two.zip
"""

import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def gumroad(*args, json_out=True):
    cmd = ["gumroad", *args, "--no-input", "--non-interactive"]
    if json_out:
        cmd.append("--json")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gumroad {' '.join(args)} failed: {result.stderr or result.stdout}")
    if json_out:
        return json.loads(result.stdout)
    return result.stdout


def build_description(spec):
    image_ids = [img["id"].replace("-", " ") for img in spec["images"]]
    scenes = ", ".join(image_ids[:-1]) + f", and {image_ids[-1]}" if len(image_ids) > 1 else image_ids[0]
    n = len(spec["images"])
    return (
        f"<p>{spec['theme']}: {n} quiet, warm-toned travel scenes including {scenes}.</p>"
        f"<p>Each image comes ready to print (high-resolution, standard print ratios) and as a cropped "
        f"wallpaper for your phone.</p>"
        f"<p><strong>What's included:</strong></p><ul>"
        f"<li>{n} high-resolution images, print-ready (2:3 ratio, suitable for standard frame sizes)</li>"
        f"<li>{n} phone wallpaper crops (9:16)</li>"
        f"<li>A quick-start note on print sizes</li></ul>"
        f"<p><strong>Format:</strong> instant digital download (ZIP), no physical item ships.</p>"
    )


def publish_volume(spec_path, pack_dir, zip_path):
    with open(spec_path) as f:
        spec = json.load(f)

    print_dir = os.path.join(pack_dir, "print")
    cover_candidates = sorted(glob.glob(os.path.join(print_dir, "*.jpg")))
    if not cover_candidates:
        raise RuntimeError(f"No print images found in {print_dir}")
    cover_image = cover_candidates[0]

    price = spec.get("price", "£10").replace("£", "")
    n = len(spec["images"])
    custom_summary = f"{n} aspirational {spec['theme'].lower()} travel scenes for your walls and your phone."
    tags = ["travel", "wall art", "printable", "digital download", "wallpaper", "aesthetic", "quiet luxury", spec["theme"].lower()]

    print(f"Creating product: {spec['name']}...")
    create_args = [
        "products", "create",
        "--name", spec["name"],
        "--price", price,
        "--currency", "gbp",
        "--file", zip_path,
        "--file-name", os.path.basename(zip_path),
        "--cover-image", cover_image,
        "--thumbnail", cover_image,
        "--category", "design/wallpapers",
        "--description", build_description(spec),
        "--custom-summary", custom_summary,
    ]
    for tag in tags:
        create_args += ["--tag", tag]

    result = gumroad(*create_args)
    if not result.get("success"):
        raise RuntimeError(f"Create failed: {result}")
    product_id = result["product"]["id"]
    print(f"Created draft product id={product_id}")

    publish_result = gumroad("products", "publish", product_id)
    if not publish_result.get("success"):
        raise RuntimeError(f"Publish failed: {publish_result}")

    view_result = gumroad("products", "view", product_id)
    product = view_result["product"]
    print(f"Published: {product['name']}")
    print(f"URL: {product.get('short_url') or product.get('landing_url')}")
    return product


def main():
    parser = argparse.ArgumentParser(description="Publish a finished volume pack to Gumroad.")
    parser.add_argument("--volume", required=True, help="Path to products/volume-N.json spec")
    parser.add_argument("--pack-dir", required=True, help="Path to the gumroad-pack-volume-N directory")
    parser.add_argument("--zip", required=True, help="Path to the packaged zip file")
    args = parser.parse_args()

    publish_volume(args.volume, args.pack_dir, args.zip)


if __name__ == "__main__":
    main()
