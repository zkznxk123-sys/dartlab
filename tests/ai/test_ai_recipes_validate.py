"""validateRefs unit — refs ↔ requiredEvidence 매칭 검증 (graph node X).

본 테스트는 src/dartlab/ai/recipes/validate.py 가 stateless 인지, kind 추론이 dict / dataclass
/ id-string 모두 처리하는지 확인.
"""

from __future__ import annotations

import pytest

from dartlab.ai.contracts import Ref
from dartlab.ai.recipes import validateRefs

pytestmark = pytest.mark.unit


def test_returns_ok_when_all_required_kinds_present():
    refs = [
        {"id": "skill:recipes.credit.distressDual", "kind": "skillRef"},
        {"id": "table:bs_2025", "kind": "tableRef"},
        {"id": "value:zpp_2025", "kind": "valueRef"},
        {"id": "date:2025-12-31", "kind": "dateRef"},
    ]
    result = validateRefs(refs, ["skillRef", "tableRef", "valueRef", "dateRef"])
    assert result.ok
    assert result.missing == []
    assert sorted(result.present) == ["dateRef", "skillRef", "tableRef", "valueRef"]


def test_returns_missing_when_kind_absent():
    refs = [{"id": "skill:x", "kind": "skillRef"}]
    result = validateRefs(refs, ["skillRef", "tableRef", "valueRef"])
    assert not result.ok
    assert result.missing == ["tableRef", "valueRef"]
    assert result.present == ["skillRef"]


def test_handles_ref_dataclass_input():
    refs = [
        Ref(id="table:foo", kind="tableRef", title="t"),
        Ref(id="value:bar", kind="valueRef", title="v"),
    ]
    result = validateRefs(refs, ["tableRef", "valueRef"])
    assert result.ok


def test_falls_back_to_id_prefix_when_kind_missing():
    """legacy 호출자가 id 만 넘기는 경로 — prefix 매핑 fallback."""
    refs = [{"id": "table:foo"}, {"id": "value:bar"}, {"id": "date:2025"}]
    result = validateRefs(refs, ["tableRef", "valueRef", "dateRef"])
    assert result.ok


def test_id_only_string_inputs():
    """ref 가 그냥 문자열 id 일 때도 prefix 추론."""
    result = validateRefs(["skill:s", "table:t"], ["skillRef", "tableRef"])
    assert result.ok


def test_empty_required_returns_ok_with_empty_missing():
    result = validateRefs([{"id": "x", "kind": "skillRef"}], [])
    assert result.ok
    assert result.missing == []


def test_extras_lists_kinds_in_refs_not_required():
    refs = [
        {"id": "skill:x", "kind": "skillRef"},
        {"id": "exec:y", "kind": "executionRef"},
    ]
    result = validateRefs(refs, ["skillRef"])
    assert result.ok
    assert result.extras == ["executionRef"]
    assert result.present == ["skillRef"]


def test_none_refs_treated_as_empty():
    result = validateRefs(None, ["skillRef"])
    assert not result.ok
    assert result.missing == ["skillRef"]


def test_unknown_id_prefix_falls_through_silently():
    refs = [{"id": "weird:thing"}]
    result = validateRefs(refs, ["skillRef"])
    assert not result.ok
    assert result.missing == ["skillRef"]
