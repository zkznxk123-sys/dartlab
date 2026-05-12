"""주가 수정 매커니즘 — raw + events → adjusted (CRSP 표준 backward chaining).

dartlab 의 **단일 SSOT 수정종가 함수**. raw 는 KRX OpenAPI 그대로 HF 에 저장,
이 함수가 사용 시점에 events 와 결합해 split / Total Return 가격 시계열 생성.
새 이벤트 발견 시 factor 만 재계산 = 자동 소급 보정 (raw 영원히 불변).

이벤트 원장 schema (events DataFrame — raw 와 **동일 컬럼명** SSOT):
    BAS_DD        # 이벤트 발생일 (YYYYMMDD string, 분할 기일 · 권리락일 · 배당락일)
    ISU_CD        # 종목코드 (6자리, krxApi 기준)
    type          # "split" | "bonus" | "rights" | "dividend"
    ratio         # split/bonus/rights — newShares/oldShares (50:1 → 50.0)
    divPerShare   # 현금배당 — 주당 배당금 (원, tr 모드만 사용)

events 컬럼명을 raw 와 통일해야 join 일관 — `_loadEvents` 가 DART 원천 컬럼을
이 schema 로 normalize 후 반환. 다른 컬럼명 쓰는 호출자는 `dateCol` / `codeCol` 인자로 override.

mode:
    "raw"   — 조정 없음
    "split" — split + bonus + rights (한국 포털 "수정주가" 와 등가)
    "tr"    — split + bonus + rights + dividend reinvested (Total Return)

알고리즘 (backward chaining):
    종목별 시계열을 거꾸로 (오늘 → 과거) 순회. 이벤트 발생일 마주치면 누적 factor 곱.
    그 이전 모든 가격에 factor 적용 → past × cumProd(factor) = adjusted.

events 부재 시 raw 그대로 + warning 1회. 호출자는 항상 동일 시그니처로 호출.

학술 근거:
    - CRSP Adjustment Methodology (Center for Research in Security Prices)
    - Norgate Data — Total Return Index methodology
"""

from __future__ import annotations

import logging
import warnings
from typing import Literal

import polars as pl

log = logging.getLogger(__name__)

# Polars join_asof 가 by group 안의 정렬을 검증할 수 없다는 informational warning.
# rawSorted = raw.sort([codeCol, dateCol]) 로 이미 정렬했으므로 안전.
warnings.filterwarnings(
    "ignore",
    message="Sortedness of columns cannot be checked when 'by' groups provided",
    category=UserWarning,
)

_DEFAULT_PRICE_COLS = ("TDD_OPNPRC", "TDD_HGPRC", "TDD_LWPRC", "TDD_CLSPRC")
_warned_no_events = False

# Stage 1 (가격 자동 감지) 이벤트 임계값 — implied/declared 비율의 1.0 으로부터의 편차.
# 한국 시장 일일 변동 한계 ±30% 이내라 정상 변동은 implied≈declared (event_factor≈1).
# 권리락/분할 등 이벤트는 큰 차이 (보통 50%+) — 0.02 (2%) 임계로도 충분히 분리.
_AUTO_DETECT_THRESHOLD = 0.02


def detectEventsFromPrices(
    raw: pl.DataFrame,
    *,
    dateCol: str = "BAS_DD",
    codeCol: str = "ISU_CD",
    closeCol: str = "TDD_CLSPRC",
    flucCol: str = "FLUC_RT",
    threshold: float = _AUTO_DETECT_THRESHOLD,
) -> pl.DataFrame:
    """가격 시계열에서 split/bonus/rights 이벤트 자동 감지 (marcap 방식 + FLUC_RT 정밀화).

    Capabilities:
        - DART 공시 파싱 불필요 — KRX 응답의 ``TDD_CLSPRC`` + ``FLUC_RT`` 만 사용
        - implied vs declared 비율 비교로 권리락/분할/증자 자동 감지
        - 일반 상한가 (+30%) 와 정확히 분리 (declared=implied=1.30 → factor=1.0)
        - 한국 포털 (네이버 등) · marcap 의 표준 방식

    AIContext:
        - dartlab 의 Stage 1 수정주가 백본 — DART events 트랙 도착 전 즉시 활성
        - Stage 2 (DART 공시) 도착 후엔 cross-check 용으로 활용 가능 (false positive 검출)
        - 한계: 현금배당 감지 불가 (배당락 가격 변동이 noise 와 구분 어려움) → TR 모드는 Stage 2 필수

    Guide:
        - "DART 공시 없이 split-adj 만들고 싶다" → ``detectEventsFromPrices(raw)`` → ``applyAdjustment(raw, events, mode="split")``
        - "TR 도 필요하다" → Stage 2 의 DART dividend events 추가 후 ``mode="tr"``

    SeeAlso:
        - applyAdjustment — events DataFrame 받아서 raw → adjusted
        - gather/_hfBulk.py::_loadEvents — Stage 1/2 디스패치 (HF events 있으면 우선, 없으면 auto)
        - engines.gather §9 — 수정주가 PLAN 7-step

    Algorithm:
        implied_ratio  = TDD_CLSPRC[t] / TDD_CLSPRC[t-1]    # raw 가격 차이
        declared_ratio = 1 + FLUC_RT[t] / 100                # 공시 등락률 (권리락 조정 반영)
        event_factor   = implied_ratio / declared_ratio       # 이벤트 발생 비율

        정상 거래일:  implied = declared → event_factor ≈ 1.0
        50:1 split:  implied=0.02, declared≈1.0 → event_factor=0.02 → ratio=1/0.02=50.0
        무상 1:1:    implied=0.5, declared=1.0 → event_factor=0.5 → ratio=2.0

    Args:
        raw: KRX OpenAPI 응답 형식 long DataFrame.
        dateCol, codeCol, closeCol, flucCol: 컬럼명 (기본 KRX 표준).
        threshold: 이벤트 후보 임계 (event_factor 가 ``[1-threshold, 1+threshold]`` 벗어나면 후보).
            기본 0.02 (2%) — 일반 변동 noise 와 권리락 분리에 충분.

    Returns:
        pl.DataFrame — applyAdjustment 가 받는 events schema:
            BAS_DD, ISU_CD, type ("split"), ratio (newShares/oldShares), divPerShare (None).
    """
    if raw.is_empty() or closeCol not in raw.columns or flucCol not in raw.columns:
        return pl.DataFrame(
            schema={
                dateCol: pl.String,
                codeCol: pl.String,
                "type": pl.String,
                "ratio": pl.Float64,
                "divPerShare": pl.Float64,
            }
        )

    detected = (
        raw.sort([codeCol, dateCol])
        .with_columns(pl.col(closeCol).shift(1).over(codeCol).alias("_prevClose"))  # polars-streaming-unsupported: over
        .filter(pl.col("_prevClose").is_not_null() & (pl.col("_prevClose") > 0))
        .with_columns(
            [
                (pl.col(closeCol) / pl.col("_prevClose")).alias("_implied"),
                (1.0 + pl.col(flucCol) / 100.0).alias("_declared"),
            ]
        )
        .filter(pl.col("_declared") > 0)
        .with_columns((pl.col("_implied") / pl.col("_declared")).alias("_eventFactor"))
        .filter((pl.col("_eventFactor") < 1.0 - threshold) | (pl.col("_eventFactor") > 1.0 + threshold))
        .with_columns(
            [
                pl.lit("split").alias("type"),
                (1.0 / pl.col("_eventFactor")).alias("ratio"),
                pl.lit(None, dtype=pl.Float64).alias("divPerShare"),
            ]
        )
        .select([dateCol, codeCol, "type", "ratio", "divPerShare"])
    )
    return detected


def applyAdjustment(
    raw: pl.DataFrame,
    events: pl.DataFrame | None = None,
    *,
    mode: Literal["raw", "split", "tr"] = "split",
    priceCols: tuple[str, ...] = _DEFAULT_PRICE_COLS,
    dateCol: str = "BAS_DD",
    codeCol: str = "ISU_CD",
) -> pl.DataFrame:
    """원본 raw + events → split / TR adjusted price 시계열.

    Capabilities:
        - mode "raw": 조정 없음 (raw 그대로 통과)
        - mode "split": split + bonus + rights factor 적용 (한국 "수정주가" 등가)
        - mode "tr": split + dividend reinvested (Total Return)
        - events 부재 시 raw + warning 1회 (예외 X) — 호출자 코드 단순화
        - backward chaining = 새 이벤트 발견 시 factor 만 재계산하면 전 역사 자동 보정

    AIContext:
        - dartlab 의 단일 SSOT 수정종가 함수 — `gather/_hfBulk.loadFiltered` 가 호출
        - raw 는 영원히 불변 (KRX OpenAPI 응답 그대로 HF 저장)
        - events 데이터 트랙은 별도: `gather/dividend.py` (DART 배당결정),
          `gather/capitalEvent.py` (분할/증자) 신설 예정

    Guide:
        - "한국 수정주가 (split)" → ``mode="split"``
        - "Total Return (배당 재투자)" → ``mode="tr"``
        - "원본 그대로" → ``mode="raw"``

    SeeAlso:
        - `gather/_hfBulk.py::loadFiltered` — 엔진 진입점 (이 함수 호출)
        - `gather/krxApi.py` — raw 수집 (사용자 직접 호출)
        - `engines.gather §9` — KRX 수집 + 수정주가 사상

    Args:
        raw: KRX OpenAPI 응답 형식 DataFrame (``BAS_DD``, ``ISU_CD``, ``TDD_*PRC`` ...).
        events: 이벤트 원장. None/빈 DataFrame 이면 raw 그대로 반환 + warning.
        mode: ``"raw"`` | ``"split"`` | ``"tr"``.
        priceCols: 조정 대상 가격 컬럼 (기본 OHLC 4 종).
        dateCol, codeCol: raw 의 날짜·종목코드 컬럼명.

    Returns:
        pl.DataFrame — raw 컬럼 + ``splitFactor`` + ``divFactor`` (mode="raw" 제외).
        priceCols 자체는 adjusted 값으로 덮어씀 (raw 보존 원하면 호출 전 ``raw.clone()``).

    Example::

        from dartlab.gather.transforms.adjustPrice import applyAdjustment
        adjusted = applyAdjustment(raw, events, mode="split")
        tr = applyAdjustment(raw, events, mode="tr")

    Notes:
        events.ratio 컨벤션: newShares/oldShares (50:1 split → 50.0).
        가격 조정 factor = 1 / ratio (가격 하향).
    """
    global _warned_no_events

    if mode == "raw" or raw.is_empty():
        return raw

    if events is None or events.is_empty():
        if not _warned_no_events:
            log.warning(
                "events 데이터 없음 — raw 그대로 반환 (mode=%s 효과 없음). "
                "events 트랙: gather/dividend.py + gather/capitalEvent.py 별도 작업",
                mode,
            )
            _warned_no_events = True
        return raw.with_columns(
            [
                pl.lit(1.0).alias("splitFactor"),
                pl.lit(1.0).alias("divFactor"),
            ]
        )

    result = raw
    if mode in ("split", "tr"):
        splitEv = events.filter(pl.col("type").is_in(["split", "bonus", "rights"]))
        result = _applySplitFactor(
            result,
            splitEv,
            priceCols=priceCols,
            dateCol=dateCol,
            codeCol=codeCol,
        )
    if mode == "tr":
        divEv = events.filter(pl.col("type") == "dividend")
        result = _applyDivFactor(
            result,
            divEv,
            priceCols=priceCols,
            dateCol=dateCol,
            codeCol=codeCol,
        )
    return result


def _applySplitFactor(
    raw: pl.DataFrame,
    events: pl.DataFrame,
    *,
    priceCols: tuple[str, ...],
    dateCol: str,
    codeCol: str,
) -> pl.DataFrame:
    """Backward chaining split/bonus/rights factor (CRSP 표준).

    events.ratio = newShares/oldShares. 가격 조정 factor = 1/ratio.
    raw 의 각 row 에 대해 raw.date 이후 발생한 모든 split events 의 누적 factor.
    """
    if events.is_empty():
        return raw.with_columns(pl.lit(1.0).alias("splitFactor"))

    ev = (
        events.sort([codeCol, dateCol])
        .with_columns(
            [
                (1.0 / pl.col("ratio")).alias("_priceAdj"),
                pl.col(dateCol).alias("_evDate"),
            ]
        )
        .with_columns(
            pl.col("_priceAdj").cum_prod(reverse=True).over(codeCol).alias("_revCum")
        )  # polars-streaming-unsupported: over
        .select([codeCol, dateCol, "_evDate", "_priceAdj", "_revCum"])
    )
    rawSorted = raw.sort([codeCol, dateCol])
    joined = (
        rawSorted.join_asof(ev, on=dateCol, by=codeCol, strategy="forward")
        .with_columns(
            # CRSP: ex-day 본인의 가격은 raw (factor=1), 그 *이전* 가격에만 누적 factor.
            # forward 매칭이 raw.date <= ev.date 라 ev.date == raw.date 인 경우
            # 그 ev 자체를 누적에서 제외 (revCum / priceAdj = 다음 ev 부터의 누적).
            pl.when(pl.col(dateCol) == pl.col("_evDate"))
            .then(pl.col("_revCum") / pl.col("_priceAdj"))
            .otherwise(pl.col("_revCum"))
            .fill_null(1.0)
            .alias("splitFactor")
        )
        .drop(["_evDate", "_priceAdj", "_revCum"])
    )
    adjusts = [(pl.col(c) * pl.col("splitFactor")).alias(c) for c in priceCols if c in joined.columns]
    if adjusts:
        joined = joined.with_columns(adjusts)
    return joined


def _applyDivFactor(
    raw: pl.DataFrame,
    events: pl.DataFrame,
    *,
    priceCols: tuple[str, ...],
    dateCol: str,
    codeCol: str,
) -> pl.DataFrame:
    """Backward chaining dividend factor (Total Return, CRSP 표준).

    배당락일 종가에서 div 가 차감된 상태 → 과거 가격에 ``exClose/(exClose+div)`` 적용
    (factor < 1, 가격 하향) → today raw 가 fix, past 가 낮아져 TR 시계열 완성.
    """
    if events.is_empty():
        return raw.with_columns(pl.lit(1.0).alias("divFactor"))

    closeCol = "TDD_CLSPRC"
    if closeCol not in raw.columns:
        log.warning("_applyDivFactor: %s 없음 → divFactor=1.0 fallback", closeCol)
        return raw.with_columns(pl.lit(1.0).alias("divFactor"))

    closeLookup = raw.select([codeCol, dateCol, closeCol]).rename({closeCol: "_exClose"})
    ev = (
        events.sort([codeCol, dateCol])
        .join(closeLookup, on=[codeCol, dateCol], how="left")
        .filter(pl.col("_exClose").is_not_null() & (pl.col("_exClose") > 0))
        .with_columns(
            [
                (pl.col("_exClose") / (pl.col("_exClose") + pl.col("divPerShare"))).alias("_divAdj"),
                pl.col(dateCol).alias("_evDate"),
            ]
        )
        .with_columns(
            pl.col("_divAdj").cum_prod(reverse=True).over(codeCol).alias("_revCumDiv")
        )  # polars-streaming-unsupported: over
        .select([codeCol, dateCol, "_evDate", "_divAdj", "_revCumDiv"])
    )
    rawSorted = raw.sort([codeCol, dateCol])
    joined = (
        rawSorted.join_asof(ev, on=dateCol, by=codeCol, strategy="forward")
        .with_columns(
            pl.when(pl.col(dateCol) == pl.col("_evDate"))
            .then(pl.col("_revCumDiv") / pl.col("_divAdj"))
            .otherwise(pl.col("_revCumDiv"))
            .fill_null(1.0)
            .alias("divFactor")
        )
        .drop(["_evDate", "_divAdj", "_revCumDiv"])
    )
    adjusts = [(pl.col(c) * pl.col("divFactor")).alias(c) for c in priceCols if c in joined.columns]
    if adjusts:
        joined = joined.with_columns(adjusts)
    return joined
