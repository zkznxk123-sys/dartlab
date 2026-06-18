"""Build current-data hard-negative search gold rows from the source catalog.

The output is candidate gold by default. Use ``--mark-reviewed`` only after an
operator has reviewed the generated pairs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DEFAULT_LIMIT = 300
DEFAULT_PER_TYPE = 80
DEFAULT_NO_ANSWER_ROWS = 0
CURRENT_DATA_ORIGIN = "currentDataHardNegative"
NO_ANSWER_BASE_ROLES = (
    "rightsOffering",
    "treasuryAcquire",
    "treasuryDispose",
    "dividend",
    "ceoChange",
    "largestShareholder",
    "shareholderMeeting",
    "supplyContract",
    "merger",
    "split",
    "assetAcquire",
    "assetDispose",
    "lawsuit",
    "embezzlement",
    "tradingHalt",
)


@dataclass(frozen=True)
class CatalogRow:
    source: str
    sourceKind: str
    sourceRef: str
    companyName: str
    stockCode: str
    ticker: str
    companyKey: str
    date: str
    year: str
    reportName: str
    title: str
    sourceDataAsOf: str
    baseRole: str
    eventRole: str
    roleLabel: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, help="Source catalog parquet path.")
    parser.add_argument("--out", required=True, help="Output JSONL candidate gold path.")
    parser.add_argument("--summary-out", help="Output summary JSON path.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--per-type", type=int, default=DEFAULT_PER_TYPE)
    parser.add_argument(
        "--no-answer-rows",
        type=int,
        default=DEFAULT_NO_ANSWER_ROWS,
        help="Append catalog-derived noAnswer traps. These do not replace answerable hard-negative rows.",
    )
    parser.add_argument(
        "--mark-reviewed",
        action="store_true",
        help="Write goldOrigin=operator/reviewStatus=reviewed. Use only after operator review.",
    )
    args = parser.parse_args(argv)

    rows = loadCatalogRows(Path(args.catalog))
    goldRows = buildHardNegativeGold(
        rows,
        limit=args.limit,
        perType=args.per_type,
        noAnswerRows=args.no_answer_rows,
        markReviewed=args.mark_reviewed,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in goldRows),
        encoding="utf-8",
    )
    summary = buildSummary(goldRows, catalogPath=Path(args.catalog), catalogRows=len(rows))
    if args.summary_out:
        summaryOut = Path(args.summary_out)
        summaryOut.parent.mkdir(parents=True, exist_ok=True)
        summaryOut.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if goldRows else 1


def loadCatalogRows(path: Path) -> list[CatalogRow]:
    schema = pl.scan_parquet(path).collect_schema()
    lf = pl.scan_parquet(path).select(
        [
            _column(schema, ("source",), "source"),
            _column(schema, ("sourceRef",), "sourceRef"),
            _column(schema, ("companyName", "corp_name"), "companyName"),
            _column(schema, ("stockCode", "stock_code"), "stockCode"),
            _column(schema, ("ticker",), "ticker"),
            _column(schema, ("date", "rcept_dt"), "date"),
            _column(schema, ("reportName", "report_nm"), "reportName"),
            _column(schema, ("title", "section_title"), "title"),
            _column(schema, ("sourceDataAsOf",), "sourceDataAsOf"),
        ]
    )
    df = (
        lf.filter(pl.col("sourceRef").str.len_chars() > 0)
        .sort(["date", "sourceRef"], descending=[True, False])
        .collect(engine="streaming")
    )
    out: list[CatalogRow] = []
    seenRefs: set[str] = set()
    for item in df.iter_rows(named=True):
        sourceRef = _clean(item.get("sourceRef"))
        if not sourceRef or sourceRef in seenRefs:
            continue
        seenRefs.add(sourceRef)
        source = _clean(item.get("source"))
        sourceKind = _sourceKind(source)
        companyName = _clean(item.get("companyName"))
        stockCode = _clean(item.get("stockCode"))
        ticker = _clean(item.get("ticker")).upper()
        date = _digits(_clean(item.get("date")))[:8]
        year = date[:4]
        reportName = _clean(item.get("reportName"))
        title = _clean(item.get("title"))
        companyKey = stockCode or ticker or companyName or (sourceRef if sourceKind == "news" else "")
        if not year or not companyKey:
            continue
        baseRole, eventRole, roleLabel = inferEventRole(" ".join([reportName, title]))
        out.append(
            CatalogRow(
                source=source,
                sourceKind=sourceKind,
                sourceRef=sourceRef,
                companyName=companyName,
                stockCode=stockCode,
                ticker=ticker,
                companyKey=companyKey,
                date=date,
                year=year,
                reportName=reportName,
                title=title,
                sourceDataAsOf=_clean(item.get("sourceDataAsOf")),
                baseRole=baseRole,
                eventRole=eventRole,
                roleLabel=roleLabel,
            )
        )
    return out


def buildHardNegativeGold(
    rows: list[CatalogRow],
    *,
    limit: int = DEFAULT_LIMIT,
    perType: int = DEFAULT_PER_TYPE,
    noAnswerRows: int = DEFAULT_NO_ANSWER_ROWS,
    markReviewed: bool = False,
) -> list[dict[str, Any]]:
    indexes = buildIndexes(rows)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    seenQueries: set[str] = set()
    builders = (
        buildSameCompanyDifferentYear,
        buildSameCompanySiblingFiling,
        buildSimilarEventOtherCompany,
        buildReportTypeMismatch,
        buildNewsFilingConfusion,
        buildFilingNewsConfusion,
        buildEdgarDartConfusion,
        buildPanelFilingConfusion,
    )
    noAnswerLimit = max(0, min(noAnswerRows, limit))
    answerableLimit = max(0, limit - noAnswerLimit)
    perCategory = max(perType, math.ceil(max(1, answerableLimit) / max(1, len(builders))))
    buckets = [builder(rows, indexes, perCategory) for builder in builders]
    _appendBuckets(out, seen, seenQueries, buckets, limit=answerableLimit, markReviewed=markReviewed)
    if len(out) < limit and noAnswerLimit:
        noAnswerBucket = buildNoAnswerGold(rows, indexes, noAnswerLimit)
        _appendBuckets(out, seen, seenQueries, [noAnswerBucket], limit=limit, markReviewed=markReviewed)
    return out[:limit]


def _appendBuckets(
    out: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    seenQueries: set[str],
    buckets: list[list[dict[str, Any]]],
    *,
    limit: int,
    markReviewed: bool,
) -> None:
    if limit <= len(out):
        return
    for bucket in buckets:
        if bucket:
            _appendGold(out, seen, seenQueries, bucket[0], markReviewed=markReviewed)
            if len(out) >= limit:
                return
    maxBucket = max((len(bucket) for bucket in buckets), default=0)
    for index in range(1, maxBucket):
        for bucket in buckets:
            if index >= len(bucket):
                continue
            _appendGold(out, seen, seenQueries, bucket[index], markReviewed=markReviewed)
            if len(out) >= limit:
                return


def _appendGold(
    out: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    seenQueries: set[str],
    row: dict[str, Any],
    *,
    markReviewed: bool,
) -> None:
    query = str(row.get("query") or "").strip()
    if not query or query in seenQueries:
        return
    key = (
        str(row["hardNegativeType"]),
        str(row.get("expectedSourceRef") or ""),
        ",".join(row.get("forbiddenSourceRefs") or []),
    )
    if key in seen:
        return
    seen.add(key)
    seenQueries.add(query)
    out.append(_finalizeGoldRow(row, len(out) + 1, markReviewed=markReviewed))


def buildIndexes(rows: list[CatalogRow]) -> dict[str, dict[Any, list[CatalogRow]]]:
    indexes: dict[str, dict[Any, list[CatalogRow]]] = {
        "byCompanyRole": defaultdict(list),
        "byCompanyBase": defaultdict(list),
        "byCompanyYear": defaultdict(list),
        "byCompanyYearBase": defaultdict(list),
        "byBaseYear": defaultdict(list),
        "bySource": defaultdict(list),
    }
    for row in rows:
        indexes["byCompanyRole"][(row.companyKey, row.eventRole)].append(row)
        indexes["byCompanyBase"][(row.companyKey, row.baseRole)].append(row)
        indexes["byCompanyYear"][(row.companyKey, row.year)].append(row)
        indexes["byCompanyYearBase"][(row.companyKey, row.year, row.baseRole)].append(row)
        indexes["byBaseYear"][(row.baseRole, row.year)].append(row)
        indexes["bySource"][row.sourceKind].append(row)
    return indexes


def buildSameCompanyDifferentYear(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expected in rows:
        if expected.sourceKind == "news" or expected.baseRole == "unknown":
            continue
        forbidden = _first(
            indexes["byCompanyBase"].get((expected.companyKey, expected.baseRole), []),
            lambda row: row.sourceRef != expected.sourceRef and row.year != expected.year,
        )
        if forbidden:
            out.append(
                _gold(
                    "same-company-different-year",
                    expected,
                    [forbidden],
                    query=_filingQuery(expected, sourceHint=True),
                )
            )
        if len(out) >= limit:
            break
    return out


def buildSameCompanySiblingFiling(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expected in indexes["bySource"].get("allFilings", []):
        if expected.baseRole == "unknown":
            continue
        candidates = indexes["byCompanyYearBase"].get((expected.companyKey, expected.year, expected.baseRole), [])
        forbidden = _first(
            candidates,
            lambda row: row.sourceRef != expected.sourceRef
            and row.sourceKind == "allFilings"
            and row.eventRole != expected.eventRole,
        ) or _first(candidates, lambda row: row.sourceRef != expected.sourceRef and row.sourceKind == "allFilings")
        if forbidden:
            out.append(
                _gold(
                    "same-company-sibling-filing",
                    expected,
                    [forbidden],
                    query=_filingQuery(expected, sourceHint=True),
                )
            )
        if len(out) >= limit:
            break
    return out


def buildSimilarEventOtherCompany(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expected in indexes["bySource"].get("allFilings", []):
        if expected.baseRole == "unknown":
            continue
        forbidden = _first(
            indexes["byBaseYear"].get((expected.baseRole, expected.year), []),
            lambda row: row.sourceRef != expected.sourceRef
            and row.sourceKind == "allFilings"
            and row.companyKey != expected.companyKey,
        )
        if forbidden:
            out.append(
                _gold(
                    "similar-event-other-company",
                    expected,
                    [forbidden],
                    query=_filingQuery(expected, sourceHint=True),
                )
            )
        if len(out) >= limit:
            break
    return out


def buildReportTypeMismatch(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    reportRoles = {"annual", "quarterly", "semiannual", "audit"}
    out: list[dict[str, Any]] = []
    for expected in rows:
        if expected.sourceKind == "news" or expected.baseRole not in reportRoles:
            continue
        forbidden = _first(
            indexes["byCompanyYear"].get((expected.companyKey, expected.year), []),
            lambda row: row.sourceRef != expected.sourceRef
            and row.sourceKind == expected.sourceKind
            and row.baseRole in reportRoles
            and row.baseRole != expected.baseRole,
        )
        if forbidden:
            out.append(
                _gold(
                    "report-type-mismatch",
                    expected,
                    [forbidden],
                    query=_filingQuery(expected, sourceHint=True),
                )
            )
        if len(out) >= limit:
            break
    return out


def buildNewsFilingConfusion(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expected in indexes["bySource"].get("news", []):
        forbidden = _first(
            indexes["byBaseYear"].get((expected.baseRole, expected.year), []),
            lambda row: row.sourceKind != "news",
        )
        forbiddenRows = [forbidden] if forbidden else []
        out.append(
            _gold(
                "news-filing-confusion",
                expected,
                forbiddenRows,
                forbiddenFamilies=["filing"],
                query=f"공시 말고 뉴스로 {_queryLabel(expected)}",
            )
        )
        if len(out) >= limit:
            break
    return out


def buildFilingNewsConfusion(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    filingRows = [row for row in rows if row.sourceKind in {"allFilings", "panel"} and row.baseRole != "unknown"]
    for expected in filingRows:
        forbidden = _first(
            indexes["byBaseYear"].get((expected.baseRole, expected.year), []),
            lambda row: row.sourceKind == "news",
        )
        forbiddenRows = [forbidden] if forbidden else []
        out.append(
            _gold(
                "filing-news-confusion",
                expected,
                forbiddenRows,
                forbiddenFamilies=["news"],
                query=f"뉴스 말고 공시 원문 {_queryLabel(expected)}",
            )
        )
        if len(out) >= limit:
            break
    return out


def buildEdgarDartConfusion(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expected in indexes["bySource"].get("edgar", []):
        if expected.baseRole == "unknown":
            continue
        forbidden = _first(
            indexes["byBaseYear"].get((expected.baseRole, expected.year), []),
            lambda row: row.sourceKind in {"allFilings", "panel"} and row.sourceRef != expected.sourceRef,
        )
        if forbidden:
            out.append(
                _gold(
                    "edgar-dart-confusion",
                    expected,
                    [forbidden],
                    query=_filingQuery(expected, edgar=True),
                )
            )
        if len(out) >= limit:
            break
    return out


def buildPanelFilingConfusion(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expected in indexes["bySource"].get("panel", []):
        forbidden = _first(
            indexes["byCompanyYear"].get((expected.companyKey, expected.year), []),
            lambda row: row.sourceKind == "allFilings" and row.sourceRef != expected.sourceRef,
        )
        if forbidden:
            out.append(
                _gold(
                    "panel-filing-confusion",
                    expected,
                    [forbidden],
                    query=f"{_companyLabel(expected)} {expected.year} 사업보고서 본문 주석 panel",
                )
            )
        if len(out) >= limit:
            break
    return out


def buildNoAnswerGold(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    """Build plausible no-answer traps from source catalog gaps.

    Args:
        rows: Catalog rows.
        indexes: Catalog indexes returned by ``buildIndexes``.
        limit: Maximum no-answer rows.

    Returns:
        list[dict[str, Any]]: Candidate no-answer gold rows.

    Raises:
        None.

    Example:
        >>> buildNoAnswerGold([], buildIndexes([]), 3)
        []
    """
    builders = (buildNoAnswerMissingCompanyYearEvent,)
    out: list[dict[str, Any]] = []
    seenQueries: set[str] = set()
    buckets = [builder(rows, indexes, max(limit, 1)) for builder in builders]
    maxBucket = max((len(bucket) for bucket in buckets), default=0)
    for index in range(maxBucket):
        for bucket in buckets:
            if index >= len(bucket):
                continue
            row = bucket[index]
            query = str(row.get("query") or "").strip()
            if not query or query in seenQueries:
                continue
            seenQueries.add(query)
            out.append(row)
            if len(out) >= limit:
                return out
    return out


def buildNoAnswerMissingCompanyYearEvent(
    rows: list[CatalogRow], indexes: dict[str, dict[Any, list[CatalogRow]]], limit: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (companyKey, year), companyYearRows in indexes["byCompanyYear"].items():
        if not companyKey or not year:
            continue
        anchor = _first(companyYearRows, lambda row: row.sourceKind in {"allFilings", "panel", "edgar"})
        if anchor is None:
            continue
        presentBases = {row.baseRole for row in companyYearRows if row.baseRole != "unknown"}
        nearRows = [row for row in companyYearRows if row.sourceRef and row.baseRole != "unknown"]
        if not nearRows:
            continue
        for baseRole in NO_ANSWER_BASE_ROLES:
            if baseRole in presentBases:
                continue
            sameCompanyOtherYear = _first(
                indexes["byCompanyBase"].get((companyKey, baseRole), []),
                lambda row: row.year != year and row.sourceRef,
            )
            otherCompanySameYear = _first(
                indexes["byBaseYear"].get((baseRole, year), []),
                lambda row: row.companyKey != companyKey and row.sourceRef,
            )
            if sameCompanyOtherYear is None and otherCompanySameYear is None:
                continue
            forbiddenRows = _uniqueRows([nearRows[0], sameCompanyOtherYear, otherCompanySameYear])
            label = _roleLabel(baseRole)
            out.append(
                _noAnswerGold(
                    "no-answer-missing-company-year-event",
                    anchor,
                    forbiddenRows,
                    query=f"{_companyLabel(anchor)} {year} {label} 공시 원문",
                    expectedBaseRole=baseRole,
                )
            )
            break
        if len(out) >= limit:
            break
    return out


def inferEventRole(text: str) -> tuple[str, str, str]:
    normalized = _normalize(text)
    for baseRole, label, terms in EVENT_RULES:
        if any(term in normalized for term in terms):
            variant = "base"
            if any(token in normalized for token in ("정정", "변경", "amendment", "amended")):
                variant = "correction"
            elif any(token in normalized for token in ("결과", "완료", "result")):
                variant = "result"
            elif any(token in normalized for token in ("결정", "체결", "발행", "취득", "처분", "제출", "10-k", "10-q")):
                variant = "decision"
            return baseRole, f"{baseRole}:{variant}", label
    return "unknown", "unknown:base", "본문"


EVENT_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("annual", "사업보고서", ("사업보고서", "10-k", "annual report", "risk factors")),
    ("quarterly", "분기보고서", ("분기보고서", "10-q", "quarterly report")),
    ("semiannual", "반기보고서", ("반기보고서", "semiannual")),
    ("audit", "감사보고서", ("감사보고서", "auditor", "audit report")),
    ("rightsOffering", "유상증자", ("유상증자", "rights offering")),
    ("bonusIssue", "무상증자", ("무상증자", "bonus issue")),
    ("convertibleBond", "전환사채", ("전환사채", "convertible")),
    ("bondWithWarrants", "신주인수권부사채", ("신주인수권", "warrant")),
    ("treasuryAcquire", "자기주식 취득", ("자기주식취득", "자기주식 취득", "자사주 매입")),
    ("treasuryDispose", "자기주식 처분", ("자기주식처분", "자기주식 처분")),
    ("dividend", "배당", ("배당", "dividend")),
    ("ceoChange", "대표이사 변경", ("대표이사", "ceo change")),
    ("largestShareholder", "최대주주 변경", ("최대주주", "largest shareholder")),
    ("shareholderMeeting", "주주총회", ("주주총회", "shareholder meeting")),
    ("supplyContract", "공급계약", ("공급계약", "수주", "supply contract")),
    ("merger", "합병", ("합병", "merger")),
    ("split", "분할", ("분할", "spin-off", "split")),
    ("assetAcquire", "자산 취득", ("자산양수", "자산 취득", "타법인 주식 취득")),
    ("assetDispose", "자산 처분", ("자산처분", "자산 처분", "타법인 주식 처분")),
    ("lawsuit", "소송", ("소송", "litigation")),
    ("embezzlement", "횡령 배임", ("횡령", "배임", "embezzlement")),
    ("tradingHalt", "거래정지", ("거래정지", "매매거래정지")),
    ("fxRisk", "환율 리스크", ("환율", "외환", "foreign exchange", "currency risk")),
    ("hbmInvestment", "HBM 투자", ("hbm", "반도체", "semiconductor")),
    ("cyberRisk", "사이버 보안", ("사이버", "cyber")),
    ("environmentRisk", "환경 규제", ("환경", "environment")),
    ("customerConcentration", "고객사 집중", ("고객사", "customer concentration")),
)


def _gold(
    hardNegativeType: str,
    expected: CatalogRow,
    forbiddenRows: list[CatalogRow],
    *,
    query: str,
    forbiddenFamilies: list[str] | None = None,
) -> dict[str, Any]:
    forbiddenRefs = _unique(
        [row.sourceRef for row in forbiddenRows if row and row.sourceRef and row.sourceRef != expected.sourceRef]
    )
    return {
        "query": _squeeze(query),
        "targetKind": _targetKind(expected),
        "expectedAnswerable": True,
        "expectedSourceRef": expected.sourceRef,
        "expectedSourceRefs": [expected.sourceRef],
        "forbiddenSourceRefs": forbiddenRefs,
        "distractorSourceRefs": forbiddenRefs,
        "forbiddenSourceFamilies": _unique(forbiddenFamilies or []),
        "hardNegativeType": hardNegativeType,
        "sourceDataAsOf": expected.sourceDataAsOf,
        "expectedFacets": {
            "sourceKind": expected.sourceKind,
            "companyName": expected.companyName,
            "stockCode": expected.stockCode,
            "ticker": expected.ticker,
            "year": expected.year,
            "baseRole": expected.baseRole,
            "eventRole": expected.eventRole,
        },
    }


def _noAnswerGold(
    hardNegativeType: str,
    anchor: CatalogRow,
    forbiddenRows: list[CatalogRow],
    *,
    query: str,
    expectedBaseRole: str,
    expectedSourceKind: str = "allFilings",
    forbiddenFamilies: list[str] | None = None,
) -> dict[str, Any]:
    forbiddenRefs = _unique([row.sourceRef for row in forbiddenRows if row and row.sourceRef])
    return {
        "query": _squeeze(query),
        "targetKind": "noAnswer",
        "expectedAnswerable": False,
        "expectedSourceRef": "",
        "expectedSourceRefs": [],
        "forbiddenSourceRefs": forbiddenRefs,
        "distractorSourceRefs": forbiddenRefs,
        "forbiddenSourceFamilies": _unique(forbiddenFamilies or []),
        "hardNegativeType": hardNegativeType,
        "sourceDataAsOf": anchor.sourceDataAsOf,
        "expectedFacets": {
            "sourceKind": expectedSourceKind,
            "companyName": anchor.companyName,
            "stockCode": anchor.stockCode,
            "ticker": anchor.ticker,
            "year": anchor.year,
            "baseRole": expectedBaseRole,
            "eventRole": f"{expectedBaseRole}:missing",
        },
    }


def _finalizeGoldRow(row: dict[str, Any], index: int, *, markReviewed: bool) -> dict[str, Any]:
    queryHash = hashlib.sha1(str(row["query"]).encode("utf-8")).hexdigest()[:12]
    row["queryId"] = f"hardneg-current:{row['hardNegativeType']}:{index:04d}:{queryHash}"
    row["goldOrigin"] = "operator" if markReviewed else CURRENT_DATA_ORIGIN
    row["reviewStatus"] = "reviewed" if markReviewed else "candidate"
    row["labeler"] = "deterministic-current-catalog"
    return row


def buildSummary(rows: list[dict[str, Any]], *, catalogPath: Path, catalogRows: int) -> dict[str, Any]:
    byType: dict[str, int] = {}
    byTarget: dict[str, int] = {}
    withFamilies = 0
    withRefs = 0
    for row in rows:
        byType[str(row.get("hardNegativeType") or "")] = byType.get(str(row.get("hardNegativeType") or ""), 0) + 1
        byTarget[str(row.get("targetKind") or "")] = byTarget.get(str(row.get("targetKind") or ""), 0) + 1
        if row.get("forbiddenSourceFamilies"):
            withFamilies += 1
        if row.get("forbiddenSourceRefs"):
            withRefs += 1
    return {
        "schemaVersion": "searchHardNegativeGoldBuild.v1",
        "catalogPath": str(catalogPath),
        "catalogRowsRead": catalogRows,
        "totalRows": len(rows),
        "byHardNegativeType": dict(sorted(byType.items())),
        "byTargetKind": dict(sorted(byTarget.items())),
        "rowsWithForbiddenSourceFamilies": withFamilies,
        "rowsWithForbiddenSourceRefs": withRefs,
        "reviewState": "reviewed" if rows and rows[0].get("reviewStatus") == "reviewed" else "candidate",
        "releaseEvidence": bool(rows and rows[0].get("reviewStatus") == "reviewed"),
    }


def _column(schema: pl.Schema, names: tuple[str, ...], alias: str) -> pl.Expr:
    for name in names:
        if name in schema:
            return pl.col(name).cast(pl.Utf8, strict=False).fill_null("").alias(alias)
    return pl.lit("").alias(alias)


def _first(rows: Iterable[CatalogRow], predicate: Any) -> CatalogRow | None:
    for row in rows:
        if predicate(row):
            return row
    return None


def _sourceKind(source: str) -> str:
    value = source.strip()
    if value == "newsPublic" or value.lower().startswith("news"):
        return "news"
    if value in {"dartPanel", "panel"}:
        return "panel"
    if value in {"edgarPanel", "edgar-panel"}:
        return "edgar"
    return "allFilings" if value == "allFilings" else value


def _targetKind(row: CatalogRow) -> str:
    if row.sourceKind == "news":
        return "news"
    if row.sourceKind == "edgar":
        return "edgar"
    return "filing"


def _filingQuery(row: CatalogRow, *, sourceHint: bool = False, edgar: bool = False) -> str:
    if edgar:
        return f"EDGAR {_companyLabel(row)} {row.year} {row.roleLabel} filing"
    suffix = "공시 원문" if sourceHint else "본문"
    return f"{_companyLabel(row)} {row.year} {row.roleLabel} {suffix}"


def _queryLabel(row: CatalogRow) -> str:
    label = row.title or row.reportName or row.roleLabel
    label = _squeeze(label)
    if len(label) > 80:
        label = label[:80]
    return label or row.roleLabel


def _roleLabel(baseRole: str) -> str:
    for role, label, _ in EVENT_RULES:
        if role == baseRole:
            return label
    return baseRole


def _companyLabel(row: CatalogRow) -> str:
    return row.companyName or row.stockCode or row.ticker or row.companyKey


def _normalize(text: str) -> str:
    return _squeeze(str(text or "")).lower().replace(" ", "")


def _squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _digits(text: str) -> str:
    return re.sub(r"\D+", "", str(text or ""))


def _clean(value: Any) -> str:
    return _squeeze("" if value is None else str(value))


def _unique(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = _clean(value)
        if text and text not in out:
            out.append(text)
    return out


def _uniqueRows(rows: Iterable[CatalogRow | None]) -> list[CatalogRow]:
    out: list[CatalogRow] = []
    seen: set[str] = set()
    for row in rows:
        if row is None or not row.sourceRef or row.sourceRef in seen:
            continue
        seen.add(row.sourceRef)
        out.append(row)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
