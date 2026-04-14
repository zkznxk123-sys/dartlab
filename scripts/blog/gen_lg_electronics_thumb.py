"""LG전자 #34 썸네일 생성

실행: uv run python -X utf8 scripts/blog/gen_lg_electronics_thumb.py
사전 조건: 34-lg-factory.webp가 assets/ 또는 thumbnails/에 있어야 함
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
THUMBS = ROOT / "landing/static/thumbnails"
ASSETS = ROOT / "blog/05-company-reports/34-066570-lg-electronics/assets"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

SLUG = "066570-lg-electronics"
COMPANY = "LG전자 (066570)"
TITLE_LINES = ["매출 89조,", "영업이익률 2.8%"]
SUBTITLE = "스마트폰 철수 | TV 적자 | 구독가전 2.5조"


def make_thumb():
    W, H = 1200, 630

    # FLUX 이미지를 배경으로 사용
    src = ASSETS / "34-lg-factory.webp"
    if not src.exists():
        src = THUMBS / f"{SLUG}.webp"
    if not src.exists():
        print(f"배경 이미지 없음: {src}")
        return

    bg = Image.open(src).convert("RGB")
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
    dim = Image.new("RGBA", (W, H), (10, 14, 26, 70))
    bg = Image.alpha_composite(bg.convert("RGBA"), dim)
    bg = Image.alpha_composite(bg, ovl)

    d = ImageDraw.Draw(bg)

    # 회사명 (상단)
    f_company = ImageFont.truetype(FONT_REG, 24)
    d.text((50, 40), COMPANY, fill=(148, 163, 184, 255), font=f_company)

    # dartlab 로고 (우상단)
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    # 제목 (중앙 좌측)
    f_title = ImageFont.truetype(FONT_BOLD, 58)
    y = 190
    for line in TITLE_LINES:
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 80

    # 부제 (하단)
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), SUBTITLE, fill=(148, 163, 184, 255), font=f_sub)

    # 마스코트 (우하단)
    mascot = Image.open(MASCOT).convert("RGBA")
    ms = 160
    mascot = mascot.resize((ms, ms), Image.LANCZOS)
    bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    out = THUMBS / f"{SLUG}.webp"
    bg.convert("RGB").save(out, "WEBP", quality=90)
    print(f"OK {SLUG} -> {out.stat().st_size // 1024}KB")


if __name__ == "__main__":
    make_thumb()
    print("DONE")
