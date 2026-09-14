#!/usr/bin/env python3
"""
Post an image + caption to a Facebook Page via the Graph API.

Unlike Instagram's Content Publishing API, Facebook's /photos endpoint accepts
a direct multipart file upload — no public URL hosting required.

Requires:
    FB_PAGE_ID           - the Page's numeric ID
    FB_PAGE_ACCESS_TOKEN - a Page access token with pages_manage_posts scope

Usage:
    export FB_PAGE_ID=... FB_PAGE_ACCESS_TOKEN=...
    python3 publish_facebook.py --image /path/to/image.png --caption "..."
"""

import argparse
import json
import mimetypes
import os
import random
import string
import urllib.parse
import urllib.request

GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


def get_creds():
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    missing = [name for name, val in [("FB_PAGE_ID", page_id), ("FB_PAGE_ACCESS_TOKEN", access_token)] if not val]
    if missing:
        raise SystemExit(f"Missing Facebook credentials: {', '.join(missing)} (set as env vars)")
    return page_id, access_token


def upload_photo(page_id, access_token, image_path, caption=None, published=True):
    """Upload one photo. published=False stages it unpublished, for use as one
    item in a later multi-photo /feed post (Facebook's carousel-equivalent)."""
    url = f"{BASE_URL}/{page_id}/photos"

    with open(image_path, "rb") as f:
        image_data = f.read()
    content_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
    filename = os.path.basename(image_path)

    boundary = "----FarawayFolioBoundary" + "".join(random.choices(string.ascii_letters, k=16))
    fields = {"access_token": access_token, "published": "true" if published else "false"}
    if caption:
        fields["caption"] = caption

    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n".encode()
        + image_data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if "id" not in result:
        raise RuntimeError(f"Failed to upload photo: {result}")
    return result["id"]


def post_to_facebook(image_path, caption):
    page_id, access_token = get_creds()
    return {"id": upload_photo(page_id, access_token, image_path, caption=caption, published=True)}


def post_multi_to_facebook(image_paths, caption):
    """Post 2+ images as a single Facebook Page post (Facebook's carousel-equivalent)."""
    page_id, access_token = get_creds()

    photo_ids = [upload_photo(page_id, access_token, path, published=False) for path in image_paths]

    attached_media = json.dumps([{"media_fbid": pid} for pid in photo_ids])
    data = urllib.parse.urlencode(
        {"message": caption, "attached_media": attached_media, "access_token": access_token}
    ).encode()
    req = urllib.request.Request(f"{BASE_URL}/{page_id}/feed", data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if "id" not in result:
        raise RuntimeError(f"Failed to create multi-photo post: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Post an image (or multiple) + caption to a Facebook Page.")
    parser.add_argument("--image", action="append", dest="images", required=True,
                         help="Path to an image file; pass multiple times for a multi-photo post")
    parser.add_argument("--caption", required=True, help="Post caption")
    args = parser.parse_args()

    if len(args.images) == 1:
        result = post_to_facebook(args.images[0], args.caption)
    else:
        result = post_multi_to_facebook(args.images, args.caption)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
