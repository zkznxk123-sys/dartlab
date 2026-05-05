"""
실험 ID: 033
실험명: 위험관리 및 파생거래 파서

목적:
- 파생상품 계약 현황 테이블에서 종류/계약금액/평가손익 추출
- 환율 민감도 테이블 추출
- 267개 배치 테스트

가설:
1. 환율 민감도 테이블이 가장 보편적
2. 파생상품 계약 현황은 일부에만 존재
3. 150/267 이상에서 데이터 추출 가능

방법:
1. 환율 민감도 파서
2. 파생상품 계약 파서
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


def _detectUnit(content: str) -> str:
    m = re.search(r"단위\s*[:\s]*\s*(백만원|억원|천원|원)", content[:500])
    if m:
        return m.group(1)
    return "백만원"


def parseFxSensitivity(content: str) -> list[dict]:
    """환율 민감도 테이블 파싱.

    | 구분 | 환율 상승시 | 환율 하락시 |
    | USD | 365,273 | △365,273 |
    """
    lines = content.split("\n")
    results: list[dict] = []

    inSection = False
    headerFound = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if re.search(r"환율.*변동|환율.*민감도|외화.*민감도", stripped):
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        if any("단위" in c for c in cells):
            continue
        if any("※" in c for c in cells):
            break

        # 헤더 감지
        if any("상승" in c or "하락" in c for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 데이터 행: 통화 + 숫자
        currency = cells[0].strip()
        if not currency or currency in ("-", "−", "–"):
            continue
        if len(currency) > 10:
            continue

        nums = [parseAmount(c) for c in cells[1:]]
        validNums = [n for n in nums if n is not None]
        if not validNums:
            continue

        entry = {"currency": currency}
        if len(validNums) >= 1:
            entry["upImpact"] = validNums[0]
        if len(validNums) >= 2:
            entry["downImpact"] = validNums[1]
        results.append(entry)

    return results


def parseDerivativeContracts(content: str) -> list[dict]:
    """파생상품 계약 현황 파싱.

    | 파생상품 종류 | 계약금액 | 평가손익 | 만기 |
    """
    lines = content.split("\n")
    results: list[dict] = []

    inSection = False
    headerFound = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if re.search(r"파생상품.*계약|파생상품.*현황|파생상품.*거래", stripped):
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        if any("단위" in c or "기준일" in c for c in cells):
            continue

        # 헤더
        if any("종류" in c or "구분" in c for c in cells) and any("금액" in c or "손익" in c for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 데이터 행
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


def parseRiskDerivative(stockCode: str) -> dict | None:
    """위험관리 및 파생거래 통합 파서."""
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
            if ("위험관리" in title and "파생" in title) or ("파생" in title and "거래" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                unit = _detectUnit(content)
                fxSensitivity = parseFxSensitivity(content)
                derivatives = parseDerivativeContracts(content)

                if not fxSensitivity and not derivatives:
                    if "없습니다" in content[:500] or "해당사항" in content[:500] or len(content) < 300:
                        return {
                            "corpName": corpName,
                            "year": year,
                            "unit": unit,
                            "fxSensitivity": [],
                            "derivatives": [],
                            "noData": True,
                        }
                    # 서술형만 있는 경우 — 텍스트 요약 정보 반환
                    hasRisk = any(k in content for k in ("환율", "이자율", "시장위험", "신용위험"))
                    if hasRisk:
                        return {
                            "corpName": corpName,
                            "year": year,
                            "unit": unit,
                            "fxSensitivity": [],
                            "derivatives": [],
                            "noData": False,
                            "textOnly": True,
                        }
                    continue

                return {
                    "corpName": corpName,
                    "year": year,
                    "unit": unit,
                    "fxSensitivity": fxSensitivity,
                    "derivatives": derivatives,
                    "noData": False,
                    "textOnly": False,
                }

    return None


# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────

def testSingle(stockCode: str):
    result = parseRiskDerivative(stockCode)
    if result is None:
        print(f"  {stockCode}: 데이터 없음")
        return

    print(f"\n=== {result['corpName']} ({stockCode}) ===")
    print(f"  단위: {result['unit']}")

    if result["noData"]:
        print("  → 해당사항 없음")
        return

    if result.get("textOnly"):
        print("  → 서술형만 (테이블 없음)")
        return

    print(f"  환율 민감도: {len(result['fxSensitivity'])}개 통화")
    for fx in result["fxSensitivity"][:5]:
        up = f"{fx.get('upImpact', 0):,}" if fx.get("upImpact") else "?"
        down = f"{fx.get('downImpact', 0):,}" if fx.get("downImpact") else "?"
        print(f"    {fx['currency']}: 상승={up}, 하락={down}")

    print(f"  파생상품: {len(result['derivatives'])}건")
    for d in result["derivatives"][:5]:
        vals = ", ".join(f"{v:,}" if v else "-" for v in d["values"][:3])
        print(f"    {d['label']}: {vals}")


def batchTest():
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    ok = noData = errors = noSection = textOnly = 0
    totalFx = totalDerivatives = 0

    for code in codes:
        try:
            result = parseRiskDerivative(code)
            if result is None:
                noSection += 1
            elif result["noData"]:
                noData += 1
                ok += 1
            elif result.get("textOnly"):
                textOnly += 1
                ok += 1
            else:
                ok += 1
                totalFx += len(result["fxSensitivity"])
                totalDerivatives += len(result["derivatives"])
        except Exception as e:
            errors += 1
            print(f"  ERROR {code}: {e}")

    print(f"\n=== 배치 테스트 결과 ({len(codes)}개) ===")
    print(f"성공: {ok} ({ok/len(codes)*100:.1f}%), 섹션없음: {noSection}, 에러: {errors}")
    print(f"해당없음: {noData}, 서술형만: {textOnly}")
    print(f"총 환율민감도: {totalFx}, 총 파생상품: {totalDerivatives}")


if __name__ == "__main__":
    testSingle("005930")
    testSingle("005380")
    testSingle("035720")
    testSingle("068270")
    print()
    batchTest()
