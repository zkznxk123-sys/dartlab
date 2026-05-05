"""전체 주석 번호별 섹션 제목 수집.

267개 기업의 연결재무제표 주석에서 모든 번호 매겨진 섹션을 추출.
어떤 주석이 얼마나 많은 기업에 존재하는지 분포 파악.
"""

import os
import re
import sys
from collections import Counter

sys.path.insert(0, "src")

from dartlab.core.dataLoader import loadData
from dartlab.core.notesExtractor import extractNotesContent
from dartlab.core.reportSelector import selectReport

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"


def extractSectionTitles(contents: list[str]) -> list[tuple[int, str]]:
    """주석 콘텐츠에서 모든 번호 매겨진 섹션 제목 추출."""
    sections = []
    seen = set()
    for content in contents:
        for line in content.split("\n"):
            s = line.strip()
            if s.startswith("|"):
                continue
            m = re.match(r"^(\d{1,2})\.\s+(.+)", s)
            if m:
                num = int(m.group(1))
                title = m.group(2).strip()
                key = (num, title)
                if key not in seen:
                    seen.add(key)
                    sections.append((num, title))
    return sections


if __name__ == "__main__":
    codes = sorted(
        f.replace(".parquet", "")
        for f in os.listdir(DATA_DIR)
        if f.endswith(".parquet")
    )

    titleCounter: Counter = Counter()
    numToTitles: dict[int, Counter] = {}
    hasNotes = 0
    noNotes = 0

    for code in codes:
        df = loadData(code)
        years = sorted(df["year"].unique().to_list(), reverse=True)

        report = selectReport(df, years[0], reportKind="annual")
        if report is None:
            continue

        contents = extractNotesContent(report)
        if not contents:
            noNotes += 1
            continue

        hasNotes += 1
        sections = extractSectionTitles(contents)
        seenNums = set()
        for num, title in sections:
            if num not in seenNums:
                seenNums.add(num)
                titleCounter[(num, title)] += 1
                if num not in numToTitles:
                    numToTitles[num] = Counter()
                numToTitles[num][title] += 1

    print(f"주석 있음: {hasNotes}, 없음: {noNotes}")
    print("\n=== 주석 번호별 출현 빈도 (상위) ===")

    for num in sorted(numToTitles.keys()):
        titles = numToTitles[num]
        total = sum(titles.values())
        topTitle = titles.most_common(1)[0][0]
        variants = len(titles)
        print(f"  {num:2d}. {topTitle:<30s}  ({total}개 기업, {variants}개 변형)")

    print("\n=== 주석 제목 변형 상세 (3개 이상 변형) ===")
    for num in sorted(numToTitles.keys()):
        titles = numToTitles[num]
        if len(titles) >= 3:
            print(f"\n  {num}번 주석:")
            for title, count in titles.most_common():
                print(f"    {count:3d}개  {title}")
