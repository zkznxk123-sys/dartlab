"""엔진 축 한글·영문 slug 매핑 — Phase R PR 브랜치 네이밍 공용.

브랜치 규칙: `skill/docstring-{engine}-{axis-slug}-{YYYYMMDD}`.
한글 축명은 ASCII slug 로 변환해야 브랜치 이름에 안전하게 들어간다.
"""

from __future__ import annotations

# 엔진·축 → ASCII slug
KOREAN_AXIS_SLUG: dict[str, str] = {
    # analysis 22 축
    "수익구조": "revenue-structure",
    "자금조달": "capital-funding",
    "자산구조": "asset-structure",
    "현금흐름": "cashflow",
    "수익성": "profitability",
    "성장성": "growth",
    "안정성": "stability",
    "효율성": "efficiency",
    "종합평가": "scorecard",
    "이익품질": "earnings-quality",
    "비용구조": "cost-structure",
    "자본배분": "capital-allocation",
    "투자효율": "investment-efficiency",
    "재무정합성": "cross-statement",
    "가치평가": "valuation",
    "지배구조": "governance",
    "공시변화": "disclosure-delta",
    "비교분석": "peer-benchmark",
    "매출전망": "revenue-forecast",
    "예측신호": "prediction-signals",
    "매크로민감도": "macro-exposure",
    "밸류에이션밴드": "valuation-band",
    # scan 7 축
    "ratio": "ratio",
    "account": "account",
    "governance": "governance",
    "workforce": "workforce",
    "capital": "capital",
    "debt": "debt",
    "digest": "digest",
    # credit
    "신용평가": "credit-rating",
    # macro
    "사이클": "cycle",
    "금리": "rates",
    "유동성": "liquidity",
    "자산신호": "asset-signal",
    # industry
    "밸류체인": "valuechain",
    "공급망": "supply-chain",
}


def to_slug(axis: str) -> str:
    """축 이름 → ASCII slug.

    미매핑 시 ASCII 문자·숫자·하이픈만 남기고, 비ASCII 는 hash prefix 로 대체.
    """
    if axis in KOREAN_AXIS_SLUG:
        return KOREAN_AXIS_SLUG[axis]
    ascii_only = "".join(c if c.isascii() and (c.isalnum() or c in "-_") else "-" for c in axis.lower())
    ascii_only = "-".join(part for part in ascii_only.split("-") if part)
    if ascii_only:
        return ascii_only
    # 완전 non-ASCII → 해시 기반 fallback
    import hashlib

    return "axis-" + hashlib.sha256(axis.encode("utf-8")).hexdigest()[:8]


__all__ = ["KOREAN_AXIS_SLUG", "to_slug"]
