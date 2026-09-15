#!/usr/bin/env python3
"""
Bridge to a ComfyUI instance running on the Windows machine, reachable over the LAN.

Usage:
    python3 comfyui_bridge.py --workflow workflow_api.json --prompt "golden hour balcony, linen curtains, quiet luxury" --out ./output

Setup on the Windows ComfyUI machine:
    1. Launch ComfyUI with `--listen 0.0.0.0` so it accepts LAN connections
       (default python main.py --listen 0.0.0.0 --port 8188)
    2. Confirm Windows Firewall allows inbound TCP 8188 on the private network profile.
    3. Find the Windows machine's LAN IP (ipconfig) and set COMFYUI_HOST below,
       or export COMFYUI_HOST=192.168.x.x before running this script.
    4. In the ComfyUI web UI, build your workflow, then use "Save (API Format)"
       to export workflow_api.json — that's the file this script submits.
"""

import argparse
import json
import os
import env_loader  # noqa: F401 (loads ../.env into os.environ)
import random
import time
import urllib.parse
import urllib.request
import uuid

COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "192.168.1.100")
COMFYUI_PORT = os.environ.get("COMFYUI_PORT", "8188")
BASE_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"


def load_workflow(path):
    with open(path, "r") as f:
        return json.load(f)


def set_prompt_text(workflow, prompt_text):
    """Inject prompt text into the workflow. Tries known patterns in order:
    1. A PrimitiveStringMultiline node titled "Text String (User Prompt)"
       (used by the Krea2-turbo template's built-in prompt-refinement chain).
    2. Any CLIPTextEncode node not titled as a negative prompt.
    """
    for node in workflow.values():
        title = node.get("_meta", {}).get("title", "")
        if node.get("class_type") == "PrimitiveStringMultiline" and title == "Text String (User Prompt)":
            node["inputs"]["value"] = prompt_text
            return workflow

    for node in workflow.values():
        if node.get("class_type") == "CLIPTextEncode":
            title = node.get("_meta", {}).get("title", "").lower()
            if "negative" not in title:
                node["inputs"]["text"] = prompt_text
    return workflow


def disable_prompt_refinement(workflow):
    """The Krea2-turbo template's built-in LLM prompt-refinement step (a 32B model)
    was observed degenerating into repeated punctuation, corrupting the actual prompt.
    Bypass it and feed the raw prompt straight to the sampler instead."""
    for node in workflow.values():
        title = node.get("_meta", {}).get("title", "")
        if node.get("class_type") == "PrimitiveBoolean" and title == "Boolean (Refine Prompt?)":
            node["inputs"]["value"] = False
    return workflow


def randomize_seed(workflow):
    """Randomize seed/noise_seed fields so repeated runs don't produce identical output."""
    for node in workflow.values():
        inputs = node.get("inputs", {})
        for key in ("seed", "noise_seed"):
            if key in inputs and isinstance(inputs[key], (int, float)):
                inputs[key] = random.randint(0, 2**32 - 1)
    return workflow


def set_filename_prefix(workflow, prefix):
    """Override the SaveImage node's filename_prefix so images generated on the
    Windows ComfyUI machine are self-describing (e.g. which prompt theme they're
    from) even when not downloaded back to this Mac."""
    for node in workflow.values():
        if node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = prefix
    return workflow


def queue_prompt(workflow):
    client_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/prompt", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()), client_id


def wait_for_result(prompt_id, timeout=300, poll_interval=3):
    start = time.time()
    while time.time() - start < timeout:
        with urllib.request.urlopen(f"{BASE_URL}/history/{prompt_id}") as resp:
            history = json.loads(resp.read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI job {prompt_id} did not finish within {timeout}s")


def list_output_images(history_entry):
    """Return the image records ComfyUI produced (filename/subfolder/type) without
    downloading them — used when the images should stay on the Windows machine."""
    images = []
    outputs = history_entry.get("outputs", {})
    for node_output in outputs.values():
        for image in node_output.get("images", []):
            images.append(image)
    return images


def download_images(history_entry, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for image in list_output_images(history_entry):
        params = {
            "filename": image["filename"],
            "subfolder": image.get("subfolder", ""),
            "type": image.get("type", "output"),
        }
        query = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
        url = f"{BASE_URL}/view?{query}"
        dest = os.path.join(out_dir, image["filename"])
        urllib.request.urlretrieve(url, dest)
        saved.append(dest)
    return saved


def main():
    parser = argparse.ArgumentParser(description="Queue a ComfyUI job on the LAN and pull down results.")
    parser.add_argument("--workflow", required=True, help="Path to workflow_api.json exported from ComfyUI")
    parser.add_argument("--prompt", required=True, help="Prompt text to inject into the workflow")
    parser.add_argument("--out", default="./output", help="Directory to save generated images (ignored with --no-download)")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds to wait for generation")
    parser.add_argument("--filename-prefix", default=None, help="Override the SaveImage filename_prefix (e.g. the content theme id)")
    parser.add_argument("--no-download", action="store_true", help="Leave images on the ComfyUI machine instead of copying them back here")
    args = parser.parse_args()

    workflow = load_workflow(args.workflow)
    workflow = set_prompt_text(workflow, args.prompt)
    workflow = disable_prompt_refinement(workflow)
    workflow = randomize_seed(workflow)
    if args.filename_prefix:
        workflow = set_filename_prefix(workflow, args.filename_prefix)

    print(f"Submitting job to {BASE_URL} ...")
    result, _ = queue_prompt(workflow)
    prompt_id = result["prompt_id"]
    print(f"Queued as {prompt_id}, waiting for completion...")

    history_entry = wait_for_result(prompt_id, timeout=args.timeout)

    if args.no_download:
        images = list_output_images(history_entry)
        print(f"Generated {len(images)} image(s), left on the ComfyUI machine:")
        for image in images:
            subfolder = image.get("subfolder", "")
            path = f"{subfolder}/{image['filename']}" if subfolder else image["filename"]
            print(f"  {path}")
    else:
        saved = download_images(history_entry, args.out)
        print(f"Saved {len(saved)} image(s):")
        for path in saved:
            print(f"  {path}")


if __name__ == "__main__":
    main()
