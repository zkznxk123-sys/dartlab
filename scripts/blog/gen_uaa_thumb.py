"""Under Armour #35 썸네일 재생성 — Pillow 합성 (한글 폰트 fix).

배경: `35-ua-athlete.webp` (FLUX 기존). 이전 썸네일은 한글 폰트 누락으로 tofu 표시.
저장 2곳:
  - blog/05-company-reports/35-UAA-under-armour/assets/35-thumbnail.webp
  - landing/static/thumbnails/UAA-under-armour.webp

실행: uv run python -X utf8 scripts/blog/gen_uaa_thumb.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/35-UAA-under-armour/assets"
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

BG_FILE = ASSETS / "35-ua-athlete.webp"

COMPANY = "Under Armour (UAA)"
TITLE_LINES = ["CEO 3명이 바뀌는 동안", "매출이 줄었다"]
SUBTITLE = "GPM 47% · Plank 복귀 · Curry 이별"


def make_thumb() -> None:
    W, H = 1200, 630

    if BG_FILE.exists():
        bg = Image.open(BG_FILE).convert("RGB")
    else:
        print(f"  WARN: {BG_FILE} 없음 — 단색 배경 사용")
        bg = Image.new("RGB", (W, H), (10, 14, 26))

    bw, bh = bg.size
    ratio = max(W / bw, H / bh)
    nw, nh = int(bw * ratio), int(bh * ratio)
    bg = bg.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    bg = bg.crop((left, top, left + W, top + H))

    ovl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ovl)
    for x in range(W):
        alpha = max(0, int(210 * (1 - x / 900)))
        od.rectangle([(x, 0), (x + 1, H)], fill=(10, 14, 26, alpha))

    dim = Image.new("RGBA", (W, H), (10, 14, 26, 70))
    bg = Image.alpha_composite(bg.convert("RGBA"), dim)
    bg = Image.alpha_composite(bg, ovl)

    d = ImageDraw.Draw(bg)

    # 상단 좌: 회사명 (UA 레드)
    f_company = ImageFont.truetype(FONT_REG, 24)
    d.text((50, 40), COMPANY, fill=(234, 70, 71, 255), font=f_company)

    # 상단 우: dartlab
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    # 중앙 제목
    f_title = ImageFont.truetype(FONT_BOLD, 58)
    y = 190
    for line in TITLE_LINES:
        d.text((52, y + 2), line, fill=(0, 0, 0, 160), font=f_title)
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 80

    # 부제
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), SUBTITLE, fill=(148, 163, 184, 255), font=f_sub)

    # 마스코트
    if MASCOT.exists():
        mascot = Image.open(MASCOT).convert("RGBA")
        ms = 120
        mascot = mascot.resize((ms, ms), Image.LANCZOS)
        bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    # 하단 빨간 바
    d2 = ImageDraw.Draw(bg)
    d2.rectangle([(0, H - 4), (W, H)], fill=(234, 70, 71, 255))

    ASSETS.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)

    thumb_asset = ASSETS / "35-thumbnail.webp"
    thumb_landing = THUMBS / "UAA-under-armour.webp"

    rgb = bg.convert("RGB")
    rgb.save(thumb_asset, "WEBP", quality=90)
    rgb.save(thumb_landing, "WEBP", quality=90)

    print(f"  OK {thumb_asset} -> {thumb_asset.stat().st_size // 1024}KB")
    print(f"  OK {thumb_landing} -> {thumb_landing.stat().st_size // 1024}KB")


if __name__ == "__main__":
    make_thumb()
    print("DONE")
