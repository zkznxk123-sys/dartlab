"""라면 빅3 유튜브 커뮤니티 게시물 — GIF + 정적 슬라이드 4장"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1080
OUT = Path(__file__).parent / "slides"
OUT.mkdir(exist_ok=True)

FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

BG = rgb("#0E1116")
TEXT = rgb("#E8EAED")
ACCENT = rgb("#6366F1")
GREEN = rgb("#22c55e")
RED = rgb("#ef4444")
YELLOW = rgb("#fbbf24")
MUTED = rgb("#64748b")
CARD = rgb("#1e293b")
GRID = rgb("#1e293b")
DIM = rgb("#334155")

# ── GIF: 3사 OPM 9년 레이스 ──────────────────────────
years = list(range(2017, 2026))
samyang = [9.4, 10.4, 13.9, 10.5, 11.2, 8.0, 11.1, 18.3, 21.8]
nongshim = [5.0, 5.0, 5.0, 5.0, 4.7, 4.5, 6.6, 4.7, 5.2]
ottogi = [5.9, 6.1, 3.5, 4.6, 6.1, 5.8, 7.4, 6.3, 4.8]


def draw_chart_frame(n):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fb = ImageFont.truetype(FONT_BOLD, 42)
    fr = ImageFont.truetype(FONT_REG, 28)
    fs = ImageFont.truetype(FONT_BOLD, 24)
    fl = ImageFont.truetype(FONT_REG, 22)

    # 제목
    d.text((60, 50), "라면 빅3 — 영업이익률 9년", fill=TEXT, font=fb)
    d.text((60, 105), "같은 라면인데 왜 마진이 4배 차이 나는가", fill=MUTED, font=fr)

    # 범례
    for i, (label, color) in enumerate(
        [("삼양식품", GREEN), ("농심", YELLOW), ("오뚜기", RED)]
    ):
        x0 = 60 + i * 180
        d.rectangle([x0, 160, x0 + 24, 180], fill=color)
        d.text((x0 + 34, 158), label, fill=TEXT, font=fs)

    # 차트 영역
    cx, cy, cw, ch = 100, 220, 920, 580
    max_val = 25
    bar_w = cw // 9

    # Y축 그리드
    for yv in range(0, 30, 5):
        y = cy + ch - int(yv / max_val * ch)
        d.line([(cx, y), (cx + cw, y)], fill=GRID, width=1)
        d.text((cx - 8, y - 12), f"{yv}%", fill=MUTED, font=fl, anchor="ra")

    # X축
    for i in range(n):
        x = cx + i * bar_w + bar_w // 2
        d.text((x, cy + ch + 10), str(years[i]), fill=MUTED, font=fl, anchor="ma")

    # 라인
    def plot(data, color):
        pts = []
        for i in range(n):
            x = cx + i * bar_w + bar_w // 2
            y = cy + ch - int(data[i] / max_val * ch)
            pts.append((x, y))
        if len(pts) >= 2:
            d.line(pts, fill=color, width=4)
        for px, py in pts:
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=color)
        if pts:
            lx, ly = pts[-1]
            d.text((lx + 14, ly - 10), f"{data[n-1]}%", fill=color, font=fs)

    plot(samyang, GREEN)
    plot(nongshim, YELLOW)
    plot(ottogi, RED)

    # 하단
    d.text((60, H - 60), "dartlab 실측 2026-04-18", fill=MUTED, font=fl)
    d.text((W - 60, H - 60), "dartlab", fill=MUTED, font=fs, anchor="ra")
    return img


frames = [draw_chart_frame(n) for n in range(1, 10)]
frames += [draw_chart_frame(9)] * 6  # 마지막 3초 유지

frames[0].save(
    OUT / "01-hook-opm-race.gif",
    save_all=True,
    append_images=frames[1:],
    duration=500,
    loop=0,
    optimize=True,
)
print(f"GIF: {len(frames)} frames")

# ── 슬라이드 02: 핵심 비교 ────────────────────────────
img2 = Image.new("RGB", (W, H), BG)
d2 = ImageDraw.Draw(img2)
fb2 = ImageFont.truetype(FONT_BOLD, 44)
fr2 = ImageFont.truetype(FONT_REG, 30)
fs2 = ImageFont.truetype(FONT_BOLD, 28)
fnum = ImageFont.truetype(FONT_BOLD, 96)
fl2 = ImageFont.truetype(FONT_REG, 24)

d2.text((W // 2, 55), "같은 라면, 다른 마진", fill=TEXT, font=fb2, anchor="ma")
d2.text((W // 2, 110), "원가율이 마진을 결정한다", fill=MUTED, font=fr2, anchor="ma")

cols = [
    ("삼양식품", "22%", "원가 55%", "해외 77%", GREEN, 55),
    ("농심", "5.2%", "원가 76%", "해외 66%", YELLOW, 76),
    ("오뚜기", "4.8%", "원가 84%", "해외 15%", RED, 84),
]
for i, (name, opm, cost, overseas, color, pct) in enumerate(cols):
    cx2 = 50 + i * 340
    d2.rounded_rectangle([cx2, 170, cx2 + 310, 700], radius=20, fill=CARD)
    d2.text((cx2 + 155, 210), name, fill=TEXT, font=fs2, anchor="ma")
    d2.text((cx2 + 155, 350), opm, fill=color, font=fnum, anchor="ma")
    d2.text((cx2 + 155, 430), "OPM", fill=MUTED, font=fl2, anchor="ma")
    d2.text((cx2 + 155, 500), cost, fill=TEXT, font=fs2, anchor="ma")
    d2.text((cx2 + 155, 545), overseas, fill=MUTED, font=fl2, anchor="ma")
    # 원가율 바
    bw = int(pct / 100 * 250)
    d2.rounded_rectangle([cx2 + 30, 610, cx2 + 280, 640], radius=8, fill=DIM)
    d2.rounded_rectangle([cx2 + 30, 610, cx2 + 30 + bw, 640], radius=8, fill=color)
    d2.text((cx2 + 155, 660), f"{pct}%", fill=MUTED, font=fl2, anchor="ma")

d2.text((W // 2, 750), "100원 팔면 삼양 22원, 오뚜기 5원 남는다", fill=TEXT, font=fr2, anchor="ma")
d2.text(
    (W // 2, 800),
    "차이는 해외 프리미엄 — 같은 원가, 다른 판매 가격",
    fill=MUTED,
    font=fl2,
    anchor="ma",
)

d2.rectangle([0, 900, W, 910], fill=ACCENT)
d2.text((60, 940), "dartlab 실측 2026-04-18", fill=MUTED, font=fl2)
d2.text((W - 60, 940), "dartlab", fill=MUTED, font=fs2, anchor="ra")

img2.save(OUT / "02-cost-compare.webp", "WEBP", quality=95)
print("Slide 02")

# ── 슬라이드 03: 반전 ─────────────────────────────────
img3 = Image.new("RGB", (W, H), BG)
d3 = ImageDraw.Draw(img3)
fb3 = ImageFont.truetype(FONT_BOLD, 44)
fr3 = ImageFont.truetype(FONT_REG, 30)
fs3 = ImageFont.truetype(FONT_BOLD, 36)
fl3 = ImageFont.truetype(FONT_REG, 24)

d3.text((W // 2, 55), "농심 해외 66%인데", fill=YELLOW, font=fb3, anchor="ma")
d3.text((W // 2, 110), "왜 OPM은 삼양의 1/4인가", fill=TEXT, font=fb3, anchor="ma")

# 핵심 박스
d3.rounded_rectangle([60, 190, W - 60, 490], radius=20, fill=CARD)
d3.text((W // 2, 240), "중국 시장이 마진을 깎는다", fill=TEXT, font=fs3, anchor="ma")
d3.text((W // 2, 310), "중국 = 해외 매출의 17%", fill=YELLOW, font=fr3, anchor="ma")
d3.text(
    (W // 2, 360), "로컬 대비 2배 가격이 상한선", fill=MUTED, font=fr3, anchor="ma"
)
d3.text(
    (W // 2, 410), "물류 + 마케팅 + 관세 = 손익분기점", fill=MUTED, font=fr3, anchor="ma"
)

# 교훈 박스
d3.rounded_rectangle([60, 530, W - 60, 720], radius=20, fill=CARD, outline=ACCENT, width=2)
d3.text(
    (W // 2, 585),
    '"해외에 나갔다"와',
    fill=TEXT,
    font=fs3,
    anchor="ma",
)
d3.text(
    (W // 2, 640),
    '"해외에서 돈을 벌었다"는 다르다',
    fill=ACCENT,
    font=fs3,
    anchor="ma",
)

d3.text(
    (W // 2, 790), "내수 식품의 OPM 천장은 5~7%", fill=TEXT, font=fr3, anchor="ma"
)
d3.text(
    (W // 2, 840),
    "탈출구는 프리미엄을 받을 수 있는 해외 시장",
    fill=MUTED,
    font=fl3,
    anchor="ma",
)

d3.rectangle([0, 900, W, 910], fill=ACCENT)
d3.text((60, 940), "dartlab 실측", fill=MUTED, font=fl3)
d3.text((W - 60, 940), "dartlab", fill=MUTED, font=fs2, anchor="ra")

img3.save(OUT / "03-china-trap.webp", "WEBP", quality=95)
print("Slide 03")

# ── 슬라이드 04: CTA ──────────────────────────────────
img4 = Image.new("RGB", (W, H), BG)
d4 = ImageDraw.Draw(img4)

d4.text((W // 2, 80), "진라면은", fill=MUTED, font=fb3, anchor="ma")
d4.text(
    (W // 2, 150),
    "세계로 나갈 수 있는가",
    fill=TEXT,
    font=ImageFont.truetype(FONT_BOLD, 52),
    anchor="ma",
)

# 코드 블록
d4.rounded_rectangle([60, 260, W - 60, 560], radius=16, fill=CARD)
cf = ImageFont.truetype(FONT_REG, 26)
code = [
    ('import dartlab', TEXT),
    ('c = dartlab.Company("007310")', GREEN),
    ('c.select("IS", ["매출액","영업이익"])', TEXT),
    ('', TEXT),
    ('# 9년 재무제표로 구조를 분해한다', MUTED),
    ('# 블로그 전문 아래 링크', MUTED),
]
y = 285
for line, color in code:
    d4.text((90, y), line, fill=color, font=cf)
    y += 42

# CTA 버튼
d4.rounded_rectangle([120, 620, W - 120, 760], radius=24, fill=ACCENT)
d4.text(
    (W // 2, 660),
    "블로그 전문 읽기",
    fill=(255, 255, 255),
    font=ImageFont.truetype(FONT_BOLD, 38),
    anchor="ma",
)
d4.text(
    (W // 2, 720),
    "eddmpython.github.io/dartlab/blog/ottogi",
    fill=rgb("#c7d2fe"),
    font=fl2,
    anchor="ma",
)

d4.text((W // 2, 840), "삼양식품 · 농심 · 오뚜기", fill=TEXT, font=fr3, anchor="ma")
d4.text(
    (W // 2, 890),
    "라면 빅3 재무제표 비교 시리즈",
    fill=MUTED,
    font=fl3,
    anchor="ma",
)

d4.text((60, 1000), "dartlab", fill=MUTED, font=fs2)
d4.text(
    (W - 60, 1000),
    "#dartlab #기업분석 #라면",
    fill=DIM,
    font=fl3,
    anchor="ra",
)

img4.save(OUT / "04-cta.webp", "WEBP", quality=95)
print("Slide 04")

print("ALL DONE!")
