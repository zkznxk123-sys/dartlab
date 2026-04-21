"""리노공업 #64 FLUX 이미지 생성 (Replicate flux-1.1-pro).

- 본문 2장: 064-pogopin-macro.webp, 064-busan-factory.webp
- 썸네일 배경 1장: 064-thumbnail-bg.webp

실행: uv run python -X utf8 scripts/blog/gen_rino_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/64-058470-rino-industrial/assets"

load_dotenv(ROOT / ".env")
TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
if not TOKEN:
    print("REPLICATE_API_TOKEN 환경변수를 설정하세요 (.env)")
    sys.exit(1)

API = "https://api.replicate.com/v1/predictions"
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
}

IMAGES: list[tuple[str, str]] = [
    (
        "064-pogopin-macro.webp",
        "Extreme macro photograph of a single gold-plated spring-loaded contact "
        "pin, about 5 millimeters long, standing upright against a dark glossy "
        "surface, semiconductor test equipment context, visible spring coils "
        "inside a cylindrical brass barrel, sharp focus on the pointed tip, "
        "dramatic cool blue side lighting, clinical cleanroom atmosphere, "
        "photorealistic, product photography, ultra sharp, no text, no logos",
    ),
    (
        "064-busan-factory.webp",
        "Modest rectangular Korean precision manufacturing factory in Busan "
        "industrial area, warm evening light, family-run small-to-medium "
        "business aesthetic, a few parked vehicles in front, distant "
        "coastal mountains behind, clean white walls with no signage, "
        "cinematic wide shot, photorealistic, subtle golden hour tones, "
        "no text, no logos, no brand marks",
    ),
    (
        "064-thumbnail-bg.webp",
        "Wide cinematic macro shot of a single golden pogo pin floating "
        "against a dark navy gradient background, shallow depth of field "
        "with the spring coils visible, amber rim light on the right and "
        "fading to deep blue darkness on the left, abstract semiconductor "
        "test equipment aesthetic, photorealistic, ultra minimalist, "
        "no text, no logos",
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
