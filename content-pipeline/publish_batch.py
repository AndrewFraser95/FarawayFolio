#!/usr/bin/env python3
"""
Fully automated: generate content and publish it live to Instagram + Facebook.
No human review step (explicit choice) — the one safety rail is --limit, capping
how many posts a single run can push out, so a bad prompt/model glitch can't
flood the accounts.

Each entry in prompts.json is one POST with 4 images (a themed set), published
as an Instagram carousel and a Facebook multi-photo post. Unlike generate_batch.py
(which leaves images on the ComfyUI PC for manual posting), this script downloads
each image locally just long enough to:
  1. commit it into this repo's docs/media/ folder and push (GitHub Pages then
     serves it at a public URL, which Instagram's API requires — Facebook accepts
     direct file upload, no public hosting needed there),
  2. post the full set to Instagram (carousel) and Facebook (multi-photo post),
  3. delete the local copies.

X is not wired up here (retired 2026-09-14 due to API cost/tier issues) — see
publish_x.py if that ever needs revisiting.

Requires:
    COMFYUI_HOST, IG_USER_ID, IG_ACCESS_TOKEN, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN,
    PUBLIC_MEDIA_BASE_URL (should be https://farawayfolio.com once the custom
    domain's HTTPS cert is ready — NOT andrewfraser.com, a separate personal site
    on the same GitHub account)

Usage:
    python3 publish_batch.py --limit 1
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
LOG_PATH = os.path.join(HERE, "publish.log")

sys.path.insert(0, HERE)
import publish_facebook  # noqa: E402
import publish_instagram  # noqa: E402


def log(message):
    line = f"[{datetime.now().isoformat()}] {message}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def load_posts():
    with open(os.path.join(HERE, "prompts.json")) as f:
        return json.load(f)


def generate_image(prompt, out_dir):
    """Runs comfyui_bridge.py in normal (downloading) mode, since this image needs
    to transit through the repo for public hosting."""
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        sys.executable,
        os.path.join(HERE, "comfyui_bridge.py"),
        "--workflow", os.path.join(HERE, "workflow_api.json"),
        "--prompt", prompt,
        "--out", out_dir,
        "--timeout", "600",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Generation failed: {result.stderr}")
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.endswith(".png") or line.endswith(".jpg"):
            return line
    raise RuntimeError(f"No image path found in bridge output: {result.stdout}")


def git_push(repo_root):
    """Push using a GitHub PAT if provided (GITHUB_PAT env var), embedding it in the
    remote URL only for the duration of this push and resetting immediately after,
    rather than storing it persistently (keeps it out of .git/config on disk)."""
    pat = os.environ.get("GITHUB_PAT")
    if not pat:
        subprocess.run(["git", "-C", repo_root, "push"], check=True)
        return

    clean_url = subprocess.run(
        ["git", "-C", repo_root, "remote", "get-url", "origin"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if not clean_url.startswith("https://"):
        raise RuntimeError(f"Expected an https:// remote URL, got: {clean_url}")
    auth_url = clean_url.replace("https://", f"https://{pat}@", 1)
    try:
        subprocess.run(["git", "-C", repo_root, "remote", "set-url", "origin", auth_url], check=True)
        subprocess.run(["git", "-C", repo_root, "push"], check=True)
    finally:
        subprocess.run(["git", "-C", repo_root, "remote", "set-url", "origin", clean_url], check=True)


def publish_images_to_media_repo(local_image_paths, post_id):
    media_dir = os.path.join(REPO_ROOT, "docs", "media", date.today().isoformat())
    os.makedirs(media_dir, exist_ok=True)

    dest_paths = []
    for i, local_path in enumerate(local_image_paths, start=1):
        filename = f"{post_id}-{i}{os.path.splitext(local_path)[1]}"
        dest_path = os.path.join(media_dir, filename)
        os.rename(local_path, dest_path)
        dest_paths.append(dest_path)

    rel_paths = [os.path.relpath(p, REPO_ROOT) for p in dest_paths]
    subprocess.run(["git", "-C", REPO_ROOT, "add", *rel_paths], check=True)
    subprocess.run(["git", "-C", REPO_ROOT, "commit", "-m", f"Add media: {post_id}"], check=True)
    git_push(REPO_ROOT)

    base_url = os.environ["PUBLIC_MEDIA_BASE_URL"].rstrip("/")
    public_urls = [f"{base_url}/{rel}" for rel in rel_paths]
    return dest_paths, public_urls


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


def main():
    parser = argparse.ArgumentParser(description="Generate and publish content live to Instagram + Facebook.")
    parser.add_argument("--limit", type=int, default=1, help="Max posts this run (safety cap, no review gate)")
    args = parser.parse_args()

    posts = load_posts()[: args.limit]
    log(f"Starting publish run: {len(posts)} post(s), limit={args.limit}")

    for post in posts:
        try:
            log(f"{post['id']}: generating {len(post['images'])} images...")
            local_images = [generate_image(p, os.path.join(HERE, "_publish_tmp")) for p in post["images"]]

            log(f"{post['id']}: pushing to media repo...")
            dest_paths, public_urls = publish_images_to_media_repo(local_images, post["id"])

            for url in public_urls:
                log(f"{post['id']}: waiting for {url} to go live...")
                if not wait_until_live(url):
                    raise RuntimeError(f"{url} did not become reachable in time")

            caption = post["caption"]

            log(f"{post['id']}: posting carousel to Instagram...")
            ig_media_id = publish_instagram.post_carousel_to_instagram(public_urls, caption)
            log(f"{post['id']}: Instagram OK, media_id={ig_media_id}")

            log(f"{post['id']}: posting multi-photo to Facebook...")
            fb_result = publish_facebook.post_multi_to_facebook(dest_paths, caption)
            log(f"{post['id']}: Facebook OK, {json.dumps(fb_result)}")

            for path in dest_paths:
                os.remove(path)
            log(f"{post['id']}: done, local copies removed")

        except Exception as e:
            log(f"{post['id']}: FAILED — {e}")

    log("Publish run complete.")


if __name__ == "__main__":
    main()
