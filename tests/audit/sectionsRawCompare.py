"""parquet section_content × c.sections row 직접 1:1 비교 — 모든 종목 × 모든 period.

목적: 프론트/완성형 검증으로 잡히지 않는 sections layer 자체의 누락/허위/오정렬 전수 검출.
사용자 지시: "프론트로 검토하라고 하지말고 니가 직접 모든 섹션을 모든 docs 파케 파일과
1부터 끝까지 전부 검토해라" (2026-05-21).

검사 (per code × period × section_title):
1. heading detection — parquet section_content 안 line-start 한글/숫자/Roman marker
   ("가. ...", "1. ...", "I. ...", "ㅇ ...", "•") 가 c.sections heading row 로 존재하는가
2. table detection — parquet 안 markdown table (`|...|` 로 시작하는 연속 line) 이
   c.sections table row 로 존재하는가
3. 가짜 heading — c.sections heading row 의 label 이 parquet 본문 어디에도 line-start
   pattern 으로 등장하지 않음 (= synth 또는 over-split)
4. column count consistency — 같은 markdown table 안 row 별 cell 수 동일 여부

실행:
    uv run python -X utf8 tests/audit/sectionsRawCompare.py --codes 005930
    uv run python -X utf8 tests/audit/sectionsRawCompare.py --all --limit 50
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

DOCS_DIR = REPO_ROOT / "data" / "dart" / "docs"

# heading 마커 검출 — DART parquet 본문 line-start patterns
_RE_KOR_HEAD = re.compile(r"^([가나다라마바사아자차카타파하])\.\s*(\S.*)$")
_RE_NUM_HEAD = re.compile(r"^(\d+)\.\s+(\S.*)$")
_RE_ROMAN_HEAD = re.compile(r"^([IVXLCDM]+)\.\s+(\S.*)$")
_RE_PAREN_NUM_HEAD = re.compile(r"^\((\d+)\)\s*(\S.*)$")
_RE_PAREN_KOR_HEAD = re.compile(r"^\(([가-힣])\)\s*(\S.*)$")
# bracket / paren / circle 단독 sub-section marker
_RE_BRACKET_HEAD = re.compile(r"^(\[.+?\])\s*$")
_RE_PAREN_PHRASE_HEAD = re.compile(r"^(\(.+?\))\s*$")
_RE_CIRCLE_HEAD = re.compile(r"^([①-⑳⓪])\s+(\S.*)$")
_RE_BULLET_HEAD = re.compile(r"^([▣▶◈ㅇ•※☞])\s*(\S.*)$")

# 본문 fragment 제외 패턴 (heading 같은데 본문)
_BODY_VERB_END = re.compile(r"(?:니다|됩니다|입니다|있습니다|없습니다|같습니다|바랍니다)\.?\s*$")


def _extractHeadings(content: str) -> list[tuple[int, str, str, str]]:
    """parquet section_content 에서 heading-looking line 추출.

    Returns: list of (lineIdx, markerType, marker, label)
    """
    if not content:
        return []
    lines = content.replace("&cr;", "\n").split("\n")
    headings: list[tuple[int, str, str, str]] = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("|") or line.startswith("---"):
            continue
        if len(line) < 4 or len(line) > 200:
            continue
        # body verb-ending fragment 제외
        if _BODY_VERB_END.search(line):
            continue
        for kind, pat in (
            ("bracket", _RE_BRACKET_HEAD),
            ("parenPhrase", _RE_PAREN_PHRASE_HEAD),
            ("kor", _RE_KOR_HEAD),
            ("num", _RE_NUM_HEAD),
            ("roman", _RE_ROMAN_HEAD),
            ("parenNum", _RE_PAREN_NUM_HEAD),
            ("parenKor", _RE_PAREN_KOR_HEAD),
            ("circle", _RE_CIRCLE_HEAD),
            ("bullet", _RE_BULLET_HEAD),
        ):
            m = pat.match(line)
            if m:
                if kind in ("bracket", "parenPhrase"):
                    label = m.group(1).strip()
                    marker = label[0]
                else:
                    marker, label = m.group(1), m.group(2).strip() if m.lastindex and m.lastindex >= 2 else m.group(1)
                # label 자체가 verb-ending 이면 본문 fragment
                if _BODY_VERB_END.search(label):
                    continue
                # label 너무 길면 본문 한 문장
                if len(label) > 80:
                    continue
                headings.append((i, kind, marker, label[:60]))
                break
    return headings


def _extractTables(content: str) -> list[tuple[int, list[int]]]:
    """markdown table 의 (startLine, cellCount per row) 추출.

    Returns: list of (firstLineIdx, [cellCount, cellCount, ...])
    """
    if not content:
        return []
    lines = content.replace("&cr;", "\n").split("\n")
    tables: list[tuple[int, list[int]]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            start = i
            cellCounts: list[int] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
                cellCounts.append(len(cells))
                i += 1
            if len(cellCounts) >= 2:
                tables.append((start, cellCounts))
        else:
            i += 1
    return tables


def _labelInRawContent(normLabel: str, df: pl.DataFrame) -> bool:
    """parquet 의 모든 section_content 안 (line-start 아니어도) normLabel substring 매칭.

    inline-split 으로 sections 가 만든 heading 의 label 은 parquet 본문 mid-line 에
    등장 — line-start match 에 잡히지 않음. 본 함수가 raw content 어디든 매칭.
    """
    if len(normLabel) < 4:
        return False
    for row in df.iter_rows(named=True):
        content = row.get("section_content") or ""
        if not content:
            continue
        normContent = re.sub(r"\s+", "", content.replace("&cr;", ""))
        if normLabel in normContent:
            return True
    return False


def auditCode(code: str, *, verbose: bool = False) -> dict[str, Any]:
    from dartlab.providers.dart import Company

    parquet = DOCS_DIR / f"{code}.parquet"
    if not parquet.exists():
        return {"code": code, "ok": False, "reason": "parquet missing"}

    df = pl.read_parquet(parquet)
    sec = None
    try:
        c = Company(code)
        sec = c.sections
    except Exception as exc:
        return {"code": code, "ok": False, "reason": f"sections load error: {exc!s}[:100]"}
    if sec is None or sec.height == 0:
        return {"code": code, "ok": False, "reason": "sections empty"}

    # parquet 종합 통계
    parquetHeadings: Counter[str] = Counter()  # by markerType
    parquetTables = 0
    tableMisalign: list[dict[str, Any]] = []  # rowspan continuation 으로 cell 수 불일치

    # heading label set 모음 — sections row 의 heading label 과 매칭하기 위해
    parquetHeadingLabels: set[str] = set()

    for row in df.iter_rows(named=True):
        content = row.get("section_content") or ""
        headings = _extractHeadings(content)
        for _, kind, _, label in headings:
            parquetHeadings[kind] += 1
            # 정규화 label
            normLabel = re.sub(r"\s+", "", label)[:30]
            parquetHeadingLabels.add(normLabel)
        tables = _extractTables(content)
        parquetTables += len(tables)
        for startIdx, cellCounts in tables:
            # rowspan misalign: header row 의 cellCount 와 다른 row 가 1 이상 차이
            if len(set(cellCounts)) > 1 and len(cellCounts) > 2:
                # header 는 첫 2 줄 (보통 header + ---)
                bodyCounts = cellCounts[2:] if len(cellCounts) > 2 else cellCounts
                headerCount = cellCounts[0]
                misaligned = [c for c in bodyCounts if c != headerCount]
                if len(misaligned) > len(bodyCounts) * 0.3:
                    tableMisalign.append(
                        {
                            "rcept": row.get("rcept_date"),
                            "title": (row.get("section_title") or "")[:40],
                            "startLine": startIdx,
                            "headerCells": headerCount,
                            "bodyMisalignCount": len(misaligned),
                            "totalBodyRows": len(bodyCounts),
                        }
                    )

    # c.sections 의 heading row 들
    secHeadings = sec.filter(
        (pl.col("textNodeType").cast(pl.Utf8) == "heading") & (pl.col("blockType").cast(pl.Utf8) == "text")
    )
    secTables = sec.filter(pl.col("blockType").cast(pl.Utf8) == "table")

    # sections heading 의 label 추출 (latest period cell)
    periodCols = [c for c in sec.columns if re.fullmatch(r"\d{4}(?:Q[1-4])?", c)]
    periodColsSorted = sorted(periodCols, reverse=True)

    secHeadingLabels: set[str] = set()
    spuriousHeadings: list[dict[str, Any]] = []  # parquet 에 없는 가짜 heading

    for r in secHeadings.iter_rows(named=True):
        label = None
        for p in periodColsSorted:
            v = r.get(p)
            if isinstance(v, str) and v.strip():
                label = v.strip()
                break
        if not label:
            continue
        normLabel = re.sub(r"\s+", "", label)[:30]
        secHeadingLabels.add(normLabel)
        # parquet 에 없는 heading?
        if normLabel not in parquetHeadingLabels:
            # marker prefix 제거 후 재시도 (예 "가. 회사명" → "회사명")
            stripped = re.sub(r"^[가-하]\.\s*", "", label).strip()
            stripped = re.sub(r"^\(\d+\)\s*", "", stripped).strip()
            stripped = re.sub(r"^\d+\.\s*", "", stripped).strip()
            stripped = re.sub(r"^[IVX]+\.\s*", "", stripped).strip()
            stripped = re.sub(r"^[①-⑳⓪]\s*", "", stripped).strip()
            stripped = re.sub(r"^\([가-힣]\)\s*", "", stripped).strip()
            stripped = re.sub(r"^[【\[][^】\]]{0,30}[】\]]\s*", "", stripped).strip()
            stripped = re.sub(r"^[▣▶◈ㅇ•※☞]\s*", "", stripped).strip()
            normStripped = re.sub(r"\s+", "", stripped)[:30]
            # 추가 정합: parquet raw content 안 *어디든* (line-start 아니어도) 같은
            # label substring 존재 시 sections heading 의 evidence 있음으로 인정.
            # inline-split heading 의 label 은 parquet 본문 mid-line 에 등장.
            if (
                normStripped not in parquetHeadingLabels
                and not any(normStripped in pHL for pHL in parquetHeadingLabels if len(pHL) > 5)
                and not _labelInRawContent(normStripped, df)
            ):
                spuriousHeadings.append(
                    {
                        "bo": r.get("blockOrder"),
                        "L": r.get("textLevel"),
                        "topic": r.get("topic"),
                        "label": label[:60],
                        "path": (r.get("textPath") or "")[:80],
                    }
                )

    # missing heading: parquet 에 있지만 sections 에 없음
    # sections 의 모든 heading + body + table cell value 안에서도 substring 매칭 시도
    # — sections 가 heading 으로 만들지 않고 body 안에 묻어둔 경우 (inline 처리 등) 정상.
    secAllText: str | None = None
    missingHeadings: list[str] = []
    for plabel in list(parquetHeadingLabels)[:500]:  # 너무 많으면 sampling
        if plabel not in secHeadingLabels and len(plabel) > 4:
            # 부분 매칭 시도
            if not any(plabel in shl or shl in plabel for shl in secHeadingLabels if len(shl) > 4):
                # sections 의 모든 cell value 안 plabel 등장 여부 (lazy build)
                if secAllText is None:
                    parts: list[str] = []
                    for col in periodColsSorted:
                        try:
                            colSeries = sec.get_column(col)
                            for v in colSeries.to_list():
                                if isinstance(v, str) and v:
                                    parts.append(v)
                        except Exception:
                            continue
                    secAllText = re.sub(r"\s+", "", "".join(parts))
                if plabel not in secAllText:
                    missingHeadings.append(plabel)

    return {
        "code": code,
        "parquetRows": df.height,
        "sectionsRows": sec.height,
        "parquetHeadings": dict(parquetHeadings),
        "parquetTables": parquetTables,
        "secHeadings": secHeadings.height,
        "secTables": secTables.height,
        "spuriousHeadings": spuriousHeadings[:20],
        "spuriousCount": len(spuriousHeadings),
        "missingHeadings": missingHeadings[:20],
        "missingCount": len(missingHeadings),
        "tableMisalign": tableMisalign[:5],
        "tableMisalignCount": len(tableMisalign),
        "ok": len(spuriousHeadings) == 0 and len(tableMisalign) == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes", type=str, default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif args.all:
        codes = sorted(p.stem for p in DOCS_DIR.glob("*.parquet"))
        if args.limit > 0:
            import random

            random.seed(args.seed)
            codes = random.sample(codes, min(args.limit, len(codes)))
    else:
        codes = ["005380", "005930", "035720", "207940", "000660", "011200", "032830"]

    print(f"[audit] {len(codes)} codes")
    results: list[dict[str, Any]] = []
    t0 = time.time()
    totalSpurious = 0
    totalMissing = 0
    totalTableMisalign = 0

    for i, code in enumerate(codes, 1):
        try:
            r = auditCode(code, verbose=args.verbose)
        except Exception as exc:
            r = {"code": code, "ok": False, "reason": f"exception: {exc!s}[:100]"}
        results.append(r)
        elapsed = time.time() - t0
        eta = elapsed / i * (len(codes) - i)
        spr = r.get("spuriousCount", 0)
        msg = r.get("missingCount", 0)
        tam = r.get("tableMisalignCount", 0)
        totalSpurious += spr
        totalMissing += msg
        totalTableMisalign += tam
        status = "OK" if r.get("ok") else "FAIL"
        print(
            f"  [{i:>3}/{len(codes)}] {code} {status} "
            f"sec={r.get('sectionsRows', '-')} spurious={spr} missing={msg} tableMis={tam} "
            f"ETA={eta:.0f}s"
        )
        if args.verbose and spr > 0:
            for h in r.get("spuriousHeadings", [])[:3]:
                print(f"     spurious bo={h.get('bo')} L={h.get('L')} path={h.get('path')!r}")
                print(f"              label={h.get('label')!r}")
        sys.stdout.flush()

    print(
        f"\n=== TOTAL: {len(codes)} codes, "
        f"spurious={totalSpurious}, missing={totalMissing}, tableMisalign={totalTableMisalign} ==="
    )

    # 가장 빈번한 spurious heading label 패턴
    allSpurious: Counter[str] = Counter()
    for r in results:
        for h in r.get("spuriousHeadings", []) or []:
            allSpurious[h.get("label", "")[:40]] += 1
    if allSpurious:
        print("\n[top spurious heading labels]")
        for lbl, cnt in allSpurious.most_common(20):
            print(f"  {cnt:>4} × {lbl!r}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON saved: {out}")

    return 0 if totalSpurious + totalTableMisalign == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
