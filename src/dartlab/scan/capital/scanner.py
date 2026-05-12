"""주주환원 3축 report 스캔 — 배당, 자사주, 증자/감자."""

from __future__ import annotations

import polars as pl

from dartlab.scan.io.parquet import (
    parseDateYear,
    parseNumStr,
    scanParquets,
)

# ── 배당 ──

DPS_KEYS = {"주당 현금배당금(원)", "주당현금배당금(원)", "주당현금배당금", "현금배당금(원)"}
YIELD_KEYS = {"현금배당수익률(%)", "현금배당수익률"}
TOTAL_KEYS = {"현금배당금총액(백만원)", "현금배당금총액"}


def scanDividend() -> dict[str, dict]:
    """전종목 배당 스캔.

    최신 연도 Q4 기준. DPS 행이 100개 이상인 연도를 선택.

    Returns
    -------
    dict[str, dict]
        {종목코드: info} 매핑. 각 info:
            배당여부 : bool — DPS > 0 여부
            DPS : float — 주당 현금배당금 (원)
            배당수익률 : float — 현금배당수익률 (%)
            배당총액_백만 : float — 현금배당금 총액 (백만원)

    Raises
    ------
    polars.PolarsError
        dividend report parquet 손상 시.

    Examples
    --------
    >>> from dartlab.scan.capital.scanner import scanDividend
    >>> div = scanDividend()
    >>> div.get("005930", {}).get("DPS")
    """
    raw = scanParquets(
        "dividend",
        ["stockCode", "year", "quarter", "se", "thstrm"],
    )
    if raw.is_empty():
        return {}

    years_desc = sorted(raw["year"].unique().to_list(), reverse=True)
    latest_year = None
    for y in years_desc:
        sub = raw.filter(pl.col("year") == y)
        q4 = sub.filter(pl.col("quarter") == "4분기")
        target = q4 if not q4.is_empty() else sub
        dps_ok = target.filter(
            pl.col("se").is_in(list(DPS_KEYS))
            & pl.col("thstrm").is_not_null()
            & (pl.col("thstrm") != "-")
            & (pl.col("thstrm") != "")
        ).shape[0]
        if dps_ok >= 100:
            latest_year = y
            break
    if latest_year is None:
        return {}

    latest = raw.filter(pl.col("year") == latest_year)
    q4 = latest.filter(pl.col("quarter") == "4분기")
    if not q4.is_empty():
        latest = q4

    result: dict[str, dict] = {}
    for code, group in latest.group_by("stockCode"):
        code_val = code[0]
        dps = None
        div_yield = None
        total_div = None

        for row in group.iter_rows(named=True):
            se = row.get("se", "")
            if not se:
                continue
            val = parseNumStr(row.get("thstrm"))
            if se in DPS_KEYS and val is not None and val > 0:
                if dps is None or val > dps:
                    dps = val
            elif se in YIELD_KEYS and val is not None and val > 0:
                if div_yield is None or val > div_yield:
                    div_yield = val
            elif se in TOTAL_KEYS and val is not None and val > 0:
                total_div = val

        result[code_val] = {
            "배당여부": dps is not None and dps > 0,
            "DPS": dps or 0.0,
            "배당수익률": div_yield or 0.0,
            "배당총액_백만": total_div or 0.0,
        }
    return result


# ── 자사주 ──


def scanTreasuryStock() -> dict[str, dict]:
    """전종목 자사주 스캔.

    Returns
    -------
    dict[str, dict]
        {종목코드: info} 매핑. 각 info:
            자사주보유 : bool — 기말 보유 여부
            당기취득 : bool — 당기 취득 여부
            당기처분 : bool — 당기 처분 여부
            당기소각 : bool — 당기 소각 여부
            취득수량 : int — 당기 취득 주식수 (주)
            처분수량 : int — 당기 처분 주식수 (주)
            소각수량 : int — 당기 소각 주식수 (주)

    Raises
    ------
    polars.PolarsError
        treasuryStock report parquet 손상 시.

    Examples
    --------
    >>> from dartlab.scan.capital.scanner import scanTreasuryStock
    >>> ts = scanTreasuryStock()
    >>> ts.get("005930", {}).get("자사주보유")
    """
    raw = scanParquets(
        "treasuryStock",
        ["stockCode", "year", "quarter", "trmend_qy", "change_qy_acqs", "change_qy_dsps", "change_qy_incnr"],
    )
    if raw.is_empty():
        return {}

    years_desc = sorted(raw["year"].unique().to_list(), reverse=True)
    latest_year = None
    for y in years_desc:
        sub = raw.filter(pl.col("year") == y)
        ok = sub.filter(pl.col("trmend_qy").is_not_null() & (pl.col("trmend_qy") != "-")).shape[0]
        if ok >= 300:
            latest_year = y
            break
    if latest_year is None:
        return {}

    latest = raw.filter(pl.col("year") == latest_year)
    result: dict[str, dict] = {}
    for code, group in latest.group_by("stockCode"):
        code_val = code[0]
        total_held = 0
        total_acqs = 0
        total_dsps = 0
        total_incnr = 0
        for row in group.iter_rows(named=True):
            held = parseNumStr(row.get("trmend_qy"))
            acqs = parseNumStr(row.get("change_qy_acqs"))
            dsps = parseNumStr(row.get("change_qy_dsps"))
            incnr = parseNumStr(row.get("change_qy_incnr"))
            if held and held > 0:
                total_held += int(held)
            if acqs and acqs > 0:
                total_acqs += int(acqs)
            if dsps and dsps > 0:
                total_dsps += int(dsps)
            if incnr and incnr > 0:
                total_incnr += int(incnr)
        result[code_val] = {
            "자사주보유": total_held > 0,
            "당기취득": total_acqs > 0,
            "당기처분": total_dsps > 0,
            "당기소각": total_incnr > 0,
            "취득수량": total_acqs,
            "처분수량": total_dsps,
            "소각수량": total_incnr,
        }
    return result


# ── 증자/감자 ──

INCREASE_TYPES = {
    "유상증자(주주배정)",
    "유상증자(제3자배정)",
    "유상증자(일반공모)",
    "전환권행사",
    "신주인수권행사",
    "주식매수선택권행사",
    "무상증자",
}


def scanCapitalChange() -> dict[str, dict]:
    """전종목 증자/감자 스캔.

    최근 3년(2023~) 이내 증자(INCREASE_TYPES) 여부.

    Returns
    -------
    dict[str, dict]
        {종목코드: info} 매핑. 각 info:
            최근증자 : bool — 최근 3년 내 증자 여부

    Raises
    ------
    polars.PolarsError
        capitalChange report parquet 손상 시.

    Examples
    --------
    >>> from dartlab.scan.capital.scanner import scanCapitalChange
    >>> cc = scanCapitalChange()
    >>> cc.get("005930", {}).get("최근증자")
    """
    raw = scanParquets(
        "capitalChange",
        ["stockCode", "year", "quarter", "isu_dcrs_stle", "isu_dcrs_de"],
    )
    if raw.is_empty():
        return {}

    valid = raw.filter(
        pl.col("isu_dcrs_stle").is_not_null() & (pl.col("isu_dcrs_stle") != "-") & (pl.col("isu_dcrs_stle") != "")
    )

    result: dict[str, dict] = {}
    for code, group in valid.group_by("stockCode"):
        code_val = code[0]
        recentIncrease = False
        for row in group.iter_rows(named=True):
            stle = row.get("isu_dcrs_stle", "")
            event_year = parseDateYear(row.get("isu_dcrs_de"))
            if stle in INCREASE_TYPES and event_year and event_year >= 2023:
                recentIncrease = True
                break
        result[code_val] = {"최근증자": recentIncrease}
    return result
