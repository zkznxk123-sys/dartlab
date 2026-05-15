"""credit/features/narrative 결과 타입 — AxisNarrative dataclass.

credit/features/narrative.py 가 960 줄 god module 이라 type 분리.
identity 보존을 위해 narrative.py 가 본 모듈에서 re-export.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AxisNarrative:
    """축별 서사."""

    axisName: str
    summary: str
    details: list[str] = field(default_factory=list)
    severity: str = "adequate"  # strong | adequate | weak | critical

    def toParagraph(self) -> str:
        """details를 연결된 문단으로 조합."""
        if not self.details:
            return self.summary
        sentences = [self.summary] + self.details
        return " ".join(sentences)

    @property
    def severityKr(self) -> str:
        """severity 라벨의 한국어 표현."""
        return {"strong": "우수", "adequate": "양호", "weak": "주의", "critical": "위험"}.get(
            self.severity, self.severity
        )


__all__ = ["AxisNarrative"]
