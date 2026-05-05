"""
실험 ID: 030
실험명: 증권 발행을 통한 자금조달 탐색

목적:
- "증권의 발행을 통한 자금조달에 관한 사항" 섹션 구조 파악
- 유증/CB/BW 발행 데이터 추출 가능성 확인
- 267개 배치 섹션 존재율 및 테이블 형태 확인

가설:
1. 98% 이상에서 섹션 존재
2. 유상증자, 전환사채(CB), 신주인수권부사채(BW) 발행 테이블 존재
3. 발행금액, 일자, 용도 추출 가능

방법:
1. 삼성전자/현대차/카카오 샘플 내용 출력
2. 267개 배치 섹션 존재율 확인
3. "해당사항 없음" 비율 확인

결과 (실험 후 작성):
-

결론:
-

실험일: 2026-03-08
"""

import os
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\MSI\OneDrive\Desktop\sideProject\dartlab\src")

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport


def exploreSingle(stockCode: str):
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    print(f"\n{'='*60}")
    print(f"{corpName} ({stockCode})")
    print(f"{'='*60}")

    for year in years[:1]:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if "증권" in title and "자금조달" in title:
                content = row.get("section_content", "") or ""
                print(f"\n  [{year}] {title} (길이: {len(content)})")
                lines = content.split("\n")
                for line in lines[:50]:
                    print(f"    {line}")
                if len(lines) > 50:
                    print(f"    ... ({len(lines)} lines total)")
                break


def batchExplore():
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    found = 0
    noSection = 0
    noData = 0  # "해당사항 없음"
    hasTable = 0
    titleCounter = Counter()
    lengths = []

    for code in codes:
        try:
            df = loadData(code)
            years = sorted(df["year"].unique().to_list(), reverse=True)
            report = selectReport(df, years[0], reportKind="annual")
            if report is None:
                noSection += 1
                continue

            sectionFound = False
            for row in report.iter_rows(named=True):
                title = row.get("section_title", "") or ""
                if "증권" in title and "자금조달" in title:
                    content = row.get("section_content", "") or ""
                    if len(content) > 30:
                        sectionFound = True
                        titleCounter[title.strip()] += 1
                        lengths.append(len(content))

                        if len(content) < 300 and ("없습니다" in content or "해당" in content or "없음" in content):
                            noData += 1
                        elif "|" in content:
                            hasTable += 1

                    break

            if sectionFound:
                found += 1
            else:
                noSection += 1

        except Exception as e:
            print(f"  ERROR {code}: {e}")
            noSection += 1

    print(f"\n=== 배치 탐색 결과 ({len(codes)}개) ===")
    print(f"섹션 존재: {found} ({found/len(codes)*100:.1f}%)")
    print(f"섹션 없음: {noSection}")
    print(f"해당없음: {noData}")
    print(f"테이블 있음: {hasTable}")
    if lengths:
        print(f"평균 길이: {sum(lengths)/len(lengths):.0f}, 최대: {max(lengths)}")

    print("\n섹션 제목:")
    for title, count in titleCounter.most_common(10):
        print(f"  {count:3d} | {title}")


if __name__ == "__main__":
    exploreSingle("005930")
    exploreSingle("005380")
    exploreSingle("035720")
    exploreSingle("068270")
    print()
    batchExplore()
