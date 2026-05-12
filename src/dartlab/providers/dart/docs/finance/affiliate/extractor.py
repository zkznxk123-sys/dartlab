"""관계기업 주석 테이블 파싱 유틸."""

import re


def parseTableRows(text: str) -> list[list[str]]:
    """마크다운 테이블 행 추출. XBRL 패딩 제거.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> parseTableRows(...)

    Returns:
        <TODO: return desc> (list[list[str]])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - <TODO: external requires>

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
    rows = []
    for line in text.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        # 후행 빈 셀 제거 (XBRL 패딩)
        while cells and not cells[-1]:
            cells.pop()
        if not cells:
            continue
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        if not any(c.strip() for c in cells):
            continue
        rows.append(cells)
    return rows
