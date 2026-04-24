"""실리콘투 #72 FLUX 이미지 생성."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/72-257720-silicon2/assets"

load_dotenv(ROOT / ".env")
TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("REPLICATE_API_TOKEN 환경변수를 설정하세요 (.env)")
    sys.exit(1)

API = "https://api.replicate.com/v1/predictions"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

IMAGES: list[tuple[str, str]] = [
    (
        "72-kbeauty-shelf.webp",
        "Cinematic wide shot of beauty store shelves filled with Korean "
        "skincare products, rows of pink cushions, serums, sheet masks, and "
        "jade green bottles arranged in organized rows, soft warm boutique "
        "lighting with subtle pink and gold accents, clean modern retail "
        "aesthetic, photorealistic product photography, ultra sharp focus, "
        "shallow depth of field, no text, no logos, no watermark, no brand marks",
    ),
    (
        "72-warehouse-logistics.webp",
        "Wide shot of a modern automated logistics warehouse, tall shelves "
        "filled with pink and white cosmetics boxes, conveyor belts running "
        "through the center, workers in orange vests pushing carts, bright "
        "LED industrial lighting on polished concrete floors, slight motion "
        "blur on moving packages, cinematic industrial photography, "
        "photorealistic, ultra wide angle, no text, no logos, no watermark",
    ),
    (
        "72-thumbnail-bg.webp",
        "Cinematic dark dramatic close-up of scattered luxurious Korean "
        "skincare pink glass bottles and serums, amber warm rim lighting "
        "from the right edge fading to deep navy darkness on the left, "
        "metallic gold reflections on bottle caps, abstract beauty "
        "editorial aesthetic, photorealistic product photography, ultra "
        "sharp focus, shallow depth of field, no text, no logos, no watermark",
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
