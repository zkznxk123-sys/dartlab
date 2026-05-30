"""연결재무제표 주석 섹션 추출 공통 유틸."""

import re

import polars as pl


def extractNotesContent(report: pl.DataFrame) -> list[str]:
    """보고서에서 연결재무제표 주석 섹션 내용 추출.

    Args:
        report: ``section_title`` · ``section_content`` 컬럼이 포함된 보고서 DataFrame.

    Returns:
        ``"연결재무제표"`` + ``"주석"`` 매칭 섹션 본문 multiline 문자열 목록. 매칭 0 시 빈 리스트.

    Raises:
        없음.

    Example:
        >>> extractNotesContent(report)
        ['1. 매출 관련 ...', ...]
    """
    section = report.filter(
        pl.col("section_title").str.contains("연결재무제표") & pl.col("section_title").str.contains("주석")
    )
    if section.height == 0:
        return []
    return section["section_content"].to_list()


def findNumberedSection(contents: list[str], keyword: str) -> str | None:
    """번호 매긴 섹션에서 keyword 포함 섹션 텍스트 반환.

    Args:
        contents: 섹션 본문 목록 (각 원소 = 마크다운 multiline 문자열).
        keyword: 검색할 키워드 (섹션 제목에 포함되는 substring).

    Returns:
        매칭 섹션의 본문 multiline 문자열. 매칭 0 시 ``None``.

    Raises:
        없음.

    Example:
        >>> findNumberedSection(["1. 매출 ..."], "매출")
        '1. 매출 ...'
    """
    for content in contents:
        lines = content.split("\n")
        startIdx = None
        endIdx = None
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("|"):
                continue
            m = re.match(r"^(\d{1,2})\.\s+(.+)", s)
            if m:
                title = m.group(2).strip()
                if keyword in title:
                    startIdx = i
                elif startIdx is not None and endIdx is None:
                    endIdx = i
                    break
        if startIdx is not None:
            if endIdx is None:
                endIdx = len(lines)
            return "\n".join(lines[startIdx:endIdx])
    return None
