"""한미사이언스 #75 FLUX 이미지 생성."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/75-008930-hanmi-science/assets"
load_dotenv(ROOT / ".env")
TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("REPLICATE_API_TOKEN 필요")
    sys.exit(1)
API = "https://api.replicate.com/v1/predictions"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

IMAGES = [
    (
        "75-probiotic-bottles.webp",
        "Professional pharmacy product shelf display with white plastic "
        "pill bottles in organized rows, clean white pharmaceutical "
        "packaging, bright clinical white LED lighting in a modern "
        "pharmacy interior, minimalist medical retail environment, "
        "photorealistic product photography, ultra sharp focus, clinical "
        "and clean aesthetic, no text, no logos, no watermark",
    ),
    (
        "75-pharmaceutical-tablets.webp",
        "Wide shot of a modern pharmaceutical manufacturing clean room, "
        "white oval pills arranged in precise rows on a stainless steel "
        "industrial conveyor belt, technicians in white hair nets and "
        "lab coats monitoring equipment at workstations in the "
        "background, bright cool fluorescent lighting, highly clinical "
        "industrial environment, photorealistic industrial photography, "
        "wide angle, no text, no logos, no watermark, no brand marks",
    ),
    (
        "75-thumbnail-bg.webp",
        "Close-up of a single white oval pharmaceutical tablet held by "
        "sterile metal laboratory tweezers on a dark navy background, "
        "cool neutral lighting from the right edge, clean medical "
        "laboratory aesthetic, photorealistic product photography, "
        "ultra sharp focus, shallow depth of field, clinical and "
        "minimalist, no text, no logos, no watermark, no brand marks",
    ),
]


def _create_prediction(prompt: str) -> str:
    payload = {
        "version": "black-forest-labs/flux-1.1-pro",
        "input": {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "output_format": "webp",
            "output_quality": 90,
            "safety_tolerance": 2,
        },
    }
    return requests.post(API, headers=HEADERS, json=payload, timeout=60).json()["id"]


def _poll(pid: str, timeout: int = 180) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{API}/{pid}", headers=HEADERS, timeout=30).json()
        if r.get("status") == "succeeded":
            out = r["output"]
            return out[0] if isinstance(out, list) else out
        if r.get("status") == "failed":
            raise RuntimeError(r.get("error"))
        time.sleep(3)
    raise TimeoutError(pid)


def generate(fname: str, prompt: str, retries: int = 3) -> None:
    out = ASSETS / fname
    for i in range(1, retries + 1):
        try:
            print(f"  [{i}/{retries}] {fname}")
            pid = _create_prediction(prompt)
            url = _poll(pid)
            out.write_bytes(requests.get(url, timeout=60).content)
            print(f"  OK {fname} -> {out.stat().st_size // 1024}KB")
            return
        except Exception as e:
            print(f"  WARN {e}")
            if i < retries:
                time.sleep(6)
    raise RuntimeError(f"fail {fname}")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    for idx, (fname, prompt) in enumerate(IMAGES):
        if idx > 0:
            print("  -- 12s gap --")
            time.sleep(12)
        generate(fname, prompt)
    print("DONE")
