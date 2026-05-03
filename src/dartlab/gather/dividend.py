"""KRX 종목별 현금배당 events 수집 (Stage 2 — 수정주가 TR 모드 활성화용 트랙).

Stage 1 (가격 자동 감지, `_adjustPrice.detectEventsFromPrices`) 가 split/bonus/rights 는
이미 처리하지만 **현금배당은 가격 변동이 작아 자동 감지 불가**. 이 모듈이 DART 공시 기반
배당 events 를 수집해 `_adjustPrice.applyAdjustment(mode="tr")` 를 활성화.

PLAN (engines.gather §9 Stage 2):
    1. DART listJson 으로 "현금ㆍ현물배당결정" 보고서 rcept_no 수집 (전종목, 전기간)
    2. 각 rcept_no 의 본문 파싱:
       - 배당기준일 (≈ 배당락일 D-1)
       - 1주당 배당금 (현금)
    3. events DataFrame schema 로 정규화:
       BAS_DD (배당락일) · ISU_CD · type="dividend" · ratio=null · divPerShare
    4. HF dataset `eddmpython/dartlab-data` / `krx/events/dividends.parquet` 누적
    5. `_hfBulk._loadEvents()` 가 자동 fetch → applyAdjustment(mode="tr") 정확 작동

DART 공시 파싱 인프라 (`providers/dart/openapi/`) 재사용 — ZipDocsCollector + 본문 정규식.

⚠️ 골격만 — 본격 구현은 별도 트랙 (`memory/quantGap.md` Sprint 1 #12).
"""

from __future__ import annotations

import logging

import polars as pl

log = logging.getLogger(__name__)


def collectDividendEvents(
    *,
    stockCode: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pl.DataFrame:
    """현금배당 공시 → events DataFrame.

    PLAN — 골격. 본격 구현 미정.

    Returns
    -------
    pl.DataFrame
        applyAdjustment 의 events schema:
            BAS_DD : str — 배당락일 (YYYYMMDD)
            ISU_CD : str — 종목코드 (6자리)
            type : str — "dividend"
            ratio : float | None — 항상 None (배당은 ratio 무관)
            divPerShare : float — 1주당 배당금 (원)
    """
    log.info("collectDividendEvents: 골격 — 본격 구현 미완 (Stage 2 트랙)")
    return pl.DataFrame(
        schema={
            "BAS_DD": pl.String,
            "ISU_CD": pl.String,
            "type": pl.String,
            "ratio": pl.Float64,
            "divPerShare": pl.Float64,
        }
    )
