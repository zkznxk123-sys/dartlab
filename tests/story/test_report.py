"""P2 리포트 emitter 게이트 — Story 블록 → 계약 ReportBlock 매핑 + pro 블록 합성 (offline).

플랜 SSOT: mainPlan/professional-report-engine/03-report-engine-architecture.md §2.3.
buildReportModel 은 self-calc 0 — 본 파일은 순수 매핑 헬퍼(_mapBlock·_valuationView·
_scenarioSet·_buildThesis)를 합성 입력으로 검증. company 데이터 의존 end-to-end 는 CI.
"""

from __future__ import annotations

from types import SimpleNamespace

from dartlab.story.blocks import FlagBlock, HeadingBlock, MetricBlock, TableBlock, TextBlock
from dartlab.story.report import _buildThesis, _mapBlock, _scenarioSet, _valuationView


class _FakeDf:
    """to_dicts 만 흉내내는 경량 DataFrame 스텁(테스트용)."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def to_dicts(self) -> list[dict]:
        """행 dict 리스트 반환."""
        return self._rows


# ── 블록 매핑 (legacy 6 → 계약 8) ──


def test_map_heading_and_text():
    assert _mapBlock(HeadingBlock(title="수익체력")) == {"type": "heading", "title": "수익체력"}
    assert _mapBlock(TextBlock(text="요약")) == {"type": "text", "text": "요약"}
    assert _mapBlock(TextBlock(text="")) is None, "빈 text 는 graceful None"


def test_map_metrics_and_flags():
    m = _mapBlock(MetricBlock(metrics=[("ROIC", "9.9%"), ("WACC", "7.7%")]))
    assert m == {"type": "metrics", "metrics": [{"label": "ROIC", "value": "9.9%"}, {"label": "WACC", "value": "7.7%"}]}
    f = _mapBlock(FlagBlock(flags=["부채 급증"], kind="warning"))
    assert f == {"type": "flags", "kind": "warning", "flags": ["부채 급증"]}
    fo = _mapBlock(FlagBlock(flags=["현금 풍부"], kind="opportunity"))
    assert fo["kind"] == "opportunity"


def test_map_table_stringifies_cells():
    t = _mapBlock(TableBlock(label="요약", df=_FakeDf([{"연도": 2024, "매출": None}])))
    assert t["type"] == "table"
    assert t["data"] == [{"연도": "2024", "매출": ""}], "None=빈칸, 숫자=문자열"


# ── pro 블록 합성 ──


def test_valuation_view_from_dfv():
    dfv = {
        "dFV": 196337,
        "currentPrice": 80000,
        "primaryModel": "dcf2stage",
        "qualityWACC": {"adjustedWACC": 7.72},
        "reinvestmentCheck": {"fundamentalGrowth": 8.91, "reinvestRate": 0.9, "roic0": 9.9},
        "reverseDcf": {"impliedGrowth": 12.0, "supportedGrowth": 8.91, "verdict": "시장 과대 성장 반영"},
    }
    v = _valuationView(dfv)
    assert v["model"] == "DCF"
    assert v["intrinsic"] == 196337 and v["current"] == 80000
    assert v["wacc"] == 7.72 and v["g"] == 8.91 and v["roic"] == 9.9
    assert v["reverseDcf"]["impliedGrowth"] == 12.0
    assert {"label": "내재가치", "value": 196337} in v["bridge"]


def test_valuation_view_none_on_no_intrinsic():
    assert _valuationView({"dFV": None}) is None
    assert _valuationView({"dFV": 0}) is None, "0/음수 내재가치 = None"


def test_scenario_set_legs_and_upside():
    dfv = {"scenarios": {"bear": 172777, "base": 196337, "bull": 219897}, "currentPrice": 100000}
    s = _scenarioSet(dfv)
    assert [leg["key"] for leg in s["legs"]] == ["bear", "base", "bull"]
    base = next(leg for leg in s["legs"] if leg["key"] == "base")
    assert base["intrinsic"] == 196337 and base["upside"] == 96.3, "upside = (iv-cur)/cur×100"


def test_scenario_set_none_without_base():
    assert _scenarioSet({"scenarios": {}}) is None


# ── thesis 합성 ──


def test_thesis_pillars_and_call():
    card = SimpleNamespace(
        conclusion="자본이 지속 가치 창출",
        strengths=["ROIC 9.9% > WACC 7.7%", "FCF 흑자 지속", "부채 통제", "4번째(잘림)"],
        warnings=["메모리 사이클 변동"],
        grades={},
    )
    view = {"intrinsic": 196337, "current": 80000}
    th = _buildThesis(card, view)
    assert th["central"] == "자본이 지속 가치 창출"
    assert len(th["pillars"]) == 3, "기둥 최대 3"
    assert th["bearCase"] == "메모리 사이클 변동"
    assert th["call"] is not None and "196,337" in th["call"]


def test_thesis_none_when_empty():
    assert _buildThesis(SimpleNamespace(conclusion="", strengths=[], warnings=[], grades={}), None) is None
