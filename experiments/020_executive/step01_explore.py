"""
실험 ID: 020-01
실험명: 임원 현황 섹션 구조 탐색

목적:
- DART 사업보고서에서 "임원 현황" 관련 섹션 구조 파악
- 267개 기업에서 어떤 섹션 제목이 사용되는지, 테이블 구조는 어떤지 조사

가설:
1. 대부분의 기업이 "임원 현황" 관련 섹션을 갖고 있을 것
2. 테이블 컬럼: 성명, 성별, 출생년월, 직위, 등기임원여부, 상근여부, 담당업무, 주요경력, 재임기간, 임기만료일
3. 등기/비등기, 사내/사외 구분으로 시계열 가능

방법:
1. 267개 기업의 최신 사업보고서에서 "임원" 관련 섹션 제목 수집
2. 섹션 내 테이블 구조 분석
3. 파싱 전략 수립

결과 (실험 후 작성):

결론:

실험일: 2026-03-07
"""
import os
import re
import sys
from collections import Counter

import polars as pl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

EXECUTIVE_PATTERNS = [
    r"임원.*현황",
    r"임원.*직원.*현황",
    r"임원.*직원.*에\s*관한",
]


def findExecutiveSections(df: pl.DataFrame, year: str) -> list[dict]:
    """임원 관련 섹션 찾기."""
    report = selectReport(df, year, reportKind="annual")
    if report is None:
        return []

    results = []
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if any(re.search(p, title) for p in EXECUTIVE_PATTERNS):
            results.append({
                "title": title,
                "content": row.get("section_content", "") or "",
                "contentLen": len(row.get("section_content", "") or ""),
            })
    return results


def analyzeTableStructure(content: str) -> dict:
    """테이블 구조 분석."""
    lines = content.split("\n")

    # 테이블 블록 분리
    blocks = []
    current = []
    for line in lines:
        if line.strip().startswith("|"):
            current.append(line)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)

    if not blocks:
        return {"hasTables": False, "nTables": 0}

    headers = []
    for block in blocks:
        if len(block) >= 2:
            header = block[0]
            cells = [c.strip() for c in header.split("|")[1:-1]]
            headers.append(cells)

    totalRows = sum(len(b) for b in blocks)

    return {
        "hasTables": True,
        "nTables": len(blocks),
        "headers": headers,
        "totalRows": totalRows,
    }


if __name__ == "__main__":
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])
    print(f"총 {len(codes)}개 기업")

    # 1. 섹션 제목 수집
    titleCounter = Counter()
    hasSection = 0
    noSection = 0
    sampleContents = {}

    sampleCodes = ["005930", "005380", "000660", "035720"]

    for code in codes:
        try:
            df = loadData(code)
            years = sorted(df["year"].unique().to_list(), reverse=True)
            if not years:
                noSection += 1
                continue

            sections = findExecutiveSections(df, years[0])
            if sections:
                hasSection += 1
                for s in sections:
                    titleCounter[s["title"]] += 1
                if code in sampleCodes:
                    sampleContents[code] = sections
            else:
                noSection += 1
        except Exception as e:
            print(f"  ERROR {code}: {e}")

    print(f"\n섹션 있음: {hasSection}, 없음: {noSection}")
    print("\n=== 섹션 제목 분포 (top 30) ===")
    for title, count in titleCounter.most_common(30):
        print(f"  {count:4d} | {title}")

    # 2. 샘플 기업 테이블 구조 분석
    for code in sampleCodes:
        if code not in sampleContents:
            print(f"\n{code}: 섹션 없음")
            continue

        print(f"\n{'='*60}")
        df = loadData(code)
        corpName = extractCorpName(df)
        print(f"{corpName} ({code})")
        print(f"{'='*60}")

        for s in sampleContents[code]:
            print(f"\n  제목: {s['title']}")
            print(f"  길이: {s['contentLen']:,}자")

            analysis = analyzeTableStructure(s["content"])
            if analysis["hasTables"]:
                print(f"  테이블 수: {analysis['nTables']}")
                print(f"  총 행 수: {analysis['totalRows']}")
                for i, header in enumerate(analysis.get("headers", [])):
                    print(f"  테이블 {i+1} 헤더: {header}")
            else:
                print("  테이블 없음")

            # 첫 1000자 미리보기
            preview = s["content"][:1000]
            print("\n  --- 미리보기 ---")
            for line in preview.split("\n")[:30]:
                print(f"  {line}")
