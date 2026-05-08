"""에코프로비엠 (#91) FLUX 4 컷.

저장: blog/05-company-reports/91-247540-ecopro-bm/assets/91-{slug}.webp
실행: uv run python -X utf8 scripts/blog/gen_ecopro_bm_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/91-247540-ecopro-bm/assets"

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
        "cathode-powder",
        "Macro close-up of jet-black cathode active material powder spilling from a stainless steel container onto a smooth surface, "
        "dramatic top-down studio lighting reveals fine particle texture, subtle blue-grey reflections on metallic surface, "
        "lithium-ion battery material industrial photography, depth of field, "
        "premium scientific material capture, photorealistic, " + NO_TEXT,
    ),
    (
        "rotary-calciner",
        "Industrial rotary calciner kiln operating at 850 Celsius, glowing orange-red interior visible through inspection port, "
        "long horizontal cylindrical furnace rotating with refractory brick lining, ceramic tubes feeding precursor material, "
        "Korean cathode manufacturing line in Cheongju Ochang, wide cinematic shot, "
        "high-temperature industrial atmosphere, photorealistic, " + NO_TEXT,
    ),
    (
        "ev-battery-pack",
        "Cutaway view of an electric vehicle battery pack module showing rows of cylindrical 21700 lithium-ion cells, "
        "polished aluminum casing reflecting clean lighting, copper bus bars connecting cells, BMS circuit boards visible, "
        "automotive engineering documentary atmosphere, wide cinematic technical photography, "
        "photorealistic, " + NO_TEXT,
    ),
    (
        "thumbnail-bg",
        "Single jet-black cathode powder mound on a dark reflective surface, "
        "dramatic side rim light highlighting fine particle texture, subtle blue-violet hue at edges, "
        "premium scientific material hero shot, depth of field, magazine cover atmosphere, "
        "photorealistic, " + NO_TEXT,
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
        out = ASSETS / f"91-{slug}.webp"
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
