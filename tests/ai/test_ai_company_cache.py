"""회사 캐시는 레거시 AI runtime이 아니라 엔진/데이터 계층이 소유한다."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_company_cache_runtime_is_removed():
    assert importlib.util.find_spec("dartlab.ai.runtime") is None


def test_engine_call_blocks_private_api():
    from dartlab.ai.tools.engineCall import engineCall

    result = engineCall({"apiRef": "Company._private", "target": "005930"})

    assert result.ok is False
    assert result.error == "private_api_blocked"
