"""공시 오리지널 수집 — DART(정기+비정기) document.xml zip 원본 백업.

gather 자체포함 모듈 — ``gather ↛ providers`` 규칙을 지키며 DART 인증 client·
경로·오케스트레이션을 **전부 본 패키지 안에** 둔다(core/providers 미의존,
사용자 결정 2026-06-03). DART 산출은 ``data/original/`` 로컬 백업(HF 미공개,
publish-ready-gated) — parquet 운영 방향을 바꿀 때 ground truth 재파생 테스트용.
EDGAR 는 raw ``.txt`` 를 저장하지 않고 panel 빌드 경로에서 메모리 fetch 후 즉시
``edgar/panel`` 로 쓴다.

진입점::

    from dartlab.gather.original import archiveDartOriginals
    archiveDartOriginals("20260601", "20260603", scope="nonperiodic")

    # CLI
    python -m dartlab.gather.original dart --start 20260601 --end 20260603 --scope nonperiodic
"""

from __future__ import annotations

from .dart import archiveDartOriginals
from .paths import dartDocsDir, dartFilingsDir, originalRoot

__all__ = [
    "archiveDartOriginals",
    "originalRoot",
    "dartDocsDir",
    "dartFilingsDir",
]
