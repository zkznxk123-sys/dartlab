"""비용상세 panel 추출 — ``providers/dart/panel/expenseDetail.py`` (L1, finance import 0).

panel 주석 표에서 손익계산서 비용 상세(급여·감가상각·수수료·광고…)를 추출해
core.accounts.expenseDetail.OUTPUT_SCHEMA(23컬럼) long DataFrame 으로 만든다.
DESIGN_DEBATE.md 정공 설계 baked-in:

    1. **실파서 재사용** — panel.text.parsePanelXmlTables (regex 재발명 금지).
    2. **당기 열 추출** — 표 [라벨, 당기, 전기] 에서 첫 숫자 열(당기)만. 당기/전기 합산 0.
    3. **closure 게이트** — (period,scope,lane)당 후보 블록 중 detail합이 *노트 자체 총계*
       에 닫히는(∈CLOSURE_BAND) 블록을 canonical. frankenblock·중복테이블 자동 배제.
    4. **선언단위 파싱** — '단위:백만원' 텍스트 우선(finance 비율 추론은 builder 단계 fallback).
    5. **xbrlClass scope** — NT_C_*/NT_S_* 표준코드로 연결/별도 확정(있을 때).

레이어: L1 panel. core(accounts.expenseDetail) + panel.read/text 만 import. finance 미import(R1).
reconciliationStatus 는 unchecked·reconciledTarget 은 null 로 두고, finance 결합은 builder 단계.
"""

from __future__ import annotations

import html
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl

from dartlab.core.accounts.expenseDetail import (
    EXPENSE_CATEGORIES,
    MAPPER_VERSION,
    NOTE_SOURCE_PATTERNS,
    OUTPUT_SCHEMA,
    SGA_DETAIL_CANDIDATE_ROWS,
    WISE_REPORT_STATEMENT_ROWS,
    classifyStrictRowRole,
    closureRatio,
    coarseBucket,
    laneContractByName,
    mapExpenseLabel,
    normalizeLabel,
    normalizeText,
    parseDeclaredUnit,
    stripFunctionTag,
)

# 표 파싱·parquet 경로·HF 자동 다운로드는 panel SSOT 재사용(regex/경로 재발명 금지).
from dartlab.providers.dart.panel.read import _panelDir, ensurePanelFromHf
from dartlab.providers.dart.panel.text import parsePanelXmlTables

READ_COLUMNS: tuple[str, ...] = (
    "chapter",
    "sectionLeaf",
    "sectionPath",
    "blockLeaf",
    "xbrlClass",
    "aassocnote",
    "disclosureKey",
    "blockOrder",
    "contentRaw",
    "period",
    "corp",
)
TITLE_COLUMNS: tuple[str, ...] = (
    "chapter",
    "sectionLeaf",
    "sectionPath",
    "blockLeaf",
    "xbrlClass",
    "aassocnote",
    "disclosureKey",
)
# prefilter — 매출원가/제조원가 포함(v1 cogs 공백 직접원인 수정).
PREFILTER_TERMS: tuple[str, ...] = tuple(
    dict.fromkeys(term for terms in NOTE_SOURCE_PATTERNS.values() for term in terms)
)
# NT 표준 주석코드 → (lane, scope). 있을 때 scope/lane 확정 보조신호.
NT_LANE_SCOPE: dict[str, tuple[str, str]] = {
    "D834310": ("strictSgaDetail", "consolidated"),
    "D834315": ("strictSgaDetail", "separate"),
    "D834300": ("strictExpensesByNature", "consolidated"),
    "D834305": ("strictExpensesByNature", "separate"),
}
LANE_STATEMENT_PARENT: dict[str, str] = {
    "strictSgaDetail": "sellingGeneralAdministrativeExpenses",
    "strictExpensesByNature": "operatingProfit",
    "strictCostOfSalesDetail": "costOfSales",
}
STRICT_SOURCE_LANES: tuple[str, ...] = ("strictSgaDetail", "strictExpensesByNature", "strictCostOfSalesDetail")
_STATEMENT_LABEL: dict[str, str] = {row.key: row.label for row in WISE_REPORT_STATEMENT_ROWS}
_DETAIL_KEY_LABEL: dict[str, str] = {
    **{row.key: row.label for row in SGA_DETAIL_CANDIDATE_ROWS},
    **{category.key: category.label for category in EXPENSE_CATEGORIES},
    "quarantine": "(quarantine)",
}
_DIGIT_RE = re.compile(r"\d")
_KOREAN_RE = re.compile(r"[가-힣]")
_SCHEMA_COLUMNS: tuple[str, ...] = tuple(column.column for column in OUTPUT_SCHEMA)


def panelPath(code: str) -> Path:
    """종목 panel parquet 경로 — 부재 시 HF 자동 다운로드(panel.read SSOT).

    Args:
        code: 6자리 종목코드.

    Returns:
        Path — ``data/dart/panel/{code}.parquet`` (회사당 1파일).

    Example:
        >>> panelPath("005930")  # doctest: +SKIP

    Raises:
        없음 — 다운로드 실패해도 경로는 반환(존재 여부는 호출자가 ``.exists()`` 로 확인).
    """
    ensurePanelFromHf(code)
    return _panelDir(code).parent / f"{code}.parquet"


def _titleFilterExpr() -> pl.Expr:
    expr = pl.lit(False)
    for column in TITLE_COLUMNS:
        textExpr = pl.col(column).cast(pl.Utf8)
        for term in PREFILTER_TERMS:
            expr = expr | textExpr.str.contains(term, literal=True)
    return expr


def _isNoteLike(row: dict[str, Any]) -> bool:
    sectionText = f"{row.get('sectionLeaf') or ''} {row.get('sectionPath') or ''}"
    blockText = str(row.get("blockLeaf") or "")
    xbrlClass = str(row.get("xbrlClass") or "")
    return "주석" in sectionText or bool(blockText.strip()) or xbrlClass.startswith("NT_")


def _ntKey(xbrlClass: object) -> str | None:
    token = str(xbrlClass or "").rsplit("_", 1)[-1]
    return token if token in NT_LANE_SCOPE else None


def _scopeOf(row: dict[str, Any]) -> str:
    nt = _ntKey(row.get("xbrlClass"))
    if nt:
        return NT_LANE_SCOPE[nt][1]
    text = f"{row.get('chapter') or ''} {row.get('sectionPath') or ''} {row.get('sectionLeaf') or ''}"
    return "consolidated" if "연결" in text else "separate"


def _classifyLane(row: dict[str, Any]) -> str:
    nt = _ntKey(row.get("xbrlClass"))
    if nt:
        return NT_LANE_SCOPE[nt][0]
    title = normalizeText(" ".join(str(row.get(c) or "") for c in TITLE_COLUMNS))
    xbrlClass = str(row.get("xbrlClass") or "")
    isIs = xbrlClass.startswith("IS")
    if "비용의성격별분류" in title or "성격별비용" in title:
        return "strictExpensesByNature"
    if not isIs and any(t in title for t in ("판매비와관리비", "판매비및관리비", "판매관리비", "판관비")):
        return "strictSgaDetail"
    if not isIs and ("매출원가" in title or "제조원가" in title):
        return "strictCostOfSalesDetail"
    return "noSource"


def _cleanCell(rawCell: str) -> str:
    text = html.unescape(str(rawCell or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).replace("　", " ").strip()


def _parseAmount(rawCell: str) -> float | None:
    text = rawCell.strip()
    if not text or not _DIGIT_RE.search(text):
        return None
    norm = (
        text.replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .replace("△", "-")
        .replace("−", "-")
        .replace("－", "-")
        .replace("%", "")
        .strip()
    )
    if norm in {"-", ""}:
        return None
    try:
        return float(norm)
    except ValueError:
        return None


def _rowLabelAndCurrent(cells: list[str]) -> tuple[str, float | None]:
    """표 행 [라벨, 당기, 전기] → (라벨, 당기금액). 당기 = 첫 숫자 열. 병합셀 대응."""
    firstNumIdx = next((i for i, c in enumerate(cells) if _parseAmount(c) is not None), None)
    if firstNumIdx is None:
        return "", None
    label = ""
    for cell in cells[:firstNumIdx]:
        if _KOREAN_RE.search(cell) and _parseAmount(cell) is None:
            label = cell
    if not label:
        label = cells[0] if cells else ""
    return label, _parseAmount(cells[firstNumIdx])


def _blockRows(contentRaw: str) -> list[dict[str, Any]]:
    """블록 contentRaw → detail/total 행. 실파서 + 당기 열 + 기능 태그 strip.

    panel 셀분할 포맷('광고선전비, 판관비')은 기능 태그를 라벨에 붙인다. stripFunctionTag
    로 떼어 비용 라벨을 깨끗이(role/매핑 회복) 하고, 떼낸 기능은 row 단위 lane 신호로 둔다.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for table in parsePanelXmlTables(contentRaw):
        for cells in table:
            cells = [_cleanCell(c) for c in cells]
            rawLabel, amount = _rowLabelAndCurrent(cells)
            if not rawLabel or amount is None or not _KOREAN_RE.search(rawLabel):
                continue
            label, rowLane = stripFunctionTag(rawLabel)
            role = classifyStrictRowRole(label, "detail")
            key = normalizeLabel(label)
            if role == "detail":
                if key in seen:  # 당기/전기 중복 테이블 → 첫 등장만.
                    continue
                seen.add(key)
            rows.append({"label": label[:100], "labelNorm": key, "amount": amount, "rowRole": role, "rowLane": rowLane})
    return rows


# lane 별 노트 자체 총계 앵커(closure 게이트). by-nature 는 '성격별 비용'/'영업비용' 총계 행으로
# 더블카운트·frankenblock 블록을 거른다(detail 합이 자기 총계에 닫히는 블록만 canonical).
_NOTE_TOTAL_ANCHORS: dict[str, tuple[str, ...]] = {
    "strictSgaDetail": ("판매비와관리비",),
    "strictCostOfSalesDetail": ("매출원가",),
    "strictExpensesByNature": ("성격별비용", "영업비용", "비용의합계", "총비용"),
}


def _noteTotal(rows: list[dict[str, Any]], lane: str) -> float | None:
    """블록 자체 기능별 총계(판관비/매출원가/영업비용 합계) 금액 = closure anchor."""
    anchors = _NOTE_TOTAL_ANCHORS.get(lane)
    if not anchors:
        return None
    cands = [
        r["amount"]
        for r in rows
        if r["rowRole"] in ("functionalTotal", "total") and any(normalizeLabel(a) in r["labelNorm"] for a in anchors)
    ]
    return max(cands) if cands else None


def _blockSignature(block: dict[str, Any]) -> frozenset[tuple[str, int]]:
    """블록의 detail (라벨, 반올림금액) 집합 — 완전 중복 블록 판정용."""
    return frozenset((r["labelNorm"], int(round(r["amount"]))) for r in block["rows"] if r["rowRole"] == "detail")


def _detailSum(block: dict[str, Any]) -> float:
    return sum(r["amount"] for r in block["rows"] if r["rowRole"] == "detail")


def _mergeComplementary(unique: list[dict[str, Any]]) -> dict[str, Any]:
    """unique 블록들의 detail 을 labelNorm first-wins 로 합산(상보 sub-table 결합)."""
    seenLabel: set[str] = set()
    mergedRows: list[dict[str, Any]] = []
    noteTotal: float | None = None
    for block in sorted(unique, key=lambda b: -_detailSum(b)):
        if noteTotal is None and block.get("noteTotal"):
            noteTotal = block["noteTotal"]
        for r in block["rows"]:
            if r["rowRole"] == "detail":
                if r["labelNorm"] in seenLabel:
                    continue
                seenLabel.add(r["labelNorm"])
            mergedRows.append(r)
    return {**unique[0], "rows": mergedRows, "noteTotal": noteTotal}


def _selectBlocks(blocks: list[dict[str, Any]], *, combine: bool = False) -> dict[tuple[str, str, str], dict[str, Any]]:
    """(period, scope, lane)당 블록 선택.

    combine=False(기본·안전): closure 게이트 우선, detail-최다 단일 블록. 과다추출 0.
    combine=True: 완전 중복 제거 후 상보 결합(판매비+관리비 분할 합산). finance-가드 하에서만 쓴다
    (단일이 과소추출할 때 fallback, finance 총액 cap). 무가드 결합은 근접중복을 과다추출하므로 금지.
    """
    byKey: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        byKey[(block["period"], block["scope"], block["lane"])].append(block)

    selected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, cands in byKey.items():
        cands = [b for b in cands if any(r["rowRole"] == "detail" for r in b["rows"])]
        if not cands:
            continue
        # 완전 중복 블록 제거.
        seenSig: set[frozenset[tuple[str, int]]] = set()
        unique: list[dict[str, Any]] = []
        for block in sorted(cands, key=lambda b: -sum(1 for r in b["rows"] if r["rowRole"] == "detail")):
            sig = _blockSignature(block)
            if sig and sig not in seenSig:
                seenSig.add(sig)
                unique.append(block)
        if not unique:
            continue
        if combine:
            selected[key] = _mergeComplementary(unique)
            continue
        # 단일 best-closure pick.
        scored: list[tuple[int, float, int, dict[str, Any]]] = []
        for block in unique:
            ratio = closureRatio(_detailSum(block), block["noteTotal"])
            dc = sum(1 for r in block["rows"] if r["rowRole"] == "detail")
            if ratio is not None and 0.80 <= ratio <= 1.05:
                scored.append((0, abs(ratio - 1.0), -dc, block))
            else:
                scored.append((1, abs((ratio or 9.9) - 1.0), -dc, block))
        scored.sort(key=lambda s: (s[0], s[1], s[2]))
        selected[key] = scored[0][3]
    return selected


def readNoteBlocks(code: str) -> list[dict[str, Any]]:
    """panel parquet → 비용 주석 블록(메타 + 파싱된 행 + scope/lane/단위).

    Args:
        code: 6자리 종목코드.

    Returns:
        list[dict] — 블록별 code/corp/period/scope/lane/rows/noteTotal/unitFactor.

    Example:
        >>> readNoteBlocks("005930")  # doctest: +SKIP

    Raises:
        없음 — parquet 부재 시 빈 리스트.
    """
    path = panelPath(code)
    if not path.exists():
        return []
    frame = pl.scan_parquet(path).select(READ_COLUMNS).filter(_titleFilterExpr()).collect()
    blocks: list[dict[str, Any]] = []
    for row in frame.iter_rows(named=True):
        if not _isNoteLike(row):
            continue
        lane = _classifyLane(row)
        if lane not in STRICT_SOURCE_LANES:
            continue
        contentRaw = str(row.get("contentRaw") or "")
        rows = _blockRows(contentRaw)
        if not any(r["rowRole"] == "detail" for r in rows):
            continue
        unit = parseDeclaredUnit(contentRaw)
        blocks.append(
            {
                "code": code,
                "corp": row.get("corp"),
                "period": str(row.get("period") or ""),
                "scope": _scopeOf(row),
                "lane": lane,
                "xbrlClass": row.get("xbrlClass"),
                "chapter": row.get("chapter"),
                "sectionPath": row.get("sectionPath"),
                "blockOrder": row.get("blockOrder"),
                "rows": rows,
                "noteTotal": _noteTotal(rows, lane),
                "unitFactor": unit[0] if unit else None,
                "unitLabel": unit[1] if unit else None,
            }
        )
    return blocks


def expenseDetailRows(code: str) -> pl.DataFrame:
    """panel → 비용상세 long DataFrame (OUTPUT_SCHEMA 23컬럼). reconciliation 전 단계.

    reconciliationStatus=unchecked·reconciledTarget=null 로 채운다(finance 결합은 builder 단계).

    Args:
        code: 6자리 종목코드.

    Returns:
        pl.DataFrame — OUTPUT_SCHEMA 23컬럼 long. 빈 종목은 빈 프레임(스키마 보존).

    Example:
        >>> expenseDetailRows("005930").columns  # doctest: +SKIP

    Raises:
        없음.
    """
    selected = _selectBlocks(readNoteBlocks(code))
    laneContracts = laneContractByName()
    out: list[dict[str, Any]] = []
    for (period, scope, lane), block in selected.items():
        contract = laneContracts[lane]
        statementKey = LANE_STATEMENT_PARENT[lane]
        ref = "|".join(
            [code, period, scope, lane, str(block.get("xbrlClass") or ""), str(block.get("blockOrder") or "")]
        )
        for r in block["rows"]:
            label, role = str(r["label"]), str(r["rowRole"])
            mapped = mapExpenseLabel(label)
            if mapped["kind"] == "wiseReportExact":
                detailKey, naturalKey = str(mapped["categoryKey"]), None
            elif mapped["kind"] in ("naturalExact", "stem"):
                detailKey = naturalKey = str(mapped["categoryKey"])
            else:
                detailKey, naturalKey = "quarantine", None
            if role == "detail":
                canonical = contract.canonicalStatus if detailKey != "quarantine" else "quarantine"
            else:
                canonical = "noteTotal"
            out.append(
                {
                    "stockCode": code,
                    "corpName": block.get("corp"),
                    "period": period,
                    "scope": scope,
                    "statementRowKey": statementKey,
                    "statementRowLabel": _STATEMENT_LABEL.get(statementKey, statementKey),
                    "detailKey": detailKey,
                    "detailLabel": _DETAIL_KEY_LABEL.get(detailKey, label),
                    "naturalExpenseKey": naturalKey,
                    "sourceLane": lane,
                    "sourceConfidence": contract.confidence,
                    "sourceChapter": str(block.get("chapter") or "") or None,
                    "sourcePath": str(block.get("sectionPath") or "") or None,
                    "sourceRef": ref,
                    "labelOriginal": label,
                    "labelNormalized": normalizeLabel(label),
                    "amount": r["amount"],
                    "unit": block.get("unitLabel"),
                    "rowRole": role,
                    "mapperVersion": MAPPER_VERSION,
                    "reconciliationStatus": "unchecked",
                    "canonicalStatus": canonical,
                }
            )
    schema = {col: (pl.Float64 if col == "amount" else pl.Utf8) for col in _SCHEMA_COLUMNS}
    if not out:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame([{c: r.get(c) for c in _SCHEMA_COLUMNS} for r in out], schema=schema)


def annualSgaDetailSums(
    code: str, *, lane: str = "strictSgaDetail", scope: str = "consolidated", combine: bool = False
) -> dict[str, Any]:
    """연간(Q4) 단위 lane/scope detail 합 + 단위 — finance reconcile 인터페이스.

    Args:
        code: 6자리 종목코드.
        lane: strictSgaDetail/strictExpensesByNature/strictCostOfSalesDetail.
        scope: consolidated/separate.
        combine: True면 상보 sub-table 결합(finance-가드 하에서만).

    Returns:
        dict — {year: {extractedSum, mappedSum, coarseSum, detailCount, noteTotal, unitFactor, labels}}.

    Example:
        >>> annualSgaDetailSums("005930", lane="strictExpensesByNature")  # doctest: +SKIP

    Raises:
        없음.
    """
    blocks = _selectBlocks(readNoteBlocks(code), combine=combine)
    byYear: dict[str, Any] = {}
    for (period, scp, ln), block in blocks.items():
        if ln != lane or scp != scope or not period.endswith("Q4"):
            continue
        year = period[:4]
        detail = [r for r in block["rows"] if r["rowRole"] == "detail"]
        mappedSum = 0.0
        coarseSum = 0.0
        for r in detail:
            mapped = mapExpenseLabel(r["label"])
            if mapped["kind"] != "quarantine":
                mappedSum += r["amount"]
                if coarseBucket(mapped["categoryKey"]) != "etc":
                    coarseSum += r["amount"]
        byYear[year] = {
            "period": period,
            "extractedSum": round(sum(r["amount"] for r in detail), 2),
            "mappedSum": round(mappedSum, 2),
            "coarseSum": round(coarseSum, 2),
            "detailCount": len(detail),
            "noteTotal": block["noteTotal"],
            "unitFactor": block["unitFactor"],
            "labels": [r["label"] for r in detail],
        }
    return byYear


def annualCategorySums(
    code: str, *, lane: str = "strictSgaDetail", scope: str = "consolidated", combine: bool = False
) -> dict[str, Any]:
    """연간(Q4) *fine 카테고리*별 detail 합 — 기타잔차 분해(FnGuide식)용. {year: {categoryKey: amount}}.

    mapped detail 만 카테고리에 적재. quarantine(미명명)은 적재 안 함 → expenseBreakdown 의
    기타미분류 잔차(= finance 총액 - 명명합)가 quarantine + 미추출을 모두 흡수한다.

    Args:
        code: 6자리 종목코드.
        lane: strictSgaDetail/strictExpensesByNature/strictCostOfSalesDetail.
        scope: consolidated/separate.
        combine: True면 상보 sub-table 결합.

    Returns:
        dict — {year: {categoryKey: amount}} (fine 카테고리별 합).

    Example:
        >>> annualCategorySums("005930")  # doctest: +SKIP

    Raises:
        없음.
    """
    blocks = _selectBlocks(readNoteBlocks(code), combine=combine)
    byYear: dict[str, Any] = {}
    for (period, scp, ln), block in blocks.items():
        if ln != lane or scp != scope or not period.endswith("Q4"):
            continue
        year = period[:4]
        cats: dict[str, float] = byYear.setdefault(year, {})
        for r in block["rows"]:
            if r["rowRole"] != "detail":
                continue
            mapped = mapExpenseLabel(r["label"])
            if mapped["kind"] == "quarantine":
                continue
            key = str(mapped["categoryKey"])
            cats[key] = round(cats.get(key, 0.0) + r["amount"], 2)
    return byYear


def main(argv: list[str] | None = None) -> int:
    """CLI — 종목별 비용상세 long DataFrame + 연간 합 미리보기(개발용).

    Args:
        argv: 종목코드 리스트(없으면 sys.argv 또는 005930).

    Returns:
        int — 종료 코드 0.

    Example:
        >>> main(["005930"])  # doctest: +SKIP

    Raises:
        없음.
    """
    import json

    codes = (argv or sys.argv[1:]) or ["005930"]
    for code in codes:
        code = str(code).zfill(6)
        frame = expenseDetailRows(code)
        canonical = frame.filter((pl.col("rowRole") == "detail") & (pl.col("canonicalStatus") != "quarantine"))
        print(f"=== {code} === rows={frame.height} canonical={canonical.height} cols={frame.width}")
        print(json.dumps(annualSgaDetailSums(code), ensure_ascii=False, indent=2)[:1200])
        if canonical.height:
            print(canonical.select("period", "scope", "detailKey", "labelOriginal", "amount", "unit").head(8))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
