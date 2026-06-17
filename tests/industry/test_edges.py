"""Industry.edges() DataFrame 컬럼 unit 테스트 — 거래액/의존도(%) evidence 노출 (Killer#2).

실 edges.json 의존 X — pipeline.loadEdges 를 monkeypatch (합성 IndustryEdge). 추출 누락은
None 보존(0 채움 금지) 검증.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def _edge(fromCode, toCode, industry, amount=None, ratio=None, edgeType="supplier"):
    from dartlab.industry.types import IndustryEdge

    return IndustryEdge(
        fromCode=fromCode,
        fromName=f"c-{fromCode}",
        toCode=toCode,
        toName=f"c-{toCode}",
        edgeType=edgeType,
        industry=industry,
        confidence=0.9,
        source="docs_table",
        evidence="주요 매입처",
        amount=amount,
        ratio=ratio,
    )


class TestEdgesColumns:
    def test_amount_ratio_columns_present_and_null_preserved(self, monkeypatch):
        """거래액·의존도(%) 컬럼 노출 + 추출 누락은 None (0 채움 금지)."""
        from dartlab.industry import Industry
        from dartlab.industry.build import pipeline

        monkeypatch.setattr(
            pipeline,
            "loadEdges",
            lambda: [
                _edge("A", "B", "auto", amount=120.0, ratio=91.4),
                _edge("C", "D", "auto", amount=None, ratio=None),  # 추출 누락분
            ],
        )
        df = Industry().edges(industryId="auto")
        assert "거래액" in df.columns
        assert "의존도(%)" in df.columns
        rows = df.to_dicts()
        assert rows[0]["거래액"] == 120.0
        assert rows[0]["의존도(%)"] == 91.4
        # 누락은 None — 0 으로 채우면 거짓 evidence
        assert rows[1]["거래액"] is None
        assert rows[1]["의존도(%)"] is None

    def test_empty_result_keeps_columns(self, monkeypatch):
        """매칭 0 이어도 거래액·의존도(%) 컬럼 스키마 유지 (소비자 계약)."""
        from dartlab.industry import Industry
        from dartlab.industry.build import pipeline

        monkeypatch.setattr(pipeline, "loadEdges", lambda: [])
        df = Industry().edges(industryId="none")
        assert df.height == 0
        assert "거래액" in df.columns
        assert "의존도(%)" in df.columns
