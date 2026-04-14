"""Oklo #31 FLUX 이미지 2장 생성

fal.ai FLUX schnell 사용.
실행: FAL_KEY=xxx uv run python -X utf8 scripts/blog/gen_oklo_flux.py
"""

import os
import sys
from pathlib import Path

import requests

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/31-OKLO-oklo/assets"

FAL_KEY = os.getenv("FAL_KEY", "")
if not FAL_KEY:
    print("FAL_KEY 환경변수를 설정하세요")
    sys.exit(1)

IMAGES = [
    (
        "31-oklo-aurora.webp",
        "futuristic small modular nuclear reactor in pristine white building, "
        "minimalist design, aurora borealis style lighting, compact power plant, "
        "photorealistic, cinematic, no text, no logos",
    ),
    (
        "31-oklo-datacenter.webp",
        "massive data center facility powered by small nuclear reactor, "
        "cooling towers and server racks visible, twilight sky, "
        "orange and blue contrast, photorealistic, cinematic, no text, no logos",
    ),
]

API = "https://fal.run/fal-ai/flux/schnell"
HEADERS = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}


def generate(filename: str, prompt: str) -> None:
    out = ASSETS / filename
    payload = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 4,
        "num_images": 1,
    }
    print(f"  generating {filename} ...")
    resp = requests.post(API, json=payload, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    img_url = data["images"][0]["url"]
    img_data = requests.get(img_url, timeout=60).content
    out.write_bytes(img_data)
    print(f"  OK {filename} -> {out.stat().st_size // 1024}KB")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    for fname, prompt in IMAGES:
        generate(fname, prompt)
    print("DONE")
