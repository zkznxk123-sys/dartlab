"""레거시 AI runtime 제거 계약 테스트."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_ai_runtime_package_is_not_available():
    assert importlib.util.find_spec("dartlab.ai.runtime") is None
