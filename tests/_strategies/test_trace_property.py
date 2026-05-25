"""ai/trace.AuditCollector hypothesis property — T6-1."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.mark.unit
class TestTraceProperty:
    """AuditCollector observe / dump / load property 5."""

    @settings(deadline=None)
    @given(n=st.integers(min_value=1, max_value=10))
    def test_observe_accumulates(self, n: int) -> None:
        from dartlab.ai.trace import AuditCollector

        c = AuditCollector(question="x")
        for i in range(n):
            c.observe("BRIEF", {"i": i})
        assert len(c.events) == n

    def test_observe_records_kind(self) -> None:
        kinds = ["BRIEF", "WORK", "CRITIQUE", "COMPOSE", "GATE", "HARVEST"]
        from dartlab.ai.trace import AuditCollector

        c = AuditCollector(question="x")
        for k in kinds:
            c.observe(k)
        recorded = [e["kind"] for e in c.events]
        assert recorded == kinds

    def test_to_dict_round_trip(self) -> None:
        from dartlab.ai.trace import AuditCollector

        c = AuditCollector(question="q", provider="dart", model="x")
        c.observe("BRIEF", {"msg": "hello"})
        d = c.toDict()
        assert d["question"] == "q"
        assert d["provider"] == "dart"
        assert len(d["events"]) == 1

    def test_dump_and_load_round_trip(self) -> None:
        from dartlab.ai.trace import AuditCollector

        c = AuditCollector(question="q")
        c.observe("WORK", {"refUsed": "x:1"})

        with TemporaryDirectory() as td:
            p = Path(td) / "trace.json"
            c.dumpToJson(p)
            loaded = json.loads(p.read_text(encoding="utf-8"))
            assert loaded["question"] == "q"
            assert len(loaded["events"]) == 1

    def test_session_id_unique(self) -> None:
        from dartlab.ai.trace import AuditCollector

        c1 = AuditCollector(question="a")
        c2 = AuditCollector(question="b")
        assert c1.sessionId != c2.sessionId
