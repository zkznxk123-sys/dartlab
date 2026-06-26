"""증권사 리서치 메타 sync — gather 수집 + 월별 parquet write + changed manifest + HF push.

online sync (외부 게시판 → 로컬 parquet → HF). 별도빌드 금지: 스크랩·파싱·ticker 해소는
``gather.sources.brokerage`` 가 소유하고, 본 스크립트는 ``g.brokerageReports()`` 호출만 한다.
사용법: ``python syncBrokerageReports.py [--no-upload]`` (--no-upload = 로컬 빌드만, HF push 생략).
"""

from __future__ import annotations

import argparse

from dartlab.gather import getDefaultGather
from dartlab.gather.sources.brokerage.config import enabledBrokers
from dartlab.gather.sources.brokerage.fetch import _detectBroken
from dartlab.gather.sources.brokerage.io import writeMonthly
from dartlab.pipeline.changed import writeChanged
from dartlab.pipeline.hfUpload import uploadCategoryToHf

_CATEGORY = "brokerageReports"


def main() -> int:
    """enabled 증권사 메타 수집 → 월별 parquet write → manifest → (옵션) HF push. 반환 = exit code."""
    parser = argparse.ArgumentParser(description="증권사 리서치 메타 sync")
    parser.add_argument("--no-upload", action="store_true", help="HF push 생략 (로컬 빌드만)")
    args = parser.parse_args()

    gather = getDefaultGather()
    df = gather.brokerageReports()
    changed = writeMonthly(df)
    writeChanged(_CATEGORY, changed)
    print(f"[brokerageReports] {df.height} rows · {len(changed)} months changed: {changed}", flush=True)

    # 수율 가드 (PRD 03 §4) — enabled 인데 0행이면 셀렉터 깨짐 의심, 운영자에게 surface.
    counts = {row[0]: int(row[1]) for row in df.group_by("broker").len().iter_rows()} if df.height else {}
    print(f"[brokerageReports] 증권사별 수집: {counts}", flush=True)
    broken = _detectBroken(counts, list(enabledBrokers()))
    if broken:
        print(f"[brokerageReports] ⚠ 수율 0 — 셀렉터 깨짐 의심: {broken} (config selector 점검 필요)", flush=True)

    if changed and not args.no_upload:
        pushed = uploadCategoryToHf(_CATEGORY)
        print(f"[brokerageReports] HF push: {pushed} files", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
