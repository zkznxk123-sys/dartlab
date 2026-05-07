"""펄어비스 (#89) FLUX 이미지 4장.

저장: blog/05-company-reports/89-263750-pearlabyss-two-ips-meet/assets/89-{slug}.webp
실행: uv run python -X utf8 scripts/blog/gen_pearlabyss_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/89-263750-pearlabyss-two-ips-meet/assets"

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
        "fantasy-warrior-cinematic",
        "Cinematic fantasy warrior in heavy ornate armor standing on a windswept desert plateau at golden hour, "
        "scarlet cloak flowing, longsword grounded, wide cinematic landscape behind, "
        "AAA action-adventure game key art aesthetic, photorealistic CGI, high detail textures, "
        "dramatic side rim light, depth of field, " + NO_TEXT,
    ),
    (
        "mmorpg-cityscape",
        "Vast medieval fantasy city built on mountain cliffs, intricate stone architecture with flowing pennants, "
        "wide aerial cinematic view at twilight blue hour, glowing torches and lanterns lighting streets, "
        "characters small in foreground for scale, atmospheric haze and depth, "
        "MMORPG world environment art, photorealistic CGI, high detail, " + NO_TEXT,
    ),
    (
        "spaceship-cluster-eve",
        "Massive sci-fi space battle between thousands of capital starships in deep space, "
        "lasers and explosions across vast distances, blue and orange ion trail lights, "
        "nebula clouds in background, hard sci-fi cinematic capture, "
        "scale of EVE Online style fleet engagement, photorealistic CGI, " + NO_TEXT,
    ),
    (
        "thumbnail-bg",
        "Lone fantasy warrior silhouette on a dark crimson desert dune at twilight, "
        "dramatic side rim light, deep navy sky transitioning to crimson glow at horizon, "
        "premium AAA game cover hero shot, depth of field, magazine cover atmosphere, "
        "photorealistic CGI, " + NO_TEXT,
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
        out = ASSETS / f"89-{slug}.webp"
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
