"""ON Semiconductor (#87) FLUX 이미지 4장 생성.

본문 3장 + 썸네일 배경 1장. flux-1.1-pro, 16:9, webp 90, 12초 간격.
저장: blog/05-company-reports/87-ON-onsemi-sic-cycle-bill/assets/87-{slug}.webp
실행: uv run python -X utf8 scripts/blog/gen_on_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/87-ON-onsemi-sic-cycle-bill/assets"

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
        "sic-wafer",
        "Macro close-up of a 200mm silicon carbide (SiC) semiconductor wafer, "
        "iridescent blue-violet surface revealing thousands of microscopic die patterns, "
        "wafer held by a robotic arm in a semiconductor cleanroom, "
        "soft cinematic top-light reflecting on the wafer, depth of field, "
        "premium semiconductor industrial photography, photorealistic, " + NO_TEXT,
    ),
    (
        "ev-inverter-module",
        "Electric vehicle traction inverter power module exposed on a workbench, "
        "tightly packed silicon carbide MOSFET dies under a transparent epoxy package, "
        "thick copper busbars and gold bond wires visible, automotive grade dark grey casing, "
        "studio macro photography, dramatic side-light, technical documentary tone, "
        "photorealistic, " + NO_TEXT,
    ),
    (
        "fab-cleanroom",
        "Semiconductor fabrication plant cleanroom interior, rows of stainless steel etching "
        "and deposition tools, technicians in white bunny suits walking down the bay aisle, "
        "yellow lithography area lighting in the distance, polished epoxy floor reflecting equipment, "
        "wide cinematic interior shot, documentary photography, photorealistic, " + NO_TEXT,
    ),
    (
        "thumbnail-bg",
        "Single 200mm silicon carbide wafer floating on a dark reflective surface, "
        "iridescent blue-violet rim light, glowing subtle teal underglow, "
        "premium semiconductor product hero shot, dramatic side cinematic lighting, "
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
        out = ASSETS / f"87-{slug}.webp"
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
