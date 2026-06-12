"""GDELT 2.0 GKG backfill cron — Phase D 글로벌 5 년 백필 진입점.

http://data.gdeltproject.org/gdeltv2/ 의 15-min GKG 슬롯을 시간대 루프로
다운로드 → market 필터 → 일별 parquet 통합 → `data/news/gdelt/{market}/{date}.parquet`.

실행::

    # smoke (1 일, 6-시간 슬롯 = 4 fetch)
    uv run python -X utf8 .github/scripts/sync/syncGdeltBackfill.py --start 2026-05-27 --end 2026-05-27 --step-minutes 360

    # 30 일 (6-시간 슬롯, 120 fetch)
    uv run python -X utf8 .github/scripts/sync/syncGdeltBackfill.py --start 2026-04-28 --end 2026-05-28

    # 5 년 (heavy, ~7300 fetch, 24-시간 슬롯)
    uv run python -X utf8 .github/scripts/sync/syncGdeltBackfill.py --start 2021-05-28 --end 2026-05-28 --step-minutes 1440

GDELT 슬롯 빈도:
    15  → 모든 슬롯 (전수)
    60  → 시간당 1 슬롯 (24/day)
    360 → 6 시간당 1 슬롯 (4/day, narrative 충분)
    1440 → 일당 1 슬롯 (1/day, 가장 빠름)

ToS: GDELT 명시 학술+상업 무료 (https://www.gdeltproject.org/about.html).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date as _date
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[3]
_log = logging.getLogger("syncGdeltBackfill")

# 저장 경로·upsert 는 gather.sources.newsIo.writeDailyParquet 공유 (dir SSOT=newsSources).


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GDELT 2.0 GKG backfill cron")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD UTC")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD UTC (inclusive)")
    parser.add_argument(
        "--step-minutes",
        type=int,
        default=360,
        help="슬롯 간격 — 15(전수)/60(시간)/360(6h, default narrative 충분)/1440(일)",
    )
    parser.add_argument(
        "--markets",
        nargs="+",
        default=None,
        help="시장 필터 (KR US JP CN GLOBAL). 미지정 시 전체.",
    )
    parser.add_argument("--sleep", type=float, default=0.5, help="슬롯 간 sleep 초 (GDELT 부담 완화)")
    parser.add_argument("--max-slots", type=int, default=None, help="상한 (테스트용)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from dartlab.gather.sources.gdelt import fetchGdeltGkg, iterGdeltSlots

    startDt = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    endDt = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) + timedelta(hours=23, minutes=45)

    slots = iterGdeltSlots(startDt, endDt, stepMinutes=args.step_minutes)
    if args.max_slots:
        slots = slots[: args.max_slots]
    _log.info(
        "범위 %s~%s, %d 슬롯 (step=%d 분, markets=%s)",
        args.start,
        args.end,
        len(slots),
        args.step_minutes,
        args.markets or "전체",
    )

    if not slots:
        _log.warning("슬롯 0 — abort")
        return 1

    # 일자별 누적 — same day 의 여러 슬롯 결과를 한 parquet 으로 합침.
    dayBuffer: dict[tuple[str, _date], list[pl.DataFrame]] = {}

    for i, slot in enumerate(slots):
        df = fetchGdeltGkg(slot, markets=args.markets)
        if df.height == 0:
            _log.debug("슬롯 %s — 0 row", slot)
            time.sleep(args.sleep)
            continue
        # 슬롯 결과를 (market, day) 그룹으로 분리
        for (m, d), partDf in df.group_by(["market", "date"]):
            dayBuffer.setdefault((m, d), []).append(partDf)
        _log.info(
            "[%d/%d] %s → %d row (markets=%s)",
            i + 1,
            len(slots),
            slot.strftime("%Y-%m-%d %H:%M"),
            df.height,
            list(df["market"].unique().to_list()),
        )
        time.sleep(args.sleep)

    # 일자별 flush
    from dartlab.gather.sources.newsIo import writeDailyParquet
    from dartlab.gather.sources.newsSources import getNewsSource

    gdeltDir = getNewsSource("gdelt").dir
    totalAdded = 0
    for (m, d), frames in dayBuffer.items():
        combined = pl.concat(frames, how="diagonal_relaxed")
        target, total, added = writeDailyParquet(combined, dir=gdeltDir, market=m, day=d)
        totalAdded += added
        _log.info("저장 %s — total=%d added=%d", target, total, added)

    _log.info("완료 — %d (market, day) 파일, 신규 %d row", len(dayBuffer), totalAdded)

    # uploadData.py 호환
    distDir = REPO_ROOT / "dist"
    distDir.mkdir(parents=True, exist_ok=True)
    (distDir / "changed_newsGdelt.txt").write_text(
        "\n".join(f"{m}/{d.isoformat()}.parquet" for (m, d) in dayBuffer.keys()) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
