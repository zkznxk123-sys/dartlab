"""록히드마틴 #76 FLUX 이미지 생성."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/76-LMT-lockheed-martin/assets"
load_dotenv(ROOT / ".env")
TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("REPLICATE_API_TOKEN 필요")
    sys.exit(1)
API = "https://api.replicate.com/v1/predictions"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

IMAGES = [
    (
        "76-f35-cockpit.webp",
        "Cinematic close-up of a modern fifth-generation stealth fighter "
        "jet on a tarmac at dusk, sleek angular fuselage with characteristic "
        "geometric panels and large bubble canopy, ground crew in flight "
        "suits in the background, dramatic warm sunset reflecting on "
        "polished metallic surfaces, photorealistic aviation photography, "
        "ultra wide angle, no text, no logos, no watermark, no brand marks",
    ),
    (
        "76-missile-defense.webp",
        "Wide cinematic shot of a tactical mobile missile defense launcher "
        "vehicle in a desert landscape at golden hour, large rectangular "
        "launch tubes elevated on a heavy military truck chassis, soldiers "
        "in tactical gear in the background, dramatic dust haze and warm "
        "amber sunset, photorealistic military photography, ultra wide "
        "angle, no text, no logos, no watermark, no brand marks",
    ),
    (
        "76-thumbnail-bg.webp",
        "Cinematic dark dramatic close-up of a polished metallic stealth "
        "aircraft wing edge with characteristic angular geometric panels, "
        "amber warm rim lighting from the right edge fading to deep navy "
        "darkness on the left, metallic reflections on the angular "
        "surface, abstract aerospace defense aesthetic, photorealistic "
        "product photography, ultra sharp focus, shallow depth of field, "
        "no text, no logos, no watermark, no brand marks",
    ),
]


def _create_pred(p):
    return requests.post(
        API,
        headers=HEADERS,
        json={
            "version": "black-forest-labs/flux-1.1-pro",
            "input": {
                "prompt": p,
                "aspect_ratio": "16:9",
                "output_format": "webp",
                "output_quality": 90,
                "safety_tolerance": 2,
            },
        },
        timeout=60,
    ).json()["id"]


def _poll(pid, t=180):
    dl = time.time() + t
    while time.time() < dl:
        r = requests.get(f"{API}/{pid}", headers=HEADERS, timeout=30).json()
        if r.get("status") == "succeeded":
            o = r["output"]
            return o[0] if isinstance(o, list) else o
        if r.get("status") == "failed":
            raise RuntimeError(r.get("error"))
        time.sleep(3)
    raise TimeoutError(pid)


def gen(fn, p, retries=3):
    out = ASSETS / fn
    for i in range(1, retries + 1):
        try:
            print(f"  [{i}/{retries}] {fn}")
            pid = _create_pred(p)
            url = _poll(pid)
            out.write_bytes(requests.get(url, timeout=60).content)
            print(f"  OK {fn} -> {out.stat().st_size // 1024}KB")
            return
        except Exception as e:
            print(f"  WARN {e}")
            if i < retries:
                time.sleep(6)
    raise RuntimeError(f"fail {fn}")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    for idx, (fn, p) in enumerate(IMAGES):
        if idx > 0:
            print("  -- 12s gap --")
            time.sleep(12)
        gen(fn, p)
    print("DONE")
