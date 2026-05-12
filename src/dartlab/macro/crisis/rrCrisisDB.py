"""Reinhart & Rogoff Crisis Type Classification + Historical DB SSOT.

Reinhart, C. & Rogoff, K. (2009), *This Time Is Different* — 4 crisis types:
    banking / currency / inflation / sovereign_debt (+ stagflation boundary case)

한 에피소드가 여러 유형을 동반할 수 있음 ("triple crisis" = banking + currency + debt).
현재 매크로 시그널을 유형별 임계치와 비교해 분류.

데이터: `reference/data/rrCrises800y.json` — 1800-present 주요 ~21 케이스 (subset).
"""

from __future__ import annotations

import json
import logging
from importlib import resources

log = logging.getLogger(__name__)


CRISIS_TYPES = ("banking", "currency", "inflation", "sovereign_debt", "stagflation")


def classifyCrisisType(
    *,
    hySpread: float | None = None,
    npl: float | None = None,
    fxDepreciationYoy: float | None = None,
    inflationYoy: float | None = None,
    sovereignSpread: float | None = None,
    gdpGrowth: float | None = None,
) -> dict:
    """현재 매크로 시그널 → R&R 위기 유형 분류 (multi-label).

    Parameters
    ----------
    hySpread : HY bond spread (bp). >800 → banking 신호.
    npl : NPL 비율 (%). >5 → banking.
    fxDepreciationYoy : 환율 절하율 (%). >25 → currency.
    inflationYoy : CPI YoY (%). >15 → inflation.
    sovereignSpread : 국채 스프레드 (bp) 또는 CDS. >500 → sovereign_debt.
    gdpGrowth : 실질 성장률. inflation 과 결합 시 stagflation.

    Returns
    -------
    dict
        activeTypes : list[str] — 활성화된 유형
        signals : list[str] — 판정 근거
        isTripleCrisis : bool — banking + currency + debt 동반
        dominantType : str | None
    """
    active: list[str] = []
    signals: list[str] = []

    if hySpread is not None and hySpread > 800:
        active.append("banking")
        signals.append(f"HY 스프레드 {hySpread:.0f}bp — banking crisis")
    if npl is not None and npl > 5.0:
        if "banking" not in active:
            active.append("banking")
        signals.append(f"NPL {npl:.1f}% — banking")

    if fxDepreciationYoy is not None and fxDepreciationYoy > 25.0:
        active.append("currency")
        signals.append(f"환율 {fxDepreciationYoy:+.0f}% — currency crisis")

    if inflationYoy is not None and inflationYoy > 15.0:
        active.append("inflation")
        signals.append(f"CPI {inflationYoy:+.1f}% — inflation crisis")

    if sovereignSpread is not None and sovereignSpread > 500:
        active.append("sovereign_debt")
        signals.append(f"국채 스프레드 {sovereignSpread:.0f}bp — sovereign debt crisis")

    # stagflation: inflation > 5 + gdpGrowth < 1
    if inflationYoy is not None and gdpGrowth is not None and inflationYoy > 5.0 and gdpGrowth < 1.0:
        active.append("stagflation")
        signals.append(f"CPI {inflationYoy:+.1f}% + GDP {gdpGrowth:+.1f}% — stagflation")

    triple = all(t in active for t in ["banking", "currency", "sovereign_debt"])

    dominant = active[0] if active else None
    return {
        "activeTypes": active,
        "signals": signals,
        "isTripleCrisis": triple,
        "dominantType": dominant,
    }


def _loadRrCrises() -> list[dict]:
    """Reinhart-Rogoff 800y crisis database 로드.

    2026-04-19 사고 class 방어 — silent `[]` 대신 loud-fail.
    """
    try:
        with resources.files("dartlab.reference.data").joinpath("rrCrises800y.json").open("r", encoding="utf-8") as f:
            return json.load(f).get("crises", [])
    except (FileNotFoundError, OSError) as e:
        raise FileNotFoundError(
            f"필수 번들 리소스 누락: dartlab/reference/data/rrCrises800y.json ({e})\n"
            f"  → pip install -U --force-reinstall dartlab"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"rrCrises800y.json 포맷 손상: {e}") from e


def matchRrHistorical(
    currentTypes: list[str],
    *,
    country: str | None = None,
    topK: int = 5,
) -> dict:
    """현재 crisis type 조합 → R&R DB 에서 같은 유형 에피소드 top-K.

    일치 점수 = 공통 type 수 (country 일치 시 +1 보너스).

    Parameters
    ----------
    currentTypes : 현재 활성화된 crisis types.
    country : 국가 코드 (KR, US, ...). 일치 시 가중치 부여.
    topK : 반환 개수.

    Returns
    -------
    dict
        matches : list of {id, country, year, types, severity, score, note}
        sameTypeCount : int — 같은 유형 조합 일치 에피소드 수
    """
    crises = _loadRrCrises()
    current_set = set(currentTypes)
    if not current_set:
        return {"matches": [], "sameTypeCount": 0}

    scored: list[dict] = []
    for c in crises:
        overlap = len(current_set & set(c.get("types", [])))
        if overlap == 0:
            continue
        bonus = 1 if (country and c.get("country") == country) else 0
        scored.append(
            {
                "id": c["id"],
                "country": c.get("country"),
                "year": c.get("year"),
                "endYear": c.get("endYear"),
                "types": c.get("types", []),
                "severity": c.get("severity"),
                "note": c.get("note"),
                "score": overlap + bonus,
            }
        )

    scored.sort(key=lambda x: (-x["score"], x["year"]))
    top = scored[:topK]

    return {
        "matches": top,
        "sameTypeCount": sum(1 for s in scored if set(s["types"]) == current_set),
    }
