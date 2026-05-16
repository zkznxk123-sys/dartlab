"""dartlab-news 카테고리 썸네일 배경 FLUX 생성 (8편).

스펙: BLOG.md §썸네일 — dartlab-news 카테고리 (2026-04-21 확장)
- Replicate flux-1.1-pro, aspect 16:9, webp quality 90
- 저장: blog/02-dartlab-news/{NN}-{slug}/assets/{NN}-thumbnail-bg.webp
- Rate limit: 분당 6건 → 12초 간격 순차

실행: uv run python -X utf8 blog/_scripts/gen_news_flux.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
NEWS_DIR = ROOT / "blog/02-dartlab-news"

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

POSTS: list[tuple[str, str, str]] = [
    (
        "01",
        "dartlab-easy-start",
        "A clean minimalist desk with a dark laptop screen showing a terminal window running Python commands, "
        "uv package manager installing a library with colorful progress bars, cozy home office, "
        "warm ambient lamp light, cinematic shallow depth of field, photorealistic, " + NO_TEXT,
    ),
    (
        "02",
        "vscode-extension-install",
        "A wide shot of a modern editor window with VS Code style interface, sidebar panel open "
        "showing an extension, Korean financial data dashboard visible on the right half, "
        "dark IDE theme, syntax highlighted code lines, soft studio lighting, "
        "photorealistic, cinematic, " + NO_TEXT,
    ),
    (
        "03",
        "scan-market-finance",
        "A wall of glowing screens showing dozens of financial market tickers and candlestick charts in a "
        "dark analytics room, Korean stock market style, blue and green numbers blinking, wide cinematic shot, "
        "data wall aesthetic, photorealistic, " + NO_TEXT,
    ),
    (
        "04",
        "company-one-stock-code",
        "A single dark screen displaying one large 6-digit stock code in bold, surrounded by soft-focus company "
        "financial charts and data cards, spotlight on the code, moody blue tones, cinematic close-up, "
        "photorealistic product shot, " + NO_TEXT,
    ),
    (
        "05",
        "search-without-embeddings",
        "A dark minimalist search bar floating over a cascading waterfall of Korean financial documents and "
        "filings pages, search results materializing instantly as tiny paper fragments, cyan accent glow, "
        "cinematic wide shot, photorealistic, " + NO_TEXT,
    ),
    (
        "06",
        "magic-formula-korea",
        "A dark trading desk with a stack of ranked Korean stock cards glowing, a magnifying glass hovering "
        "over the top card, formulaic ranking visualization, gold and amber rim light, cinematic still life, "
        "photorealistic, " + NO_TEXT,
    ),
    (
        "07",
        "dataset-auto-sync",
        "A sleek laptop on a dark desk receiving streams of data packets from a cloud, cinematic data pipeline "
        "visualization, glowing network lines flowing into the screen, late-night developer workspace, "
        "photorealistic, " + NO_TEXT,
    ),
    (
        "08",
        "pyodide-dartlab-lite",
        "A Microsoft Excel web interface on a laptop screen with a Python sidebar panel open on the right, "
        "spreadsheet cells filled with glowing financial numbers, modern clean office desk, "
        "Korean corporate context, cinematic wide product shot, photorealistic, " + NO_TEXT,
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
    for i, (nn, slug, prompt) in enumerate(POSTS):
        folder = NEWS_DIR / f"{nn}-{slug}" / "assets"
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / f"{nn}-thumbnail-bg.webp"
        if out.exists():
            print(f"SKIP {nn}-{slug} (already exists)")
            continue
        print(f"[{i + 1}/{len(POSTS)}] {nn}-{slug} ...")
        pid = create(prompt)
        img_url = poll(pid)
        download(img_url, out)
        print(f"  -> {out.relative_to(ROOT)} ({out.stat().st_size // 1024}KB)")
        if i < len(POSTS) - 1:
            time.sleep(12)
    print("DONE")


if __name__ == "__main__":
    main()
