"""Oklo #31 썸네일 생성 — Pillow 합성

FLUX 배경 이미지 위에 텍스트 오버레이.
실행: uv run python -X utf8 scripts/blog/gen_oklo_thumbnail.py
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
ASSETS = ROOT / "blog/05-company-reports/31-OKLO-oklo/assets"
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

# FLUX 배경 (gen_oklo_flux.py로 사전 생성 필요)
BG_FILE = ASSETS / "31-oklo-aurora.webp"

COMPANY = "Oklo Inc. (OKLO)"
TITLE_LINES = ["매출 0원, 직원 120명", "시총 18조원"]
SUBTITLE = "계약 14GW | 가동 0기 | Sam Altman"


def make_thumb():
    W, H = 1200, 630

    # 배경
    if BG_FILE.exists():
        bg = Image.open(BG_FILE).convert("RGB")
    else:
        # FLUX 없으면 단색 배경
        bg = Image.new("RGB", (W, H), (10, 14, 26))
        print(f"  WARN: {BG_FILE} 없음 — 단색 배경 사용")

    # 비율 유지하며 crop to 1200x630
    bw, bh = bg.size
    ratio = max(W / bw, H / bh)
    nw, nh = int(bw * ratio), int(bh * ratio)
    bg = bg.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    bg = bg.crop((left, top, left + W, top + H))

    # 좌측 어두운 그라데이션 오버레이
    ovl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ovl)
    for x in range(W):
        if x < 720:
            alpha = int(200 * (1 - x / 900))
        else:
            alpha = max(0, int(200 * (1 - x / 900)))
        od.rectangle([(x, 0), (x + 1, H)], fill=(10, 14, 26, alpha))

    # 전체 어두운 필터
    dim = Image.new("RGBA", (W, H), (10, 14, 26, 70))
    bg = Image.alpha_composite(bg.convert("RGBA"), dim)
    bg = Image.alpha_composite(bg, ovl)

    d = ImageDraw.Draw(bg)

    # 회사명 (상단)
    f_company = ImageFont.truetype(FONT_REG, 24)
    d.text((50, 40), COMPANY, fill=(234, 70, 71, 255), font=f_company)

    # dartlab 로고 (우상단)
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    # 제목 (중앙 좌측)
    f_title = ImageFont.truetype(FONT_BOLD, 58)
    y = 190
    for line in TITLE_LINES:
        # 그림자
        d.text((52, y + 2), line, fill=(0, 0, 0, 128), font=f_title)
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 80

    # 부제 (하단)
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), SUBTITLE, fill=(148, 163, 184, 255), font=f_sub)

    # 마스코트 (우하단)
    if MASCOT.exists():
        mascot = Image.open(MASCOT).convert("RGBA")
        ms = 160
        mascot = mascot.resize((ms, ms), Image.LANCZOS)
        bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    # 하단 빨간 바
    d2 = ImageDraw.Draw(bg)
    d2.rectangle([(0, H - 4), (W, H)], fill=(234, 70, 71, 255))

    # 저장: assets + landing 양쪽
    ASSETS.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)

    thumb_asset = ASSETS / "thumbnail.webp"
    thumb_landing = THUMBS / "OKLO-oklo.webp"

    rgb = bg.convert("RGB")
    rgb.save(thumb_asset, "WEBP", quality=90)
    rgb.save(thumb_landing, "WEBP", quality=90)

    print(f"  OK {thumb_asset} -> {thumb_asset.stat().st_size // 1024}KB")
    print(f"  OK {thumb_landing} -> {thumb_landing.stat().st_size // 1024}KB")


if __name__ == "__main__":
    make_thumb()
    print("DONE")
