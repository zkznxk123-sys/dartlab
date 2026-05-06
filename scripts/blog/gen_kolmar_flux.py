"""한국콜마 (#86) FLUX 이미지 4장 생성.

본문 3장 + 썸네일 배경 1장. flux-1.1-pro, 16:9, webp 90, 12초 간격.
저장: blog/05-company-reports/86-161890-kolmar/assets/86-{slug}.webp
실행: uv run python -X utf8 scripts/blog/gen_kolmar_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/86-161890-kolmar/assets"

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
        "k-beauty-ampoule",
        "Macro close-up of multiple K-beauty cosmetic ampoule glass bottles with droppers, "
        "glowing golden serum liquid inside, dewy droplets on glass surface, "
        "premium dark reflective surface, dramatic studio backlight, "
        "K-beauty ODM hero product shot, photorealistic, cinematic, " + NO_TEXT,
    ),
    (
        "pharma-production",
        "Pharmaceutical tablet pill production line in a sterile cleanroom, "
        "blister packaging machine pressing white round tablets, "
        "Korean pharmaceutical CMO factory floor, workers in white coveralls, "
        "stainless steel equipment, soft fluorescent lighting, "
        "documentary cinematic wide shot, photorealistic, " + NO_TEXT,
    ),
    (
        "odm-factory-floor",
        "Cosmetics manufacturing factory floor with stainless steel reactor tanks "
        "and automated bottling line, glass containers being filled with creamy serum, "
        "Korean ODM facility interior, modern industrial photography, "
        "soft daylight from large windows, clean white walls, "
        "wide cinematic shot, photorealistic, " + NO_TEXT,
    ),
    (
        "thumbnail-bg",
        "Multiple K-beauty cosmetic ampoule bottles arranged on a dark reflective surface, "
        "golden glowing serum, soft cinematic side lighting, premium beauty product hero shot, "
        "depth of field, magazine cover quality, photorealistic, " + NO_TEXT,
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
        out = ASSETS / f"86-{slug}.webp"
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
