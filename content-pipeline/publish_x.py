#!/usr/bin/env python3
"""
Post an image + caption to X (Twitter) via API v2 (tweet creation) + v1.1 (media upload,
still required for media even under v2).

Requires OAuth 1.0a user-context credentials (posting needs user context, not app-only
bearer auth): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET.

Usage:
    export X_API_KEY=... X_API_SECRET=... X_ACCESS_TOKEN=... X_ACCESS_TOKEN_SECRET=...
    python3 publish_x.py --image /path/to/image.png --text "caption here"
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import random
import string
import time
import urllib.parse
import urllib.request


def oauth1_header(method, url, params, api_key, api_secret, token, token_secret):
    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    all_params = {**params, **oauth_params}
    param_string = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )
    base_string = "&".join([method.upper(), urllib.parse.quote(url, safe=""), urllib.parse.quote(param_string, safe="")])
    signing_key = f"{urllib.parse.quote(api_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    signature = base64.b64encode(hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()).decode()
    oauth_params["oauth_signature"] = signature

    header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(oauth_params.items())
    )
    return header


def get_creds():
    creds = {
        "api_key": os.environ.get("X_API_KEY"),
        "api_secret": os.environ.get("X_API_SECRET"),
        "token": os.environ.get("X_ACCESS_TOKEN"),
        "token_secret": os.environ.get("X_ACCESS_TOKEN_SECRET"),
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        raise SystemExit(f"Missing X credentials: {', '.join(missing)} (set as env vars)")
    return creds


def upload_media(image_path, creds):
    url = "https://upload.twitter.com/1.1/media/upload.json"
    with open(image_path, "rb") as f:
        image_data = f.read()

    boundary = "----FarawayFolioBoundary" + "".join(random.choices(string.ascii_letters, k=16))
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media_data"\r\n\r\n'
        f"{base64.b64encode(image_data).decode()}\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    auth_header = oauth1_header("POST", url, {}, creds["api_key"], creds["api_secret"], creds["token"], creds["token_secret"])
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result["media_id_string"]


def create_tweet(text, media_id, creds):
    url = "https://api.twitter.com/2/tweets"
    payload = {"text": text}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}

    auth_header = oauth1_header("POST", url, {}, creds["api_key"], creds["api_secret"], creds["token"], creds["token_secret"])
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def post_to_x(image_path, text):
    creds = get_creds()
    media_id = upload_media(image_path, creds) if image_path else None
    result = create_tweet(text, media_id, creds)
    return result


def main():
    parser = argparse.ArgumentParser(description="Post an image + caption to X.")
    parser.add_argument("--image", help="Path to image file (optional, text-only post if omitted)")
    parser.add_argument("--text", required=True, help="Tweet text")
    args = parser.parse_args()

    result = post_to_x(args.image, args.text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
