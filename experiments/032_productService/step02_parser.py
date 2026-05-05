"""
실험 ID: 032
실험명: 주요 제품 및 서비스 파서

목적:
- 주요 제품/서비스 테이블에서 부문/제품별 매출 추출
- 매출액, 비중(%) 파싱
- 267개 배치 테스트

가설:
1. 첫 번째 테이블이 부문별 매출/비중
2. 180/267 이상에서 데이터 추출 가능

방법:
1. 주요 제품/서비스 테이블 파서
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


def parseRatio(text: str) -> float | None:
    """비중(%) 문자열을 float로 변환."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip().replace("%", "").replace(",", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None

    negative = False
    if text.startswith("△") or text.startswith("(") or text.startswith("−"):
        negative = True
        text = text.lstrip("△(−").rstrip(")")

    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return None


def _detectUnit(content: str) -> str:
    """단위 감지."""
    m = re.search(r"단위\s*[:\s]*\s*(백만원|억원|천원|원)", content[:500])
    if m:
        return m.group(1)
    return "백만원"


def parseProductService(content: str) -> list[dict]:
    """주요 제품/서비스 테이블 파싱.

    | 부 문 | 주요 제품 | 매출액 | 비중 |
    | DX 부문 | TV, 모니터 등 | 1,748,877 | 58.1% |
    """
    lines = content.split("\n")
    results: list[dict] = []

    headerFound = False
    inTable = False
    nonTableGap = 0

    for line in lines:
        stripped = line.strip()

        if "|" not in stripped or isSeparatorRow(stripped):
            if inTable:
                nonTableGap += 1
                if nonTableGap > 2:
                    break
            continue

        nonTableGap = 0
        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        # 단위 행 건너뛰기
        if any("단위" in c for c in cells):
            continue

        # 참고/주석 행 건너뛰기
        if any("※" in c or "참고" in c or "참조" in c for c in cells):
            if inTable and results:
                break
            continue

        # 가격변동 테이블은 별도 — 종료
        if any("가격" in c and "변동" in c for c in cells):
            break

        # 헤더 감지
        if not headerFound:
            hasProduct = any(
                k in c for c in cells
                for k in ("제품", "서비스", "품목", "품 목", "구분", "부문", "부 문",
                           "사업부문", "상품명", "사업영역")
            )
            hasMoney = any(
                k in c for c in cells
                for k in ("매출", "금액", "비중", "비율")
            )
            if hasProduct and hasMoney:
                headerFound = True
                continue

            # 2줄 헤더의 첫 줄만 있는 경우
            if hasProduct or hasMoney:
                headerFound = True
                continue

        if not headerFound:
            continue

        # 2줄 헤더의 두 번째 줄 건너뛰기
        if all(c.strip() in ("매출액", "비중", "비율", "금액", "") for c in cells):
            continue

        inTable = True

        # 데이터 행 파싱
        label_parts = []
        amount = None
        ratio = None

        for c in cells:
            c_stripped = c.strip()
            if not c_stripped:
                continue

            # 비중(%) 감지
            if "%" in c_stripped:
                if ratio is None:
                    ratio = parseRatio(c_stripped)
                continue

            # 금액 감지
            parsed = parseAmount(c_stripped)
            if parsed is not None and abs(parsed) > 10:
                if amount is None:
                    amount = parsed
                continue

            # 비중이 % 없이 소수인 경우 (예: 58.1)
            try:
                fval = float(c_stripped.replace(",", ""))
                if 0 < abs(fval) <= 100 and "." in c_stripped:
                    if ratio is None:
                        ratio = fval
                    continue
            except ValueError:
                pass

            # 라벨
            label_parts.append(c_stripped)

        if not label_parts:
            continue

        label = " > ".join(label_parts)

        entry = {"label": label}
        if amount is not None:
            entry["amount"] = amount
        if ratio is not None:
            entry["ratio"] = ratio
        results.append(entry)

    return results


def parseProductServiceData(stockCode: str) -> dict | None:
    """주요 제품 및 서비스 통합 파서."""
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
            if "주요 제품" in title or "주요 서비스" in title:
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                unit = _detectUnit(content)
                products = parseProductService(content)

                if not products:
                    if "없습니다" in content[:500] or len(content) < 200:
                        return {
                            "corpName": corpName,
                            "year": year,
                            "unit": unit,
                            "products": [],
                            "noData": True,
                        }
                    continue

                return {
                    "corpName": corpName,
                    "year": year,
                    "unit": unit,
                    "products": products,
                    "noData": False,
                }

    return None


# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────

def testSingle(stockCode: str):
    result = parseProductServiceData(stockCode)
    if result is None:
        print(f"  {stockCode}: 데이터 없음")
        return

    print(f"\n=== {result['corpName']} ({stockCode}) ===")
    print(f"  단위: {result['unit']}, 제품수: {len(result['products'])}")

    if result["noData"]:
        print("  → 해당사항 없음")
        return

    for p in result["products"][:8]:
        amt = f"{p['amount']:,}" if p.get("amount") else "?"
        rat = f"{p['ratio']}%" if p.get("ratio") else "?"
        print(f"  {p['label']}: {amt} ({rat})")


def batchTest():
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    ok = noData = errors = noSection = 0
    totalProducts = 0

    for code in codes:
        try:
            result = parseProductServiceData(code)
            if result is None:
                noSection += 1
            elif result["noData"]:
                noData += 1
                ok += 1
            else:
                ok += 1
                totalProducts += len(result["products"])
        except Exception as e:
            errors += 1
            print(f"  ERROR {code}: {e}")

    print(f"\n=== 배치 테스트 결과 ({len(codes)}개) ===")
    print(f"성공: {ok} ({ok/len(codes)*100:.1f}%), 섹션없음: {noSection}, 에러: {errors}")
    print(f"해당없음: {noData}")
    print(f"총 제품/서비스 행: {totalProducts:,}")


if __name__ == "__main__":
    testSingle("005930")
    testSingle("005380")
    testSingle("035720")
    testSingle("068270")
    print()
    batchTest()
