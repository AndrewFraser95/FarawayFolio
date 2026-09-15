#!/usr/bin/env python3
"""
Generate and publish single-image engagement posts (starter_content.json) live
to Instagram + Facebook. Unlike the product-pick carousels in prompts.json,
these are lighter single-image posts not tied to a specific pack.

Requires the same env vars as publish_batch.py: COMFYUI_HOST, IG_USER_ID,
IG_ACCESS_TOKEN, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GITHUB_PAT,
PUBLIC_MEDIA_BASE_URL (https://farawayfolio.com).

Usage:
    python3 publish_starter_content.py --limit 6
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
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
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def load_entries():
    with open(os.path.join(HERE, "starter_content.json")) as f:
        return json.load(f)


def generate_image(prompt, out_dir, timeout=900):
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        sys.executable,
        os.path.join(HERE, "comfyui_bridge.py"),
        "--workflow", os.path.join(HERE, "workflow_api.json"),
        "--prompt", prompt,
        "--out", out_dir,
        "--timeout", str(timeout),
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
    pat = os.environ.get("GITHUB_PAT")
    if not pat:
        subprocess.run(["git", "-C", repo_root, "push"], check=True)
        return
    clean_url = subprocess.run(
        ["git", "-C", repo_root, "remote", "get-url", "origin"], capture_output=True, text=True, check=True
    ).stdout.strip()
    auth_url = clean_url.replace("https://", f"https://{pat}@", 1)
    try:
        subprocess.run(["git", "-C", repo_root, "remote", "set-url", "origin", auth_url], check=True)
        subprocess.run(["git", "-C", repo_root, "push"], check=True)
    finally:
        subprocess.run(["git", "-C", repo_root, "remote", "set-url", "origin", clean_url], check=True)


def publish_to_media_repo(local_image_path, post_id, push=True):
    media_dir = os.path.join(REPO_ROOT, "docs", "media", date.today().isoformat())
    os.makedirs(media_dir, exist_ok=True)
    filename = f"{post_id}{os.path.splitext(local_image_path)[1]}"
    dest_path = os.path.join(media_dir, filename)
    os.rename(local_image_path, dest_path)

    rel_path = os.path.relpath(dest_path, REPO_ROOT)
    subprocess.run(["git", "-C", REPO_ROOT, "add", rel_path], check=True)
    subprocess.run(["git", "-C", REPO_ROOT, "commit", "-m", f"Add starter content media: {post_id}"], check=True)
    if push:
        git_push(REPO_ROOT)

    base_url = os.environ.get("PUBLIC_MEDIA_BASE_URL")
    public_url = f"{base_url.rstrip('/')}/{rel_path}" if base_url else None
    return dest_path, public_url


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
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Generate and publish starter engagement content.")
    parser.add_argument("--limit", type=int, default=6, help="Max posts this run")
    parser.add_argument("--no-push", action="store_true",
                         help="Commit media locally but don't push/post to Instagram (needs the public URL "
                              "live); still posts to Facebook via direct upload, which doesn't need a public URL.")
    args = parser.parse_args()

    entries = load_entries()[: args.limit]
    log(f"Starting starter content run: {len(entries)} post(s), push={not args.no_push}")

    for entry in entries:
        try:
            log(f"{entry['id']}: generating image...")
            local_image = generate_image(entry["prompt"], os.path.join(HERE, "_publish_tmp"))

            log(f"{entry['id']}: committing to media repo (push={not args.no_push})...")
            dest_path, public_url = publish_to_media_repo(local_image, entry["id"], push=not args.no_push)

            if args.no_push:
                log(f"{entry['id']}: skipping Instagram (no push this run, {public_url} not live yet)")
            else:
                log(f"{entry['id']}: waiting for {public_url} to go live...")
                if not wait_until_live(public_url):
                    raise RuntimeError(f"{public_url} did not become reachable in time")
                log(f"{entry['id']}: posting to Instagram...")
                ig_media_id = publish_instagram.post_to_instagram(public_url, entry["caption"])
                log(f"{entry['id']}: Instagram OK, media_id={ig_media_id}")

            log(f"{entry['id']}: posting to Facebook...")
            fb_result = publish_facebook.post_to_facebook(dest_path, entry["caption"])
            log(f"{entry['id']}: Facebook OK, {json.dumps(fb_result)}")

            if not args.no_push:
                os.remove(dest_path)
                log(f"{entry['id']}: done, local copy removed")
            else:
                log(f"{entry['id']}: done, local copy kept at {dest_path} (committed, not pushed)")

        except Exception as e:
            log(f"{entry['id']}: FAILED — {e}")

    log("Starter content run complete.")


if __name__ == "__main__":
    main()
