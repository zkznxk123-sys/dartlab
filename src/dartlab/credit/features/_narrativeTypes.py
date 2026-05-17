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
        """details를 연결된 문단으로 조합.

        Capabilities:
            summary + details 라인을 공백으로 join 한 단일 문단 반환. AI 답변 / UI 한 줄 요약에
            그대로 인용 가능한 형태.

        Returns:
            문단 텍스트. details 비면 summary 만.

        Raises:
            없음.

        Example:
            >>> AxisNarrative("유동성", "유동성은 양호하다.", ["현금비율 우수."]).toParagraph()
            '유동성은 양호하다. 현금비율 우수.'

        Guide:
            ``severityKr`` 라벨과 결합해 "유동성 [양호] — ..." 형태로 카드 라인 생성 가능.

        When:
            UI / Story / 답변에 narrative 한 줄 인용이 필요할 때.

        How:
            summary + details list 를 " " 로 join.

        Requires:
            - 외부 의존 없음.

        See Also:
            - ``dartlab.credit.features._narrativeTypes.AxisNarrative.severityKr`` : 한국어 라벨

        AIContext:
            AI 답변에 narrative 인용 시 본 메서드 결과 그대로 사용 가능.
        """
        if not self.details:
            return self.summary
        sentences = [self.summary] + self.details
        return " ".join(sentences)

    @property
    def severityKr(self) -> str:
        """severity 라벨의 한국어 표현.

        Raises:
            없음.

        Example:
            >>> AxisNarrative("유동성", "...", severity="strong").severityKr
            '우수'

        Requires:
            - 외부 의존 없음.
        """
        return {"strong": "우수", "adequate": "양호", "weak": "주의", "critical": "위험"}.get(
            self.severity, self.severity
        )


__all__ = ["AxisNarrative"]
