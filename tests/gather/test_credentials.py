"""gather 자격증명 facade 회귀 — gather/credentials.py.

core SSOT(dataCredentials) 위의 thin facade: re-export 표면 + writeEnvExample +
doctor. 해석 로직 본체 테스트는 tests/core/test_data_credentials.py.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_reexport_surface() -> None:
    from dartlab.gather import credentials as gc

    for name in ("resolveKey", "getKey", "isConfigured", "credentialStatus", "formatStatus", "setCredential"):
        assert hasattr(gc, name), name
    # core 와 동일 객체를 노출 (별도 구현 아님)
    from dartlab.core.providers.dataCredentials import resolveKey as coreResolve

    assert gc.resolveKey is coreResolve


def test_writeEnvExample(tmp_path) -> None:
    from dartlab.gather.credentials import writeEnvExample

    out = writeEnvExample(tmp_path / ".env.example")
    text = out.read_text(encoding="utf-8")
    assert "DATA_GO_KR_KEY=" in text
    assert "FRED_API_KEY=" in text


def test_formatStatus_runs() -> None:
    from dartlab.gather.credentials import credentialStatus, formatStatus

    assert isinstance(credentialStatus(), list)
    assert "공급자" in formatStatus()
