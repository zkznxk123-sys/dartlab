"""notesSplit 전사 검증 — KIND 전 종목에 splitNotesSections 적용 후 LazyFrame 집계.

목적:
    - splitNotesSections 의 N 추출 / sub-topic 매핑이 *어느 회사에서* 무너지는지 전수 파악.
    - parent topic 잔존 (split 실패) row 수집 + per-corp / per-N 미스매치 분포.

실행:
    uv run python -X utf8 tests/audit/notesSplitCensus.py
    uv run python -X utf8 tests/audit/notesSplitCensus.py --limit 200
    uv run python -X utf8 tests/audit/notesSplitCensus.py --market 유가

산출물 (gitignored):
    .dartlab/audit/notesSplitCensus/
        per_corp.parquet       — 회사별 요약 (parent_rows, matched_rows, unmatched_rows, distinct_N, sub_topic_count)
        unmatched_rows.parquet — split 실패 row 의 (code, name, topic, blockOrder, body_head) 샘플

집계 결과는 stdout 으로 LazyFrame summary 출력.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / ".dartlab" / "audit" / "notesSplitCensus"

_NOTES_PARENT_TOPICS = ("financialNotes", "consolidatedNotes")


def _patchOfflineMode() -> None:
    """data/dart/docs/*.parquet 가 이미 있으므로 freshness 체크 무력화 → 네트워크 0."""
    from dartlab.core import dataLoader, dataLoaderFreshness

    def _always_false(*args, **kwargs):
        return False

    # 두 module 모두 패치 (pipeline 이 dataLoader 의 _shouldRefreshDart 를 통해 호출).
    dataLoader._shouldRefreshDart = _always_false
    dataLoader._shouldRefreshHfCategory = _always_false
    dataLoaderFreshness.shouldRefreshDart = _always_false
    dataLoaderFreshness.shouldRefreshHfCategory = _always_false


def _periodCols(cols: list[str]) -> list[str]:
    import re

    annual = sorted([c for c in cols if re.fullmatch(r"\d{4}", c)], reverse=True)
    q4 = sorted([c for c in cols if re.fullmatch(r"\d{4}Q4", c)], reverse=True)
    other_q = sorted([c for c in cols if re.fullmatch(r"\d{4}Q[1-3]", c)], reverse=True)
    return annual + q4 + other_q


def _firstNonEmptyBody(row: dict, period_cols: list[str]) -> str | None:
    for p in period_cols:
        v = row.get(p)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _workerInit() -> None:
    """worker 프로세스에서 offline 패치 + dartlab 사전 import."""
    _patchOfflineMode()
    import dartlab  # noqa: F401  — 한번 import해서 lazy 비용 분산


def _workerTask(args: tuple[str, str]) -> tuple[dict | None, list[dict]]:
    code, name = args
    return _processOne(code, name)


def _processOne(code: str, name: str) -> tuple[dict | None, list[dict]]:
    """한 회사의 sections 빌드 + notesSplit 적용 후 미스매치 row 수집.

    Returns:
        (per_corp_summary, unmatched_rows). 데이터 없으면 (None, []).
    """
    from dartlab.providers.dart.builder.notesSplit import splitNotesSections
    from dartlab.providers.dart.docs.sectionsLegacy.pipeline import sections as _buildSections

    try:
        raw = _buildSections(code)
        if raw is None or raw.height == 0:
            return None, []
        parent_mask = pl.col("topic").is_in(_NOTES_PARENT_TOPICS)
        parent_rows = raw.filter(parent_mask).height
        if parent_rows == 0:
            return None, []

        split = splitNotesSections(raw)
        # split 후 parent topic 그대로 남은 row = N 추출 실패.
        unmatched_df = split.filter(pl.col("topic").is_in(_NOTES_PARENT_TOPICS))
        unmatched_rows = unmatched_df.height
        matched_rows = parent_rows - unmatched_rows

        sub_topic_pattern = r"^(?:financialNotes|consolidatedNotes)_\d{2}_"
        sub_topics = (
            split.filter(pl.col("topic").cast(pl.Utf8).str.contains(sub_topic_pattern)).select("topic").unique().height
        )

        # 미스매치 sample — body head 50자 + topic + blockOrder.
        period_cols = _periodCols(unmatched_df.columns)
        unmatched_samples: list[dict] = []
        for row in unmatched_df.head(20).to_dicts():
            body = _firstNonEmptyBody(row, period_cols) or ""
            unmatched_samples.append(
                {
                    "code": code,
                    "name": name,
                    "topic": row.get("topic"),
                    "blockOrder": row.get("blockOrder"),
                    "body_head": body[:80].replace("\n", " "),
                }
            )

        summary = {
            "code": code,
            "name": name,
            "parent_rows": parent_rows,
            "matched_rows": matched_rows,
            "unmatched_rows": unmatched_rows,
            "matched_pct": round(matched_rows / parent_rows * 100, 2) if parent_rows else 0.0,
            "sub_topic_count": sub_topics,
            "error": None,
        }
        return summary, unmatched_samples
    except Exception as e:
        return (
            {
                "code": code,
                "name": name,
                "parent_rows": -1,
                "matched_rows": -1,
                "unmatched_rows": -1,
                "matched_pct": 0.0,
                "sub_topic_count": -1,
                "error": f"{type(e).__name__}: {e}",
            },
            [],
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="0=전수, N=상위 N개")
    parser.add_argument("--market", default="", help="유가/코스닥/'' (전부)")
    parser.add_argument("--resume", action="store_true", help="기존 per_corp.parquet 의 code 는 skip")
    parser.add_argument("--workers", type=int, default=1, help="병렬 worker 수 (1=순차)")
    args = parser.parse_args()

    _patchOfflineMode()

    from dartlab.gather.krx.listing import getKindList

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    per_corp_pq = OUT_DIR / "per_corp.parquet"
    unmatched_pq = OUT_DIR / "unmatched_rows.parquet"

    kind = getKindList()
    if args.market:
        kind = kind.filter(pl.col("시장구분") == args.market)
    kind = kind.sort("종목코드")
    if args.limit > 0:
        kind = kind.head(args.limit)

    already: set[str] = set()
    if args.resume and per_corp_pq.exists():
        already = set(pl.read_parquet(per_corp_pq)["code"].to_list())
        print(f"[resume] skip {len(already)} corps already processed")

    rows = kind.select(["종목코드", "회사명"]).to_dicts()
    total = len(rows)
    print(f"[census] target={total} corps (market={args.market or 'ALL'}, limit={args.limit or 'NONE'})")

    summaries: list[dict] = []
    unmatched_all: list[dict] = []
    start = time.time()

    todo = [(row["종목코드"], row["회사명"]) for row in rows if row["종목코드"] not in already]
    total_todo = len(todo)

    if args.workers > 1:
        print(f"[parallel] workers={args.workers}")
        done = 0
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_workerInit) as ex:
            futures = {ex.submit(_workerTask, t): t for t in todo}
            for fut in as_completed(futures):
                code, name = futures[fut]
                done += 1
                try:
                    summary, unmatched = fut.result()
                except Exception as e:
                    print(f"  [{done}/{total_todo}] {code} {name} — FAIL: {e}")
                    continue
                if summary is None:
                    if done % 100 == 0:
                        elapsed = time.time() - start
                        rate = done / elapsed if elapsed else 0
                        eta = (total_todo - done) / rate if rate else 0
                        print(f"  [{done}/{total_todo}] no-notes — rate={rate:.1f}/s ETA={eta / 60:.0f}min")
                    continue
                summaries.append(summary)
                unmatched_all.extend(unmatched)
                marker = "OK" if summary.get("matched_pct", 0) >= 95 else "LOW"
                if done % 50 == 0 or marker == "LOW":
                    elapsed = time.time() - start
                    rate = done / elapsed if elapsed else 0
                    eta = (total_todo - done) / rate if rate else 0
                    print(
                        f"  [{done}/{total_todo}] {code} {name} — parent={summary['parent_rows']} "
                        f"matched={summary['matched_pct']}% sub={summary['sub_topic_count']} [{marker}] "
                        f"rate={rate:.1f}/s ETA={eta / 60:.0f}min"
                    )
                if len(summaries) >= 100:
                    _flush(summaries, unmatched_all, per_corp_pq, unmatched_pq)
                    summaries.clear()
                    unmatched_all.clear()
    else:
        for idx, (code, name) in enumerate(todo, 1):
            t0 = time.time()
            summary, unmatched = _processOne(code, name)
            gc.collect()
            if summary is None:
                if idx % 50 == 0:
                    elapsed = time.time() - start
                    print(f"  [{idx}/{total_todo}] {code} {name} — no notes (elapsed={elapsed:.0f}s)")
                continue
            summaries.append(summary)
            unmatched_all.extend(unmatched)
            dt = time.time() - t0
            marker = "OK" if summary.get("matched_pct", 0) >= 95 else "LOW"
            print(
                f"  [{idx}/{total_todo}] {code} {name} — parent={summary['parent_rows']} "
                f"matched={summary['matched_rows']} ({summary['matched_pct']}%) "
                f"sub={summary['sub_topic_count']} [{marker}] ({dt:.1f}s)"
            )
            if len(summaries) >= 50:
                _flush(summaries, unmatched_all, per_corp_pq, unmatched_pq)
                summaries.clear()
                unmatched_all.clear()

    if summaries or unmatched_all:
        _flush(summaries, unmatched_all, per_corp_pq, unmatched_pq)

    _summarize(per_corp_pq, unmatched_pq)
    return 0


def _flush(summaries: list[dict], unmatched: list[dict], per_corp_pq: Path, unmatched_pq: Path) -> None:
    if summaries:
        df = pl.DataFrame(summaries)
        if per_corp_pq.exists():
            old = pl.read_parquet(per_corp_pq)
            df = pl.concat([old, df], how="diagonal_relaxed")
        df.write_parquet(per_corp_pq)
    if unmatched:
        df = pl.DataFrame(unmatched)
        if unmatched_pq.exists():
            old = pl.read_parquet(unmatched_pq)
            df = pl.concat([old, df], how="diagonal_relaxed")
        df.write_parquet(unmatched_pq)


def _summarize(per_corp_pq: Path, unmatched_pq: Path) -> None:
    print("\n=== LazyFrame 집계 ===")
    if not per_corp_pq.exists():
        print("(no data)")
        return

    lf = pl.scan_parquet(per_corp_pq)
    agg = lf.select(
        [
            pl.len().alias("corps_with_notes"),
            pl.col("parent_rows").sum().alias("total_parent_rows"),
            pl.col("matched_rows").sum().alias("total_matched"),
            pl.col("unmatched_rows").sum().alias("total_unmatched"),
            (pl.col("matched_rows").sum() / pl.col("parent_rows").sum() * 100).round(2).alias("overall_pct"),
            (pl.col("matched_pct") >= 95).sum().alias("corps_ge_95"),
            (pl.col("matched_pct") < 80).sum().alias("corps_lt_80"),
            pl.col("error").is_not_null().sum().alias("corps_error"),
        ]
    ).collect()
    print(agg)

    print("\n=== matched_pct 분포 ===")
    bins = (
        lf.with_columns(
            pl.when(pl.col("matched_pct") >= 99)
            .then(pl.lit("99~100"))
            .when(pl.col("matched_pct") >= 95)
            .then(pl.lit("95~99"))
            .when(pl.col("matched_pct") >= 80)
            .then(pl.lit("80~95"))
            .when(pl.col("matched_pct") >= 50)
            .then(pl.lit("50~80"))
            .otherwise(pl.lit("<50"))
            .alias("bucket")
        )
        .group_by("bucket")
        .agg(pl.len().alias("corps"))
        .sort("bucket", descending=True)
        .collect()
    )
    print(bins)

    print("\n=== 미스매치 비율 상위 20 회사 ===")
    worst = lf.filter(pl.col("parent_rows") > 0).sort("matched_pct").head(20).collect()
    print(worst.select(["code", "name", "parent_rows", "matched_rows", "matched_pct", "sub_topic_count"]))

    if unmatched_pq.exists():
        print("\n=== body_head 패턴 빈도 top 30 (split 실패 row 의 첫 단어) ===")
        u_lf = pl.scan_parquet(unmatched_pq)
        head_freq = (
            u_lf.with_columns(pl.col("body_head").str.extract(r"^\s*(\S+)", 1).alias("first_token"))
            .group_by("first_token")
            .agg(pl.len().alias("rows"))
            .sort("rows", descending=True)
            .head(30)
            .collect()
        )
        print(head_freq)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[interrupted]")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
