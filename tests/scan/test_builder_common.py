"""Scan builder shared-runtime guards."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_configured_batch_size_uses_safe_env_override(monkeypatch):
    """CI can lower scan batch size without changing local/default builder behavior."""
    from dartlab.scan.builders.kr.common import configuredBatchSize

    monkeypatch.delenv("DARTLAB_SCAN_BATCH_SIZE", raising=False)
    assert configuredBatchSize() == 200

    monkeypatch.setenv("DARTLAB_SCAN_BATCH_SIZE", "50")
    assert configuredBatchSize() == 50

    monkeypatch.setenv("DARTLAB_SCAN_BATCH_SIZE", "0")
    assert configuredBatchSize() == 1

    monkeypatch.setenv("DARTLAB_SCAN_BATCH_SIZE", "not-an-int")
    assert configuredBatchSize() == 200


def test_release_native_memory_is_safe_to_call():
    """Allocator trimming is best-effort and must not break non-Linux local runs."""
    from dartlab.scan.builders.kr.common import releaseNativeMemory

    assert releaseNativeMemory() is None
