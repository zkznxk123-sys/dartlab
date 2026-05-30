"""zipScanWorker mirror — 공개 심볼 import-smoke (데이터 0).

``gather/dart/panel/build/refScan/zipScanWorker.py`` 의 1:1 mirror. 전 corpus refScan
진입점(scanAllZips/scanRefBaseline/scanZipFiles)이 존재·callable 인지 확인. 실 스캔은
로컬 zip(102k) 필요 → ref 생산 경로 검증. import 회귀 가드.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_zip_scan_worker_symbols_callable() -> None:
    """scanAllZips / scanRefBaseline / scanZipFiles 공개표면 존재 + callable."""
    from dartlab.gather.dart.panel.build.refScan import scanAllZips, scanRefBaseline, scanZipFiles

    assert callable(scanAllZips)
    assert callable(scanRefBaseline)
    assert callable(scanZipFiles)
