"""#13~24 블로그 썸네일 재생성 — 정식 스펙

스펙 (기존 01~12 기준):
- 1200x630 WEBP
- 좌측 텍스트: 회사명(종목코드) + 큰 제목 2줄 + 부제
- 우측 FLUX 이미지 배경 + 좌측 어두운 그라데이션
- 우상단 dartlab 로고, 우하단 마스코트
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(r"c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab")
THUMBS = ROOT / "landing/static/thumbnails"
MASCOT = ROOT / "landing/static/avatar-chart.png"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REG = "C:/Windows/Fonts/malgun.ttf"

# 기존 FLUX 원본(현재 썸네일)을 배경으로 사용
POSTS = [
    ("009450-kyungdong-navien", "경동나비엔 (009450)",
     ["민둥산의 연탄회사가", "미국 온수기를 먹다"],
     "매총이익률 42% | 북미 탱크리스 1위"),
    ("439260-daehan-shipbuilding", "대한조선 (439260)",
     ["3번 죽은 조선소가", "OPM 24%를 찍었다"],
     "수에즈막스 올인 | 2,000억 → 3.3조"),
    ("086280-hyundai-glovis", "현대글로비스 (086280)",
     ["물류회사 장부에", "로봇과 경쟁사 차"],
     "PCC선 98척 | 보스턴다이내믹스 3.3조"),
    ("004370-nongshim", "농심 (004370)",
     ["라면 1위인데 왜", "마진은 삼양의 1/4?"],
     "1위의 저주 | OPM 5% vs 22%"),
    ("018880-hanon-systems", "한온시스템 (018880)",
     ["순이익의 7배를", "배당으로 쥐어짜면"],
     "사모펀드 10년 | 차입 11배"),
    ("011070-lg-innotek", "LG이노텍 (011070)",
     ["애플 독점인데", "왜 마진이 3%인가"],
     "매출 80% 애플 | OPM 3%"),
    ("011780-kumho-petrochemical", "금호석유화학 (011780)",
     ["화학 빅4 중", "유일한 흑자"],
     "NCC 없는 방패 | NB라텍스 세계 1위"),
    ("294870-hdc-hyundai-dev", "HDC현대산업개발 (294870)",
     ["2,500억 날리고", "6명 죽었는데 살았다"],
     "아시아나 패소 | 자체개발 해자"),
    ("012330-hyundai-mobis", "현대모비스 (012330)",
     ["연결 5.5% vs 별도 21%", "15%p 갭의 정체"],
     "순환출자 정점 | AS 부품 독점"),
    ("017670-skt", "SK텔레콤 (017670)",
     ["해킹 한 번이", "8년 공식을 깼다"],
     "2,500만명 유출 | OPM 10→6.3%"),
    ("006360-gs-engineering", "GS건설 (006360)",
     ["5,524억을 한 분기에", "몰아낸 빅배스"],
     "검단 붕괴 | 1년 만에 흑전"),
    ("011760-hyundai-corp", "현대코퍼레이션 (011760)",
     ["종합상사가 아니라", "자원 + 지주다"],
     "OPM 7.3% | 정몽혁 개인 지배"),
]

def make_thumb(slug, company, title_lines, subtitle):
    W, H = 1200, 630
    src = THUMBS / f"{slug}.webp"
    # 배경
    bg = Image.open(src).convert("RGB")
    # 비율 유지하며 crop to 1200x630
    bw, bh = bg.size
    ratio = max(W/bw, H/bh)
    nw, nh = int(bw*ratio), int(bh*ratio)
    bg = bg.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    bg = bg.crop((left, top, left+W, top+H))

    # 좌측 어두운 그라데이션 오버레이
    ovl = Image.new("RGBA", (W, H), (0,0,0,0))
    od = ImageDraw.Draw(ovl)
    for x in range(W):
        if x < 720:
            alpha = int(200 * (1 - x/900))
        else:
            alpha = max(0, int(200 * (1 - x/900)))
        od.rectangle([(x,0),(x+1,H)], fill=(10,14,26,alpha))
    # 전체 어두운 필터
    dim = Image.new("RGBA", (W, H), (10,14,26,70))
    bg = Image.alpha_composite(bg.convert("RGBA"), dim)
    bg = Image.alpha_composite(bg, ovl)

    d = ImageDraw.Draw(bg)
    # 회사명 (상단)
    f_company = ImageFont.truetype(FONT_REG, 24)
    d.text((50, 40), company, fill=(148,163,184,255), font=f_company)

    # dartlab 로고 (우상단)
    f_logo = ImageFont.truetype(FONT_BOLD, 22)
    logo_w = d.textlength("dartlab", font=f_logo)
    d.text((W - 50 - logo_w, 44), "dartlab", fill=(241,245,249,255), font=f_logo)

    # 제목 (중앙 좌측)
    f_title = ImageFont.truetype(FONT_BOLD, 58)
    y = 190
    for line in title_lines:
        d.text((50, y), line, fill=(255,255,255,255), font=f_title)
        y += 80

    # 부제 (하단)
    f_sub = ImageFont.truetype(FONT_REG, 22)
    d.text((50, y + 30), subtitle, fill=(148,163,184,255), font=f_sub)

    # 마스코트 (우하단)
    mascot = Image.open(MASCOT).convert("RGBA")
    ms = 160
    mascot = mascot.resize((ms, ms), Image.LANCZOS)
    bg.paste(mascot, (W - ms - 30, H - ms - 30), mascot)

    out = THUMBS / f"{slug}.webp"
    bg.convert("RGB").save(out, "WEBP", quality=90)
    print(f"OK {slug} -> {out.stat().st_size//1024}KB")

for slug, company, title, sub in POSTS:
    make_thumb(slug, company, title, sub)

print("DONE")
