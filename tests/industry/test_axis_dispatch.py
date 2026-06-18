"""industry gather 표준 axis-dispatch — 옛 호출 ≡ 신 호출 backward-compat 골든.

industry 를 gather(axis, target) 표준으로 통일하되 옛 형식(industryId-first + 플래그 + 메서드)이
계속 동작하는지 고정. 신 형식 industry("summary","semiconductor") == 옛 industry("semiconductor",
summary=True) 동치.
"""

from __future__ import annotations

import pytest

from dartlab.industry import _AXIS_REGISTRY, Industry


def test_axis_registry_covers_flags_and_methods():
    """_AXIS_REGISTRY 가 옛 플래그 6종 + 메서드 3종(edges/map/theme)을 축으로 포함."""
    axes = set(_AXIS_REGISTRY)
    assert {"summary", "timeline", "lifecycle", "concentration", "dynamics", "polarization"} <= axes
    assert {"edges", "map", "theme"} <= axes


@pytest.mark.requires_data
def test_guide_and_backward_compat_industryId():
    """industry() 산업목록 가이드(불변) + industry("semiconductor") 옛 형식 동작."""
    ind = Industry()
    guide = ind()
    assert set(guide.columns) >= {"산업ID", "산업명", "공정수"}  # 옛 가이드 불변
    assert ind("semiconductor").height > 0  # 옛 industryId-first


@pytest.mark.requires_data
def test_old_flag_equals_new_axis():
    """옛 플래그 ≡ 신 축 — 동일 DataFrame."""
    ind = Industry()
    for axis in ("summary", "timeline", "lifecycle", "concentration", "dynamics", "polarization"):
        old = ind("semiconductor", **{axis: True})  # 옛: industry(id, flag=True)
        new = ind(axis, "semiconductor")  # 신: industry(axis, target)
        assert old.equals(new), f"{axis} 옛≠신"


@pytest.mark.requires_data
def test_method_equals_axis():
    """메서드 ≡ 축 — edges/theme 동일."""
    ind = Industry()
    assert ind.edges("semiconductor").equals(ind("edges", "semiconductor"))
    assert ind.theme("secondaryBattery").equals(ind("theme", "secondaryBattery"))
    assert ind.theme(stockCode="051910").equals(ind("theme", stockCode="051910"))


@pytest.mark.requires_data
def test_old_stage_positional_preserved():
    """옛 2번째 positional = stage 유지 — industry("semiconductor", "<stage>")."""
    ind = Industry()
    full = ind("semiconductor")
    stage = full["공정"][0] if "공정" in full.columns and full.height else None
    if stage:
        filtered = ind("semiconductor", stage)  # 옛: (industryId, stage)
        assert filtered.height <= full.height
