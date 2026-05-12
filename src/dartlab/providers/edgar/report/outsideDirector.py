"""사외이사 추출 — 10-K Item 10 텍스트 파싱.

DEF 14A proxy 없이도 10-K에서 이사회 구성을 추출할 수 있다.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company

_INDEPENDENT_PATTERN = re.compile(
    r"(?:^|\n)\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)"
    r".*?(?:independent|outside|non-executive)\s*(?:director|member)",
    re.IGNORECASE | re.DOTALL,
)


def extractOutsideDirector(company: "Company") -> pl.DataFrame | None:
    """사외이사 정보 추출.

    10-K Item 10 (Directors and Corporate Governance) 섹션에서
    independent director 언급을 파싱.

    Args:
        company: EDGAR Company 인스턴스.

    Returns:
        ``period/independentCount/totalDirectors`` 컬럼 DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> extractOutsideDirector(Company("AAPL"))

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    sections = company._docs.sections
    if isEmptyDf(sections):
        return None

    item10 = sections.filter(pl.col("topic").str.contains("(?i)item10|directors|corporateGovernance"))
    if item10.is_empty():
        return None

    periodCols = [
        c
        for c in item10.columns
        if c
        not in (
            "topic",
            "blockType",
            "blockOrder",
            "textNodeType",
            "textLevel",
            "textPath",
        )
    ]
    if not periodCols:
        return None

    latestPeriod = periodCols[-1]
    texts = item10[latestPeriod].drop_nulls().to_list()
    fullText = " ".join(str(t) for t in texts)

    # independent director 수 추정
    independentCount = len(re.findall(r"(?i)independent\s+director", fullText))
    totalBoard = len(re.findall(r"(?i)(?:director|member\s+of\s+the\s+board)", fullText))

    if independentCount == 0 and totalBoard == 0:
        return None

    return pl.DataFrame(
        [
            {
                "period": latestPeriod,
                "independentDirectors": independentCount if independentCount > 0 else None,
                "totalBoardMentions": totalBoard if totalBoard > 0 else None,
                "source": "10-K_text",
            }
        ]
    )
