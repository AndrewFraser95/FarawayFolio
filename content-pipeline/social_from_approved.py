#!/usr/bin/env python3
"""
Post one approved review-queue group (a single image, or a full carousel)
live to Instagram + Facebook, given a small JSON description of it.

This is the second half of the "approve in Folio Proofing -> goes live"
flow: Claude reads the review queue's database (only Claude can -- that's
an Artifact-tool capability, not a public API a script can call), writes
the approved group out as JSON, runs this script to do the actual
posting, then writes the resulting permalinks back into the queue.

Input JSON shape:
    {
      "kind": "single" | "carousel",
      "group": "rome-dream-day",
      "caption": "...",
      "images": [{"id": "...", "path": "/abs/local/path.png"}, ...]
    }
(single has exactly one entry in "images"; carousel has 2-10, in order)

Usage:
    python3 social_from_approved.py --input group.json
Prints a JSON result: {"instagram_permalink": ..., "facebook_post_id": ...}
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import subprocess
import sys
import time
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import publish_facebook  # noqa: E402
import publish_instagram  # noqa: E402


def git_push(repo_root):
    pat = os.environ.get("GITHUB_PAT")
    clean_url = subprocess.run(
        ["git", "-C", repo_root, "remote", "get-url", "origin"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if not pat:
        subprocess.run(["git", "-C", repo_root, "push"], check=True)
        return
    auth_url = clean_url.replace("https://", f"https://{pat}@", 1)
    try:
        subprocess.run(["git", "-C", repo_root, "remote", "set-url", "origin", auth_url], check=True)
        subprocess.run(["git", "-C", repo_root, "push"], check=True)
    finally:
        subprocess.run(["git", "-C", repo_root, "remote", "set-url", "origin", clean_url], check=True)


def wait_until_live(url, timeout=180, poll_interval=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


def commit_and_push(images, group):
    """Copy each local image into docs/media/<date>/, commit, push once."""
    media_dir = os.path.join(REPO_ROOT, "docs", "media", date.today().isoformat())
    os.makedirs(media_dir, exist_ok=True)
    dest_paths, rel_paths = [], []
    for img in images:
        ext = os.path.splitext(img["path"])[1] or ".png"
        dest = os.path.join(media_dir, f"{img['id']}{ext}")
        subprocess.run(["cp", img["path"], dest], check=True)
        dest_paths.append(dest)
        rel_paths.append(os.path.relpath(dest, REPO_ROOT))

    subprocess.run(["git", "-C", REPO_ROOT, "add", *rel_paths], check=True)
    subprocess.run(["git", "-C", REPO_ROOT, "commit", "-m", f"Add approved media: {group}"], check=True)
    git_push(REPO_ROOT)

    base_url = os.environ["PUBLIC_MEDIA_BASE_URL"].rstrip("/")
    public_urls = [f"{base_url}/{rel}" for rel in rel_paths]
    return dest_paths, public_urls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    with open(args.input) as f:
        group = json.load(f)

    dest_paths, public_urls = commit_and_push(group["images"], group["group"])

    for url in public_urls:
        if not wait_until_live(url):
            raise RuntimeError(f"{url} did not become reachable in time")

    if group["kind"] == "single":
        ig_media_id = publish_instagram.post_to_instagram(public_urls[0], group["caption"])
    else:
        ig_media_id = publish_instagram.post_carousel_to_instagram(public_urls, group["caption"])

    if group["kind"] == "single":
        fb_result = publish_facebook.post_to_facebook(dest_paths[0], group["caption"])
    else:
        fb_result = publish_facebook.post_multi_to_facebook(dest_paths, group["caption"])

    print(json.dumps({
        "instagram_media_id": ig_media_id,
        "facebook_result": fb_result,
        "public_urls": public_urls,
    }, indent=2))


if __name__ == "__main__":
    main()
