"""공시 오리지널 수집 — DART(정기+비정기) + EDGAR(전 form) 가공 0 원본 백업.

gather 자체포함 모듈 — ``gather ↛ providers`` 규칙을 지키며 DART 인증 client·EDGAR
fetch·경로·오케스트레이션을 **전부 본 패키지 안에** 둔다(core/providers 미의존,
사용자 결정 2026-06-03). 산출은 ``data/original/`` 로컬 백업(HF 미공개,
publish-ready-gated) — parquet 운영 방향을 바꿀 때 ground truth 재파생 테스트용.

진입점::

    from dartlab.gather.original import archiveDartOriginals, archiveEdgarOriginals
    archiveDartOriginals("20260601", "20260603", scope="nonperiodic")
    archiveEdgarOriginals(["AAPL"], forms=["8-K"], sinceYear=2024)

    # CLI
    python -m dartlab.gather.original dart  --start 20260601 --end 20260603 --scope nonperiodic
    python -m dartlab.gather.original edgar --tickers AAPL --forms 8-K --since-year 2024
"""

from __future__ import annotations

from .dart import archiveDartOriginals
from .edgar import archiveEdgarOriginals
from .paths import dartDocsDir, dartFilingsDir, edgarDir, originalRoot

__all__ = [
    "archiveDartOriginals",
    "archiveEdgarOriginals",
    "originalRoot",
    "dartDocsDir",
    "dartFilingsDir",
    "edgarDir",
]
