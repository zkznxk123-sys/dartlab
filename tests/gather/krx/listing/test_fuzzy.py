"""dartlab.gather.krx.listing.fuzzy mirror 슬롯 — smoke import (P-G7.2).

룰 7 (src↔tests 1:1 mirror) 만족용 placeholder. 본격 단위 테스트는 후속.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.krx.listing.fuzzy`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.krx.listing.fuzzy")
