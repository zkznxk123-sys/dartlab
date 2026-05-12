"""EDGAR companyfacts → 분기별/연도별 시계열 dict 피벗.

정규화 전략:
- IS: duration ≤100일 standalone 직접 선택, 없으면 YTD deaccumulate
- CF: 항상 YTD deaccumulate (Q2=Q2_YTD-Q1, Q3=Q3_YTD-Q2_YTD)
- BS: end 내림차순 최신값 선택
- Q4 = FY - Q1 - Q2 - Q3 역산 (BS 제외)

결과 구조 (DART와 동일)::

    {
        "BS":  {"total_assets": [v1, v2, ...], ...},
        "IS":  {"sales": [...], ...},
        "CF":  {"operating_cashflow": [...], ...},
        "CI":  {"comprehensive_income": [...], ...},
    }

periods = ["2020-Q1", "2020-Q2", ..., "2024-Q4"]
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl

from dartlab.core.utils.ordering import sortSeries
from dartlab.core.utils.period import (
    buildFiscalToCalendarMap,
    extractYear,
    formatPeriod,
    parsePeriod,
)
from dartlab.providers.edgar.finance.mapper import EdgarMapper


def _getEdgarDir() -> Path:
    from dartlab.core.dataLoader import _dataDir

    return _dataDir("edgar")


def buildTimeseries(
    cik: str,
    *,
    edgarDir: Path | None = None,
) -> Optional[tuple[dict[str, dict[str, list[Optional[float]]]], list[str]]]:
    """EDGAR companyfacts → 분기별 standalone 시계열.

    Args:
        cik: SEC CIK 번호 (예: "0000320193").
        edgarDir: EDGAR 데이터 디렉토리 (None이면 config 기본값).

    Returns:
        (series, periods) 또는 None.
        series = {"BS": {"snakeId": [값...]}, "IS": {...}, "CF": {...}, "CI": {...}}
        periods = ["2020-Q1", "2020-Q2", ..., "2024-Q4"]

    Raises:
        없음.

    Example:
        >>> buildTimeseries("0000320193")
    """
    if edgarDir is None:
        edgarDir = _getEdgarDir()
    df = _loadFacts(edgarDir, cik)
    if df is None or df.height == 0:
        return None

    return _buildTimeseriesFromFacts(df)


def _buildTimeseriesFromFacts(
    df: pl.DataFrame,
) -> tuple[dict[str, dict[str, list[Optional[float]]]], list[str]]:
    stmtDfs = _splitStmtFacts(df)

    # period 라벨 = end_date 기반 캘린더 앵커링 (Capital IQ 규칙).
    # `core/finance/period.py::buildFiscalToCalendarMap` SSOT 적용.
    # 12월 결산 기업(MNST/INTC/CPNG/OKLO 등) 은 identity — 효과 없음.
    # 비-12월 결산(UAA 3월·NKE 5월·AAPL 9월) 은 fy/fp → end-month CY 매핑.
    # 4 비교 가능성 (회사간 비교) 의 근본 — DART(Dec) ↔ EDGAR cross-company join 가능.
    fiscalToCal = buildFiscalToCalendarMap(df)

    series: dict[str, dict[str, dict[str, float]]] = {"BS": {}, "IS": {}, "CF": {}, "CI": {}}
    sidSource: dict[str, dict[str, dict[str, str]]] = {"BS": {}, "IS": {}, "CF": {}, "CI": {}}
    allPeriods: set[str] = set()

    for stmt, stmtDf in stmtDfs.items():
        selected = _selectStandalone(stmtDf, stmt)
        if selected.height == 0:
            continue

        pivoted = _pivotTimeseries(selected)
        pivoted = _computeQ4(pivoted, stmt)
        # post-pivot column rename: fiscal → calendar
        if fiscalToCal:
            # NVDA 같이 결산월 변경 이력 있는 기업은 fiscal `2010-Q2` / `2010-Q3`
            # 가 같은 calendar 로 중복 매핑될 수 있음. 먼저 등장한 fiscal 만 rename.
            existingCols = set(pivoted.columns)
            claimedTargets: set[str] = set()
            renameMap: dict[str, str] = {}
            for c in pivoted.columns:
                tgt = fiscalToCal.get(c)
                if tgt is None or tgt == c or tgt in existingCols or tgt in claimedTargets:
                    continue
                renameMap[c] = tgt
                claimedTargets.add(tgt)
            if renameMap:
                pivoted = pivoted.rename(renameMap)

        periodCols = [c for c in pivoted.columns if c != "tag"]

        for row in pivoted.iter_rows(named=True):
            tag = row["tag"]
            dartSid = EdgarMapper.mapToDart(tag, stmt)
            if dartSid is None:
                continue

            # NT(주석) 상세 항목은 IS/BS/CF 본문에서 제외
            if dartSid.endswith("_detail") or dartSid.endswith("_note"):
                continue

            # snakeId의 정식 stmt와 현재 stmt가 다르면 제외 (BS 항목이 IS에 섞이는 것 방지)
            # 단, _change 접미사(운전자본 변동)는 CF에서 정당하므로 예외
            if not dartSid.endswith("_change"):
                canonStmt = EdgarMapper.getAccountStmt(dartSid)
                if canonStmt and canonStmt in ("BS", "IS", "CF", "CI", "EQ", "NT") and canonStmt != stmt:
                    continue

            isCommon = EdgarMapper.isCommonTag(tag)

            for p in periodCols:
                if "-FY" in p:
                    continue
                val = row.get(p)
                if val is not None:
                    allPeriods.add(p)
                    _storeMappedValue(series[stmt], sidSource[stmt], dartSid, p, val, isCommon)

    periods = _sortPeriods(allPeriods)
    nPeriods = len(periods)
    periodIdx = {p: i for i, p in enumerate(periods)}

    result: dict[str, dict[str, list[Optional[float]]]] = {"BS": {}, "IS": {}, "CF": {}, "CI": {}}
    for stmt in series:
        for sid, pMap in series[stmt].items():
            vals: list[Optional[float]] = [None] * nPeriods
            for p, v in pMap.items():
                idx = periodIdx.get(p)
                if idx is not None:
                    vals[idx] = v
            result[stmt][sid] = vals

    _computeEquity(result, periods)
    _computeDerived(result, periods)

    # SNAKEID_ALIASES 양방향 확장 — canonical · alias 둘 다 series 에 노출.
    # `core/finance/helpers.py::toDictBySnakeId` 의 fixpoint 루프와 동일 패턴 (SSOT).
    # 예: mapper 가 "Assets" → "assets" 로 normalize 해도 소비자 (story · test) 가
    # "total_assets" 로 접근 가능하도록 복제.
    from dartlab.core.utils.labels import SNAKEID_ALIASES

    for stmtMap in result.values():
        for _ in range(4):  # transitive chain (A→B→C) 해소용 fixpoint
            changed = False
            for alias, canonical in SNAKEID_ALIASES.items():
                canonRow = stmtMap.get(canonical)
                aliasRow = stmtMap.get(alias)
                if canonRow is not None and aliasRow is None:
                    stmtMap[alias] = canonRow
                    changed = True
                elif aliasRow is not None and canonRow is None:
                    stmtMap[canonical] = aliasRow
                    changed = True
            if not changed:
                break

    sortSeries(result)

    return result, periods


def buildAnnual(
    cik: str,
    *,
    edgarDir: Path | None = None,
) -> Optional[tuple[dict[str, dict[str, list[Optional[float]]]], list[str]]]:
    """EDGAR companyfacts → 연도별 시계열.

    IS/CF: 해당 연도 분기별 standalone 합산 (4분기 필수).
           4분기 미만이면 FY 직접값 폴백.
    BS: 해당 연도 마지막 분기 시점잔액.

    Args:
        cik: SEC CIK 번호.
        edgarDir: EDGAR 데이터 디렉토리 (None이면 config 기본값).

    Returns:
        (series, years) 또는 None.

    Raises:
        없음.

    Example:
        >>> buildAnnual("0000320193")
    """
    if edgarDir is None:
        edgarDir = _getEdgarDir()
    df = _loadFacts(edgarDir, cik)
    if df is None or df.height == 0:
        return None

    qResult = _buildTimeseriesFromFacts(df)
    qSeries, qPeriods = qResult

    # FY 직접값 맵 구축 (분기 합산 실패 시 폴백)
    fyMap = _buildFyMap(df)

    yearSet: dict[str, list[int]] = {}
    for i, p in enumerate(qPeriods):
        year = extractYear(p)
        yearSet.setdefault(year, []).append(i)
    for stmtMap in fyMap.values():
        for yearMap in stmtMap.values():
            for year in yearMap:
                yearSet.setdefault(year, [])

    years = sorted(yearSet.keys())
    nYears = len(years)
    yearIdx = {y: i for i, y in enumerate(years)}

    result: dict[str, dict[str, list[Optional[float]]]] = {"BS": {}, "IS": {}, "CF": {}, "CI": {}}

    for sjDiv in result:
        snakeIds = set(qSeries.get(sjDiv, {}).keys())
        snakeIds.update(fyMap.get(sjDiv, {}).keys())

        for snakeId in snakeIds:
            # _detail/_note는 IS/BS/CF 본문에서 제외
            if snakeId.endswith("_detail") or snakeId.endswith("_note"):
                continue
            # canonStmt 검증 — BS 항목이 IS에 섞이는 것 방지
            if not snakeId.endswith("_change"):
                canonStmt = EdgarMapper.getAccountStmt(snakeId)
                if canonStmt and canonStmt in ("BS", "IS", "CF", "CI", "EQ", "NT") and canonStmt != sjDiv:
                    continue
            vals = qSeries.get(sjDiv, {}).get(snakeId, [])
            annual: list[Optional[float]] = [None] * nYears

            for year, qIndices in yearSet.items():
                yIdx = yearIdx[year]

                if sjDiv == "BS":
                    if qIndices:
                        lastIdx = max(qIndices)
                        annual[yIdx] = vals[lastIdx] if lastIdx < len(vals) else None
                else:
                    qVals = [vals[qi] for qi in qIndices if qi < len(vals) and vals[qi] is not None]
                    if len(qVals) >= 4:
                        annual[yIdx] = sum(qVals)
                    else:
                        # FY 직접값 폴백
                        fyVal = fyMap.get(sjDiv, {}).get(snakeId, {}).get(year)
                        annual[yIdx] = fyVal

            result[sjDiv][snakeId] = annual

    return result, years


def _buildFyMap(
    df: pl.DataFrame,
) -> dict[str, dict[str, dict[str, float]]]:
    """raw companyfacts에서 FY 직접값을 annual 폴백 맵으로 구축."""
    stmtDfs = _splitStmtFacts(df)
    fyMap: dict[str, dict[str, dict[str, float]]] = {"IS": {}, "CF": {}, "CI": {}}
    sidSource: dict[str, dict[str, dict[str, str]]] = {"IS": {}, "CF": {}, "CI": {}}

    for stmt in ["IS", "CF", "CI"]:
        stmtDf = stmtDfs.get(stmt)
        if stmtDf is None or stmtDf.height == 0:
            continue

        selected = _selectStandalone(stmtDf, stmt)
        if selected.height == 0:
            continue
        annualRows = selected.filter(pl.col("period").str.ends_with("-FY"))
        if annualRows.height == 0:
            continue

        for row in annualRows.iter_rows(named=True):
            tag = row["tag"]
            dartSid = EdgarMapper.mapToDart(tag, stmt)
            if dartSid is None:
                continue
            period = row["period"]
            year = extractYear(period)
            val = row["val"]
            if val is None:
                continue
            _storeMappedValue(fyMap[stmt], sidSource[stmt], dartSid, year, val, EdgarMapper.isCommonTag(tag))

    return fyMap


def _splitStmtFacts(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """XBRL fact 를 sj_div (BS/IS/CF/CI) 로 분류 + USD only 필터.

    XBRL ``unit`` 컬럼이 USD/USDshare/share/USDxshares/pure 등 혼합. 같은 tag 에
    다른 unit 의 entry 가 있을 경우 (소수) 잘못된 합산 위험. 통화성 stmt (BS/IS/CF/CI)
    는 USD only 로 필터링.
    """
    # XBRL unit 정규화 (USD only).
    # USD/shares(EPS)·shares·pure 등 은 통화 재무제표에 섞이면 스케일 오염 →
    # 별도 경로로 처리 (pivot 밖). test_l2Coverage 의 basic/diluted_earnings_per_share
    # 는 별도 EPS 전용 빌더가 필요 (follow-up).
    if "unit" in df.columns:
        df = df.filter(pl.col("unit") == "USD")
    if df.height == 0:
        return {}

    stmtTags = EdgarMapper.classifyTagsByStmt()

    # standardAccounts의 stmt가 가장 정확 — 태그별 1개 stmt만 배정
    primaryStmt = EdgarMapper.getPrimaryStmtMap()  # tag → stmt (1:1)

    allTags = df.select("tag").unique().to_series().to_list()
    tagToStmt: dict[str, str] = {}
    for tag in allTags:
        # 1순위: standardAccounts의 primary stmt (정확)
        if tag in primaryStmt:
            tagToStmt[tag] = primaryStmt[tag]
        # 2순위: classifyTagsByStmt (충돌 가능 — 첫 번째만)
        elif tag in {t for tags in stmtTags.values() for t in tags}:
            for stmt in ["IS", "BS", "CF", "CI"]:
                if tag in stmtTags.get(stmt, set()):
                    tagToStmt[tag] = stmt
                    break
        # 3순위: 휴리스틱 (None이면 제외)
        else:
            guessed = _guessStmt(tag)
            if guessed:
                tagToStmt[tag] = guessed

    stmtDfs: dict[str, pl.DataFrame] = {}
    for stmt in ["IS", "BS", "CF", "CI"]:
        stmtTagList = [t for t, s in tagToStmt.items() if s == stmt]
        if not stmtTagList:
            continue
        stmtDf = df.filter(pl.col("tag").is_in(stmtTagList))
        if stmtDf.height > 0:
            stmtDfs[stmt] = stmtDf
    return stmtDfs


def _storeMappedValue(
    stmtValues: dict[str, dict[str, float]],
    stmtSources: dict[str, dict[str, str]],
    dartSid: str,
    period: str,
    value: float,
    isCommon: bool,
) -> None:
    if dartSid not in stmtValues:
        stmtValues[dartSid] = {}
        stmtSources[dartSid] = {}

    prevSource = stmtSources.get(dartSid, {}).get(period)
    if prevSource is None or (prevSource == "learned" and isCommon):
        stmtValues[dartSid][period] = value
        stmtSources.setdefault(dartSid, {})[period] = "common" if isCommon else "learned"


def _loadFacts(edgarDir: Path, cik: str) -> Optional[pl.DataFrame]:
    path = edgarDir / f"{cik}.parquet"
    if not path.exists():
        path = _autoDownloadEdgarFinance(cik, path)
        if path is None:
            return None
    df = pl.read_parquet(path)
    return df.filter(pl.col("namespace") == "us-gaap")


def _autoDownloadEdgarFinance(cik: str, dest: Path) -> Optional[Path]:
    """SEC EDGAR companyfacts API에서 재무 데이터를 자동 다운로드."""
    from urllib.error import URLError

    from dartlab.core.messaging import emit

    emit("edgar:sec_download", cik=cik)
    try:
        from dartlab.providers.edgar.openapi.facts import (
            companyFactsToRows,
            getCompanyFactsJson,
        )

        payload = getCompanyFactsJson(cik)
        df = companyFactsToRows(payload)
        if df.is_empty():
            emit("edgar:empty", cik=cik)
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(dest)
        emit("edgar:save_done", path=str(dest))
        return dest
    except (URLError, OSError, RuntimeError) as e:
        emit("edgar:download_failed", cik=cik, error=str(e))
        return None


def _guessStmt(tag: str) -> str | None:
    """XBRL 태그명에서 재무제표 유형을 추정. 매칭 없으면 None (IS에 넣지 않음)."""
    tagLower = tag.lower()

    # CF 키워드 (가장 명확)
    cfKeywords = [
        "cashflow",
        "cash_flow",
        "netcash",
        "payment",
        "proceeds",
        "repayment",
        "issuance",
        "capex",
        "purchaseof",
        "saleof",
    ]
    for kw in cfKeywords:
        if kw in tagLower:
            return "CF"

    # IS 키워드 (명시적으로만)
    isKeywords = [
        "revenue",
        "sales",
        "costofgood",
        "costofrevenue",
        "grossprofit",
        "operatingincome",
        "operatingexpense",
        "sellinggeneral",
        "researchand",
        "interestexpense",
        "incometax",
        "netincome",
        "earningspershare",
        "dilutedearnings",
        "basicearnings",
        "operatingloss",
        "netloss",
        "otheroperating",
        "comprehensiveincome",
    ]
    for kw in isKeywords:
        if kw in tagLower:
            return "IS"

    # BS 키워드
    bsKeywords = [
        "asset",
        "liabilit",
        "equity",
        "receivable",
        "payable",
        "inventory",
        "inventories",
        "cash",
        "debt",
        "borrowing",
        "goodwill",
        "intangible",
        "property",
        "plant",
        "deferred",
        "accruedliabilit",
        "leasecurrent",
        "leasenoncurrent",
        "retainedearning",
        "treasurystock",
        "commonstock",
    ]
    for kw in bsKeywords:
        if kw in tagLower:
            return "BS"

    # detail/note 패턴은 NT(주석) → IS/BS/CF에 넣지 않음
    if "detail" in tagLower or "note" in tagLower:
        return None

    # 매칭 없으면 None — IS에 쓰레기가 들어가는 것을 방지
    return None


def _selectStandalone(df: pl.DataFrame, stmtType: str) -> pl.DataFrame:
    # frame.is_null() 필터 제거 — downstream(_selectFlowDirect 등)이
    # duration_days 기반으로 standalone/YTD를 정확히 구분한다.
    # frame이 있는 행(CY2025, CY2025Q2 등)도 standalone일 수 있으므로
    # 여기서 미리 제거하면 Q2/Q3/FY 데이터가 누락된다.
    tagDf = df.filter(pl.col("fp").is_in(["Q1", "Q2", "Q3", "FY"]))

    if tagDf.height == 0:
        return pl.DataFrame()

    tagDf = tagDf.with_columns((pl.col("fy").cast(pl.Utf8) + "-" + pl.col("fp")).alias("period"))

    if stmtType == "BS":
        return _selectBS(tagDf)
    elif stmtType == "CF":
        return _selectFlowYTD(tagDf)
    else:
        return _selectFlowDirect(tagDf)


def _selectBS(tagDf: pl.DataFrame) -> pl.DataFrame:
    """BS 시점잔액 선택.

    각 (tag, period)에서 해당 fiscal period에 맞는 end date 값을 선택.
    multiEnd 혼합 방지: 같은 (tag, fy, fp)에 end가 여러 개면
    fp의 기대 월(Q1→3월, Q2→6월, Q3→9월, FY→12월)에 가장 가까운 end를 선택.
    """
    if tagDf.height == 0:
        return pl.DataFrame(schema={"tag": pl.Utf8, "period": pl.Utf8, "val": pl.Float64})

    hasEnd = tagDf.filter(pl.col("end").is_not_null())
    if hasEnd.height == 0:
        return _selectByLatestPeriod(tagDf)

    # frame이 있으면 우선 (정확한 기간 데이터)
    hasFrame = hasEnd.filter(pl.col("frame").is_not_null())
    noFrame = hasEnd.filter(pl.col("frame").is_null())

    if hasFrame.height > 0:
        # frame 있는 것 우선, 없으면 frame 없는 것으로 보충
        frameResult = (
            hasFrame.sort(["end", "filed"], descending=[True, True])
            .group_by(["tag", "period"])
            .agg(pl.col("val").first().alias("val"))
        )
        if noFrame.height > 0:
            noFrameResult = (
                noFrame.sort(["end", "filed"], descending=[True, True])
                .group_by(["tag", "period"])
                .agg(pl.col("val").first().alias("val"))
            )
            # frame 결과에 없는 (tag, period)만 보충
            supplement = noFrameResult.join(frameResult, on=["tag", "period"], how="anti")
            if supplement.height > 0:
                return pl.concat([frameResult, supplement])
        return frameResult

    return (
        hasEnd.sort(["end", "filed"], descending=[True, True])
        .group_by(["tag", "period"])
        .agg(pl.col("val").first().alias("val"))
    )


def _selectByLatestPeriod(df: pl.DataFrame) -> pl.DataFrame:
    if df.height == 0:
        return pl.DataFrame(schema={"tag": pl.Utf8, "period": pl.Utf8, "val": pl.Float64})

    hasEnd = df.filter(pl.col("end").is_not_null())
    if hasEnd.height > 0:
        return (
            hasEnd.sort(["end", "filed"], descending=[True, True])
            .group_by(["tag", "period"])
            .agg(pl.col("val").first().alias("val"))
        )

    return df.sort("filed", descending=True).group_by(["tag", "period"]).agg(pl.col("val").first().alias("val"))


def _computeDurationDays(tagDf: pl.DataFrame) -> pl.DataFrame:
    return tagDf.with_columns(
        pl.when(pl.col("start").is_not_null() & pl.col("end").is_not_null())
        .then((pl.col("end") - pl.col("start")).dt.total_days())
        .otherwise(pl.lit(None))
        .alias("duration_days")
    )


def _selectFlowDirect(tagDf: pl.DataFrame) -> pl.DataFrame:
    tagDf = _computeDurationDays(tagDf)

    # FY: 연간(300d+)만 선택 — 10-K 비교재무제표에 포함된 90일 standalone 제외
    fyRows = tagDf.filter(
        (pl.col("fp") == "FY") & pl.col("duration_days").is_not_null() & (pl.col("duration_days") > 300)
    )
    fyResult = _selectByLatestPeriod(fyRows)

    q1Rows = tagDf.filter(pl.col("fp") == "Q1")
    q1Result = _selectByLatestPeriod(q1Rows)

    q2q3Standalone = tagDf.filter(
        pl.col("fp").is_in(["Q2", "Q3"]) & pl.col("duration_days").is_not_null() & (pl.col("duration_days") <= 100)
    )
    q2q3Result = _selectByLatestPeriod(q2q3Standalone)

    parts = [df for df in [fyResult, q1Result, q2q3Result] if df.height > 0]
    result = pl.concat(parts) if parts else pl.DataFrame(schema={"tag": pl.Utf8, "period": pl.Utf8, "val": pl.Float64})

    missingPeriods = _findMissingQuarters(tagDf, result)
    if missingPeriods.height > 0:
        ytdFallback = _ytdDeaccumulate(tagDf, missingPeriods)
        if ytdFallback.height > 0:
            result = pl.concat([result, ytdFallback])

    return result


def _selectFlowYTD(tagDf: pl.DataFrame) -> pl.DataFrame:
    tagDf = _computeDurationDays(tagDf)

    # FY: 연간(300d+)만, Q1: duration 무관 (항상 ~90d)
    fyRows = tagDf.filter(
        (pl.col("fp") == "FY") & pl.col("duration_days").is_not_null() & (pl.col("duration_days") > 300)
    )
    q1Rows = tagDf.filter(pl.col("fp") == "Q1")
    fyQ1 = (
        pl.concat([fyRows, q1Rows])
        if fyRows.height > 0 or q1Rows.height > 0
        else tagDf.filter(pl.col("fp").is_in(["FY", "Q1"]))
    )
    fyQ1Result = _selectByLatestPeriod(fyQ1)

    q2q3Ytd = tagDf.filter(
        pl.col("fp").is_in(["Q2", "Q3"]) & pl.col("duration_days").is_not_null() & (pl.col("duration_days") > 100)
    )

    q2q3Result = (
        q2q3Ytd.sort(["end", "filed"], descending=[True, True])
        .group_by(["tag", "fy", "fp"])
        .agg(pl.col("val").first().alias("ytd_val"))
    )

    deaccumulated = _deaccumulateCF(fyQ1Result, q2q3Result)
    return pl.concat([fyQ1Result, deaccumulated])


def _deaccumulateCF(
    fyQ1Result: pl.DataFrame,
    q2q3Ytd: pl.DataFrame,
) -> pl.DataFrame:
    rows = []
    q1Map: dict[tuple[str, str], float] = {}
    for row in fyQ1Result.iter_rows(named=True):
        period = row["period"]
        if period.endswith("-Q1"):
            q1Map[(row["tag"], extractYear(period))] = row["val"]

    ytdMap: dict[tuple[str, str, str], float] = {}
    for row in q2q3Ytd.iter_rows(named=True):
        key = (row["tag"], str(row["fy"]), row["fp"])
        ytdMap[key] = row["ytd_val"]

    revTags = EdgarMapper.getTagsForSnakeIds(["sales", "revenue"])
    for (tag, fy, fp), ytdVal in ytdMap.items():
        if fp == "Q2":
            q1Val = q1Map.get((tag, fy))
            if q1Val is not None and ytdVal is not None:
                standalone = ytdVal - q1Val
                if standalone < 0 and tag in revTags:
                    continue
                rows.append({"tag": tag, "period": formatPeriod(fy, 2), "val": standalone})
        elif fp == "Q3":
            q2YtdVal = ytdMap.get((tag, fy, "Q2"))
            if q2YtdVal is not None and ytdVal is not None:
                standalone = ytdVal - q2YtdVal
                if standalone < 0 and tag in revTags:
                    continue
                rows.append({"tag": tag, "period": formatPeriod(fy, 3), "val": standalone})

    if not rows:
        return pl.DataFrame(schema={"tag": pl.Utf8, "period": pl.Utf8, "val": pl.Float64})
    return pl.DataFrame(rows)


def _findMissingQuarters(tagDf: pl.DataFrame, result: pl.DataFrame) -> pl.DataFrame:
    """Q1~Q3 중 기대되지만 result 에 없는 period 탐색.

    Q1 이 raw 에도 없는 YTD-전용 기업(Google 등) 대응:
    동일 (tag, fy) 에 Q2/Q3/FY 중 하나라도 있으면 Q1/Q2/Q3 모두 기대한다.
    """
    # raw 에 포함된 (tag, period) 조합
    rawPeriods = tagDf.select("tag", "period").unique()

    # (tag, fy) 단위로 Q2/Q3/FY 존재 여부 기반 기대 집합 생성
    tagFy = tagDf.select("tag", "fy").unique()
    # Q2/Q3/FY 중 하나라도 있는 (tag, fy) 만 기대 대상
    seenFp = tagDf.filter(pl.col("fp").is_in(["Q2", "Q3", "FY"])).select("tag", "fy").unique()
    expected = tagFy.join(seenFp, on=["tag", "fy"], how="semi")
    expectedPeriods = pl.concat(
        [
            expected.with_columns((pl.col("fy").cast(pl.Utf8) + pl.lit(f"-{q}")).alias("period")).select(
                "tag", "period"
            )
            for q in ("Q1", "Q2", "Q3")
        ]
    ).unique()

    allPeriods = pl.concat([rawPeriods, expectedPeriods]).unique()
    existingPeriods = result.select("tag", "period").unique()
    missing = allPeriods.join(existingPeriods, on=["tag", "period"], how="anti")
    return missing.filter(pl.col("period").str.contains("Q[123]"))


def _ytdDeaccumulate(tagDf: pl.DataFrame, missingPeriods: pl.DataFrame) -> pl.DataFrame:
    """YTD(누적) 데이터로 standalone 분기값 역산.

    Q1 누락 + Q2/Q3 standalone + Q3_YTD 보유 경우 (Google 같은 YTD-전용 보고 기업):
        Q1 = Q3_YTD - Q2_standalone - Q3_standalone
    Q1 누락 + Q2 standalone + Q2_YTD 경우:
        Q1 = Q2_YTD - Q2_standalone
    Q2 누락 + Q1 standalone + Q2_YTD 경우 (기존):
        Q2 = Q2_YTD - Q1_standalone
    Q3 누락 + Q2_YTD + Q3_YTD 경우 (기존):
        Q3 = Q3_YTD - Q2_YTD
    """
    tagDf = _computeDurationDays(tagDf) if "duration_days" not in tagDf.columns else tagDf

    ytdRows = tagDf.filter(pl.col("duration_days").is_not_null() & (pl.col("duration_days") > 100))
    standaloneRows = tagDf.filter(pl.col("duration_days").is_not_null() & (pl.col("duration_days") <= 100))

    revTags = EdgarMapper.getTagsForSnakeIds(["sales", "revenue"])
    rows = []
    for mpRow in missingPeriods.iter_rows(named=True):
        tag, period = mpRow["tag"], mpRow["period"]
        fy = extractYear(period)
        fp = period.split("-")[1]
        fyInt = int(fy)

        def _firstVal(df: pl.DataFrame) -> float | None:
            if df.height == 0:
                return None
            return df.sort(["end", "filed"], descending=[True, True]).row(0, named=True)["val"]

        if fp == "Q1":
            # 우선 Q2_YTD - Q2_standalone
            q2Ytd = _firstVal(ytdRows.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == "Q2")))
            q2Stand = _firstVal(
                standaloneRows.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == "Q2"))
            )
            standalone: float | None = None
            if q2Ytd is not None and q2Stand is not None:
                standalone = q2Ytd - q2Stand
            else:
                # fallback: Q3_YTD - Q2_standalone - Q3_standalone (GOOGL 케이스)
                q3Ytd = _firstVal(
                    ytdRows.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == "Q3"))
                )
                q3Stand = _firstVal(
                    standaloneRows.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == "Q3"))
                )
                if q3Ytd is not None and q2Stand is not None and q3Stand is not None:
                    standalone = q3Ytd - q2Stand - q3Stand
            if standalone is not None:
                if standalone < 0 and tag in revTags:
                    continue
                rows.append({"tag": tag, "period": period, "val": standalone})
            continue

        candidates = ytdRows.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == fp)).sort(
            ["end", "filed"], descending=[True, True]
        )
        if candidates.height == 0:
            continue
        ytdVal = candidates.row(0, named=True)["val"]

        if fp == "Q2":
            q1Rows = tagDf.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == "Q1")).sort(
                "filed", descending=True
            )
            if q1Rows.height > 0:
                q1Val = q1Rows.row(0, named=True)["val"]
                if q1Val is not None and ytdVal is not None:
                    standalone = ytdVal - q1Val
                    if standalone < 0 and tag in revTags:
                        continue
                    rows.append({"tag": tag, "period": period, "val": standalone})

        elif fp == "Q3":
            q2YtdRows = ytdRows.filter((pl.col("tag") == tag) & (pl.col("fy") == fyInt) & (pl.col("fp") == "Q2")).sort(
                ["end", "filed"], descending=[True, True]
            )
            if q2YtdRows.height > 0:
                q2YtdVal = q2YtdRows.row(0, named=True)["val"]
                if q2YtdVal is not None and ytdVal is not None:
                    standalone = ytdVal - q2YtdVal
                    if standalone < 0 and tag in revTags:
                        continue
                    rows.append({"tag": tag, "period": period, "val": standalone})

    if not rows:
        return pl.DataFrame(schema={"tag": pl.Utf8, "period": pl.Utf8, "val": pl.Float64})
    return pl.DataFrame(rows)


def _pivotTimeseries(selected: pl.DataFrame) -> pl.DataFrame:
    if selected.height == 0:
        return pl.DataFrame()

    pivoted = selected.pivot(  # polars-streaming-unsupported: pivot
        on="period",
        index="tag",
        values="val",
        aggregate_function="first",
    )

    periodCols = [c for c in pivoted.columns if c != "tag"]

    def _sortKey(col: str) -> tuple:
        parts = col.split("-")
        if len(parts) == 2:
            fy = int(parts[0])
            fpOrder = {"Q1": 1, "Q2": 2, "Q3": 3, "FY": 5}
            return (fy, fpOrder.get(parts[1], 9))
        return (9999, 9)

    sortedCols = sorted(periodCols, key=_sortKey)
    return pivoted.select(["tag"] + sortedCols)


def _computeQ4(pivoted: pl.DataFrame, stmtType: str) -> pl.DataFrame:
    """Q4 = FY - Q1 - Q2 - Q3 역산. BS는 FY 복사."""
    periodCols = [c for c in pivoted.columns if c != "tag"]
    years = sorted({extractYear(c) for c in periodCols if "-" in c})

    newCols = {}
    for year in years:
        fyCol = f"{year}-FY"
        q4Col = formatPeriod(year, 4)

        if stmtType == "BS":
            if fyCol in pivoted.columns and q4Col not in pivoted.columns:
                newCols[q4Col] = pivoted[fyCol]
        else:
            q1Col = formatPeriod(year, 1)
            q2Col = formatPeriod(year, 2)
            q3Col = formatPeriod(year, 3)
            if all(c in pivoted.columns for c in [fyCol, q1Col, q2Col, q3Col]):
                q4Raw = pivoted[fyCol] - pivoted[q1Col] - pivoted[q2Col] - pivoted[q3Col]
                newCols[q4Col] = q4Raw

    if not newCols:
        return pivoted

    for colName, colData in newCols.items():
        pivoted = pivoted.with_columns(colData.alias(colName))

    # Q4 sanity check: revenue/sales 태그에서 음수 Q4 → None 처리
    pivoted = _sanitizeQ4(pivoted, years)

    allCols = [c for c in pivoted.columns if c != "tag"]

    def _sortKey(col: str) -> tuple:
        parts = col.split("-")
        if len(parts) == 2:
            fy = int(parts[0])
            fpOrder = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "FY": 5}
            return (fy, fpOrder.get(parts[1], 9))
        return (9999, 9)

    sortedCols = sorted(allCols, key=_sortKey)
    return pivoted.select(["tag"] + sortedCols)


def _sanitizeQ4(pivoted: pl.DataFrame, years: list[str]) -> pl.DataFrame:
    """역산된 Q4 sanity check — 같은 연도 Q1~Q3 합 대비 비정상 Q4 제거.

    조건: Q4 < 0이고 |Q4| > Q1~Q3 평균의 2배 → Q4=None (YTD 오염 가능성).
    revenue 계열 태그가 음수면 무조건 None.
    """
    _REVENUE_TAGS = EdgarMapper.getTagsForSnakeIds(["sales", "revenue"])

    tags = pivoted["tag"].to_list()

    for year in years:
        q4Col = formatPeriod(year, 4)
        if q4Col not in pivoted.columns:
            continue
        q1Col = formatPeriod(year, 1)
        q2Col = formatPeriod(year, 2)
        q3Col = formatPeriod(year, 3)

        q4Vals = pivoted[q4Col].to_list()
        hasQ1 = q1Col in pivoted.columns
        hasQ2 = q2Col in pivoted.columns
        hasQ3 = q3Col in pivoted.columns

        nullMask = []
        for i, (tag, q4) in enumerate(zip(tags, q4Vals)):
            shouldNull = False
            if q4 is not None and q4 < 0:
                # revenue 계열은 음수 Q4 무조건 제거
                if tag in _REVENUE_TAGS:
                    shouldNull = True
                else:
                    # 다른 태그: Q1~Q3 평균 대비 비정상 검사
                    qVals = []
                    if hasQ1:
                        v = pivoted[q1Col][i]
                        if v is not None:
                            qVals.append(abs(v))
                    if hasQ2:
                        v = pivoted[q2Col][i]
                        if v is not None:
                            qVals.append(abs(v))
                    if hasQ3:
                        v = pivoted[q3Col][i]
                        if v is not None:
                            qVals.append(abs(v))
                    if qVals:
                        avgQ = sum(qVals) / len(qVals)
                        if avgQ > 0 and abs(q4) > avgQ * 2:
                            shouldNull = True
            nullMask.append(shouldNull)

        if any(nullMask):
            newVals = [None if nullMask[i] else q4Vals[i] for i in range(len(q4Vals))]
            pivoted = pivoted.with_columns(pl.Series(q4Col, newVals))

    return pivoted


def _sortPeriods(periods: set[str]) -> list[str]:
    def _sortKey(p: str) -> tuple:
        try:
            year, q = parsePeriod(p)
            return (int(year), q)
        except (ValueError, IndexError):
            return (9999, 9)

    return sorted(periods, key=_sortKey)


def _computeEquity(
    result: dict[str, dict[str, list[Optional[float]]]],
    periods: list[str],
) -> None:
    nci = result["BS"].get("noncontrolling_interests_equity")
    eqNci = result["BS"].get("total_stockholders_equity")
    teq = result["BS"].get("owners_of_parent_equity")
    redeemNci = result["BS"].get("redeemable_noncontrolling_interest")
    n = len(periods)

    if eqNci is None and teq is not None:
        eqNci = [None] * n
        result["BS"]["total_stockholders_equity"] = eqNci

    if teq is None and eqNci is not None:
        teq = [None] * n
        result["BS"]["owners_of_parent_equity"] = teq

    if eqNci is not None and teq is not None:
        for i in range(n):
            nciVal = (nci[i] or 0) if nci else 0
            if eqNci[i] is None and teq[i] is not None:
                eqNci[i] = teq[i] + nciVal
            if teq[i] is None and eqNci[i] is not None:
                teq[i] = eqNci[i] - nciVal

    assets = result["BS"].get("total_assets")
    if eqNci is not None and redeemNci is not None:
        for i in range(n):
            if eqNci[i] is not None and redeemNci[i] is not None:
                merged = eqNci[i] + redeemNci[i]
                if assets and assets[i] is not None and merged > assets[i]:
                    continue
                if eqNci[i] != 0 and abs(merged) > abs(eqNci[i]) * 2:
                    continue
                eqNci[i] = merged


_DERIVED_FORMULAS = [
    ("BS", "total_liabilities", "total_assets", "total_stockholders_equity", "subtract"),
    ("BS", "total_liabilities", "current_liabilities", "noncurrent_liabilities", "add"),
    ("IS", "gross_profit", "sales", "cost_of_sales", "subtract"),
    ("BS", "noncurrent_assets", "total_assets", "current_assets", "subtract"),
    ("BS", "noncurrent_liabilities", "total_liabilities", "current_liabilities", "subtract"),
]


def _computeDerived(
    result: dict[str, dict[str, list[Optional[float]]]],
    periods: list[str],
) -> None:
    n = len(periods)
    for stmt, target, srcA, srcB, op in _DERIVED_FORMULAS:
        existing = result[stmt].get(target)
        aVals = result[stmt].get(srcA)
        bVals = result[stmt].get(srcB)
        if aVals is None or bVals is None:
            continue

        derived = [None] * n
        filled = False
        for i in range(n):
            if existing is not None and existing[i] is not None:
                continue
            a = aVals[i]
            b = bVals[i]
            if a is None or b is None:
                continue
            derived[i] = (a + b) if op == "add" else (a - b)
            filled = True

        if not filled:
            continue

        if existing is None:
            result[stmt][target] = derived
        else:
            for i in range(n):
                if existing[i] is None and derived[i] is not None:
                    existing[i] = derived[i]


# ── SCE (자본변동표) ─────────────────────────────────────────────

# BS equity 컴포넌트 → SCE cause 매핑
_EQUITY_COMPONENTS: list[tuple[str, str]] = [
    ("common_stock", "Common Stock"),
    ("additional_paid_in_capital", "Additional Paid-in Capital"),
    ("retained_earnings", "Retained Earnings"),
    ("treasury_stock", "Treasury Stock"),
    ("accumulated_other_comprehensive_income", "Accumulated OCI"),
    ("noncontrolling_interests_equity", "Noncontrolling Interest"),
    ("owners_of_parent_equity", "Total Parent Equity"),
    ("total_stockholders_equity", "Total Equity"),
]

# CF equity 거래 → SCE 참고 항목
_EQUITY_TRANSACTIONS: list[tuple[str, str]] = [
    ("dividends_paid", "Dividends Paid"),
    ("stock_repurchase", "Share Repurchase"),
    ("stock_issuance", "Share Issuance"),
    ("stock_compensation", "Stock-Based Compensation"),
]


def buildSce(
    cik: str,
    *,
    edgarDir: Path | None = None,
) -> pl.DataFrame | None:
    """BS equity 컴포넌트 연간 변화 + CF equity 거래로 SCE 구성.

    Args:
        cik: SEC CIK 번호.
        edgarDir: EDGAR 데이터 디렉토리 (None 이면 config 기본).

    Returns:
        DataFrame with columns: component, label, {year columns...}
        각 셀은 해당 연도의 변화량 (당기말 - 전기말). 첫 연도는 None.

    Raises:
        없음.

    Example:
        >>> buildSce("0000320193")
    """
    annual = buildAnnual(cik, edgarDir=edgarDir)
    if annual is None:
        return None

    series, years = annual
    bs = series.get("BS", {})
    cf = series.get("CF", {})
    isStmt = series.get("IS", {})

    rows: list[dict] = []
    len(years)

    # 1. BS equity 컴포넌트 연간 변화량
    for snakeId, label in _EQUITY_COMPONENTS:
        vals = bs.get(snakeId)
        if vals is None:
            continue
        hasData = False
        row: dict = {"component": snakeId, "label": label}
        for i, year in enumerate(years):
            if i == 0:
                row[str(year)] = None
            else:
                prev = vals[i - 1]
                curr = vals[i]
                if prev is not None and curr is not None:
                    row[str(year)] = curr - prev
                    hasData = True
                else:
                    row[str(year)] = None
        if hasData:
            rows.append(row)

    # 2. Net Income (IS)
    netIncome = isStmt.get("net_profit") or isStmt.get("net_income")
    if netIncome is not None:
        row = {"component": "net_income", "label": "Net Income"}
        hasData = False
        for i, year in enumerate(years):
            val = netIncome[i]
            row[str(year)] = val
            if val is not None:
                hasData = True
        if hasData:
            rows.append(row)

    # 3. CF equity 거래
    for snakeId, label in _EQUITY_TRANSACTIONS:
        vals = cf.get(snakeId)
        if vals is None:
            continue
        hasData = False
        row = {"component": snakeId, "label": label}
        for i, year in enumerate(years):
            val = vals[i]
            row[str(year)] = val
            if val is not None:
                hasData = True
        if hasData:
            rows.append(row)

    # 4. OCI (CI statement)
    ci = series.get("CI", {})
    oci = ci.get("other_comprehensive_income") or ci.get("total_other_comprehensive_income")
    if oci is not None:
        row = {"component": "other_comprehensive_income", "label": "Other Comprehensive Income"}
        hasData = False
        for i, year in enumerate(years):
            val = oci[i]
            row[str(year)] = val
            if val is not None:
                hasData = True
        if hasData:
            rows.append(row)

    if not rows:
        return None

    df = pl.DataFrame(rows)
    # 기간 컬럼 역순 정렬 (최신 먼저)
    metaCols = ["component", "label"]
    periodCols = [c for c in df.columns if c not in metaCols]
    periodCols.sort(reverse=True)
    return df.select(metaCols + periodCols)


# ── Shares Outstanding ──────────────────────────────────────────


def getSharesOutstanding(cik: str, *, edgarDir: Path | None = None) -> Optional[int]:
    """SEC DEI 에서 최신 발행주식수 추출.

    Args:
        cik: SEC CIK 번호.
        edgarDir: EDGAR 데이터 디렉토리 (None 이면 config 기본).

    Returns:
        발행주식수 int 또는 None.

    Raises:
        없음.

    Example:
        >>> getSharesOutstanding("0000320193")
    """
    if edgarDir is None:
        edgarDir = _getEdgarDir()
    path = edgarDir / f"{cik}.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    dei = df.filter((pl.col("namespace") == "dei") & (pl.col("tag") == "EntityCommonStockSharesOutstanding"))
    if dei.height == 0:
        return None
    latest = dei.sort("end", descending=True).row(0, named=True)
    val = latest.get("val")
    return int(val) if val is not None else None
