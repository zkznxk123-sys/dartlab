"""dashboards/meta.json — engines 정적 카드 + 블로그 인덱스 + thesis 템플릿.

대시보드 v16 Tier 3 — 회사 독립적 메타데이터 단일 파일.

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildMetaJson.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOG_DIR = ROOT / "blog" / "05-company-reports"
OUT = ROOT / "landing" / "static" / "dashboards" / "meta.json"


ENGINES = [
    {
        "key": "analysis",
        "name": "Analysis",
        "nameKr": "재무분석",
        "tagline": "재무제표·밸류에이션·성장 분석",
        "color": "#fb923c",
        "outputs": ["IS/BS/CF 정규화", "Bridge Matching", "DCF·DDM·RIM", "5Y CAGR"],
        "powers": ["Hero · Value", "Past Performance", "Financials"],
    },
    {
        "key": "credit",
        "name": "Credit",
        "nameKr": "신용분석",
        "tagline": "독립 신용등급 dCR · 7축 정량 스코어",
        "color": "#ea4647",
        "outputs": [
            "dCR-AAA ~ D (20단계)",
            "7축: 채무상환·자본구조·유동성·현금흐름·사업안정성·재무신뢰성·공시리스크",
            "Notch Adjustment + CHS 시장보정",
            "PD 추정 + 투자적격 분류",
        ],
        "powers": ["Credit Radar 7축", "Health · Altman Z", "경고 플래그"],
    },
    {
        "key": "macro",
        "name": "Macro",
        "nameKr": "거시경제",
        "tagline": "경기 사이클 4국면 + 섹터 순풍/역풍",
        "color": "#fbbf24",
        "outputs": [
            "확장·둔화·수축·회복 4국면 분류",
            "KR/US 시장 동시 분석 (7 매크로 지표)",
            "섹터별 순풍·역풍 가중치 + 전략 가이드",
            "전환 시퀀스 감지 (signals)",
        ],
        "powers": ["Macro Card", "Future 포캐스트", "Health Check · 매크로"],
    },
    {
        "key": "quant",
        "name": "Quant",
        "nameKr": "계량분석",
        "tagline": "팩터 스코어·백테스트",
        "color": "#34d399",
        "outputs": ["5축 Snowflake", "업종 백분위", "모멘텀·퀄리티"],
        "powers": ["Hero Radar", "Health Checks"],
    },
    {
        "key": "industry",
        "name": "Industry",
        "nameKr": "산업·공급망",
        "tagline": "공급망 그래프 + 업종 내 위치",
        "color": "#a78bfa",
        "outputs": [
            "HHI 집중도 + Top N 공급사/고객",
            "업종 내 백분위 (수익성·성장·품질·부채)",
            "crossViews · 회사 narrative",
            "산업지도 네트워크 + crossViews",
        ],
        "powers": ["Supply Chain", "Peer Card", "산업지도 링크"],
    },
]


THESIS_TEMPLATES = {
    "strengths": {
        "A_profit": "수익성 프리미엄 — 영업이익률 업종 상위",
        "A_growth": "성장 동력 — 매출 CAGR 업종 중앙값 상회",
        "A_stable": "재무 안정성 우수 — 부채비율 낮고 유동성 양호",
        "A_quality": "이익 품질 우수 — 영업현금흐름 / 순이익 > 1",
        "A_gov": "지배구조 양호 — 지분 구조 + 감사 리스크 낮음",
    },
    "weaknesses": {
        "F_profit": "수익성 약세 — 영업손실 또는 업종 하위",
        "F_growth": "성장 정체 — 매출 성장률 둔화 또는 역성장",
        "F_stable": "재무 리스크 — 부채비율 과도하거나 유동성 부족",
        "F_quality": "이익 품질 주의 — 발생액 대비 현금흐름 괴리",
        "F_gov": "지배구조 리스크 — 감사 또는 지분 이슈",
    },
    "default": {
        "call_buy": "주요 지표가 업종 평균을 상회. 가치 대비 매력적 구간 가능성.",
        "call_hold": "강점과 약점이 혼재. 이벤트 대기 구간.",
        "call_sell": "주요 지표가 업종 대비 하회. 리스크 우세.",
    },
}


def _loadBlogIndex() -> dict[str, dict]:
    """blog/05-company-reports/{NN-CODE-slug}/index.md → stockCode: {slug, title, date}."""
    index: dict[str, dict] = {}
    if not BLOG_DIR.exists():
        return index
    for dir_ in BLOG_DIR.iterdir():
        if not dir_.is_dir():
            continue
        parts = dir_.name.split("-", 2)
        if len(parts) < 3:
            continue
        code = parts[1]
        md = dir_ / "index.md"
        if not md.exists():
            continue
        title = ""
        date = ""
        excerpt = ""
        try:
            txt = md.read_text(encoding="utf-8")
            if txt.startswith("---"):
                fm_end = txt.find("---", 3)
                fm = txt[3:fm_end] if fm_end > 0 else ""
                body = txt[fm_end + 3 :] if fm_end > 0 else txt
                for line in fm.splitlines():
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("date:"):
                        date = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("excerpt:") or line.startswith("summary:"):
                        excerpt = line.split(":", 1)[1].strip().strip('"').strip("'")
                if not excerpt:
                    first_para = next(
                        (ln.strip() for ln in body.splitlines() if ln.strip() and not ln.startswith("#")),
                        "",
                    )
                    excerpt = first_para[:160]
        except (OSError, UnicodeDecodeError):
            continue
        index[code] = {
            "slug": dir_.name,
            "title": title or f"{code} 심층분석",
            "date": date or "2026-01-01",
            "excerpt": excerpt or "",
            "readTime": "10분",
        }
    return index


def main() -> int:
    blog = _loadBlogIndex()
    print(f"blog entries: {len(blog)}", flush=True)

    meta = {
        "version": "v16",
        "engines": ENGINES,
        "blog": blog,
        "thesisTemplates": THESIS_TEMPLATES,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")

    size_kb = OUT.stat().st_size / 1024
    print(f"완료: {size_kb:.1f}KB → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
