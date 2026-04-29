"""Repair company-report thumbnails #79-#85.

The affected thumbnails were composed with corrupted Korean text or temporary
SVG og images. This script keeps the company-report thumbnail spec: 1200x630
WEBP, full-bleed dark visual background, left gradient, Malgun Gothic text, and
the chart avatar.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BLOG = ROOT / "blog/05-company-reports"
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_REG = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
W, H = 1200, 630


POSTS = [
    {
        "folder": "79-011170-lotte-chemical",
        "bg": "79-thumbnail-bg.webp",
        "out": "011170-lotte-chemical.webp",
        "company": "롯데케미칼 (011170)",
        "title": ["매출 18조인데", "왜 3년째 적자인가"],
        "subtitle": "영업손실 9,375억 | 기초화학 손실 8,577억",
        "theme": "chemical",
    },
    {
        "folder": "80-096770-sk-on",
        "out": "096770-sk-on.webp",
        "company": "SK온 (096770)",
        "title": ["11조 합작공장", "5.6조 순손실의 출발점"],
        "subtitle": "BlueOval SK 해체 | 자본집약의 청구서",
        "theme": "battery",
    },
    {
        "folder": "81-082740-hanwha-engine",
        "bg": "81-thumbnail-bg.webp",
        "out": "082740-hanwha-engine.webp",
        "company": "한화엔진 (082740)",
        "title": ["배 엔진은 왜", "AI 앞에 섰나"],
        "subtitle": "수주잔고 4.1조 | DF엔진 88% | 684MW 전력",
        "theme": "engine",
    },
    {
        "folder": "82-MSTR-strategy",
        "out": "MSTR-strategy.webp",
        "company": "Strategy (MSTR)",
        "title": ["비트코인이", "손익계산서를 먹었다"],
        "subtitle": "공정가치 회계 | 현금흐름보다 가격 변동",
        "theme": "bitcoin",
    },
    {
        "folder": "83-DELL-dell-technologies",
        "bg": "83-thumbnail-bg.webp",
        "out": "DELL-dell-technologies.webp",
        "company": "Dell Technologies (DELL)",
        "title": ["AI 서버 주문은", "왜 마진을 못 지켰나"],
        "subtitle": "주문 $64B | gross margin 20.0% | 운전자본",
        "theme": "server",
    },
    {
        "folder": "84-003670-posco-future-m",
        "out": "003670-posco-future-m.webp",
        "company": "포스코퓨처엠 (003670)",
        "title": ["영업이익 328억", "CAPEX 1.5조"],
        "subtitle": "양극재 베팅 | FCF -1.53조 | EV 캐즘",
        "theme": "materials",
    },
    {
        "folder": "85-402340-sk-square",
        "out": "402340-sk-square.webp",
        "company": "SK스퀘어 (402340)",
        "title": ["매출 1.4조인데", "영업이익 8.8조"],
        "subtitle": "SK하이닉스 지분법이익 8.93조 | NAV 할인",
        "theme": "holding",
    },
]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def cover_resize(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    bw, bh = img.size
    ratio = max(W / bw, H / bh)
    nw, nh = int(bw * ratio), int(bh * ratio)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    return img.crop((left, top, left + W, top + H))


def procedural_background(theme: str) -> Image.Image:
    img = Image.new("RGB", (W, H), "#07111f")
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(W):
        r = 7 + x // 140
        g = 17 + x // 95
        b = 31 + x // 70
        d.line((x, 0, x, H), fill=(r, g, b, 255))

    if theme == "battery":
        for x in range(690, 1130, 92):
            d.rounded_rectangle(
                (x, 285, x + 88, 438), radius=12, fill=(15, 23, 42, 225), outline=(96, 165, 250, 140), width=2
            )
            d.rectangle((x + 16, 313, x + 72, 336), fill=(34, 197, 94, 180))
            d.rectangle((x + 16, 358, x + 72, 382), fill=(59, 130, 246, 160))
        for i, x in enumerate(range(650, 1160, 85)):
            y = 160 + (i % 2) * 45
            color = (59, 130, 246, 190) if i % 2 else (251, 191, 36, 185)
            d.ellipse((x, y, x + 32, y + 32), fill=color)
        d.line((640, 510, 1160, 470), fill=(148, 163, 184, 80), width=4)
        d.line((640, 552, 1160, 512), fill=(148, 163, 184, 55), width=3)

    elif theme == "bitcoin":
        d.ellipse((760, 115, 1035, 390), fill=(234, 179, 8, 180), outline=(251, 191, 36, 210), width=8)
        d.arc((815, 165, 980, 335), start=70, end=290, fill=(254, 240, 138, 170), width=8)
        for x, y, r in [(700, 140, 35), (1060, 205, 28), (720, 430, 42), (1010, 475, 34), (1125, 385, 40)]:
            d.ellipse((x - r, y - r, x + r, y + r), outline=(234, 179, 8, 150), width=4)
        for x in range(650, 1120, 95):
            d.line((x, 120, x + 60, 540), fill=(148, 163, 184, 28), width=2)

    elif theme == "materials":
        for i, x in enumerate(range(680, 1140, 78)):
            height = 210 + (i % 3) * 38
            d.rounded_rectangle(
                (x, 245 - height // 5, x + 44, 520),
                radius=12,
                fill=(22, 37, 55, 220),
                outline=(71, 85, 105, 160),
                width=2,
            )
            d.ellipse(
                (x - 6, 210 - height // 5, x + 50, 260 - height // 5),
                fill=(15, 118, 110, 120),
                outline=(45, 212, 191, 150),
                width=2,
            )
        for i, x in enumerate(range(710, 1120, 90)):
            color = (34, 197, 94, 190) if i % 2 == 0 else (251, 191, 36, 190)
            d.ellipse((x, 130, x + 22, 152), fill=color)
        d.line((650, 455, 1140, 375), fill=(148, 163, 184, 95), width=5)
        d.line((650, 500, 1140, 420), fill=(148, 163, 184, 70), width=5)

    elif theme == "holding":
        nodes = [(705, 185), (895, 145), (1035, 270), (805, 390), (1010, 465)]
        for a, b in zip(nodes, nodes[1:]):
            d.line((a[0], a[1], b[0], b[1]), fill=(56, 189, 248, 120), width=4)
        for i, (x, y) in enumerate(nodes):
            fill = (30, 41, 59, 230)
            stroke = (34, 197, 94, 170) if i == 1 else (56, 189, 248, 150)
            d.rounded_rectangle((x - 72, y - 46, x + 72, y + 46), radius=10, fill=fill, outline=stroke, width=3)
            d.rectangle((x - 42, y - 8, x + 42, y + 10), fill=stroke)
        d.rounded_rectangle((620, 105, 1135, 535), radius=24, outline=(51, 65, 85, 170), width=2)

    return img


def load_background(post: dict[str, object]) -> Image.Image:
    bg_name = post.get("bg")
    if bg_name:
        src = BLOG / str(post["folder"]) / "assets" / str(bg_name)
        if src.exists():
            return cover_resize(Image.open(src))
    return procedural_background(str(post["theme"]))


def apply_overlay(bg: Image.Image) -> Image.Image:
    base = bg.convert("RGBA")
    dim = Image.new("RGBA", (W, H), (10, 14, 26, 105))
    base = Image.alpha_composite(base, dim)

    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for x in range(W):
        alpha = max(0, int(245 * (1 - x / 880)))
        gd.line((x, 0, x, H), fill=(10, 14, 26, alpha))
    gd.rectangle((0, 0, 680, 140), fill=(10, 14, 26, 145))
    return Image.alpha_composite(base, grad)


def fit_font(draw: ImageDraw.ImageDraw, text: str, base_size: int, max_width: int) -> ImageFont.FreeTypeFont:
    size = base_size
    while size > 40:
        candidate = font(FONT_BOLD, size)
        if draw.textlength(text, font=candidate) <= max_width:
            return candidate
        size -= 2
    return font(FONT_BOLD, size)


def compose(post: dict[str, object]) -> None:
    bg = apply_overlay(load_background(post))
    d = ImageDraw.Draw(bg)

    f_company = font(FONT_REG, 24)
    f_logo = font(FONT_BOLD, 22)
    f_sub = font(FONT_REG, 22)

    d.text((50, 42), str(post["company"]), fill=(148, 163, 184, 255), font=f_company)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241, 245, 249, 255), font=f_logo)

    y = 195
    for line in post["title"]:
        f_title = fit_font(d, str(line), 58, 650)
        d.text((50, y), str(line), fill=(255, 255, 255, 255), font=f_title)
        y += 80

    d.text((50, y + 28), str(post["subtitle"]), fill=(203, 213, 225, 255), font=f_sub)

    mascot = Image.open(MASCOT).convert("RGBA").resize((160, 160), Image.LANCZOS)
    bg.paste(mascot, (W - 190, H - 190), mascot)

    out = THUMBS / str(post["out"])
    bg.convert("RGB").save(out, "WEBP", quality=90)
    print(f"wrote {out.relative_to(ROOT)}")


def main() -> None:
    for post in POSTS:
        compose(post)


if __name__ == "__main__":
    main()
