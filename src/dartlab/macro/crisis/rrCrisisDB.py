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

    Capabilities:
        Reinhart-Rogoff (2009) "This Time Is Different" 5 위기 유형 (banking/
        currency/inflation/sovereign_debt/stagflation) 동시 분류 — 임계 매칭
        multi-label + Triple Crisis (banking + currency + debt 동반) 판정.

    Args:
        hySpread: HY OAS (bp). > 800 → banking.
        npl: NPL 비율 (%). > 5 → banking.
        fxDepreciationYoy: 환율 절하율 (%). > 25 → currency.
        inflationYoy: CPI YoY (%). > 15 → inflation.
        sovereignSpread: 국채 스프레드 (bp). > 500 → sovereign_debt.
        gdpGrowth: 실질 성장률 (%). inflation > 5 + GDP < 1 → stagflation.

    Returns:
        dict — activeTypes(list)/signals(list)/isTripleCrisis(bool)/
        dominantType(str | None).

    Example:
        >>> r = classifyCrisisType(hySpread=900, fxDepreciationYoy=30)
        >>> r["activeTypes"]
        ['banking', 'currency']

    Guide:
        isTripleCrisis=True = 가장 심각 (1997 아시아·1998 러시아 사례). dominant
        은 첫 번째 활성 type.

    When:
        ``analyzeCrisis`` 내부 + AI 위기 유형 답변.

    How:
        각 임계 매칭 → active 리스트 누적 → triple (banking+currency+debt) 검증.

    Requires:
        지표 별 적어도 1 개 입력. 모두 None 이면 빈 active.

    Raises:
        없음.

    See Also:
        - matchRrHistorical : R&R DB 800 년 매칭
        - analyzeCrisis : 본 함수 호출 진입점

    AIContext:
        activeTypes + dominantType 인용으로 "banking + currency 동시 위기"
        답변.

    LLM Specifications:
        AntiPatterns:
            - dominantType 만 인용 + activeTypes 무시 (multi-label 잃음)
            - 임계 임의 변경 (R&R 표준)
            - 단일 지표 (HY 만) 로 banking 단정 (NPL 동반 확인 권장)
        OutputSchema:
            ``{activeTypes, signals, isTripleCrisis, dominantType}``.
        Prerequisites: HY/NPL/FX/CPI/sovereign/GDP 중 일부.
        Freshness: 일간 (HY/FX) ~ 분기 (GDP/NPL).
        Dataflow: 지표 → 임계 → 라벨.
        TargetMarkets: Global. KR/US 적용.
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

    Capabilities:
        Reinhart-Rogoff 800 년 위기 DB 와 현재 crisis types 교집합 매칭 → top-K
        에피소드 + 같은 유형 조합 일치 카운트. 일치 점수 = 공통 type 수 +
        country 일치 보너스.

    Args:
        currentTypes: classifyCrisisType activeTypes 리스트.
        country: 국가 코드 ("KR"/"US" 등). 일치 시 +1 보너스.
        topK: 반환 개수. 기본 5.

    Returns:
        dict — matches(id/country/year/endYear/types/severity/note/score list)/
        sameTypeCount(int).

    Example:
        >>> r = matchRrHistorical(["banking", "currency"], country="KR")
        >>> r["matches"][0]["year"], r["matches"][0]["score"]
        (1997, 3)

    Guide:
        sameTypeCount 가 많으면 보편적 유형 (자주 발생). matches[0] note 인용으로
        과거 사례 답변.

    When:
        ``analyzeCrisis`` 내부 + AI 역사적 위기 답변.

    How:
        _loadRrCrises (JSON) → 각 epi 교집합 → score 정렬 → top-K.

    Requires:
        rrCrises800y.json (dartlab.reference.data 번들).

    Raises:
        FileNotFoundError — JSON 리소스 누락 (재설치 안내).
        RuntimeError — JSON 포맷 손상.

    See Also:
        - classifyCrisisType : currentTypes 입력 생성
        - analyzeCrisis : 본 함수 호출 진입점

    AIContext:
        matches[0] (year/country) + sameTypeCount 인용으로 "1997 KR 위기와 유형
        일치, 800 년 DB 12 건 동일" 답변.

    LLM Specifications:
        AntiPatterns:
            - top 1 단정 + sameTypeCount 미노출
            - country 누락한 채 KR 분석 (보너스 미적용)
        OutputSchema:
            ``{matches, sameTypeCount}``.
        Prerequisites: rrCrises800y.json + currentTypes.
        Freshness: 정적 (R&R DB).
        Dataflow: types → 교집합 → score → top-K.
        TargetMarkets: Global. country 인자로 보너스.
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
