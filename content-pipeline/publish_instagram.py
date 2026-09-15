#!/usr/bin/env python3
"""
Post an image + caption to Instagram via the Graph API (Content Publishing).

Uses the Instagram API with Instagram Login (graph.instagram.com), not the older
Facebook-Page-token flow (graph.facebook.com) — the two are different APIs with
different base URLs and token formats (this one's tokens start with "IGAA").

Requires:
    IG_USER_ID       - the Instagram professional account's numeric ID (from
                        GET https://graph.instagram.com/v21.0/me?fields=id,username)
    IG_ACCESS_TOKEN  - an Instagram Login access token with instagram_content_publish scope.
                        Short-lived by default (~1hr); exchange for a 60-day token via
                        GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token
                        &client_secret=<APP_SECRET>&access_token=<TOKEN> once the app secret is available.

The image must already be reachable at a public HTTPS URL (Instagram fetches it
server-side, it does not accept direct file uploads).

Usage:
    export IG_USER_ID=... IG_ACCESS_TOKEN=...
    python3 publish_instagram.py --image-url https://farawayfolio.example/media/foo.png --caption "..."
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import time
import urllib.parse
import urllib.request

GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"


def get_creds():
    ig_user_id = os.environ.get("IG_USER_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    missing = [name for name, val in [("IG_USER_ID", ig_user_id), ("IG_ACCESS_TOKEN", access_token)] if not val]
    if missing:
        raise SystemExit(f"Missing Instagram credentials: {', '.join(missing)} (set as env vars)")
    return ig_user_id, access_token


def api_post(path, params):
    url = f"{BASE_URL}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_get(path, params):
    url = f"{BASE_URL}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def create_container(ig_user_id, access_token, image_url, caption=None, is_carousel_item=False):
    params = {"image_url": image_url, "access_token": access_token}
    if caption:
        params["caption"] = caption
    if is_carousel_item:
        params["is_carousel_item"] = "true"
    result = api_post(f"{ig_user_id}/media", params)
    if "id" not in result:
        raise RuntimeError(f"Failed to create media container: {result}")
    return result["id"]


def create_carousel_container(ig_user_id, access_token, child_ids, caption):
    result = api_post(
        f"{ig_user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": access_token,
        },
    )
    if "id" not in result:
        raise RuntimeError(f"Failed to create carousel container: {result}")
    return result["id"]


def wait_for_container_ready(container_id, access_token, timeout=120, poll_interval=3):
    start = time.time()
    while time.time() - start < timeout:
        status = api_get(container_id, {"fields": "status_code", "access_token": access_token})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Media container failed processing: {status}")
        time.sleep(poll_interval)
    raise TimeoutError(f"Media container {container_id} did not finish processing within {timeout}s")


def publish_container(ig_user_id, access_token, container_id):
    result = api_post(f"{ig_user_id}/media_publish", {"creation_id": container_id, "access_token": access_token})
    if "id" not in result:
        raise RuntimeError(f"Failed to publish media: {result}")
    return result["id"]


def post_to_instagram(image_url, caption):
    ig_user_id, access_token = get_creds()
    container_id = create_container(ig_user_id, access_token, image_url, caption)
    wait_for_container_ready(container_id, access_token)
    media_id = publish_container(ig_user_id, access_token, container_id)
    return media_id


def post_carousel_to_instagram(image_urls, caption):
    """Post 2-10 images as a single Instagram carousel post."""
    if not (2 <= len(image_urls) <= 10):
        raise ValueError(f"Instagram carousels need 2-10 images, got {len(image_urls)}")
    ig_user_id, access_token = get_creds()

    child_ids = []
    for url in image_urls:
        child_id = create_container(ig_user_id, access_token, url, is_carousel_item=True)
        wait_for_container_ready(child_id, access_token)
        child_ids.append(child_id)

    carousel_id = create_carousel_container(ig_user_id, access_token, child_ids, caption)
    wait_for_container_ready(carousel_id, access_token)
    media_id = publish_container(ig_user_id, access_token, carousel_id)
    return media_id


def main():
    parser = argparse.ArgumentParser(description="Post an image (or carousel) + caption to Instagram.")
    parser.add_argument("--image-url", action="append", dest="image_urls", required=True,
                         help="Public HTTPS URL of an image; pass multiple times for a carousel (2-10 images)")
    parser.add_argument("--caption", required=True, help="Post caption")
    args = parser.parse_args()

    if len(args.image_urls) == 1:
        media_id = post_to_instagram(args.image_urls[0], args.caption)
    else:
        media_id = post_carousel_to_instagram(args.image_urls, args.caption)
    print(json.dumps({"media_id": media_id}, indent=2))


if __name__ == "__main__":
    main()
