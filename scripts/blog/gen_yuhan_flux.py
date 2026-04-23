"""유한양행 #71 FLUX 이미지 생성."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/71-000100-yuhan/assets"

load_dotenv(ROOT / ".env")
TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("REPLICATE_API_TOKEN 환경변수를 설정하세요 (.env)")
    sys.exit(1)

API = "https://api.replicate.com/v1/predictions"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

IMAGES: list[tuple[str, str]] = [
    (
        "71-lab-pills.webp",
        "Pharmaceutical laboratory scene with precision white oval tablets "
        "arranged in organized rows on a metallic dispensing tray, glass "
        "beakers and analytical instruments in soft focus background, "
        "warm laboratory lighting, clean and clinical aesthetic, slight blue "
        "tint on glass surfaces, cinematic product photography, ultra sharp "
        "focus on pills, shallow depth of field, no text, no logos, no "
        "watermark, no brand marks",
    ),
    (
        "71-office-legacy.webp",
        "Wide cinematic shot of a historic Korean corporate headquarters "
        "building exterior at dusk, elegant mid-century modern architecture "
        "with large windows illuminated from inside, wide plaza in front, "
        "tall mature trees framing the scene, warm amber city lights in the "
        "distance, slight misty atmosphere, classic corporate photography, "
        "photorealistic, ultra wide angle, no text, no logos, no watermark",
    ),
    (
        "71-thumbnail-bg.webp",
        "Cinematic dark dramatic close-up of a single white oval "
        "pharmaceutical tablet held in sterile tweezers, amber warm rim "
        "lighting from the right edge fading to deep navy darkness on the "
        "left, metallic reflections on the tweezers, abstract medical "
        "laboratory aesthetic, photorealistic product photography, ultra "
        "sharp focus, shallow depth of field, no text, no logos, no "
        "watermark, no brand marks",
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
    resp = requests.post(API, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["id"]


def _poll(pred_id: str, timeout: int = 180) -> str:
    url = f"{API}/{pred_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(url, headers=HEADERS, timeout=30).json()
        status = r.get("status")
        if status == "succeeded":
            out = r["output"]
            return out[0] if isinstance(out, list) else out
        if status == "failed":
            raise RuntimeError(f"prediction failed: {r.get('error')}")
        time.sleep(3)
    raise TimeoutError(f"prediction timed out after {timeout}s: {pred_id}")


def generate(filename: str, prompt: str, retries: int = 3) -> None:
    out = ASSETS / filename
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            print(f"  [{attempt}/{retries}] generating {filename} ...")
            pred_id = _create_prediction(prompt)
            img_url = _poll(pred_id)
            img_data = requests.get(img_url, timeout=60).content
            out.write_bytes(img_data)
            size_kb = out.stat().st_size // 1024
            print(f"  OK {filename} -> {size_kb}KB")
            return
        except (requests.RequestException, RuntimeError, TimeoutError) as exc:
            last_err = exc
            print(f"  WARN attempt {attempt} failed: {exc}")
            if attempt < retries:
                time.sleep(6)
    raise RuntimeError(f"failed to generate {filename}: {last_err}")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    for idx, (fname, prompt) in enumerate(IMAGES):
        if idx > 0:
            print("  -- rate limit gap 12s --")
            time.sleep(12)
        generate(fname, prompt)
    print("DONE")
