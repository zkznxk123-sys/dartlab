"""한미반도체 #63 썸네일 생성 — Pillow 합성.

FLUX 배경 `063-thumbnail-bg.webp` 위에 텍스트/아바타 오버레이.
저장 2곳:
  - blog/05-company-reports/63-042700-hanmi-semi/assets/063-thumbnail.webp
  - landing/static/thumbnails/042700-hanmi-semi.webp

실행: uv run python -X utf8 scripts/blog/gen_hanmi_semi_thumb.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/63-042700-hanmi-semi/assets"
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

BG_FILE = ASSETS / "063-thumbnail-bg.webp"

COMPANY = "한미반도체 (042700)"
TITLE_LINES = ["매출 반토막 난 회사가", "1년 만에 영업이익 7.4배"]
SUBTITLE = "HBM TC 본딩 장비 독점 — AI 붐이 상류로 역류한 경로"


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

    f_company = ImageFont.truetype(FONT_REG, 24)
    d.text((50, 40), COMPANY, fill=(251, 191, 36, 255), font=f_company)

    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    f_title = ImageFont.truetype(FONT_BOLD, 56)
    y = 190
    for line in TITLE_LINES:
        d.text((52, y + 2), line, fill=(0, 0, 0, 160), font=f_title)
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 78

    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), SUBTITLE, fill=(148, 163, 184, 255), font=f_sub)

    if MASCOT.exists():
        mascot = Image.open(MASCOT).convert("RGBA")
        ms = 120
        mascot = mascot.resize((ms, ms), Image.LANCZOS)
        bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    d2 = ImageDraw.Draw(bg)
    d2.rectangle([(0, H - 4), (W, H)], fill=(251, 191, 36, 255))

    ASSETS.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)

    thumb_asset = ASSETS / "063-thumbnail.webp"
    thumb_landing = THUMBS / "042700-hanmi-semi.webp"

    rgb = bg.convert("RGB")
    rgb.save(thumb_asset, "WEBP", quality=90)
    rgb.save(thumb_landing, "WEBP", quality=90)

    print(f"  OK {thumb_asset} -> {thumb_asset.stat().st_size // 1024}KB")
    print(f"  OK {thumb_landing} -> {thumb_landing.stat().st_size // 1024}KB")


if __name__ == "__main__":
    make_thumb()
    print("DONE")
