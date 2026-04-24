"""KRX 종목별 자본변동 events 수집 (Stage 2 — Stage 1 cross-validation + 정확 ratio).

Stage 1 (`_adjustPrice.detectEventsFromPrices`) 가 가격 점프로 split/bonus/rights 자동 감지하지만:
- false positive 위험 (정상 변동을 이벤트로 오감지)
- ratio 정밀도 한계 (FLUC_RT 노이즈)

이 모듈이 DART 공시 기반 정확 events 를 수집해 Stage 1 결과를 검증 + 보정.

PLAN (ops/gather.md §9 Stage 2):
    1. DART listJson 으로 다음 보고서 rcept_no 수집:
       - "주식분할결정" / "주식병합결정"
       - "무상증자결정"
       - "유상증자결정"
       - "감자결정"
    2. 각 rcept_no 본문 파싱:
       - 분할/병합: 분할비 (newShares/oldShares), 분할기일
       - 무상증자: 신주배정비율, 권리락일
       - 유상증자: 권리락일, 이론권리락가 / 시가 비율
       - 감자: 감자비율, 감자기일
    3. events DataFrame schema 로 정규화:
       BAS_DD · ISU_CD · type ∈ {split, bonus, rights, reverseSplit} · ratio · divPerShare=null
    4. HF dataset `eddmpython/dartlab-data` / `krx/events/capital.parquet` 누적
    5. Stage 1 가격 자동 감지 결과와 cross-check → false positive 제거 + 정확 ratio

DART 공시 파싱 인프라 (`providers/dart/openapi/`) 재사용.

⚠️ 골격만 — 본격 구현은 별도 트랙 (`memory/quantGap.md` Sprint 1 #12).
"""

from __future__ import annotations

import logging

import polars as pl

log = logging.getLogger(__name__)


def collectCapitalEvents(
    *,
    stockCode: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pl.DataFrame:
    """자본변동 공시 → events DataFrame.

    PLAN — 골격. 본격 구현 미정.

    Returns
    -------
    pl.DataFrame
        applyAdjustment 의 events schema:
            BAS_DD : str — 권리락일 / 분할기일 (YYYYMMDD)
            ISU_CD : str — 종목코드 (6자리)
            type : str — "split" | "bonus" | "rights" | "reverseSplit"
            ratio : float — newShares / oldShares (50:1 split → 50.0, 1:5 병합 → 0.2)
            divPerShare : float | None — 항상 None (자본변동은 배당 무관)
    """
    log.info("collectCapitalEvents: 골격 — 본격 구현 미완 (Stage 2 트랙)")
    return pl.DataFrame(
        schema={
            "BAS_DD": pl.String,
            "ISU_CD": pl.String,
            "type": pl.String,
            "ratio": pl.Float64,
            "divPerShare": pl.Float64,
        }
    )
