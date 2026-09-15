#!/usr/bin/env python3
"""Regenerate the 3 prompts.json carousel posts (4 images each) with the
hardened negative-prompt workflow, for swipe review before posting."""
import json, os, subprocess, sys
sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_carousel_review")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(HERE, "prompts.json")) as f:
    posts = json.load(f)

manifest = []
for post in posts:
    for i, prompt in enumerate(post["images"], start=1):
        prefix = f"{post['id']}_{i}"
        out_png = os.path.join(OUT, f"{prefix}.png")
        if os.path.exists(out_png):
            print(f"=== {prefix} already done, skipping ===")
            manifest.append({"post": post["id"], "pack": post["id"], "index": i, "prompt": prompt, "path": out_png})
            continue
        print(f"=== generating {prefix} ===")
        cmd = [sys.executable, os.path.join(HERE, "comfyui_bridge.py"),
               "--workflow", os.path.join(HERE, "workflow_api.json"),
               "--prompt", prompt, "--out", OUT, "--timeout", "600"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"!! {prefix} FAILED: {result.stderr[-800:]}")
            continue
        found = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.endswith(".png"):
                found = line
        if not found:
            print(f"!! {prefix} no image path in output")
            continue
        os.rename(found, out_png)
        manifest.append({"post": post["id"], "pack": post["id"], "index": i, "prompt": prompt, "path": out_png})

with open(os.path.join(OUT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
print(f"\n=== done: {len(manifest)}/12 images ===")
