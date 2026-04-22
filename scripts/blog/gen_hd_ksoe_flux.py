"""HD한국조선해양 #66 FLUX 이미지 생성 (Replicate flux-1.1-pro).

- 본문 2장: 066-ulsan-lng-carrier.webp, 066-yeongam-vlcc.webp
- 썸네일 배경 1장: 066-thumbnail-bg.webp

실행: uv run python -X utf8 scripts/blog/gen_hd_ksoe_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/66-009540-hd-ksoe/assets"

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
        "066-ulsan-lng-carrier.webp",
        "Massive LNG carrier ship under construction in a Korean dry dock at "
        "Ulsan shipyard, giant spherical LNG cargo tanks visible on deck in "
        "multiple rows, towering yellow gantry cranes with red tops looming "
        "overhead, industrial shipbuilding scene at golden hour with warm "
        "sunlight on steel hull, ocean and distant Korean mountains in "
        "background, wide cinematic composition, photorealistic, ultra "
        "sharp, no text, no logos, no watermark",
    ),
    (
        "066-yeongam-vlcc.webp",
        "Enormous VLCC crude oil supertanker hull being assembled in a "
        "coastal shipyard in Yeongam, South Jeolla province, red-painted "
        "steel bottom exposed above the dry dock floor, blue hull panels "
        "lifted by massive cranes in the process of being welded, scaffolding "
        "and workers in hard hats for scale, overcast cool daylight, "
        "panoramic wide shot showing the sheer size of the vessel, "
        "photorealistic, shipbuilding industry, no text, no logos, "
        "no watermark",
    ),
    (
        "066-thumbnail-bg.webp",
        "Cinematic aerial view of a massive Korean shipyard at dusk with "
        "multiple large ships under construction in parallel dry docks, "
        "dozens of yellow and red gantry cranes forming a forest of steel "
        "against a fading blue-orange sunset sky, deep water reflections, "
        "industrial scale of world-leading shipbuilding, dramatic side "
        "lighting from the right, dark navy tones on the left for text "
        "overlay, photorealistic, ultra wide, no text, no logos, no "
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
