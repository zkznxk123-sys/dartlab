"""
실험 ID: 030
실험명: 증권 발행(증자/감자) 파서

목적:
- 증자(감자) 현황 테이블에서 발행 이력 추출
- 발행일자, 형태, 종류, 수량, 액면가, 발행가 파싱
- 267개 배치 테스트

가설:
1. 증자(감자) 테이블은 7열 (일자|형태|종류|수량|액면가|발행가|비고)
2. 180/267 이상에서 증자 이력 추출 가능
3. "-" 만 있으면 발행 실적 없음

방법:
1. 증자(감자) 테이블 파서
2. 배치 테스트

결과 (실험 후 작성):
-

결론:
-

실험일: 2026-03-08
"""

import os
import re
import sys

sys.path.insert(0, r"C:\Users\MSI\OneDrive\Desktop\sideProject\dartlab\src")

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport


def splitCells(line: str) -> list[str]:
    cells = [c.strip() for c in line.split("|")]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()
    return cells


def isSeparatorRow(line: str) -> bool:
    cells = splitCells(line)
    return all(re.match(r"^-+$", c.strip()) for c in cells if c.strip())


def parseAmount(text: str) -> int | None:
    """숫자 문자열을 정수로 변환."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        if abs(val) > 9_000_000_000_000_000_000:
            return None
        return val
    except (ValueError, OverflowError):
        return None


def parseEquityIssuance(content: str) -> list[dict]:
    """증자(감자) 현황 테이블 파싱.

    | 주식발행(감소)일자 | 발행(감소)형태 | 종류 | 수량 | 주당액면가액 | 주당발행(감소)가액 | 비고 |
    | 2020.01.03 | 전환권행사 | 보통주 | 92,603 | 500 | 118,786 | 발행회차: 제 10회 |
    """
    lines = content.split("\n")
    results: list[dict] = []

    # 증자(감자) 테이블 영역 찾기
    inSection = False
    headerFound = False

    for line in lines:
        stripped = line.strip()

        # 섹션 시작 감지
        if "증자" in stripped and ("감자" in stripped or "현황" in stripped):
            inSection = True
            continue

        # 채무증권 섹션이 시작되면 종료
        if "채무증권" in stripped:
            break

        if not inSection:
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)

        # 헤더 행 건너뛰기
        if any("발행" in c and ("일자" in c or "형태" in c) for c in cells):
            headerFound = True
            continue
        if any(c in ("종류", "수량", "주당액면가액") for c in cells):
            continue

        if not headerFound:
            continue

        # 기준일/단위 행 건너뛰기
        if any("기준일" in c or "단위" in c for c in cells):
            continue

        # 데이터 행: 최소 4열 이상, 첫 셀이 날짜 패턴
        if len(cells) < 4:
            continue

        dateStr = cells[0].strip()
        # 날짜 패턴: YYYY.MM.DD or YYYY-MM-DD or YYYY/MM/DD or YYYY년 MM월 DD일
        dateMatch = re.match(r"^(\d{4})[\.\-/](\d{2})[\.\-/](\d{2})$", dateStr)
        if not dateMatch:
            dateMatch = re.match(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일$", dateStr)
        if not dateMatch:
            continue

        # 날짜 정규화: YYYY.MM.DD
        normalizedDate = f"{dateMatch.group(1)}.{int(dateMatch.group(2)):02d}.{int(dateMatch.group(3)):02d}"

        # 파싱
        entry = {"date": normalizedDate}

        if len(cells) > 1:
            entry["issueType"] = cells[1].strip()
        if len(cells) > 2:
            entry["stockType"] = cells[2].strip()
        if len(cells) > 3:
            entry["quantity"] = parseAmount(cells[3])
        if len(cells) > 4:
            entry["parValue"] = parseAmount(cells[4])
        if len(cells) > 5:
            entry["issuePrice"] = parseAmount(cells[5])
        if len(cells) > 6:
            entry["note"] = cells[6].strip()

        results.append(entry)

    return results


def parseFundraising(stockCode: str) -> dict | None:
    """증권 발행 통합 파서."""
    try:
        df = loadData(stockCode)
    except Exception:
        return None

    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    for year in years[:2]:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if "증권" in title and "자금조달" in title:
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                issuances = parseEquityIssuance(content)

                if not issuances:
                    # 해당사항 없음 감지
                    noDataSignals = (
                        "없습니다" in content[:500]
                        or "해당사항 없음" in content[:500]
                        or "해당없음" in content[:500]
                        or len(content) < 300
                    )
                    # 테이블 헤더는 있지만 데이터 행이 없는 경우도 noData
                    hasHeader = "발행" in content and ("일자" in content or "형태" in content)
                    if noDataSignals or hasHeader:
                        return {
                            "corpName": corpName,
                            "year": year,
                            "issuances": [],
                            "noData": True,
                        }
                    continue

                return {
                    "corpName": corpName,
                    "year": year,
                    "issuances": issuances,
                    "noData": False,
                }

    return None


# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────

def testSingle(stockCode: str):
    result = parseFundraising(stockCode)
    if result is None:
        print(f"  {stockCode}: 데이터 없음")
        return

    print(f"\n=== {result['corpName']} ({stockCode}) ===")
    print(f"  발행 건수: {len(result['issuances'])}")

    if result["noData"]:
        print("  → 발행 실적 없음")
        return

    # 형태별 집계
    from collections import Counter
    typeCounter = Counter(i.get("issueType", "?") for i in result["issuances"])
    for t, c in typeCounter.most_common():
        print(f"  {t}: {c}건")

    # 샘플 출력
    for i in result["issuances"][:3]:
        qty = f"{i['quantity']:,}" if i.get("quantity") else "?"
        price = f"{i['issuePrice']:,}" if i.get("issuePrice") else "?"
        print(f"    {i['date']} | {i.get('issueType', '?')} | {i.get('stockType', '?')} | {qty}주 | @{price}원")


def batchTest():
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    ok = noData = errors = noSection = 0
    totalIssuances = 0

    for code in codes:
        try:
            result = parseFundraising(code)
            if result is None:
                noSection += 1
            elif result["noData"]:
                noData += 1
                ok += 1
            else:
                ok += 1
                totalIssuances += len(result["issuances"])
        except Exception as e:
            errors += 1
            print(f"  ERROR {code}: {e}")

    print(f"\n=== 배치 테스트 결과 ({len(codes)}개) ===")
    print(f"성공: {ok} ({ok/len(codes)*100:.1f}%), 섹션없음: {noSection}, 에러: {errors}")
    print(f"발행실적 없음: {noData}")
    print(f"총 추출 발행건: {totalIssuances:,}")


if __name__ == "__main__":
    testSingle("005930")
    testSingle("005380")
    testSingle("035720")
    testSingle("068270")
    print()
    batchTest()
