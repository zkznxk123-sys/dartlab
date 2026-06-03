"""EDGAR stage — daily 벌크(companyfacts.zip) + 분기 데이터셋(sub/pre/tag) 동형.

edgarSync 의 daily core 2 스텝(inline python)을 충실 재현 — companyfacts bulk
download+convert + 최신 4 분기 discover/download/convert. force 플래그는 env
EDGAR_FORCE_COMPANYFACTS/EDGAR_FORCE_QUARTERLY. (docs/panel/scan 은 조건부·별 캐시라
별 스텝 유지.) build 만(로컬 parquet) — HF deploy 는 별 스텝.
"""

from __future__ import annotations

import os

from dartlab.pipeline.types import PipelineMode, StageResult


def _fourQuarters(year: int, quarter: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for i in range(4):
        q, y = quarter - i, year
        while q <= 0:
            q += 4
            y -= 1
        out.append((y, q))
    return out


def runEdgar(
    *, category: str = "edgar", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """EDGAR daily 벌크 + 분기 데이터셋 — providers.edgar.bulk(gather 위임) 동형 호출.

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: 미사용(build 만; HF deploy 는 별 스텝).
        token: 미사용.

    Returns:
        StageResult (bulk/quarterly 부분 실패는 격리 기록).

    Raises:
        없음.

    Example:
        >>> runEdgar()  # doctest: +SKIP
        StageResult(category='edgar', ...)
    """
    from dartlab.providers.edgar.bulk import (
        convertBulkToParquets,
        convertQuarterlyToParquets,
        discoverLatestQuarter,
        downloadCompanyfactsBulk,
        downloadQuarterlyDataset,
        listLocalQuarters,
    )

    res = StageResult(category="edgar")

    # 1. daily 벌크: companyfacts.zip → {cik}.parquet
    try:
        forceCf = os.environ.get("EDGAR_FORCE_COMPANYFACTS") == "true"
        zipPath = downloadCompanyfactsBulk(force=forceCf, progress=False)
        print(f"[pipeline] edgar companyfacts zip: {zipPath}", flush=True)
        print(f"[pipeline] edgar convert: {convertBulkToParquets(zipPath=zipPath, progress=False)}", flush=True)
        res.report.ok += 1
    except Exception as exc:  # noqa: BLE001 — bulk 실패 격리(quarterly 진행)
        res.report.err += 1
        res.report.failures.append(f"companyfacts: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgar companyfacts 실패(격리): {exc}", flush=True)

    # 2. 분기 벌크: 최신 4 분기 discover/download/convert
    try:
        forceQ = os.environ.get("EDGAR_FORCE_QUARTERLY") == "true"
        latest = discoverLatestQuarter()
        if latest is None:
            print("[pipeline] edgar 분기 감지 실패 — skip", flush=True)
            res.report.skip += 1
        else:
            have = set(listLocalQuarters(kind="sub"))
            for y, q in _fourQuarters(*latest):
                if not forceQ and (y, q) in have:
                    continue
                zp = downloadQuarterlyDataset(y, q, force=forceQ)
                if zp is None:
                    print(f"[pipeline] edgar {y}Q{q} 다운로드 실패", flush=True)
                    continue
                print(
                    f"[pipeline] edgar {y}Q{q}: {list(convertQuarterlyToParquets(y, q, zipPath=zp).keys())}", flush=True
                )
            res.report.ok += 1
    except Exception as exc:  # noqa: BLE001 — quarterly 실패 격리
        res.report.err += 1
        res.report.failures.append(f"quarterly: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgar quarterly 실패(격리): {exc}", flush=True)

    return res
