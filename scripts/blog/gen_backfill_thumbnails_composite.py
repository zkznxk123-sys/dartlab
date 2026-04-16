"""META/TSLA/HYBE/IONQ 썸네일 4장을 MNST 스타일로 합성.

원본 FLUX 배경: blog/.../assets/{NN}-thumbnail-bg.webp (gen_backfill_thumbnails_flux.py 로 먼저 생성)
출력: landing/static/thumbnails/{code}-{slug}.webp

스펙은 gen_thumbnails.py 와 동일 — 풀블리드 + 좌측 그라데이션 + 흰 제목 오버레이.
실행: uv run python -X utf8 scripts/blog/gen_backfill_thumbnails_composite.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

POSTS = [
    (
        "37-META-meta-platforms",
        "37-thumbnail-bg.webp",
        "META-meta-platforms",
        "Meta Platforms (META)",
        ["CAPEX 697억 달러를", "AI에 쏟아붓는데 OPM 41%"],
        "광고 플랫폼 GP 마진 82% | 2022년 추락에서 복귀",
    ),
    (
        "38-TSLA-tesla",
        "38-thumbnail-bg.webp",
        "TSLA-tesla",
        "Tesla (TSLA)",
        ["매출 10년 만의 역성장", "EVA 마이너스로 돌아섰다"],
        "OPM 16.8→4.6% | DCF 마이너스 vs 시총 $1T",
    ),
    (
        "39-352820-hybe",
        "39-thumbnail-bg.webp",
        "352820-hybe",
        "하이브 (352820)",
        ["매출 사상 최대 2.65조인데", "당기순손실 2,566억"],
        "BTS 없는 2년 | 북미 손상차손 2,000억",
    ),
    (
        "40-IONQ-ionq",
        "40-thumbnail-bg.webp",
        "IONQ-ionq",
        "IonQ (IONQ)",
        ["첫 $100M 양자 컴퓨팅 회사가", "영업손실 $634M"],
        "매출의 4.87배 손실 | 분기 순이익 ±10억 달러 요동",
    ),
]


def make_thumb(folder, bg_name, out_slug, company, title_lines, subtitle):
    W, H = 1200, 630
    src = ROOT / "blog/05-company-reports" / folder / "assets" / bg_name
    # 배경
    bg = Image.open(src).convert("RGB")
    # 비율 유지 crop → 1200x630
    bw, bh = bg.size
    ratio = max(W / bw, H / bh)
    nw, nh = int(bw * ratio), int(bh * ratio)
    bg = bg.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    bg = bg.crop((left, top, left + W, top + H))

    # 좌측 가로 그라데이션
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
    d.text((50, 40), company, fill=(148, 163, 184, 255), font=f_company)

    # dartlab 로고 (우상단)
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    # 제목 (중앙 좌측)
    f_title = ImageFont.truetype(FONT_BOLD, 58)
    y = 190
    for line in title_lines:
        d.text((50, y), line, fill=(255, 255, 255, 255), font=f_title)
        y += 80

    # 부제 (하단)
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), subtitle, fill=(148, 163, 184, 255), font=f_sub)

    # 마스코트 (우하단)
    mascot = Image.open(MASCOT).convert("RGBA")
    ms = 160
    mascot = mascot.resize((ms, ms), Image.LANCZOS)
    bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    out = THUMBS / f"{out_slug}.webp"
    bg.convert("RGB").save(out, "WEBP", quality=90)
    print(f"OK {out_slug} -> {out.stat().st_size // 1024}KB")


for folder, bg_name, out_slug, company, title, sub in POSTS:
    make_thumb(folder, bg_name, out_slug, company, title, sub)

print("DONE")
