"""resolveOutcomes ops script smoke — import 가능 + empty sweep + 가짜 pending sweep.

`.github/scripts/ops/resolveOutcomes.py` 는 운영자 로컬 cron 용. CI runner 에는
decisions 가 없으므로 본 테스트는 *script 자체의 무결성* 만 검증.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "ops" / "resolveOutcomes.py"


def _loadScript():
    """ops 스크립트 동적 import — sys.path 변경 없이."""
    spec = importlib.util.spec_from_file_location("resolveOutcomes", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["resolveOutcomes"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_script_file_exists():
    assert _SCRIPT_PATH.exists(), f"ops 스크립트 누락: {_SCRIPT_PATH}"


@pytest.mark.unit
def test_script_imports_and_has_main():
    module = _loadScript()
    assert hasattr(module, "main")
    assert callable(module.main)


@pytest.mark.unit
def test_resolve_decisions_root_prefers_explicit_env(tmp_path, monkeypatch):
    module = _loadScript()
    monkeypatch.setenv("DARTLAB_DECISIONS_ROOT", str(tmp_path))
    monkeypatch.delenv("DARTLAB_HOME", raising=False)
    assert module._resolveDecisionsRoot() == tmp_path


@pytest.mark.unit
def test_resolve_decisions_root_falls_back_to_dartlab_home(tmp_path, monkeypatch):
    module = _loadScript()
    monkeypatch.delenv("DARTLAB_DECISIONS_ROOT", raising=False)
    monkeypatch.setenv("DARTLAB_HOME", str(tmp_path))
    assert module._resolveDecisionsRoot() == tmp_path / "decisions"


@pytest.mark.unit
def test_main_returns_0_on_missing_root(tmp_path, monkeypatch, capsys):
    module = _loadScript()
    monkeypatch.setenv("DARTLAB_DECISIONS_ROOT", str(tmp_path / "missing"))
    rc = module.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "decisions root" in out


@pytest.mark.unit
def test_main_sweeps_empty_dir_and_reports_zero(tmp_path, monkeypatch, capsys):
    module = _loadScript()
    (tmp_path / "KR").mkdir()
    monkeypatch.setenv("DARTLAB_DECISIONS_ROOT", str(tmp_path))
    rc = module.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 entries 전이" in out


@pytest.mark.unit
def test_main_sweeps_decisions_with_pending_no_pricer_for_us(tmp_path, monkeypatch, capsys):
    """US 종목은 defaultPriceLookup 가 미구현 — pricer None 으로 호출되어 0 resolved."""
    module = _loadScript()
    us_dir = tmp_path / "US"
    us_dir.mkdir()
    (us_dir / "AAPL.md").write_text(
        "[2024-01-01 | AAPL | Verdict | pending]\n\nDECISION:\nholdvar\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DARTLAB_DECISIONS_ROOT", str(tmp_path))
    rc = module.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "1 파일 검사" in out
    assert "0 entries 전이" in out  # US 는 pricer None
