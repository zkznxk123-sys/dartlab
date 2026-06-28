"""buildSectionSummary 견고성 게이트 — cosmetic 요약이 리포트를 죽이지 않음 (회귀).

배경: thread.title/flag 가 드물게 tuple 인 일부 회사(예 NAVER)에서 `" / ".join(parts)` 가
TypeError 로 buildStory 전체를 크래시 → reportModel skip. cosmetic 1줄 요약은 무크래시 우선.
"""

from __future__ import annotations

from types import SimpleNamespace

from dartlab.story.summary import buildSectionSummary


def test_section_summary_survives_tuple_thread_title():
    # thread.title 이 tuple 인 악성 입력 — 크래시 대신 str 반환(NAVER 회귀 가드).
    sec = SimpleNamespace(blocks=[], threads=[SimpleNamespace(title=("a", "b"))])
    out = buildSectionSummary(sec)
    assert isinstance(out, str), "tuple 섞여도 str 반환(무크래시)"


def test_section_summary_empty_when_no_parts():
    assert buildSectionSummary(SimpleNamespace(blocks=[], threads=[])) == ""


def test_section_summary_joins_metric_parts():
    from dartlab.story.blocks import MetricBlock

    sec = SimpleNamespace(blocks=[MetricBlock(metrics=[("ROIC", "9.9%"), ("WACC", "8.7%")])], threads=[])
    out = buildSectionSummary(sec)
    assert "ROIC 9.9%" in out and "WACC 8.7%" in out
