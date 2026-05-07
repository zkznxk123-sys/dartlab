"""LG생활건강 (#89) FLUX 이미지 3장 생성.

본문 2장 + 썸네일 배경 1장. flux-1.1-pro, 16:9, webp 90, 12초 간격.
저장: blog/05-company-reports/89-051900-lg-h-and-h/assets/89-{slug}.webp
실행: uv run python -X utf8 scripts/blog/gen_lghnh_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/90-051900-lg-h-and-h/assets"

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

NO_TEXT = "no text, no logos, no watermark, no brand marks"

POSTS: list[tuple[str, str]] = [
    (
        "luxury-hanbang-cosmetics",
        "Luxury Korean traditional hanbang cosmetics premium product display, "
        "ornate dark red lacquered cosmetic jars with gold accents and golden lids, "
        "delicate calligraphic floral patterns on the glass surfaces, "
        "arranged on a polished black marble counter, "
        "soft warm spotlight from above, royal heritage aesthetic, "
        "premium boutique department store cosmetic counter shot, "
        "shallow depth of field, magazine quality, photorealistic, " + NO_TEXT,
    ),
    (
        "duty-free-cosmetics-aisle",
        "Korean airport duty-free cosmetics shelf aisle, rows of high-end skincare bottles "
        "and lotions on glass shelves with soft cool LED backlighting, "
        "almost empty long aisle perspective, polished marble floor reflecting fluorescent lights, "
        "Incheon airport duty-free atmosphere, melancholic quiet evening lighting, "
        "wide cinematic shot, documentary photography, photorealistic, " + NO_TEXT,
    ),
    (
        "thumbnail-bg",
        "Luxury Korean hanbang cosmetic jars with gold accents arranged on dark reflective marble, "
        "ornate red and black lacquer containers, soft cinematic warm side lighting, "
        "premium beauty product hero composition, depth of field, "
        "moody dramatic atmosphere, magazine cover quality, photorealistic, " + NO_TEXT,
    ),
]


def create(prompt: str) -> str:
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
    r = requests.post(API, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def poll(pid: str, timeout: int = 180) -> str:
    url = f"{API}/{pid}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        j = r.json()
        s = j.get("status")
        if s == "succeeded":
            out = j.get("output")
            return out[0] if isinstance(out, list) else out
        if s == "failed":
            raise RuntimeError(f"FLUX failed: {j.get('error')}")
        time.sleep(2)
    raise TimeoutError(f"FLUX poll timeout {pid}")


def download(url: str, path: Path) -> None:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for i, (slug, prompt) in enumerate(POSTS):
        out = ASSETS / f"90-{slug}.webp"
        if out.exists():
            print(f"SKIP {slug} (already exists)")
            continue
        print(f"[{i + 1}/{len(POSTS)}] {slug} ...")
        pid = create(prompt)
        img_url = poll(pid)
        download(img_url, out)
        print(f"  -> {out.relative_to(ROOT)} ({out.stat().st_size // 1024}KB)")
        if i < len(POSTS) - 1:
            time.sleep(12)
    print("DONE")


if __name__ == "__main__":
    main()
