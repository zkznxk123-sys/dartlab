"""YoY delta 사전 계산 — 전 종목 × 최신년 대비 전년 재무 지표 변화.

산업지도 회사 카드의 **delta badge** (예: "ROE 12.4% · YoY +1.8%p ▲") 용.

Returns
-------
dict[str, dict]
    stockCode → {
        roeDelta: float | None,             # %p (최신년 ROE - 전년 ROE)
        opMarginDelta: float | None,        # %p
        netMarginDelta: float | None,       # %p
        revenueYoyPct: float | None,        # % (전년 대비 증감률)
        debtRatioDelta: float | None,       # %p (부채비율)
        asOfYear: int | None,               # 최신년
        priorYear: int | None,              # 전년
    }

설계 결정
---------
- finance.parquet 1회 로드 → 최신·전년 2개 연도 동시 계산
- 음수/0 분모 방어
- 업데이트 직후 전년 데이터 없는 신규 상장사 → None (필드 스킵)
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


def _extractByIds(rowSub: pl.DataFrame, idList, nmList) -> float | None:
    """단일 연도 subset 에서 특정 계정의 금액 추출.

    scan._helpers.extractAccount 를 래핑하여 account_id 또는 account_nm 으로
    매칭되는 행의 thstrm_amount 를 반환한다.

    Parameters
    ----------
    rowSub : pl.DataFrame
        단일 연도 · 단일 종목의 재무 데이터 subset.
    idList : set[str] | list[str]
        매칭할 account_id 목록 (예: _REVENUE_IDS).
    nmList : set[str] | list[str]
        매칭할 account_nm 목록 (예: _REVENUE_NMS).

    Returns
    -------
    float | None
        매칭된 계정의 금액 (원). 없으면 None.
    """
    from dartlab.scan.io.parquet import extractAccount

    return extractAccount(rowSub, list(idList), list(nmList))


def computeYoyDelta() -> dict[str, dict[str, Any]]:
    """전년 대비 재무 비율 변화(YoY delta) 전 종목 사전 계산.

    Capabilities:
        scan/finance.parquet 에서 최신 2 개 연도를 추출하고 종목별로 ROE/영업이익률/순이익률/
        매출 증감률/부채비율의 전기 대비 차이를 일괄 산출. 산업지도 CompanyCard delta
        badge ("▲ +1.8%p") 의 데이터 소스.

    scan/finance.parquet 에서 최신 2개 연도를 추출하고, 종목별로
    ROE/영업이익률/순이익률/매출 증감률/부채비율 의 전기 대비 차이를 계산한다.
    산업지도 CompanyCard 의 delta badge ("▲ +1.8%p") 에 사용.

    Parameters
    ----------
    없음 — 내부적으로 _ensureScanData() 경로의 finance.parquet 로드.

    Returns
    -------
    dict[str, dict[str, Any]]
        stockCode → {
            roeDelta : float | None — ROE 변화 (%p). 양수=개선
            opMarginDelta : float | None — 영업이익률 변화 (%p)
            netMarginDelta : float | None — 순이익률 변화 (%p)
            revenueYoyPct : float | None — 매출 전년대비 증감률 (%)
            debtRatioDelta : float | None — 부채비율 변화 (%p). 양수=악화
            asOfYear : int | None — 최신 연도 (예: 2025)
            priorYear : int | None — 전년 (예: 2024)
        }

    Notes
    -----
    - 연결재무제표(CFS) 우선, 없으면 개별(OFS) fallback
    - 전년 데이터 없는 신규 상장사는 dict 에서 제외
    - 모든 delta 가 None 인 종목도 제외
    - scan.profitability 의 계정 ID/명 매핑을 재사용

    Examples
    --------
    >>> from dartlab.industry.build.delta import computeYoyDelta
    >>> d = computeYoyDelta()
    >>> d['005930']['roeDelta']   # 삼성전자 ROE 변화 (%p)
    -230.2
    >>> d['000660']['revenueYoyPct']  # SK하이닉스 매출 YoY
    41.9

    Raises:
        없음 — finance.parquet 없으면 빈 dict 반환 + warning log.

    Guide:
        파이프라인 빌드 1 회 (`buildIndustryMap`) 에서 사용. delta dict 은 industry.json
        manifest 의 ``deltas`` 키로 직렬화돼 UI 카드/Story 6 막 narrative 에 인용.

    When:
        산업지도 manifest 빌드 시 (드물게: 회사 카드의 전년대비 badge 갱신 필요 시).
        일반 분석 흐름에서는 호출하지 않는다 — finance.parquet 전수 스캔 비용 때문.

    How:
        ``_ensureScanData()`` → finance.parquet 로드 → 연결/개별 fallback → 최신 2 연도 분리
        → 종목 단위 ratio 추출 → ``_diff`` / ``_pctChange`` → dict 반환.

    Requires:
        - L1.5 scan: ``scan/io/parquet._ensureScanData`` 가 산출한 finance.parquet 존재
        - DART 연간 보고서 2 개 연도 이상

    See Also:
        - ``dartlab.industry.build.pipeline.buildIndustryMap`` : 본 함수 호출 사용자
        - ``dartlab.scan.io.parquet.extractAccount`` : 계정 추출 헬퍼

    AIContext:
        산업지도 회사 카드의 "전년대비" 1 줄 답변 데이터 소스. AI 답변에는 ``roeDelta`` /
        ``opMarginDelta`` / ``revenueYoyPct`` 3 개가 가장 인용 가치 높음.
    """
    from pathlib import Path

    from dartlab.scan.io.parquet import (
        EQ_IDS,
        EQ_NMS,
        LIABILITY_IDS,
        LIABILITY_NMS,
        NI_IDS,
        NI_NMS,
        OP_IDS,
        OP_NMS,
        REVENUE_IDS,
        REVENUE_NMS,
        TA_IDS,
        TA_NMS,
        _ensureScanData,
    )

    scanDir = _ensureScanData()
    scanPath = Path(scanDir) / "finance.parquet"
    if not scanPath.exists():
        logger.warning(f"finance.parquet 없음: {scanPath}")
        return {}

    # 로드 — scanProfitability 와 동일 필터 (SSOT: scan/io/parquet 상수)
    allIds = list(REVENUE_IDS | OP_IDS | NI_IDS | TA_IDS | EQ_IDS | LIABILITY_IDS)
    allNms = list(REVENUE_NMS | OP_NMS | NI_NMS | TA_NMS | EQ_NMS | LIABILITY_NMS)
    schemaNames = pl.scan_parquet(str(scanPath)).collect_schema().names()
    scCol = "stockCode" if "stockCode" in schemaNames else "stock_code"

    df = (
        pl.scan_parquet(str(scanPath))
        .filter(
            pl.col("sj_div").is_in(["IS", "CIS", "BS"])
            & (pl.col("fs_nm").str.contains("연결") | pl.col("fs_nm").str.contains("재무제표"))
            & (pl.col("account_id").is_in(allIds) | pl.col("account_nm").is_in(allNms))
        )
        .collect(engine="streaming")
    )
    # 연결 우선
    cfs = df.filter(pl.col("fs_nm").str.contains("연결"))
    if not cfs.is_empty():
        df = cfs
    if df.is_empty():
        return {}
    years = sorted(df["bsns_year"].unique().to_list(), reverse=True)
    if len(years) < 2:
        logger.warning("YoY delta 계산 불가 — 연도 2개 미만")
        return {}

    latestYear = years[0]
    priorYear = years[1]
    latest = df.filter(pl.col("bsns_year") == latestYear)
    prior = df.filter(pl.col("bsns_year") == priorYear)

    def _ratios(sub: pl.DataFrame) -> tuple:
        rev = _extractByIds(sub, REVENUE_IDS, REVENUE_NMS)
        op = _extractByIds(sub, OP_IDS, OP_NMS)
        ni = _extractByIds(sub, NI_IDS, NI_NMS)
        eq = _extractByIds(sub, EQ_IDS, EQ_NMS)
        li = _extractByIds(sub, LIABILITY_IDS, LIABILITY_NMS)

        opMargin = (op / rev * 100) if rev and rev != 0 and op is not None else None
        netMargin = (ni / rev * 100) if rev and rev != 0 and ni is not None else None
        roe = (ni / eq * 100) if eq and eq != 0 and ni is not None else None
        debtRatio = (li / eq * 100) if eq and eq != 0 and li is not None else None
        return rev, opMargin, netMargin, roe, debtRatio

    out: dict[str, dict[str, Any]] = {}
    codes = set(latest[scCol].unique().to_list())

    for code in codes:
        lsub = latest.filter(pl.col(scCol) == code)
        psub = prior.filter(pl.col(scCol) == code)
        if psub.is_empty():
            continue

        lrev, lop, lnm, lroe, ldebt = _ratios(lsub)
        prev, pop, pnm, proe, pdebt = _ratios(psub)

        def _diff(a, b, digits=1):
            if a is None or b is None:
                return None
            return round(a - b, digits)

        def _pctChange(a, b, digits=1):
            if a is None or b is None or b == 0:
                return None
            return round((a - b) / abs(b) * 100, digits)

        entry = {
            "roeDelta": _diff(lroe, proe),
            "opMarginDelta": _diff(lop, pop),
            "netMarginDelta": _diff(lnm, pnm),
            "revenueYoyPct": _pctChange(lrev, prev),
            "debtRatioDelta": _diff(ldebt, pdebt),
            "asOfYear": int(latestYear) if latestYear else None,
            "priorYear": int(priorYear) if priorYear else None,
        }

        # 모든 필드가 None 이면 저장하지 않음
        if all(v is None for k, v in entry.items() if k not in ("asOfYear", "priorYear")):
            continue

        out[code] = entry

    logger.info(f"YoY delta 계산 완료: {len(out)} 종목 (latest={latestYear}, prior={priorYear})")
    return out
