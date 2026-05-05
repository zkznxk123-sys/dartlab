"""
실험 ID: 031
실험명: 매출 및 수주상황 파서

목적:
- 매출실적 테이블에서 부문/품목별 매출 추출
- 수주상황 테이블에서 수주잔고 추출
- 267개 배치 테스트

가설:
1. 매출실적 테이블은 부문|품목|당기|전기|전전기 구조
2. 180/267 이상에서 매출 데이터 추출 가능
3. 수주상황은 일부 제조업에서만 존재

방법:
1. 매출실적 테이블 파서
2. 수주상황 테이블 파서
3. 배치 테스트

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
    """숫자 문자열을 정수로 변환. △는 음수."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if text in ("-", "−", "–", ""):
        return None

    negative = False
    if text.startswith("△") or text.startswith("(") or text.startswith("−"):
        negative = True
        text = text.lstrip("△(−").rstrip(")")

    text = text.replace(",", "").replace(" ", "")
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        if abs(val) > 9_000_000_000_000_000_000:
            return None
        return -val if negative else val
    except (ValueError, OverflowError):
        return None


def _detectUnit(content: str) -> str:
    """단위 감지."""
    m = re.search(r"단위\s*[:\s]*\s*(백만원|억원|천원|원)", content[:500])
    if m:
        return m.group(1)
    return "백만원"


def _isHeaderRow(cells: list[str]) -> bool:
    """헤더 행 판별."""
    keywords = {"구분", "부문", "매출유형", "품목", "품 목", "주요제품", "사업구분",
                "매출액", "비중", "금액", "내수", "수출", "합계", "합 계",
                "제품", "상품", "용역"}
    return sum(1 for c in cells if c.strip() in keywords or "기" in c or "년" in c) >= 2


def parseSalesTable(content: str) -> list[dict]:
    """매출실적 테이블 파싱.

    다양한 구조를 일반적으로 처리:
    - 첫 번째 매출 테이블에서 행별로 라벨+숫자 추출
    - 각 행: label, values (숫자 목록)
    """
    lines = content.split("\n")
    results: list[dict] = []

    # "매출실적" 또는 "매출현황" 영역 찾기
    inSection = False
    headerCols: list[str] = []
    skipCount = 0

    for line in lines:
        stripped = line.strip()

        # 섹션 시작
        if not inSection:
            if re.search(r"매출\s*실적|매출\s*현황|부문별\s*매출", stripped):
                inSection = True
            continue

        # 섹션 종료 감지
        if re.search(r"판매경로|판매방법|판매전략|수주상황|수주 상황|나\.\s", stripped) and "|" not in stripped:
            break

        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        # 단위/기준 행 건너뛰기
        if any("단위" in c or "기준일" in c for c in cells):
            continue

        # 헤더 행 감지 (최초 1회)
        if not headerCols and _isHeaderRow(cells):
            headerCols = cells
            continue

        # 2줄 헤더 (비중/금액 등이 별도 행인 경우) 건너뛰기
        if headerCols and skipCount < 1 and _isHeaderRow(cells):
            skipCount += 1
            continue

        if not headerCols:
            continue

        # 데이터 행: 숫자가 1개 이상 있어야
        nums = [parseAmount(c) for c in cells]
        hasNum = sum(1 for n in nums if n is not None)
        if hasNum < 1:
            continue

        # 라벨 추출: 첫 번째 비숫자 셀
        label_parts = []
        values = []
        for c in cells:
            val = parseAmount(c)
            if val is not None:
                values.append(val)
            elif c.strip() and c.strip() not in ("-", "−", "–"):
                # 비율(%) 셀은 무시
                if re.match(r"^\d+\.?\d*%$", c.strip()):
                    continue
                label_parts.append(c.strip())

        if not label_parts:
            continue

        label = " > ".join(label_parts)

        results.append({
            "label": label,
            "values": values,
        })

    return results


def parseOrderBacklog(content: str) -> list[dict]:
    """수주상황 테이블 파싱.

    | 품목 | 수주일자 | 납기 | 수주총액 | 기납품액 | 수주잔고 |
    """
    lines = content.split("\n")
    results: list[dict] = []

    inSection = False
    headerFound = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if "수주상황" in stripped or "수주 상황" in stripped:
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        # 헤더
        if any("수주" in c and ("총액" in c or "잔고" in c) for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        if any("단위" in c or "기준일" in c for c in cells):
            continue

        # 데이터 행
        nums = [parseAmount(c) for c in cells]
        hasNum = sum(1 for n in nums if n is not None)
        if hasNum < 1:
            continue

        label_parts = []
        values = []
        for c in cells:
            val = parseAmount(c)
            if val is not None:
                values.append(val)
            elif c.strip() and c.strip() not in ("-", "−", "–"):
                label_parts.append(c.strip())

        if not label_parts:
            continue

        results.append({
            "label": " > ".join(label_parts),
            "values": values,
        })

    return results


def parseSalesOrder(stockCode: str) -> dict | None:
    """매출 및 수주상황 통합 파서."""
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
            if "매출" in title and ("수주" in title or "사항" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                unit = _detectUnit(content)
                sales = parseSalesTable(content)
                orders = parseOrderBacklog(content)

                if not sales and not orders:
                    if "없습니다" in content[:500] or len(content) < 300:
                        return {
                            "corpName": corpName,
                            "year": year,
                            "unit": unit,
                            "sales": [],
                            "orders": [],
                            "noData": True,
                        }
                    continue

                return {
                    "corpName": corpName,
                    "year": year,
                    "unit": unit,
                    "sales": sales,
                    "orders": orders,
                    "noData": False,
                }

    return None


# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────

def testSingle(stockCode: str):
    result = parseSalesOrder(stockCode)
    if result is None:
        print(f"  {stockCode}: 데이터 없음")
        return

    print(f"\n=== {result['corpName']} ({stockCode}) ===")
    print(f"  단위: {result['unit']}")
    print(f"  매출 행수: {len(result['sales'])}, 수주 행수: {len(result['orders'])}")

    if result["noData"]:
        print("  → 해당사항 없음")
        return

    for s in result["sales"][:5]:
        vals = ", ".join(f"{v:,}" if v else "-" for v in s["values"][:3])
        print(f"  매출: {s['label']}: {vals}")

    for o in result["orders"][:3]:
        vals = ", ".join(f"{v:,}" if v else "-" for v in o["values"][:3])
        print(f"  수주: {o['label']}: {vals}")


def batchTest():
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    ok = noData = errors = noSection = 0
    totalSalesRows = 0
    totalOrderRows = 0

    for code in codes:
        try:
            result = parseSalesOrder(code)
            if result is None:
                noSection += 1
            elif result["noData"]:
                noData += 1
                ok += 1
            else:
                ok += 1
                totalSalesRows += len(result["sales"])
                totalOrderRows += len(result["orders"])
        except Exception as e:
            errors += 1
            print(f"  ERROR {code}: {e}")

    print(f"\n=== 배치 테스트 결과 ({len(codes)}개) ===")
    print(f"성공: {ok} ({ok/len(codes)*100:.1f}%), 섹션없음: {noSection}, 에러: {errors}")
    print(f"해당없음: {noData}")
    print(f"총 매출 행: {totalSalesRows:,}, 총 수주 행: {totalOrderRows:,}")


if __name__ == "__main__":
    testSingle("005930")
    testSingle("005380")
    testSingle("035720")
    testSingle("068270")
    print()
    batchTest()
