"""DART 원본 XML 의 <TITLE> hierarchy 기반 정공법 구조화 prototype.

목표: 005930 의 1 rcept zip 풀고 XML 파싱 → 새 row-level parquet 변환 → 기존
docs.parquet 와 정밀도 비교. sections layer 의 regex 추론을 builder 단에서 사전
해결 가능한지 검증.

새 schema (per row):
    rcept_no, atocid, assocnote, title_text,
    chapter_level (Roman I/II/...), sub_level (1/2/...), subsub_level (1-1/...),
    body_text (본문 paragraph + markdown table)

비교:
- 기존 docs.parquet: 1 rcept 의 sub-doc 별 1 row, section_content = chapter 본문 통째
- 새 parquet: <TITLE> 별 1 row, body_text = 그 TITLE 의 직속 본문만

실행: uv run python -X utf8 tests/_attempts/xmlStructureProto.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import polars as pl
from lxml import etree

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _cellText(elem) -> str:
    return " ".join((elem.itertext() if elem is not None else [])).strip()


def _tableToMarkdown(table) -> str:
    """XML TABLE → markdown."""
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


def _parseAssocnote(s: str | None) -> dict:
    """AASSOCNOTE 'D-0-1-1-0' / 'L-0-2-3-L1' 등 path-id 파싱.

    형식 추정: {prefix}-0-{chapter}-{sub}-{subsub}
    """
    if not s:
        return {"prefix": None, "chapter": None, "sub": None, "subsub": None}
    parts = s.split("-")
    if len(parts) < 4:
        return {"prefix": s, "chapter": None, "sub": None, "subsub": None}
    return {
        "prefix": parts[0],
        "chapter": parts[2] if len(parts) > 2 else None,
        "sub": parts[3] if len(parts) > 3 else None,
        "subsub": parts[4] if len(parts) > 4 else None,
    }


def extractRowsFromXml(xmlPath: Path, rcept_no: str) -> list[dict]:
    """단일 XML → row-level dict list (<TITLE> 별 1 row + body)."""
    # DART XML 가 비표준 entity (&XYZ;) 다수 — recover mode + huge tree limit.
    parser = etree.XMLParser(recover=True, huge_tree=True)
    tree = etree.parse(str(xmlPath), parser=parser)
    root = tree.getroot()

    # 모든 TITLE / COVER-TITLE 위치 추출 (document order)
    rows: list[dict] = []
    body = root.find(".//BODY")
    if body is None:
        return []

    # 순차 walk — TITLE 만나면 새 row 시작, 다음 TITLE 까지 본문 누적
    # ElementTree iter 는 depth-first document order — 우리가 원하는 흐름.
    currentTitle: dict | None = None
    bodyParts: list[str] = []

    def _flush():
        nonlocal currentTitle, bodyParts
        if currentTitle is not None:
            currentTitle["body_text"] = "\n\n".join(p for p in bodyParts if p).strip()
            rows.append(currentTitle)
        bodyParts = []
        currentTitle = None

    for elem in body.iter():
        tag = elem.tag
        if tag in ("TITLE", "COVER-TITLE"):
            _flush()
            atoc = elem.get("ATOC", "")
            assoc = elem.get("AASSOCNOTE", "")
            atocid = elem.get("ATOCID", "")
            text = _cellText(elem)
            assocParsed = _parseAssocnote(assoc)
            currentTitle = {
                "rcept_no": rcept_no,
                "atocid": atocid,
                "atoc": atoc,
                "assocnote": assoc,
                "prefix": assocParsed["prefix"],
                "chapter": assocParsed["chapter"],
                "sub": assocParsed["sub"],
                "subsub": assocParsed["subsub"],
                "title_text": text,
                "body_text": "",
            }
        elif tag == "P" and currentTitle is not None:
            t = _cellText(elem)
            if t:
                bodyParts.append(t)
        elif tag == "TABLE" and currentTitle is not None:
            # parent 가 TABLE-GROUP 이면 group title 도 합쳐서 보존 필요할 수 있음
            md = _tableToMarkdown(elem)
            if md:
                bodyParts.append(md)
    _flush()
    return rows


def main() -> int:
    target = REPO_ROOT / "data" / "dart" / "original" / "005930" / "20260310002820.zip"
    if not target.exists():
        print(f"missing: {target}")
        return 1

    extractDir = REPO_ROOT / "tests" / "_attempts" / "xml_extract"
    extractDir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as zf:
        zf.extractall(extractDir)
    xmlFiles = list(extractDir.glob("*.xml"))
    if not xmlFiles:
        print("no xml in zip")
        return 1
    print(f"xml: {xmlFiles[0]} ({xmlFiles[0].stat().st_size:,} bytes)")

    rows = extractRowsFromXml(xmlFiles[0], "20260310002820")
    print(f"extracted rows: {len(rows)}")

    # 기존 docs.parquet 와 비교
    df = pl.read_parquet(REPO_ROOT / "data" / "dart" / "docs" / "005930.parquet")
    sub = df.filter(pl.col("rcept_no") == "20260310002820")
    print(f"\n기존 docs.parquet: rcept 20260310002820 의 sub-doc rows = {sub.shape[0]}")
    if sub.shape[0] > 0:
        for r in sub.iter_rows(named=True):
            cLen = len(r.get("section_content") or "")
            print(f"  order={r['section_order']:>3} title={r['section_title'][:40]!r:<40} body={cLen:,} chars")

    print(f"\n새 XML 파싱: {len(rows)} TITLE-level rows")
    # 상위 30 row sample
    for r in rows[:50]:
        bodyLen = len(r["body_text"])
        ch = r.get("chapter") or "-"
        sub = r.get("sub") or "-"
        sub2 = r.get("subsub") or "-"
        print(
            f"  atocid={r['atocid']:>4} assoc={r['assocnote']:<15} "
            f"ch={ch:<3} sub={sub:<3} sub2={sub2:<3} "
            f"title={r['title_text'][:50]!r:<50} body={bodyLen:,}"
        )

    # row level 분포 — chapter 별
    from collections import Counter

    ch = Counter(r["chapter"] for r in rows if r["chapter"])
    print(f"\nchapter 별 row 수: {dict(sorted(ch.items()))}")

    # parquet 저장 후 비교
    newDf = pl.DataFrame(rows)
    outPath = REPO_ROOT / "tests" / "_attempts" / "xml_proto_005930_2025.parquet"
    newDf.write_parquet(outPath)
    print(f"\n새 parquet saved: {outPath} ({outPath.stat().st_size:,} bytes)")
    print(f"기존 parquet size (전체 종목): {(REPO_ROOT / 'data/dart/docs/005930.parquet').stat().st_size:,} bytes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
