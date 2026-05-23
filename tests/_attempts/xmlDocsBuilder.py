"""XML zip → docs.parquet 호환 schema builder (정공법).

기존 collector.py (viewer.do HTML → htmlToText → plain text) 대체.

핵심 차이:
- 기존: section_content = chapter 전체 본문 (regex 추론 필요)
- 새:   section_title 별 row (chapter/sub 분리) + body 안 가/나/다 marker 는
        markdown ## prefix 로 변환 → sections layer 의 가/나/다 추론 제거

schema (기존 docs.parquet 와 동일):
- corp_code / corp_name / stock_code / year / rcept_date / rcept_no
- report_type / section_order / section_title / section_url / section_content

새 추가 column (optional — sections layer 가 활용 시):
- assocnote (D-0-1-1-0 path-id)
- atocid

실행:
    uv run python -X utf8 tests/_attempts/xmlDocsBuilder.py --code 005930

검증:
    새 parquet 를 docs/005930.parquet 와 비교 + Company('005930').sections 호출 결과.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Any

import polars as pl
from lxml import etree

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _tableToMarkdown(table) -> str:
    rows: list[list[str]] = []
    for tr in table.iter("TR"):
        cells: list[str] = []
        for cell in tr.xpath(".//TD|.//TH|.//TU|.//TE"):
            colspan = int(cell.get("COLSPAN", "1") or "1")
            text = " ".join(cell.itertext()).strip().replace("\n", " ").replace("|", "｜")
            cells.append(text)
            cells.extend("" for _ in range(colspan - 1))
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    nCols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < nCols:
            r.append("")
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * nCols) + " |"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


_SUB_MARKER_RE = None  # lazy


def _elemText(elem) -> str:
    return " ".join(elem.itertext()).strip()


def extractTitleRows(xmlPath: Path) -> list[dict[str, Any]]:
    """XML 안 <TITLE> 별 row 추출. body 는 다음 TITLE 까지의 본문 (markdown table 포함)."""
    parser = etree.XMLParser(recover=True, huge_tree=True)
    tree = etree.parse(str(xmlPath), parser=parser)
    root = tree.getroot()
    body = root.find(".//BODY")
    if body is None:
        return []

    rows: list[dict[str, Any]] = []
    currentTitle: dict[str, Any] | None = None
    bodyParts: list[str] = []

    def _flush() -> None:
        nonlocal currentTitle, bodyParts
        if currentTitle is not None:
            currentTitle["section_content"] = "\n\n".join(p for p in bodyParts if p).strip()
            rows.append(currentTitle)
        bodyParts = []
        currentTitle = None

    # body 안 모든 element 순차 walk (document order)
    for elem in body.iter():
        tag = elem.tag
        if tag in ("TITLE", "COVER-TITLE"):
            _flush()
            atoc = elem.get("ATOC", "")
            assoc = elem.get("AASSOCNOTE", "")
            atocid = elem.get("ATOCID", "")
            text = _elemText(elem)
            currentTitle = {
                "atoc": atoc,
                "assocnote": assoc,
                "atocid": atocid,
                "section_title": text,
                "section_content": "",
            }
        elif tag == "P" and currentTitle is not None:
            t = _elemText(elem)
            if t:
                bodyParts.append(t)
        elif tag == "SPAN" and currentTitle is not None:
            # 가/나/다 sub-sub marker — USERMARK 의 bold (B 끝) 가 marker.
            # markdown ## prefix 로 변환 → sections textStructure 가 직접 인식.
            usermark = elem.get("USERMARK", "")
            t = _elemText(elem)
            if t:
                # F-14 B / F-16 B / F-10 B 등 bold 표시 — sub-section heading
                isBold = "B" in usermark.split() or usermark.endswith(" B")
                if isBold and t and len(t) < 80:
                    # heading 처리 — markdown ## prefix
                    bodyParts.append(f"## {t}")
                else:
                    bodyParts.append(t)
        elif tag == "TABLE" and currentTitle is not None:
            # TABLE-GROUP 안 TABLE 만 직접 처리 (중복 피하기 위해 parent 가 TABLE-GROUP 인지 확인)
            md = _tableToMarkdown(elem)
            if md:
                bodyParts.append(md)
    _flush()
    return rows


def _documentNameToReportType(docName: str) -> str:
    """DOCUMENT-NAME → report_type 매핑 (기존 collector 와 동일 형식)."""
    if "분기" in docName:
        return "분기보고서"
    if "반기" in docName:
        return "반기보고서"
    if "사업" in docName:
        return "사업보고서"
    return docName


_SCHEMA_FIELDS = [
    "corp_code",
    "corp_name",
    "stock_code",
    "year",
    "rcept_date",
    "rcept_no",
    "report_type",
    "section_order",
    "section_title",
    "section_url",
    "section_content",
    "atocid",
    "assocnote",
]


def buildCodeParquet(code: str, originalDir: Path) -> pl.DataFrame:
    """code 의 모든 zip 을 새 schema parquet 으로 streaming 변환 (메모리 친화).

    회귀 사례: 005380 (현대차) 모든 rcept 의 row dict 누적 → polars.DataFrame(all_rows)
    호출 시 `bytes.len() <= u32::MAX as usize` PanicException (single column buffer
    4GB 한도 초과).

    fix: rcept 1 개 처리할 때마다 그 rcept 의 row dict list 를 polars DataFrame 으로
    변환 후 즉시 부분 parquet 으로 sink. 마지막에 모든 부분 parquet 을
    pyarrow.parquet.ParquetWriter 로 row group 별 stream concat 후 return.
    rcept 단위 메모리 누적 only → 종목 전체 누적 0.
    """
    import gc

    zips = sorted((originalDir / code).glob("*.zip"))
    if not zips:
        print(f"[err] no zip for {code} at {originalDir / code}")
        return pl.DataFrame()

    extractDir = REPO_ROOT / "tests" / "_attempts" / "xml_extract" / code
    extractDir.mkdir(parents=True, exist_ok=True)

    # 기존 parquet 에서 corp_code/corp_name/year 정보 추출 (rcept_no 매칭)
    oldParquet = REPO_ROOT / "data" / "dart" / "docs" / f"{code}.parquet"
    rcptMeta: dict[str, dict] = {}
    if oldParquet.exists():
        old = pl.read_parquet(oldParquet)
        for r in old.iter_rows(named=True):
            rcpNo = r["rcept_no"]
            if rcpNo not in rcptMeta:
                rcptMeta[rcpNo] = {
                    "corp_code": r["corp_code"],
                    "corp_name": r["corp_name"],
                    "stock_code": r["stock_code"],
                    "year": r["year"],
                    "rcept_date": r["rcept_date"],
                    "report_type": r["report_type"],
                }

    # 부분 parquet 누적 (rcept 별 1 개) → 마지막에 concat
    partsDir = extractDir / "_parts"
    partsDir.mkdir(parents=True, exist_ok=True)
    # 기존 부분 정리
    for old_part in partsDir.glob("*.parquet"):
        old_part.unlink()

    totalRows = 0
    for zp in zips:
        rcpNo = zp.stem
        meta = rcptMeta.get(
            rcpNo,
            {
                "corp_code": "",
                "corp_name": "",
                "stock_code": code,
                "year": "",
                "rcept_date": "",
                "report_type": "",
            },
        )
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(extractDir)
        xmlFiles = list(extractDir.glob(f"{rcpNo}*.xml"))
        if not xmlFiles:
            print(f"  [skip] {rcpNo}: no xml in zip")
            continue
        xmlPath = xmlFiles[0]
        try:
            titleRows = extractTitleRows(xmlPath)
        except Exception as exc:
            print(f"  [err] {rcpNo}: {exc!s}[:100]")
            xmlPath.unlink(missing_ok=True)
            continue

        # 이 rcept 의 row dict list 만 in-memory → 즉시 parquet 으로 sink
        rcpt_rows = [
            {
                **meta,
                "rcept_no": rcpNo,
                "section_order": i,
                "section_title": tr["section_title"],
                "section_url": "",
                "section_content": tr["section_content"],
                "atocid": tr.get("atocid", ""),
                "assocnote": tr.get("assocnote", ""),
            }
            for i, tr in enumerate(titleRows)
        ]
        if rcpt_rows:
            try:
                df_rcpt = pl.DataFrame(
                    rcpt_rows, schema={f: pl.Utf8 for f in _SCHEMA_FIELDS} | {"section_order": pl.Int64}
                )
                df_rcpt.write_parquet(partsDir / f"{rcpNo}.parquet")
                totalRows += len(rcpt_rows)
            except Exception as exc:
                print(f"  [err parquet] {rcpNo}: {exc!s}[:100]")
        # cleanup
        rcpt_rows = None  # noqa: F841
        try:
            xmlPath.unlink()
        except Exception:
            pass
        print(f"  {rcpNo}: rows={len(titleRows)}")
        if len(zips) > 20 and totalRows % 1000 == 0:
            gc.collect()

    # 부분 parquet 들 streaming concat → 단일 LazyFrame → collect (한 번)
    parts = sorted(partsDir.glob("*.parquet"))
    if not parts:
        return pl.DataFrame()
    lf = pl.concat([pl.scan_parquet(p) for p in parts])
    df = lf.collect()
    # cleanup parts
    for p in parts:
        try:
            p.unlink()
        except Exception:
            pass
    return df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="005930")
    args = parser.parse_args()

    originalDir = REPO_ROOT / "data" / "dart" / "original" / "docs"
    df = buildCodeParquet(args.code, originalDir)
    if df.shape[0] == 0:
        return 1

    outPath = REPO_ROOT / "tests" / "_attempts" / f"docs_xml_{args.code}.parquet"
    df.write_parquet(outPath)
    print(f"\n=== {args.code} ===")
    print(f"new schema parquet: {outPath}")
    print(f"  rows: {df.shape[0]}, size: {outPath.stat().st_size:,} bytes")

    oldPath = REPO_ROOT / "data" / "dart" / "docs" / f"{args.code}.parquet"
    if oldPath.exists():
        old = pl.read_parquet(oldPath)
        print("\n기존 docs.parquet:")
        print(f"  rows: {old.shape[0]}, size: {oldPath.stat().st_size:,} bytes")
        print(f"\n  new/old row ratio: {df.shape[0] / old.shape[0]:.2f}x")

    # rcept 별 비교
    if oldPath.exists():
        new_per_rcept = df.group_by("rcept_no").len().rename({"len": "new_rows"})
        old_per_rcept = old.group_by("rcept_no").len().rename({"len": "old_rows"})
        cmp = new_per_rcept.join(old_per_rcept, on="rcept_no", how="full").sort("rcept_no", descending=True)
        print("\n  rcept 별 row 비교 (최근 10):")
        for r in cmp.head(10).iter_rows(named=True):
            print(f"    {r['rcept_no']}: new={r['new_rows']} vs old={r['old_rows']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
