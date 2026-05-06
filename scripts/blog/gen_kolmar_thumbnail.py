"""한국콜마 (#86) 썸네일 합성 — gen_thumbnails.py 패턴.

배경: blog/05-company-reports/86-161890-kolmar/assets/86-thumbnail-bg.webp
출력: landing/static/thumbnails/161890-kolmar.webp
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
SRC_BG = ROOT / "blog/05-company-reports/86-161890-kolmar/assets/86-thumbnail-bg.webp"
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

SLUG = "161890-kolmar"
COMPANY = "한국콜마 (161890)"
TITLE = ["사상최대 영업이익이", "8년 영업외에서 새다"]
SUB = "1.3조 인수 차입 이자 540억 | OPM 8.80% 사상최대"


def make_thumb():
    W, H = 1200, 630
    bg = Image.open(SRC_BG).convert("RGB")
    bw, bh = bg.size
    ratio = max(W / bw, H / bh)
    nw, nh = int(bw * ratio), int(bh * ratio)
    bg = bg.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    bg = bg.crop((left, top, left + W, top + H))

    # 좌측 어두운 그라데이션
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
    # 회사명 좌상단
    f_company = ImageFont.truetype(FONT_REG, 24)
    d.text((50, 40), COMPANY, fill=(148, 163, 184, 255), font=f_company)

    # dartlab 우상단
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    # 제목 중앙 좌측
    f_title = ImageFont.truetype(FONT_BOLD, 58)
    y = 190
    for line in TITLE:
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 80

    # 부제 하단
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), SUB, fill=(148, 163, 184, 255), font=f_sub)

    # 마스코트 우하단
    mascot = Image.open(MASCOT).convert("RGBA")
    ms = 160
    mascot = mascot.resize((ms, ms), Image.LANCZOS)
    bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    THUMBS.mkdir(parents=True, exist_ok=True)
    out = THUMBS / f"{SLUG}.webp"
    bg.convert("RGB").save(out, "WEBP", quality=90)
    print(f"OK {SLUG} -> {out.relative_to(ROOT)} ({out.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    make_thumb()
