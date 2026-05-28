"""sections wide-format 수평화 정합성 — 200 종목 generic 게이트.

`sectionsHorizontalAlign.py` 가 SK하이닉스 specific (textPath 이름·표 hash 그룹)
케이스로 검증한 4 조건을 **모든 종목 generic** 으로 일반화. 사용자 SSOT 200+ 종목
스케일 게이트.

4 조건 (generic):

1. **분기 disclaimer 단일 row** — `"※ 기업공시서식 작성기준에 따라 분기보고서에는 본
   항목을 기재하지 아니하였습니다."` 를 포함한 row 가 (topic) 당 ≤ 1 개.
   occurrence 카운터 분산 → > 1 회귀.

2. **표 row 안 header hash 충돌 0** — blockType=="table" row 각각이 period cell 들에서
   서로 다른 표 header hash 를 mix 하지 않는다 (옛/최근 *내용 다른* 표가 같은
   segmentKey 로 합쳐지는 회귀 차단). 같은 row 의 distinct non-empty hash ≤ 1.

3. **heading row 의 textPath 중복 0** — (topic, textPath) 당 blockType=="text" +
   textNodeType=="heading" row 가 latest annual cell 보유 시점에 ≤ 1 개.

4. **textPath 오염 0**:
   - 4a. textPath 에 raw HTML entity (`&cr`/`&amp`/`&lt`/`&gt`/`&nbsp`/`&quot`) 없음.
   - 4b. textPathKey 안 `@topic:` 카운트 ≤ 1 (alias stack 중복 누적 차단).

실행:
    uv run python -X utf8 tests/audit/sectionsHorizontalAlignBulk.py
    uv run python -X utf8 tests/audit/sectionsHorizontalAlignBulk.py --n 50   # 빠른 50 종목
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import sys
import time
from pathlib import Path

import polars as pl

from dartlab.providers.dart.docs.sectionsArchive.pipeline import (
    clearPreparedCache,
    sections,
)

_DOCS_DIR = Path("data/dart/docs")
_CORP_PROFILE = Path("data/dart/scan/corpProfile.parquet")

_DISCLAIMER_FRAGMENT_A = "기업공시서식"
_DISCLAIMER_FRAGMENT_B = "기재하지 아니하였습니다"

_HTML_ENTITY_PATTERNS = ("&cr", "&amp", "&lt", "&gt", "&nbsp", "&quot")

_DEFAULT_TOPICS = frozenset({"companyOverview", "companyHistory", "businessOverview"})


def _tableHeaderHash(md: str) -> str:
    """표 markdown 첫 데이터 행 cells 의 blake2b 4-byte hash."""
    for line in md.strip().split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip().lower() for c in stripped.strip("|").split("|")]
        if all(set(c) <= {"-", ":"} for c in cells if c):
            continue
        norm = tuple(sorted(c for c in cells if c))
        return hashlib.blake2b(str(norm).encode("utf-8"), digest_size=4).hexdigest()
    return "empty"


def _pickCandidates(n: int) -> list[str]:
    """corpProfile + docs parquet 보유 종목 중 n 개 stratified pick.

    KOSPI(K)·KOSDAQ(Y) 위주로 시가/시점 분산 골고루.
    """
    profile = pl.read_parquet(_CORP_PROFILE).filter(pl.col("stockCode").is_not_null())
    haveDocs = {p.stem for p in _DOCS_DIR.glob("*.parquet")}
    profile = profile.filter(pl.col("stockCode").is_in(list(haveDocs)))

    pickPerCls: dict[str, int] = {}
    if n >= 200:
        pickPerCls = {"K": 100, "Y": 60, "E": 30, "N": 10}
    else:
        ratio = n / 200
        pickPerCls = {
            "K": max(1, int(100 * ratio)),
            "Y": max(1, int(60 * ratio)),
            "E": max(1, int(30 * ratio)),
            "N": max(1, int(10 * ratio)),
        }

    selected: list[str] = []
    for cls, take in pickPerCls.items():
        bucket = profile.filter(pl.col("corp_cls") == cls).sort("stockCode")
        if bucket.height == 0:
            continue
        step = max(1, bucket.height // take)
        picked = bucket["stockCode"][::step][:take].to_list()
        selected.extend(picked)

    if len(selected) < n:
        more = profile.filter(~pl.col("stockCode").is_in(selected))["stockCode"].to_list()[: n - len(selected)]
        selected.extend(more)

    return selected[:n]


def _checkOneCompany(code: str, topics: frozenset[str]) -> tuple[list[str], dict[str, int]]:
    """1 종목 4 조건 검증. (failures, perTopicStats) 반환."""
    failures: list[str] = []
    stats = {"rows": 0, "topics": 0}

    try:
        df = sections(code, topics=set(topics))
    except Exception as exc:
        return [f"sections({code}) raise: {type(exc).__name__}: {exc}"], stats

    if df is None or df.height == 0:
        return [], stats

    stats["rows"] = df.height
    stats["topics"] = df["topic"].n_unique() if "topic" in df.columns else 0

    periodCols = [c for c in df.columns if len(c) >= 4 and c[:4].isdigit()]
    quarterPeriods = [c for c in periodCols if "Q" in c]
    annualPeriods = sorted([c for c in periodCols if "Q" not in c], reverse=True)
    latestAnnual = annualPeriods[0] if annualPeriods else None

    # 조건 1 — topic 당 분기 disclaimer row ≤ 1
    if quarterPeriods:
        disclaimerByTopic: dict[str, int] = {}
        for r in df.iter_rows(named=True):
            topic = str(r.get("topic") or "")
            for p in quarterPeriods:
                v = r.get(p)
                if v is None:
                    continue
                s = str(v)
                if _DISCLAIMER_FRAGMENT_A in s and _DISCLAIMER_FRAGMENT_B in s:
                    disclaimerByTopic[topic] = disclaimerByTopic.get(topic, 0) + 1
                    break
        for topic, count in disclaimerByTopic.items():
            if count > 1:
                failures.append(f"[{code}/{topic}] 조건 1 — 분기 disclaimer row {count} (≤ 1 기대)")

    # 조건 2 — 표 row 안 distinct non-empty header hash ≤ 1
    tableFrame = df.filter(pl.col("blockType") == "table") if "blockType" in df.columns else df.head(0)
    for r in tableFrame.iter_rows(named=True):
        hashes: set[str] = set()
        for p in periodCols:
            v = r.get(p)
            if v is None:
                continue
            h = _tableHeaderHash(str(v))
            if h != "empty":
                hashes.add(h)
        if len(hashes) > 1:
            failures.append(
                f"[{code}/{r.get('topic')}] 조건 2 — table row blockOrder={r.get('blockOrder')} "
                f"distinct header hash {len(hashes)} (≤ 1 기대)"
            )
            if len([f for f in failures if "조건 2" in f]) >= 3:
                break  # 종목당 같은 류 3 건이면 충분

    # 조건 3 — heading row 의 textPath 중복 (latest annual cell 보유 시점)
    if latestAnnual and "blockType" in df.columns and "textNodeType" in df.columns:
        headingFrame = df.filter(
            (pl.col("blockType") == "text") & (pl.col("textNodeType") == "heading") & pl.col(latestAnnual).is_not_null()
        )
        if headingFrame.height > 0:
            dup = headingFrame.group_by(["topic", "textPath"]).agg(pl.len().alias("n")).filter(pl.col("n") > 1)
            for r in dup.iter_rows(named=True):
                failures.append(
                    f"[{code}/{r['topic']}] 조건 3 — heading textPath='{r['textPath']}' "
                    f"row {r['n']} 분산 (latest={latestAnnual})"
                )
                if len([f for f in failures if "조건 3" in f]) >= 3:
                    break

    # 조건 4a — textPath HTML entity
    if "textPath" in df.columns:
        entityHits = 0
        for path in df["textPath"].drop_nulls().to_list():
            if any(p in path for p in _HTML_ENTITY_PATTERNS):
                entityHits += 1
        if entityHits > 0:
            failures.append(f"[{code}] 조건 4a — textPath HTML entity 잔존 {entityHits} 건")

    # 조건 4b — textPathKey 안 @topic: 중복
    if "textPathKey" in df.columns:
        aliasHits = 0
        for key in df["textPathKey"].drop_nulls().to_list():
            if str(key).count("@topic:") >= 2:
                aliasHits += 1
        if aliasHits > 0:
            failures.append(f"[{code}] 조건 4b — textPathKey @topic alias 중복 {aliasHits} 건")

    return failures, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="검증 종목 수 (default 200)")
    ap.add_argument("--clear-every", type=int, default=20, help="N 종목마다 prepared cache 해제")
    args = ap.parse_args()

    codes = _pickCandidates(args.n)
    print(f"[sections-bulk-align] {len(codes)} 종목 검증 시작 (topics={sorted(_DEFAULT_TOPICS)})")
    print(f"  K/Y/E/N 분포 확인 — first 10: {codes[:10]}")

    allFailures: list[str] = []
    totalRows = 0
    skipped = 0
    started = time.perf_counter()

    for idx, code in enumerate(codes, 1):
        try:
            failures, stats = _checkOneCompany(code, frozenset(_DEFAULT_TOPICS))
        except Exception as exc:  # noqa: BLE001
            failures = [f"sections({code}) outer raise: {type(exc).__name__}: {exc}"]
            stats = {"rows": 0, "topics": 0}

        totalRows += stats["rows"]
        if stats["rows"] == 0 and stats["topics"] == 0:
            skipped += 1

        if failures:
            allFailures.extend(failures)
            print(f"  [{idx:>3}/{len(codes)}] {code} — FAIL {len(failures)}")
            for f in failures[:3]:
                print(f"      {f}")
        else:
            if idx % 20 == 0 or idx == len(codes):
                elapsed = time.perf_counter() - started
                print(
                    f"  [{idx:>3}/{len(codes)}] {code} — OK (누적 {totalRows:,} rows, skip {skipped}, {elapsed:.0f}s)"
                )

        if idx % args.clear_every == 0:
            clearPreparedCache()
            gc.collect()

    clearPreparedCache()
    elapsed = time.perf_counter() - started
    print()
    print(f"[sections-bulk-align] {len(codes)} 종목 — {elapsed:.0f}s, 누적 {totalRows:,} rows, skip {skipped}")
    if not allFailures:
        print("[sections-bulk-align] OK — 4 조건 모두 통과")
        return 0

    print(f"[sections-bulk-align] FAIL — {len(allFailures)} 건:")
    byKind: dict[str, int] = {}
    for f in allFailures:
        kind = (
            "조건 1"
            if "조건 1" in f
            else (
                "조건 2"
                if "조건 2" in f
                else (
                    "조건 3"
                    if "조건 3" in f
                    else (
                        "조건 4a"
                        if "조건 4a" in f
                        else ("조건 4b" if "조건 4b" in f else ("raise" if "raise" in f else "기타"))
                    )
                )
            )
        )
        byKind[kind] = byKind.get(kind, 0) + 1
    for kind, count in sorted(byKind.items()):
        print(f"  {kind:<10}: {count}")
    print()
    print("샘플 실패 (상위 10):")
    for f in allFailures[:10]:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
