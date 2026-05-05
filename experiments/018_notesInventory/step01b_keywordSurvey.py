"""키워드 기반 주석 섹션 분포 조사.

번호는 기업마다 다르므로 키워드로 분류.
현재 추출 중: 부문, 유형자산, 관계기업/지분법, 비용+성격
추출 후보: 무형자산, 차입금/사채, 매출채권, 재고자산, 투자부동산,
         리스, 충당부채, 퇴직급여, 주당이익, 법인세 등
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

KEYWORDS = [
    "유형자산",
    "무형자산",
    "투자부동산",
    "사용권자산",
    "리스",
    "재고자산",
    "매출채권",
    "금융자산",
    "금융부채",
    "차입금",
    "사채",
    "전환사채",
    "충당부채",
    "우발부채",
    "퇴직급여",
    "종업원급여",
    "확정급여",
    "자본금",
    "이익잉여금",
    "기타포괄손익",
    "주당이익",
    "주당순이익",
    "법인세",
    "매출",
    "영업수익",
    "판매비",
    "비용의 성격",
    "비용 성격",
    "부문",
    "관계기업",
    "지분법",
    "공동기업",
    "종속기업",
    "특수관계자",
    "재무위험",
    "공정가치",
    "우발채무",
    "약정사항",
    "담보",
    "보고기간후",
    "배당",
    "현금흐름",
    "수익인식",
    "재무상태표",
]


def findKeywordsInNotes(contents: list[str]) -> set[str]:
    """주석에서 번호 매겨진 섹션 제목의 키워드를 추출."""
    found = set()
    for content in contents:
        for line in content.split("\n"):
            s = line.strip()
            if s.startswith("|"):
                continue
            m = re.match(r"^(\d{1,2})\.\s+(.+)", s)
            if m:
                title = m.group(2).strip()
                for kw in KEYWORDS:
                    if kw in title:
                        found.add(kw)
    return found


if __name__ == "__main__":
    codes = sorted(
        f.replace(".parquet", "")
        for f in os.listdir(DATA_DIR)
        if f.endswith(".parquet")
    )

    kwCounter: Counter = Counter()
    total = 0

    for code in codes:
        df = loadData(code)
        years = sorted(df["year"].unique().to_list(), reverse=True)

        report = selectReport(df, years[0], reportKind="annual")
        if report is None:
            continue

        contents = extractNotesContent(report)
        if not contents:
            continue

        total += 1
        found = findKeywordsInNotes(contents)
        for kw in found:
            kwCounter[kw] += 1

    print(f"주석 있는 기업: {total}")
    print("\n=== 키워드별 출현 빈도 ===")

    already = {"유형자산", "부문", "관계기업", "지분법", "공동기업", "비용의 성격", "비용 성격"}

    print("\n[현재 추출 중]")
    for kw, count in sorted(kwCounter.items(), key=lambda x: -x[1]):
        if kw in already:
            print(f"  {count:3d}/{total}  ({count/total*100:5.1f}%)  {kw}")

    print("\n[미추출 — 추출 후보]")
    for kw, count in sorted(kwCounter.items(), key=lambda x: -x[1]):
        if kw not in already:
            print(f"  {count:3d}/{total}  ({count/total*100:5.1f}%)  {kw}")
