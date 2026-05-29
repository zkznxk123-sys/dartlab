"""RUNTIME finance 정규화 — raw DART XBRL parquet → account × period wide 표.

facade sections 합성용 (요구 정정): docs sections 의 재무제표 XBRL 표(BS_C/IS_C…)는
*골격*일 뿐, 실제 데이터는 본 모듈의 **정규화 wide 표**가 이긴다 (account 단위
다기간 수평화. raw XML 표보다 우월).

옛 providers finance 엔진(40 파서) 의존 0 — data/dart/finance/{code}.parquet (DART
OpenAPI XBRL 원본) 을 직접 읽어 sj_div(BS/IS/CIS/CF/SCE) × fs_div(CFS/OFS) 별로
account_nm × period pivot.

LLM Specifications:
    AntiPatterns:
        - 옛 providers.dart.docs.finance import 금지 — filings 독립.
        - account_nm 중복 무시 금지 — account_id 보조 키로 안정화.
        - 금액 str 그대로 pivot 금지 — 콤마 strip + 음수(△/괄호) 정규화 후 Float.
    OutputSchema:
        - ``statementWide(code, sjDiv, fsDiv) -> pl.DataFrame`` (account 행 × period 열).
    Prerequisites:
        - data/dart/finance/{code}.parquet (DART OpenAPI XBRL 원본).
    Freshness:
        - finance parquet 갱신 시점 (분기 마감 후 ~45 일).
    Dataflow:
        - finance parquet → sj_div/fs_div filter → period 매핑 → 금액 정규화 →
          account_nm pivot.
    TargetMarkets:
        - KR (DART). EDGAR 는 별도.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

# DART reprt_code → calendar quarter suffix.
_REPRT_QUARTER = {
    "11013": "Q1",  # 1분기보고서
    "11012": "Q2",  # 반기보고서
    "11014": "Q3",  # 3분기보고서
    "11011": "Q4",  # 사업보고서 (annual)
}

# sj_div 정규 (재무제표 5종). CIS = 포괄손익계산서.
STATEMENT_DIVS = ("BS", "IS", "CIS", "CF", "SCE")

# fs_div: CFS = 연결(consolidated), OFS = 별도(separate/standalone).
_SCOPE_FS = {"consolidated": "CFS", "separate": "OFS"}


def _financePath(code: str) -> Path:
    return Path(_cfg.dataDir) / "dart" / "finance" / f"{code}.parquet"


def _periodExpr() -> pl.Expr:
    """bsns_year + reprt_code → YYYYQn period 컬럼 (sections period 양식 호환)."""
    return (pl.col("bsns_year") + pl.col("reprt_code").replace_strict(_REPRT_QUARTER, default="Q4")).alias("period")


def _amountExpr(col: str) -> pl.Expr:
    """DART 금액 str → Float64. 콤마 strip + 음수(△ / (...)) 정규화. 빈값 → null."""
    cleaned = (
        pl.col(col)
        .cast(pl.Utf8)
        .str.replace_all(",", "")
        .str.replace_all(r"\s", "")
        .str.replace(r"^\((.*)\)$", "-${1}")  # (123) → -123
        .str.replace_all("△", "-")
        .str.replace_all("−", "-")
    )
    return pl.when(cleaned.str.len_chars() == 0).then(None).otherwise(cleaned).cast(pl.Float64, strict=False)


def statementWide(
    code: str,
    sjDiv: str,
    *,
    scope: str = "consolidated",
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """재무제표 정규화 wide 표 (account_nm 행 × period 열).

    Args:
        code: 종목코드.
        sjDiv: "BS"/"IS"/"CIS"/"CF"/"SCE".
        scope: "consolidated"(CFS) / "separate"(OFS).
        marketNs: 시장 (현재 KR 만).

    Returns:
        wide DataFrame (account_id / account_nm + period 열, 금액 Float). 또는 None.
    """
    if marketNs != "kr":
        return None
    p = _financePath(code)
    if not p.exists():
        return None
    fsDiv = _SCOPE_FS.get(scope, "CFS")
    try:
        lf = pl.scan_parquet(str(p)).filter((pl.col("sj_div") == sjDiv) & (pl.col("fs_div") == fsDiv))
        df = lf.with_columns(_periodExpr(), _amountExpr("thstrm_amount").alias("_amt")).collect()
    except (pl.exceptions.PolarsError, OSError) as exc:
        _log.warning("finance read 실패 %s %s: %s", code, sjDiv, exc)
        return None
    if df.is_empty():
        return None
    # account_id + account_nm 로 안정 정렬 (ord 보존), period pivot.
    idx = [c for c in ("account_id", "account_nm") if c in df.columns]
    if not idx:
        return None
    try:
        wide = df.pivot(
            values="_amt",
            index=idx,
            on="period",
            aggregate_function="first",
        )
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("finance pivot 실패 %s %s: %s", code, sjDiv, exc)
        return None
    # period 컬럼 내림차순 (최근 우선).
    pcols = sorted(
        (c for c in wide.columns if c not in idx),
        reverse=True,
    )
    return wide.select(idx + pcols)


def hasFinance(code: str) -> bool:
    """finance parquet 존재 여부."""
    return _financePath(code).exists()
