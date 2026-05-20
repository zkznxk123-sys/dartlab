"""sections SSOT 정확성 회귀 가드 — fragment heading / chapter mix / Korean sub-heading 순서.

5 종목 sanity:
    uv run python -X utf8 tests/audit/sectionsParity.py --codes 005380,005930,035720,207940,000660 --strict

200 종목 회귀:
    uv run python -X utf8 tests/audit/sectionsParity.py --codes-from tests/audit/golden/_universe200.txt --strict

3 가지 검사 (각 0 위반 = 통과):

1. **fragment heading** — heading row 의 textPath 마지막 segment 가 본문 fragment 가 아닌
   cherrypicked title 인지. fragment 검출 패턴: 한국 조사 prefix ("에서/로/는/은/이/가/을/를/의/도/만/과/와") 로 시작.
   회귀 사례: 005380 의 "(주)에서 푸본현대생명보험" 가 level 5 heading 으로 박혀 textPath
   에 fragment "에서 푸본현대생명보험" 추가 (2026-05-20 fix 전).

2. **chapter mix** — 같은 segmentKey row 에 다른 chapter 가 cell-period 별 박힐 수 없음.
   회귀 사례: Roman chapter section ("I. 회사의 개요") 본문이 sub-section 합본 → chapter
   본문 통째 등록 시 다른 chapter row 가 머금어짐 (2026-05-19 substring 제거 fix 전).

3. **Korean sub-heading 순서 역전** — 같은 chapter 안 한글 sub-heading (가/나/다/라/마/바/사/...)
   는 본문 원문 순서 보존. blockOrder 정렬 후 textPath 의 마지막 한글 prefix 가 가나다 순서.
   회귀 사례: NH투자증권 companyOverview 차→바 순서 역전 (분기보고서 disclaimer-only period
   rowMeta 가 옛 chunk position 유지, 2026-05-20 미해결).

known-defect 사전 — parquet body 자체 결손으로 sections layer 가 만들 수 없는 케이스.
신규 누락 = fail, 등록된 누락 = pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


# 한국 조사 — fragment heading 검출용 prefix
_JOSA_PREFIX_RE = re.compile(r"^(?:에서|로서|로|는|은|이|가|을|를|의|도|만|과|와|및|또는|이며|에게|에서는|에게서)\s")

# Korean sub-heading prefix — 가나다 순서 검증용
_KOR_HEADING_ORDER = ["가", "나", "다", "라", "마", "바", "사", "아", "자", "차", "카", "타", "파", "하"]
_KOR_HEADING_RANK = {ch: idx for idx, ch in enumerate(_KOR_HEADING_ORDER)}
_KOR_PREFIX_RE = re.compile(r"^([가-힣])\.\s")

# known-defect 사전 — parquet body 자체 결손. 신규 누락은 fail, 본 사전은 pass.
# 등록 예: {"028260": {"companyOverview": ["나"]}}  # 삼성물산 (가→다 skip, parquet 본문 결손)
_KNOWN_DEFECTS: dict[str, dict[str, list[str]]] = {}


def _fragmentHeadings(df: pl.DataFrame) -> list[dict[str, Any]]:
    """heading row 중 textPath 마지막 segment 가 조사 prefix 인 fragment 검출."""
    if "textNodeType" not in df.columns or "textPath" not in df.columns:
        return []
    headings = (
        df.filter(pl.col("textNodeType") == "heading")
        .select(["topic", "blockOrder", "textPath", "textLevel"])
        .to_dicts()
    )
    bad: list[dict[str, Any]] = []
    for r in headings:
        path = r.get("textPath") or ""
        if not path:
            continue
        segs = [s.strip() for s in path.split(" > ") if s.strip()]
        if not segs:
            continue
        last = segs[-1]
        if _JOSA_PREFIX_RE.match(last):
            bad.append(
                {"topic": r["topic"], "blockOrder": r["blockOrder"], "textPath": path, "textLevel": r.get("textLevel")}
            )
    return bad


def _chapterMix(df: pl.DataFrame) -> list[dict[str, Any]]:
    """같은 segmentKey row 안 chapter 가 일관 — wide-format 에서 자연히 1 chapter / row.

    sections 의 row 단위 chapter 컬럼이 categorical 1 값이라 *이미 row 내부 일관*.
    chapter mix 회귀는 본문 cell value 에 다른 chapter 의 텍스트가 흘러들어간 경우 — cell
    안 chapter heading marker (Roman) 출현 검사로 캐치.
    """
    bad: list[dict[str, Any]] = []
    if "blockType" not in df.columns or "chapter" not in df.columns:
        return bad
    body_rows = df.filter((pl.col("blockType") == "text") & (pl.col("textNodeType") == "body"))
    period_cols = [c for c in df.columns if re.fullmatch(r"\d{4}(?:Q[1-4])?", c)]
    if not period_cols:
        return bad
    # 본문 cell 안 "I. " / "II. " / "III. " 같은 Roman chapter marker 출현 (다른 chapter
    # 본문이 침투했을 때 시그널)
    chapter_marker_re = re.compile(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.\s+[가-힣]", re.MULTILINE)
    for r in body_rows.iter_rows(named=True):
        row_chapter = str(r.get("chapter") or "")
        for p in period_cols:
            cell = r.get(p)
            if not isinstance(cell, str) or not cell:
                continue
            # 첫 줄에 chapter marker 가 있고 그 chapter 가 row chapter 와 다르면 mix
            first_line = cell.splitlines()[0] if cell.splitlines() else ""
            m = chapter_marker_re.match(first_line)
            if m:
                marker_chapter = first_line.split(".")[0].strip()
                if row_chapter and not row_chapter.startswith(marker_chapter):
                    bad.append(
                        {
                            "topic": r.get("topic"),
                            "blockOrder": r.get("blockOrder"),
                            "chapter": row_chapter,
                            "marker": marker_chapter,
                            "period": p,
                            "snippet": cell[:80],
                        }
                    )
                    break
    return bad


def _koreanOrderInversion(df: pl.DataFrame, code: str) -> list[dict[str, Any]]:
    """같은 topic 안 한글 sub-heading 가나다 순서 보존 검증.

    blockOrder 정렬 후 textPath 의 마지막 한글 prefix 가 _KOR_HEADING_ORDER 단조 증가.
    같은 chapter 안 reset 만 허용.
    """
    if "topic" not in df.columns or "textPath" not in df.columns:
        return []
    bad: list[dict[str, Any]] = []
    defects = _KNOWN_DEFECTS.get(code, {})
    for topic in df.select("topic").unique().to_series().to_list():
        topicFrame = df.filter(pl.col("topic") == topic).sort("blockOrder")
        prev_rank: int | None = None
        prev_chapter: str | None = None
        known_missing = set(defects.get(topic, []))
        seen_prefixes: set[str] = set()
        for r in topicFrame.iter_rows(named=True):
            path = r.get("textPath") or ""
            if not isinstance(path, str) or not path:
                continue
            segs = [s.strip() for s in path.split(" > ") if s.strip()]
            if not segs:
                continue
            m = _KOR_PREFIX_RE.match(segs[-1])
            if not m:
                continue
            prefix = m.group(1)
            if prefix not in _KOR_HEADING_RANK:
                continue
            rank = _KOR_HEADING_RANK[prefix]
            chapter = str(r.get("chapter") or "")
            seen_prefixes.add(prefix)
            if prev_chapter is not None and chapter != prev_chapter:
                prev_rank = None
            if prev_rank is not None and rank < prev_rank:
                bad.append(
                    {
                        "topic": topic,
                        "blockOrder": r.get("blockOrder"),
                        "textPath": path,
                        "prevRank": prev_rank,
                        "currRank": rank,
                        "prefix": prefix,
                    }
                )
            prev_rank = rank
            prev_chapter = chapter
        # missing prefix 검출 (known-defect 사전과 대조)
        for ch in _KOR_HEADING_ORDER:
            if ch in seen_prefixes:
                continue
            # 이미 다음 글자가 있는데 본 글자가 없으면 missing
            next_idx = _KOR_HEADING_RANK[ch] + 1
            has_next = any(_KOR_HEADING_RANK.get(p, -1) >= next_idx for p in seen_prefixes)
            if has_next and ch not in known_missing:
                bad.append(
                    {
                        "topic": topic,
                        "kind": "missing",
                        "prefix": ch,
                        "seenPrefixes": sorted(seen_prefixes, key=lambda p: _KOR_HEADING_RANK.get(p, 99)),
                    }
                )
    return bad


def auditCode(code: str) -> dict[str, Any]:
    from dartlab import Company

    c = Company(code)
    sec = c.sections
    if sec is None:
        return {"code": code, "ok": False, "reason": "sections is None"}

    fragments = _fragmentHeadings(sec)
    mixes = _chapterMix(sec)
    inversions = _koreanOrderInversion(sec, code)

    return {
        "code": code,
        "rowCount": sec.height,
        "fragmentHeadings": fragments,
        "chapterMixes": mixes,
        "koreanInversions": inversions,
        "ok": (len(fragments) == 0 and len(mixes) == 0 and len(inversions) == 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes", help="comma-separated stock codes")
    parser.add_argument("--codes-from", help="path to text file with one code per line")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any violation")
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout")
    args = parser.parse_args()

    codes: list[str] = []
    if args.codes:
        codes.extend([c.strip() for c in args.codes.split(",") if c.strip()])
    if args.codes_from:
        path = Path(args.codes_from)
        if path.exists():
            codes.extend([ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()])
    if not codes:
        codes = ["005380", "005930", "035720", "207940", "000660"]

    results: list[dict[str, Any]] = []
    total_violations = 0
    for code in codes:
        try:
            r = auditCode(code)
        except Exception as exc:
            r = {"code": code, "ok": False, "error": str(exc)}
        v = (
            len(r.get("fragmentHeadings", []) or [])
            + len(r.get("chapterMixes", []) or [])
            + len(r.get("koreanInversions", []) or [])
        )
        total_violations += v
        results.append(r)
        if args.json:
            continue
        status = "OK" if r.get("ok") else "FAIL"
        print(
            f"[{status}] {code}: fragmentHeadings={len(r.get('fragmentHeadings', []) or [])} chapterMixes={len(r.get('chapterMixes', []) or [])} koreanInversions={len(r.get('koreanInversions', []) or [])}"
        )
        for f in (r.get("fragmentHeadings") or [])[:3]:
            print(f"    fragment: topic={f['topic']} bo={f['blockOrder']} L={f.get('textLevel')} path={f['textPath']}")
        for m in (r.get("chapterMixes") or [])[:3]:
            print(
                f"    chapterMix: topic={m['topic']} bo={m['blockOrder']} chapter={m['chapter']} marker={m['marker']} period={m['period']}"
            )
        for inv in (r.get("koreanInversions") or [])[:3]:
            print(f"    inversion: topic={inv['topic']} bo={inv.get('blockOrder')} {inv}")

    if args.json:
        print(
            json.dumps(
                {"codes": codes, "totalViolations": total_violations, "results": results}, ensure_ascii=False, indent=2
            )
        )
    else:
        print(f"\n=== TOTAL: {total_violations} violations across {len(codes)} codes ===")

    if args.strict and total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
