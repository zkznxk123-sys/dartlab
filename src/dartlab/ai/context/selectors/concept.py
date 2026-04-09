"""Concept selector: dartlab 사용법/API 안내."""
from __future__ import annotations
from typing import Any
from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.encoder import estimateTokens

_CAPABILITIES_SUMMARY = """dartlab 주요 API:
- dartlab.Company("종목코드") → 회사 facade (show/select/analysis/review)
- c.show("IS") / c.show("BS") / c.show("CF") — 재무제표
- c.select("IS", ["매출액"]) — 행 필터
- c.analysis("수익성") — 14축 재무분석
- c.review("수익성") — 보고서
- c.credit() — 신용평가
- dartlab.scan("profitability") — 전종목 횡단분석
- dartlab.gather("price", "005930") — 주가
- dartlab.gather("macro") — 거시지표
- dartlab.search("유상증자") — 공시 검색
- dartlab.ask("질문") — AI 분석
- dartlab.listing() — 종목 리스트
"""


def selectConcept(question: str) -> list[ContextPart]:
    """dartlab API 요약을 컨텍스트에 주입."""
    text = (
        '<context source="capabilities">\n'
        f"{_CAPABILITIES_SUMMARY}\n"
        "</context>"
    )
    return [ContextPart(
        key="concept.capabilities",
        text=text,
        priority=PartPriority.HIGH,
        estimatedTokens=estimateTokens(text),
        source="capabilities",
    )]
