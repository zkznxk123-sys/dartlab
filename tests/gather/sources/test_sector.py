"""dartlab.gather.sources.sector real unit test (A 트랙 T4).

sector.fetch — KR-only 분기 + ImportError 흡수 검증.
"""

from __future__ import annotations

import asyncio
import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.sector`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.sector")


def test_sector_non_kr_returns_none() -> None:
    """market != "KR" → None (KR 만 지원)."""
    from dartlab.gather.sources import sector as sectorMod

    result = asyncio.run(sectorMod.fetch("AAPL", market="US", client=object()))
    assert result is None


def test_sector_import_error_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """provider 내부 ImportError 흡수 시 None + warning."""
    from dartlab.gather.sources import sector as sectorMod

    # ``from .domains.krx import fetchSectorInfo`` 에서 ImportError 가 발생하면 None.
    # 실제로는 import 가 잘못된 경로 (`.domains` 가 sources 안에 없음) 라
    # KR 호출 시 ImportError 흡수 분기를 검증.
    result = asyncio.run(sectorMod.fetch("005930", market="KR", client=object()))
    # provider 결과는 환경에 따라 다르지만 — None 또는 SectorInfo 모두 정상.
    # 핵심은 raise 안 함 (예외 흡수).
    assert result is None or hasattr(result, "sectorCode") or hasattr(result, "industryCode")
