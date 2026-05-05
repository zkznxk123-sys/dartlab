"""
실험 ID: 024
실험명: 우발부채·소송 섹션 탐색

목적:
- "우발부채 등에 관한 사항" 섹션의 구조와 테이블 패턴 파악
- 소송 건수, 소송금액, 진행상황 추출 가능성 확인
- 커버리지 확인

가설:
1. 220/267 이상이 우발부채 섹션 보유
2. 소송 테이블은 계류중/확정 소송, 소송금액, 원고/피고 구분 포함

방법:
1. 전체 기업의 section_title에서 "우발부채" 관련 섹션 탐색
2. 대표 기업의 섹션 내용 분석
3. 키워드/테이블 패턴 분류

결과 (실험 후 작성):
-

결론:
-

실험일: 2026-03-08
"""

import os
import re
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\MSI\OneDrive\Desktop\sideProject\dartlab\src")

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport


def exploreSectionTitles():
    """전체 기업의 우발부채 관련 섹션 타이틀 탐색."""
    codes = [f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")]

    titleCounter = Counter()
    hasSection = 0
    total = 0

    for code in codes:
        try:
            df = loadData(code)
        except Exception:
            continue
        total += 1

        years = sorted(df["year"].unique().to_list(), reverse=True)
        if not years:
            continue

        report = selectReport(df, years[0], reportKind="annual")
        if report is None:
            continue

        found = False
        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if re.search(r"우발부채|소송|채무보증|담보", title):
                titleCounter[title.strip()] += 1
                found = True

        if found:
            hasSection += 1

    print("\n=== 우발부채 관련 섹션 커버리지 ===")
    print(f"total: {total}, hasSection: {hasSection} ({hasSection/total*100:.1f}%)")
    print("\n--- 섹션 타이틀 빈도 ---")
    for title, count in titleCounter.most_common(20):
        print(f"  [{count:3d}] {title}")


def exploreContent(stockCode: str = "005930"):
    """특정 기업의 우발부채 섹션 내용 상세 탐색."""
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    print(f"\n=== {corpName} ({stockCode}) 우발부채 섹션 ===")

    for year in years[:2]:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        print(f"\n--- {year}년 ---")
        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if re.search(r"우발부채|채무보증|담보|소송", title):
                content = row.get("section_content", "") or ""
                print(f"  섹션: {title}")
                print(f"  길이: {len(content)}")

                # 테이블 블록
                lines = content.split("\n")
                tableBlocks = []
                current = []
                for line in lines:
                    if "|" in line:
                        current.append(line.strip())
                    else:
                        if current:
                            tableBlocks.append(current)
                            current = []
                if current:
                    tableBlocks.append(current)

                print(f"  테이블 블록 수: {len(tableBlocks)}")
                for i, block in enumerate(tableBlocks[:5]):
                    print(f"\n  [블록 {i+1}] ({len(block)} rows)")
                    for line in block[:6]:
                        print(f"    {line[:150]}")
                    if len(block) > 6:
                        print(f"    ... (총 {len(block)} rows)")

                # 텍스트 키워드
                kwCount = Counter()
                for kw in ["소송", "소 송", "원고", "피고", "손해배상", "담보", "보증", "채무",
                           "계류", "진행", "금액", "판결", "화해", "소취하", "기각", "항소", "상고",
                           "가. ", "나. ", "다. "]:
                    if kw in content:
                        kwCount[kw] += 1
                if kwCount:
                    print(f"  키워드: {dict(kwCount)}")


def exploreKeywordsCoverage():
    """키워드별 커버리지 확인."""
    codes = [f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")]
    keywords = Counter()
    sample = 0

    for code in codes:
        try:
            df = loadData(code)
        except Exception:
            continue

        years = sorted(df["year"].unique().to_list(), reverse=True)
        if not years:
            continue

        report = selectReport(df, years[0], reportKind="annual")
        if report is None:
            continue

        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if re.search(r"우발부채", title):
                content = row.get("section_content", "") or ""
                sample += 1
                for kw in ["소송", "원고", "피고", "담보", "보증", "채무보증", "금액",
                           "계류", "진행중", "지급보증", "채무인수"]:
                    if kw in content:
                        keywords[kw] += 1

    print(f"\n=== 키워드 빈도 (샘플: {sample}) ===")
    for kw, count in keywords.most_common():
        print(f"  [{count:3d}/{sample}] {kw}")


if __name__ == "__main__":
    exploreSectionTitles()
    exploreKeywordsCoverage()
    exploreContent("005930")  # 삼성전자
    exploreContent("005380")  # 현대차
    exploreContent("035720")  # 카카오
