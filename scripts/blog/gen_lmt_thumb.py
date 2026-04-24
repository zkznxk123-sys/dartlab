"""록히드마틴 #76 썸네일."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/76-LMT-lockheed-martin/assets"
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

BG_FILE = ASSETS / "76-thumbnail-bg.webp"
COMPANY = "록히드마틴 (LMT)"
TITLE_LINES = ["매출 100조 세계 1위", "방산이 OPM 10.3%인 이유"]
SUBTITLE = "한화에어로(#07) 24%의 절반 · Cost-Plus 50~60% 마진 캡 · F-35 천 대급"


def make_thumb() -> None:
    W, H = 1200, 630
    bg = Image.open(BG_FILE).convert("RGB") if BG_FILE.exists() else Image.new("RGB", (W, H), (10, 14, 26))
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
    d.text((50, 40), COMPANY, fill=(148, 163, 184, 255), font=f_company)
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)
    f_title = ImageFont.truetype(FONT_BOLD, 56)
    y = 195
    for line in TITLE_LINES:
        d.text((52, y + 2), line, fill=(0, 0, 0, 160), font=f_title)
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 78
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), SUBTITLE, fill=(148, 163, 184, 255), font=f_sub)
    if MASCOT.exists():
        mascot = Image.open(MASCOT).convert("RGBA").resize((160, 160), Image.LANCZOS)
        bg.paste(mascot, (W - 190, H - 190), mascot)
    d2 = ImageDraw.Draw(bg)
    d2.rectangle([(0, H - 4), (W, H)], fill=(251, 191, 36, 255))
    ASSETS.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    thumb_asset = ASSETS / "76-thumbnail.webp"
    thumb_landing = THUMBS / "LMT-lockheed-martin.webp"
    rgb = bg.convert("RGB")
    rgb.save(thumb_asset, "WEBP", quality=90)
    rgb.save(thumb_landing, "WEBP", quality=90)
    print(f"  OK {thumb_asset.stat().st_size // 1024}KB")
    print(f"  OK {thumb_landing.stat().st_size // 1024}KB")


if __name__ == "__main__":
    make_thumb()
    print("DONE")
