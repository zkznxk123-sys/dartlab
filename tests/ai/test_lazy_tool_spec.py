"""_selectTools lazy narrowing 단위 — 마스터 플랜 v2 트랙 6 PR-L4.

recentlyUsed=None → 전체. recentlyUsed=set → _CORE ∪ recentlyUsed. 외부 호출 0.
"""

from __future__ import annotations

import pytest

from dartlab.ai.agent import _CORE_TOOL_NAMES, _DEFAULT_TOOL_NAMES, _lazyToolSpecEnabled, _selectTools

pytestmark = pytest.mark.unit


def _names(specs: list[dict]) -> set[str]:
    return {s["function"]["name"] for s in specs}


def test_selectTools_full_when_recentlyUsed_none() -> None:
    specs = _selectTools(_DEFAULT_TOOL_NAMES)
    assert _names(specs) == set(_DEFAULT_TOOL_NAMES)


def test_selectTools_narrow_to_core_when_recentlyUsed_empty() -> None:
    """recentlyUsed=set() (빈) → _CORE_TOOL_NAMES 와 default 교집합."""
    specs = _selectTools(_DEFAULT_TOOL_NAMES, recentlyUsed=set())
    out = _names(specs)
    assert out == _CORE_TOOL_NAMES & set(_DEFAULT_TOOL_NAMES)


def test_selectTools_narrow_with_recentlyUsed() -> None:
    """recentlyUsed={DCFValuation} → _CORE ∪ {DCFValuation} 와 default 교집합."""
    specs = _selectTools(_DEFAULT_TOOL_NAMES, recentlyUsed={"DCFValuation"})
    out = _names(specs)
    assert "DCFValuation" in out
    assert _CORE_TOOL_NAMES.issubset(out)
    # 사용 안 한 도구는 제외 (예: SensitivityAnalysis 가 default 인데 미사용)
    assert "SensitivityAnalysis" not in out


def test_selectTools_recentlyUsed_outside_default_ignored() -> None:
    """recentlyUsed 에 toolNames 에 없는 이름 끼면 silently 제외."""
    specs = _selectTools(_DEFAULT_TOOL_NAMES, recentlyUsed={"NoSuchTool"})
    out = _names(specs)
    assert "NoSuchTool" not in out


def test_selectTools_preserve_full_when_recentlyUsed_covers_all() -> None:
    specs = _selectTools(_DEFAULT_TOOL_NAMES, recentlyUsed=set(_DEFAULT_TOOL_NAMES))
    assert _names(specs) == set(_DEFAULT_TOOL_NAMES)


def test_core_tool_names_well_formed() -> None:
    assert isinstance(_CORE_TOOL_NAMES, frozenset)
    assert len(_CORE_TOOL_NAMES) >= 5
    # _CORE 의 모든 이름이 _DEFAULT 안에 있어야 narrowing 후에도 살아남는다
    assert _CORE_TOOL_NAMES.issubset(set(_DEFAULT_TOOL_NAMES))


def test_lazy_tool_spec_default_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DARTLAB_LAZY_TOOL_SPEC", raising=False)
    assert _lazyToolSpecEnabled() is True


def test_lazy_tool_spec_explicit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DARTLAB_LAZY_TOOL_SPEC", "0")
    assert _lazyToolSpecEnabled() is False
