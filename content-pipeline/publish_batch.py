#!/usr/bin/env python3
"""
Fully automated: generate content and publish it live to Instagram + X. No human
review step (explicit choice) — the one safety rail is --limit, capping how many
posts a single run can push out, so a bad prompt/model glitch can't flood the account.

Unlike generate_batch.py (which leaves images on the ComfyUI PC for manual posting),
this script downloads each image locally just long enough to:
  1. commit it into this repo's docs/media/ folder and push (GitHub Pages then serves it
     at a public URL, which Instagram's API requires),
  2. post it to Instagram (via that public URL) and X (direct upload, no public URL needed),
  3. delete the local copy.

Requires:
    COMFYUI_HOST, IG_USER_ID, IG_ACCESS_TOKEN, X_API_KEY, X_API_SECRET,
    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, PUBLIC_MEDIA_BASE_URL
    (should be https://farawayfolio.com once the custom domain DNS is live —
    NOT andrewfraser.com, which is a separate personal site on the same GitHub account)

Usage:
    python3 publish_batch.py --limit 3
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
import publish_instagram  # noqa: E402
import publish_x  # noqa: E402


def log(message):
    line = f"[{datetime.now().isoformat()}] {message}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def load_prompts():
    with open(os.path.join(HERE, "prompts.json")) as f:
        return json.load(f)


def generate_image(entry, out_dir):
    """Runs comfyui_bridge.py in normal (downloading) mode, since this image needs
    to transit through the repo for public hosting."""
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        sys.executable,
        os.path.join(HERE, "comfyui_bridge.py"),
        "--workflow", os.path.join(HERE, "workflow_api.json"),
        "--prompt", entry["prompt"],
        "--out", out_dir,
        "--timeout", "300",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Generation failed for {entry['id']}: {result.stderr}")
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.endswith(".png") or line.endswith(".jpg"):
            return line
    raise RuntimeError(f"No image path found in bridge output for {entry['id']}: {result.stdout}")


def publish_to_media_repo(local_image_path, theme_id):
    media_dir = os.path.join(REPO_ROOT, "docs", "media", date.today().isoformat())
    os.makedirs(media_dir, exist_ok=True)
    filename = f"{theme_id}{os.path.splitext(local_image_path)[1]}"
    dest_path = os.path.join(media_dir, filename)
    os.rename(local_image_path, dest_path)

    rel_path = os.path.relpath(dest_path, REPO_ROOT)
    subprocess.run(["git", "-C", REPO_ROOT, "add", rel_path], check=True)
    subprocess.run(["git", "-C", REPO_ROOT, "commit", "-m", f"Add media: {rel_path}"], check=True)
    subprocess.run(["git", "-C", REPO_ROOT, "push"], check=True)

    base_url = os.environ["PUBLIC_MEDIA_BASE_URL"].rstrip("/")
    public_url = f"{base_url}/{rel_path}"
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
    parser = argparse.ArgumentParser(description="Generate and publish content live to Instagram + X.")
    parser.add_argument("--limit", type=int, default=3, help="Max posts this run (safety cap, no review gate)")
    args = parser.parse_args()

    prompts = load_prompts()[: args.limit]
    log(f"Starting publish run: {len(prompts)} item(s), limit={args.limit}")

    for entry in prompts:
        try:
            log(f"{entry['id']}: generating image...")
            local_image = generate_image(entry, os.path.join(HERE, "_publish_tmp"))

            log(f"{entry['id']}: pushing to media repo...")
            dest_path, public_url = publish_to_media_repo(local_image, entry["id"])

            log(f"{entry['id']}: waiting for {public_url} to go live...")
            if not wait_until_live(public_url):
                raise RuntimeError(f"{public_url} did not become reachable in time")

            caption = f"{entry['caption']}\n\n{entry['pick'].capitalize()} that comes with me everywhere → link in bio\n.\n.\n.\n#quietluxury #travelaesthetic #slowtravel #europeansummer #travelinspo"

            log(f"{entry['id']}: posting to Instagram...")
            ig_media_id = publish_instagram.post_to_instagram(public_url, caption)
            log(f"{entry['id']}: Instagram OK, media_id={ig_media_id}")

            log(f"{entry['id']}: posting to X...")
            x_result = publish_x.post_to_x(dest_path, entry["caption"])
            log(f"{entry['id']}: X OK, {json.dumps(x_result)}")

            os.remove(dest_path)
            log(f"{entry['id']}: done, local copy removed")

        except Exception as e:
            log(f"{entry['id']}: FAILED — {e}")

    log("Publish run complete.")


if __name__ == "__main__":
    main()
