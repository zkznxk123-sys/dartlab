"""META/TSLA/HYBE/IONQ 썸네일 원본 배경 4장 재생성.

2026-04-16 회귀: 이 4개 글이 썸네일 원본 배경 (assets/{NN}-thumbnail-bg.webp)
을 남기지 않았고, 최종 썸네일도 2분할 레이아웃 규칙 위반. 재생성해서
§6 썸네일 스펙에 맞춘다. 이후 gen_backfill_thumbnails_composite.py 로 합성.

레이아웃: MNST 기준작 — 좌측 어두운 그라데이션 + 흰 제목 오버레이.
→ 프롬프트도 주 피사체가 우측 또는 중앙에 배치되도록 설계.

실행: uv run python -X utf8 scripts/blog/gen_backfill_thumbnails_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")

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

TARGETS: list[tuple[str, str, str]] = [
    (
        "37-META-meta-platforms",
        "37-thumbnail-bg.webp",
        "Wide cinematic view of a massive AI datacenter hall at night, endless "
        "rows of server racks glowing with cool blue and violet LED light, "
        "dramatic perspective with the main illuminated row on the right side, "
        "left side fading into deep navy darkness, cool fog near the floor, "
        "highly detailed photorealistic industrial architecture, moody cinematic "
        "lighting, no text, no logos, no brand marks, 16:9",
    ),
    (
        "38-TSLA-tesla",
        "38-thumbnail-bg.webp",
        "Cinematic wide shot of a lone sleek electric sedan silhouette on an "
        "empty rain-soaked highway at dusk, motion blur suggesting speed, "
        "the car positioned on the right third of the frame, amber city light "
        "reflected on wet asphalt, deep navy sky with faint cloud texture, "
        "left side of the frame fading to near black, photorealistic, "
        "no text, no logos, no brand marks, 16:9",
    ),
    (
        "39-352820-hybe",
        "39-thumbnail-bg.webp",
        "Cinematic wide shot of a dark empty K-pop concert arena after the "
        "show, a single bright spotlight beam cutting through lingering smoke "
        "on the right third of the stage, scattered confetti on the floor, "
        "thousands of empty seats fading into deep navy darkness on the left, "
        "dramatic atmospheric lighting, photorealistic, no text, no logos, "
        "no brand marks, 16:9",
    ),
    (
        "40-IONQ-ionq",
        "40-thumbnail-bg.webp",
        "Extreme macro photograph of a quantum ion trap experiment, a single "
        "glowing ion suspended between electrodes with crossing laser beams "
        "in cyan and violet, the trapped ion positioned on the right side of "
        "the frame, scientific instrument bokeh in the background, left side "
        "fading to deep black, dramatic physics laboratory lighting, "
        "photorealistic, no text, no logos, no brand marks, 16:9",
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


def generate(folder: str, filename: str, prompt: str, retries: int = 3) -> None:
    out = ROOT / "blog/05-company-reports" / folder / "assets" / filename
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            print(f"  [{attempt}/{retries}] generating {folder}/{filename} ...")
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
    for idx, (folder, fname, prompt) in enumerate(TARGETS):
        if idx > 0:
            print("  -- rate limit gap 12s --")
            time.sleep(12)
        generate(folder, fname, prompt)
    print("DONE")
