"""
Thermal/reliability safety wrapper around comfyui_bridge.py, shared by every
generation script.

Built after the Windows ComfyUI machine overheated and stopped responding
during an unattended overnight run (2026-09-14/15) — the pipeline kept
retrying and moving on to the next image with almost no pause, running the
GPU flat-out for hours unattended. Two protections, both simple because
ComfyUI doesn't expose GPU temperature over the API (only vram/ram):

1. A cooldown pause between every image (success or failure) so the GPU
   gets an idle gap instead of continuous back-to-back load.
2. A per-run image cap, after which a script stops cleanly and reports how
   to resume, instead of running for hours unattended.

On top of that: a fast reachability pre-check before each image, so a
machine that's stopped responding aborts the WHOLE run immediately instead
of retry-hammering it (which is its own way of keeping a struggling machine
under load rather than letting it recover).
"""

import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

COOLDOWN_SECONDS = int(os.environ.get("COMFYUI_COOLDOWN_SECONDS", "45"))
MAX_IMAGES_PER_RUN = int(os.environ.get("COMFYUI_MAX_IMAGES_PER_RUN", "10"))


class MachineUnreachableError(Exception):
    """ComfyUI didn't respond to a basic health check -- stop the whole run
    rather than retrying against a possibly overheated/hung machine."""


class RunCapReached(Exception):
    """Hit the per-run image safety cap. Not a failure -- just stop here."""


def is_comfyui_alive(timeout=5):
    host = os.environ.get("COMFYUI_HOST", "192.168.1.100")
    port = os.environ.get("COMFYUI_PORT", "8188")
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/system_stats", timeout=timeout):
            return True
    except Exception:
        return False


def cooldown(seconds=None):
    seconds = COOLDOWN_SECONDS if seconds is None else seconds
    if seconds > 0:
        print(f"  (cooling down {seconds}s before the next image...)")
        time.sleep(seconds)


def generate_one_safe(prompt_text, filename_prefix, out_dir, timeout=600):
    """Generate one image with a reachability pre-check, a single bounded
    retry, and a mandatory cooldown afterward. Raises MachineUnreachableError
    immediately (no retry) if ComfyUI isn't responding at all; raises
    RuntimeError if it's reachable but generation failed twice."""
    os.makedirs(out_dir, exist_ok=True)

    if not is_comfyui_alive():
        raise MachineUnreachableError(
            "ComfyUI isn't responding to /system_stats -- machine may be asleep, "
            "overheated, or hung. Stopping this run rather than hammering it."
        )

    cmd = [
        sys.executable,
        os.path.join(HERE, "comfyui_bridge.py"),
        "--workflow", os.path.join(HERE, "workflow_api.json"),
        "--prompt", prompt_text,
        "--filename-prefix", filename_prefix,
        "--out", out_dir,
        "--timeout", str(timeout),
    ]

    result_path = None
    for attempt in (1, 2):
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0 and "Saved 1 image" in result.stdout:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.endswith(".png") or line.endswith(".jpg"):
                    result_path = line
            break
        print(result.stderr)
        if attempt == 1:
            if not is_comfyui_alive():
                cooldown()
                raise MachineUnreachableError(
                    "ComfyUI stopped responding mid-generation -- stopping this run."
                )
            print(f"  attempt {attempt} failed, waiting {COOLDOWN_SECONDS}s before one retry...")
            time.sleep(COOLDOWN_SECONDS)

    cooldown()

    if result_path is None:
        raise RuntimeError(f"Generation failed after retries for {filename_prefix}")
    return result_path


class RunCapCounter:
    """Tracks images generated this run against MAX_IMAGES_PER_RUN. Call
    .check() before each image; it raises RunCapReached once the cap hits,
    so the caller's existing resumable logic picks up next run."""

    def __init__(self, cap=None):
        self.cap = MAX_IMAGES_PER_RUN if cap is None else cap
        self.count = 0

    def check(self):
        if self.count >= self.cap:
            raise RunCapReached(
                f"Reached this run's safety cap of {self.cap} images. "
                f"Rerun the same command to continue -- already-finished images are skipped."
            )
        self.count += 1
