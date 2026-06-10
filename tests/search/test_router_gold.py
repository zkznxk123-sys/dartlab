"""결정론 라우터 gold 회귀 게이트 — events.json 시드의 LOO·held-out 라우팅 정확도.

unifiedSearchRecipe pipeline 회귀게이트(개선-or-동률)의 본진 이식: 실측 LOO 80.6% ·
held-out 70.8% 에서 baseline−margin (0.75−0.05 / 0.70−0.05) 미만으로 떨어지면 회귀 = FAIL.
gold = .github/scripts/search/questionSet/events.json (운영자 큐레이션 SSOT, report_nm 누수 0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_EVENTS_PATH = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "search" / "questionSet" / "events.json"

# pipeline.py 회귀 baseline (개선-or-동률만 통과)
LOO_BASELINE, HELDOUT_BASELINE, MARGIN = 0.75, 0.70, 0.05


def _loadEvents() -> dict:
    return json.loads(_EVENTS_PATH.read_text(encoding="utf-8"))["events"]


def test_events_gold_shape():
    """gold SSOT 구조 — 12 이벤트, 각각 router 시드·canon·held-out eval 보유."""
    events = _loadEvents()
    assert len(events) >= 12
    for ev, spec in events.items():
        assert spec["router"], ev
        assert spec["canon"], ev
        assert any(e["split"] == "heldout" for e in spec["eval"]), ev


def test_heldout_routing_accuracy():
    """held-out(구어·paraphrase) 질의 라우팅 정확도 ≥ baseline − margin."""
    from dartlab.providers.dart.search.router import buildRouterModel, predictEvent

    events = _loadEvents()
    model = buildRouterModel(events)
    total, correct = 0, 0
    for ev, spec in events.items():
        for e in spec["eval"]:
            if e["split"] != "heldout":
                continue
            total += 1
            if predictEvent(model, e["q"]) == ev:
                correct += 1
    assert total > 0
    acc = correct / total
    assert acc >= HELDOUT_BASELINE - MARGIN, f"held-out 라우팅 회귀: {acc:.3f} < {HELDOUT_BASELINE - MARGIN}"


def test_loo_routing_accuracy():
    """LOO(시드 1개 제외 후 그 시드 라우팅) 정확도 ≥ baseline − margin."""
    from dartlab.providers.dart.search.router import buildRouterModel, predictEvent

    events = _loadEvents()
    total, correct = 0, 0
    for ev, spec in events.items():
        for i, q in enumerate(spec["router"]):
            held = {
                name: {"router": [s for j, s in enumerate(sp["router"]) if not (name == ev and j == i)], "canon": []}
                for name, sp in events.items()
            }
            model = buildRouterModel(held)
            total += 1
            if predictEvent(model, q) == ev:
                correct += 1
    acc = correct / total
    assert acc >= LOO_BASELINE - MARGIN, f"LOO 라우팅 회귀: {acc:.3f} < {LOO_BASELINE - MARGIN}"


def test_predict_deterministic():
    """같은 질의는 항상 같은 라우팅 (결정론)."""
    from dartlab.providers.dart.search.router import buildRouterModel, predictEvent

    model = buildRouterModel(_loadEvents())
    q = "주주한테 돈 나눠주기로 한 곳"
    assert predictEvent(model, q) == predictEvent(model, q)


def test_unrouted_returns_none():
    """어느 이벤트와도 겹치지 않는 질의는 None (미라우팅 = plain 보존)."""
    from dartlab.providers.dart.search.router import buildRouterModel, predictEvent

    model = buildRouterModel(_loadEvents())
    assert predictEvent(model, "zzz qqq") is None
