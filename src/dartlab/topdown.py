"""탑다운 facade — macro 사이클 → 추천 섹터 → 종목 후보 → narrative.

dartlab의 미싱 링크. macro/scan/quant가 이미 다 있는데 연결만 안 되어 있었다.
이 facade는 새 로직을 만들지 않는다. 기존 엔진들을 사이클 → 섹터 → 종목 순으로 호출하고 narrative만 조립한다.

Usage::

    import dartlab

    dartlab.topdown()                          # 가이드 (사용법)
    dartlab.topdown(market="KR")               # 시장 사이클 → 추천 섹터 → 종목
    dartlab.topdown(market="KR", topN=5)       # 섹터당 상위 5종목
    dartlab.topdown(market="KR", sectors=["반도체"])  # 특정 섹터만
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


# ══════════════════════════════════════
# 사이클 국면 → 추천 섹터 매핑
# ══════════════════════════════════════
#
# CYCLE_SECTOR_MAP(macroCycle.py)는 베타 등급(defensive/moderate/high) 기반.
# 여기서는 사용자에게 직관적인 KR/US 섹터명으로 매핑한다.
# 책의 사이클별 섹터 추천 + Damodaran/McKinsey 사이클 가이드 결합.

_CYCLE_SECTORS_KR: dict[str, list[str]] = {
    "recovery": ["반도체", "자동차", "은행", "건설", "화학", "철강"],
    "expansion": ["반도체", "IT서비스", "자동차", "유통", "건설"],
    "slowdown": ["통신", "전기가스", "음식료", "제약", "유틸리티"],
    "contraction": ["통신", "전기가스", "음식료", "제약"],
}

_CYCLE_SECTORS_US: dict[str, list[str]] = {
    "recovery": ["Technology", "Financials", "Industrials", "Consumer Discretionary", "Materials"],
    "expansion": ["Technology", "Communication Services", "Consumer Discretionary", "Industrials"],
    "slowdown": ["Health Care", "Consumer Staples", "Utilities", "Communication Services"],
    "contraction": ["Health Care", "Consumer Staples", "Utilities"],
}


def _getCycleSectors(phase: str, market: str) -> list[str]:
    table = _CYCLE_SECTORS_KR if market.upper() == "KR" else _CYCLE_SECTORS_US
    return table.get(phase, [])


# ══════════════════════════════════════
# 메인 facade
# ══════════════════════════════════════


def topdown(
    market: str = "KR",
    *,
    sectors: list[str] | None = None,
    topN: int = 5,
    asOf: str | None = None,
    **kwargs,
) -> dict:
    """탑다운 분석 — 시장 → 섹터 → 종목.

    Args:
        market: "KR" | "US"
        sectors: 특정 섹터만 지정. None이면 사이클 국면 자동 매핑.
        topN: 섹터당 추천 종목 수
        as_of: 백테스트용 기준일

    Returns:
        dict: {
            "cycle": {phase, label, confidence, ...},
            "transition": {...} | None,
            "recommendedSectors": [...],
            "screens": {sector: [{stockCode, name, signals, ...}, ...]},
            "narrative": "사이클 → 섹터 → 종목 인과 사슬 문장"
        }
    """
    # 1. 시장 사이클
    from dartlab.macro.cycles.cycle import analyzeCycle

    cycle = analyzeCycle(market=market, asOf=asOf)
    phase = cycle.get("phase")
    if not phase:
        return {"error": "사이클 판별 실패", "market": market}

    # 2. 국면 → 추천 섹터
    rec_sectors = sectors if sectors else _getCycleSectors(phase, market)

    # 3. 각 섹터에서 종목 후보 (scan 활용)
    screens: dict[str, list[dict]] = {}
    for sector in rec_sectors:
        try:
            screens[sector] = _screenSector(sector, market, topN, asOf)
        except (KeyError, ValueError, TypeError, ImportError) as e:
            log.debug("섹터 스크리닝 실패: %s — %s", sector, e)
            screens[sector] = []

    # 4. narrative 생성
    narrative = _buildNarrative(cycle, rec_sectors, screens, market)

    return {
        "market": market.upper(),
        "cycle": {
            "phase": phase,
            "phaseLabel": cycle.get("phaseLabel"),
            "confidence": cycle.get("confidence"),
            "signals": cycle.get("signals", [])[:5],
        },
        "transition": cycle.get("transition"),
        "recommendedSectors": rec_sectors,
        "screens": screens,
        "narrative": narrative,
    }


# ══════════════════════════════════════
# 섹터 스크리닝 (scan 위임)
# ══════════════════════════════════════


def _screenSector(sector: str, market: str, topN: int, asOf: str | None) -> list[dict]:
    """섹터 내 상위 종목 스크리닝.

    현재 구현: scan.financial 결과에서 섹터 일치 종목 필터 + 수익성 정렬.
    scan API 변동에 견디도록 try-except로 감싸고 빈 리스트 fallback.
    """
    try:
        from dartlab.scan import Scan

        scan = Scan()
        # 수익성 축에서 전종목 → 섹터 필터 → 상위 N
        df = scan("financial", "수익성", market=market) if hasattr(scan, "__call__") else None
    except (KeyError, ValueError, TypeError, ImportError, AttributeError):
        return []

    if df is None or len(df) == 0:
        return []

    # 섹터 필드 추정 — 'sector', 'industry', 'sectorName' 등
    sector_col = None
    for col in ("sector", "industry", "sectorName", "업종"):
        if col in df.columns:
            sector_col = col
            break

    if sector_col is None:
        # 섹터 컬럼 없으면 그냥 상위 N개 반환
        rows = df.head(topN).to_dicts()
    else:
        try:
            filtered = df.filter(df[sector_col].str.contains(sector, literal=False))
            rows = filtered.head(topN).to_dicts()
        except (KeyError, ValueError, AttributeError):
            rows = df.head(topN).to_dicts()

    # 종목 정보만 추출
    return [
        {
            "stockCode": r.get("stockCode") or r.get("종목코드") or r.get("code"),
            "name": r.get("name") or r.get("종목명") or r.get("corpName"),
            "metrics": {k: v for k, v in r.items() if k not in ("stockCode", "name", "종목코드", "종목명")},
        }
        for r in rows
    ]


# ══════════════════════════════════════
# Narrative 조립
# ══════════════════════════════════════


def _buildNarrative(cycle: dict, sectors: list[str], screens: dict, market: str) -> str:
    phase = cycle.get("phaseLabel") or cycle.get("phase", "?")
    conf = cycle.get("confidence", "?")

    parts: list[str] = []
    parts.append(f"[{market.upper()} 시장] 현재 경제 사이클은 **{phase}** 국면 (신뢰도 {conf}).")

    signals = cycle.get("signals", [])
    if signals:
        parts.append(f"근거 신호: {', '.join(str(s) for s in signals[:3])}.")

    transition = cycle.get("transition")
    if transition:
        prog = transition.get("progress", 0)
        to_phase = transition.get("to", "?")
        parts.append(f"다음 국면({to_phase})으로의 전환 진행도 {prog}%.")

    if sectors:
        parts.append(f"이 국면에 적합한 섹터: {', '.join(sectors)}.")

    total_picks = sum(len(v) for v in screens.values())
    if total_picks > 0:
        parts.append(f"각 섹터에서 총 {total_picks}개 후보 종목을 추렸다.")
    else:
        parts.append("섹터별 종목 스크리닝 결과 없음 (scan 데이터 미수집 가능).")

    parts.append("이 결과는 출발점이다. 각 종목은 c.story() 또는 c.quant('차트패턴')으로 추가 검증한다.")

    return " ".join(parts)


# ══════════════════════════════════════
# 가이드 모드
# ══════════════════════════════════════


def _guide() -> dict:
    """인자 없이 호출 시 가이드."""
    return {
        "name": "topdown",
        "description": "탑다운 분석 — macro 사이클 → 추천 섹터 → 종목 후보 → narrative",
        "usage": [
            'dartlab.topdown(market="KR")           # 한국 시장',
            'dartlab.topdown(market="US")           # 미국 시장',
            'dartlab.topdown(market="KR", topN=10)  # 섹터당 상위 10',
            'dartlab.topdown(market="KR", sectors=["반도체"])  # 특정 섹터',
        ],
        "flow": [
            "1. dartlab.macro('사이클') → 현재 국면",
            "2. 국면 → 적합 섹터 매핑 (회복기=경기민감, 둔화기=방어주)",
            "3. 각 섹터에서 scan('financial', '수익성') → 상위 종목",
            "4. narrative 자동 조립",
        ],
        "next": [
            "dartlab.topdown('KR') 으로 실행",
            "결과의 종목 후보 → c.story() 또는 c.quant('차트패턴')으로 검증",
        ],
    }


# Module-level callable 패턴
class _TopdownEntry:
    """`dartlab.topdown(...)` 를 callable로 노출."""

    def __call__(self, market: str | None = None, **kwargs) -> dict:
        if market is None and not kwargs:
            return _guide()
        return topdown(market=market or "KR", **kwargs)

    def __repr__(self) -> str:
        return "<dartlab.topdown — 탑다운 facade (macro→sector→stocks)>"
