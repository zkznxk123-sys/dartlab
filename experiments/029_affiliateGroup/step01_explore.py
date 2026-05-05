"""
실험 ID: 029
실험명: 계열회사 현황(상세) 탐색

목적:
- "계열회사 현황(상세)" 섹션의 구조 파악
- 테이블 패턴 조사 (계열사 수, 상장/비상장, 지분율)
- 267개 배치에서 섹션 존재율 및 테이블 형태 확인

가설:
1. 98% 이상에서 "계열회사 현황(상세)" 섹션 존재
2. 파이프(|) 구분 테이블로 계열사 목록 제공
3. 회사명, 상장여부, 지분율, 주요사업 등 컬럼 존재

방법:
1. 섹션 제목 매칭 패턴 확인
2. 삼성전자/현대차/SK 등 대기업 샘플 내용 출력
3. 267개 배치 섹션 존재율 확인

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


def findSection(report, patterns: list[str]) -> str | None:
    """보고서에서 패턴에 매칭되는 섹션 content 반환."""
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        for pat in patterns:
            if re.search(pat, title):
                content = row.get("section_content", "") or ""
                if len(content) > 30:
                    return content
    return None


def exploreSingle(stockCode: str):
    """단일 종목 섹션 내용 탐색."""
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    print(f"\n{'='*60}")
    print(f"{corpName} ({stockCode})")
    print(f"{'='*60}")

    for year in years[:2]:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        # 관련 섹션 타이틀 출력
        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if "계열" in title or "관계회사" in title:
                content = row.get("section_content", "") or ""
                print(f"\n  [{year}] {title} (길이: {len(content)})")
                # 앞부분 출력
                lines = content.split("\n")
                for line in lines[:30]:
                    print(f"    {line}")
                if len(lines) > 30:
                    print(f"    ... ({len(lines)} lines total)")
                break


def batchExplore():
    """267개 배치 섹션 존재율 조사."""
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    patterns = [
        r"계열회사 현황\(상세\)",
        r"계열회사.*현황",
        r"계열회사에 관한 사항",
        r"관계회사.*현황",
    ]

    found = 0
    notFound = 0
    titleCounter = Counter()
    hasTable = 0

    for code in codes:
        try:
            df = loadData(code)
            years = sorted(df["year"].unique().to_list(), reverse=True)
            report = selectReport(df, years[0], reportKind="annual")
            if report is None:
                notFound += 1
                continue

            sectionFound = False
            for row in report.iter_rows(named=True):
                title = row.get("section_title", "") or ""
                for pat in patterns:
                    if re.search(pat, title):
                        content = row.get("section_content", "") or ""
                        if len(content) > 30:
                            sectionFound = True
                            titleCounter[title.strip()] += 1
                            if "|" in content:
                                hasTable += 1
                            break
                if sectionFound:
                    break

            if sectionFound:
                found += 1
            else:
                notFound += 1

        except Exception as e:
            print(f"  ERROR {code}: {e}")
            notFound += 1

    print(f"\n=== 배치 탐색 결과 ({len(codes)}개) ===")
    print(f"섹션 존재: {found} ({found/len(codes)*100:.1f}%)")
    print(f"섹션 없음: {notFound}")
    print(f"테이블 있음: {hasTable}")

    print("\n섹션 제목 분포:")
    for title, count in titleCounter.most_common(10):
        print(f"  {count:3d} | {title}")


if __name__ == "__main__":
    exploreSingle("005930")
    exploreSingle("005380")
    exploreSingle("035720")
    print()
    batchExplore()
