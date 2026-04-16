"""Evidence — claim → source 강제 attribution (Phase 10 G1).

Bloomberg ASKB / AlphaSense 수준의 attribution 체계.
모든 숫자/주장에 evidence (공시 위치 + 계산 경로) 부착 가능.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Evidence:
    """주장 → 근거 attribution.

    Parameters
    ----------
    source : "disclosure" | "calc" | "peer" | "market"
        공시 / 계산식 / 동종사 / 시장 데이터
    period : 기준 기간 ("2025Q3" 등)
    quote : 근거 원문 발췌 (200자 이내 권장)
    location : 공시 내 위치 ("사업의 내용/III-2" 같은 네비게이션)
    url : 외부 링크 (공시 URL, calc 문서 등)
    """

    source: Literal["disclosure", "calc", "peer", "market", "docs"]
    period: str | None = None
    quote: str = ""
    location: str = ""
    url: str = ""


@dataclass
class EvidenceGraph:
    """여러 Evidence 를 묶는 그래프 — claim 당 N evidence.

    narrate 결과를 (text, evidence_list) 로 반환할 수 있음.
    """

    claim: str
    evidence: list[Evidence] = field(default_factory=list)

    def add(self, ev: Evidence) -> "EvidenceGraph":
        self.evidence.append(ev)
        return self

    def format_footnote(self) -> str:
        """각주 렌더링 — 보고서 하단에 표시."""
        if not self.evidence:
            return ""
        lines = []
        for i, ev in enumerate(self.evidence, 1):
            parts = [f"[{i}]", ev.source]
            if ev.period:
                parts.append(ev.period)
            if ev.location:
                parts.append(ev.location)
            if ev.quote:
                parts.append(f'"{ev.quote[:100]}"')
            if ev.url:
                parts.append(ev.url)
            lines.append(" · ".join(parts))
        return "\n".join(lines)


def buildCalcEvidence(calcName: str, period: str, inputs: dict) -> Evidence:
    """계산식 기반 evidence 생성 — 재현 가능성 보장.

    Examples
    --------
    >>> buildCalcEvidence("operatingMargin", "2025Q3",
    ...                   {"revenue": 1000, "operatingIncome": 150})
    Evidence(source='calc', period='2025Q3', quote='operatingMargin = 150 / 1000 = 15.0%', ...)
    """
    args_str = ", ".join(f"{k}={v}" for k, v in inputs.items())
    return Evidence(
        source="calc",
        period=period,
        quote=f"{calcName}({args_str})",
        location="core/finance/calc.py",
    )


def buildDisclosureEvidence(
    period: str,
    topic: str,
    quote: str,
    *,
    stockCode: str | None = None,
) -> Evidence:
    """공시 기반 evidence — DART/EDGAR 원문 인용."""
    loc = f"{topic}"
    if stockCode:
        loc = f"{stockCode} / {topic}"
    return Evidence(
        source="disclosure",
        period=period,
        quote=quote[:200],
        location=loc,
    )
