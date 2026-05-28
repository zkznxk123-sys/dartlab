"""news headlines enrich cron — Phase B (sentiment + topic).

`data/news/headlines/{market}/{date}.parquet` raw archive 읽기 → sentiment +
topic enrichment → `data/news/enriched/{market}/{date}.parquet` 별도 dir 저장.

실행::

    uv run python -X utf8 .github/scripts/sync/enrichNewsHeadlines.py --market KR --since 86400
    uv run python -X utf8 .github/scripts/sync/enrichNewsHeadlines.py --market KR --start 2026-05-01 --end 2026-05-28

raw archive (Phase A) 와 별도 dir — Phase A re-run 시 enriched 무효화 안 함.
sentiment 모델 미가용 시 LM-dict fallback 자동.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date as _date
from datetime import timedelta
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[3]
_log = logging.getLogger("enrichNewsHeadlines")

_RAW_ROOT = REPO_ROOT / "data" / "news" / "headlines"
_OUT_ROOT = REPO_ROOT / "data" / "news" / "enriched"


def _findRawFiles(market: str, since_seconds: float, start: str | None, end: str | None) -> list[Path]:
    """대상 raw parquet 리스트 — --since (mtime) 또는 --start/--end (date range)."""
    rawDir = _RAW_ROOT / market.upper()
    if not rawDir.exists():
        return []
    allFiles = sorted(rawDir.glob("*.parquet"))
    if start or end:
        s = _date.fromisoformat(start) if start else _date(1970, 1, 1)
        e = _date.fromisoformat(end) if end else _date.today()
        return [p for p in allFiles if s.isoformat() <= p.stem <= e.isoformat()]
    if since_seconds > 0:
        cutoff = time.time() - since_seconds
        return [p for p in allFiles if p.stat().st_mtime >= cutoff]
    # default — 최근 1 일
    yesterday = (_date.today() - timedelta(days=1)).isoformat()
    return [p for p in allFiles if p.stem >= yesterday]


def _enrichOne(rawPath: Path, market: str, model: str, nrTopics: int) -> tuple[Path, int]:
    """단일 일자 parquet enrich → enriched/{market}/{date}.parquet."""
    from dartlab.quant.text.newsSentiment import scoreNewsBatch
    from dartlab.quant.text.newsTopic import clusterNewsTopics

    df = pl.read_parquet(rawPath)
    if df.is_empty():
        return rawPath, 0
    df = scoreNewsBatch(df, market=market, model=model)
    df = clusterNewsTopics(df, market=market, nrTopics=nrTopics)

    outDir = _OUT_ROOT / market.upper()
    outDir.mkdir(parents=True, exist_ok=True)
    target = outDir / rawPath.name
    df.write_parquet(target)
    return target, df.height


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="news headlines enrich cron (Phase B)")
    parser.add_argument("--market", choices=["KR", "US"], required=True)
    parser.add_argument("--since", type=float, default=0, help="최근 N 초 mtime 변경분")
    parser.add_argument("--start", default=None, help="범위 시작 (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="범위 종료 (YYYY-MM-DD)")
    parser.add_argument("--model", default="auto", choices=["auto", "lm_dict"])
    parser.add_argument("--nr-topics", type=int, default=30)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    files = _findRawFiles(args.market, args.since, args.start, args.end)
    if not files:
        _log.warning(
            "대상 raw parquet 0 건 (market=%s, since=%s, range=%s~%s)", args.market, args.since, args.start, args.end
        )
        return 0
    _log.info("대상 %d 파일 (model=%s, nrTopics=%d)", len(files), args.model, args.nr_topics)

    total = 0
    for p in files:
        target, h = _enrichOne(p, args.market, args.model, args.nr_topics)
        _log.info("enriched %s → %s (rows=%d)", p.name, target, h)
        total += h
    _log.info("완료 — %d 파일, %d rows", len(files), total)

    # uploadData.py 호환
    distDir = REPO_ROOT / "dist"
    distDir.mkdir(parents=True, exist_ok=True)
    (distDir / "changed_newsEnriched.txt").write_text(
        "\n".join(f"{args.market}/{p.name}" for p in files) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
