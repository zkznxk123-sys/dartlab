"""
실험 ID: 021-01
실험명: 임원 보수 파서 + 시계열

목적:
- "2. 임원의 보수 등" 섹션에서 유형별 보수 테이블 파싱
- 등기이사(사외이사/감사 제외) / 사외이사 / 감사위원 별 인원수, 보수총액, 1인당평균

가설:
1. 유형별 보수 테이블: 구분|인원수|보수총액|1인당평균보수액|비고
2. 5억 초과 개인별 테이블: 이름|직위|보수총액|...
3. 연도별 시계열 생성 가능

방법:
1. 267개 기업에서 "2. 임원의 보수 등" 또는 대분류 섹션 탐색
2. 유형별 보수 테이블 분류 + 파싱
3. 5억 초과 개인별 테이블 파싱
4. 시계열 DataFrame 생성

결과 (실험 후 작성):

결론:

실험일: 2026-03-07
"""
import os
import re
import sys

import polars as pl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

PAY_SECTION_PATTERNS = [
    r"임원의\s*보수",
    r"임원.*보수.*등",
]

# 대분류 섹션에 보수 테이블이 있는 경우 fallback
EXEC_SECTION_PATTERNS = [
    r"임원.*직원.*에\s*관한",
]


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────

def _cellsFromLine(line: str) -> list[str]:
    return [c.strip() for c in line.split("|")[1:-1]]


def _isSeparator(cells: list[str]) -> bool:
    return all(re.match(r"^-+$", c.strip()) or c.strip() == "" for c in cells)


def _parseFloat(text: str) -> float | None:
    if not text or text.strip() in ("-", "", "—", "해당없음"):
        return None
    text = text.replace(",", "").replace(" ", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def extractTableBlocks(content: str) -> list[list[str]]:
    lines = content.split("\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip().startswith("|"):
            current.append(line)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks


# ──────────────────────────────────────────────
# 섹션 탐색
# ──────────────────────────────────────────────

def findPaySection(df: pl.DataFrame, year: str) -> str | None:
    """임원 보수 섹션 content 반환."""
    report = selectReport(df, year, reportKind="annual")
    if report is None:
        return None

    # 소분류 우선
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if any(re.search(p, title) for p in PAY_SECTION_PATTERNS):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content

    # 대분류 fallback
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if any(re.search(p, title) for p in EXEC_SECTION_PATTERNS):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content

    return None


# ──────────────────────────────────────────────
# 테이블 분류
# ──────────────────────────────────────────────

def classifyBlock(block: list[str]) -> str:
    """테이블 블록 분류.

    Returns: "payByType" | "payIndividual" | "other"
    """
    allText = ""
    for line in block[:6]:
        cells = _cellsFromLine(line)
        if not _isSeparator(cells):
            allText += " " + " ".join(c for c in cells if c.strip())

    # 유형별 보수: "구분" + ("등기이사" 또는 "사외이사") + "보수총액"
    if re.search(r"구\s*분", allText) and re.search(r"보수총액|보수\s*총\s*액", allText):
        if re.search(r"등기이사|사외이사|감사위원|1인당", allText):
            return "payByType"
        # 인원수+보수총액+1인당 패턴 확인
        if re.search(r"인원수", allText) and re.search(r"1인당|평균", allText):
            return "payByType"

    # 5억 초과 개인별: "이름" + "직위" + "보수총액"
    if re.search(r"이름", allText) and re.search(r"직위", allText) and re.search(r"보수총액", allText):
        return "payIndividual"

    return "other"


# ──────────────────────────────────────────────
# 유형별 보수 파서
# ──────────────────────────────────────────────

def parsePayByTypeBlock(block: list[str]) -> list[dict]:
    """유형별 보수 테이블 파싱.

    Returns: [{"category": str, "headcount": int, "totalPay": float, "avgPay": float}]
    """
    rows = []
    for line in block:
        cells = _cellsFromLine(line)
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 3:
        return []

    # 헤더 찾기: "구분" 또는 "인원수" 포함 행
    headerIdx = None
    for i, row in enumerate(rows):
        text = " ".join(row)
        if re.search(r"구\s*분", text) and re.search(r"인원|보수", text):
            headerIdx = i
            break

    if headerIdx is None:
        return []

    header = rows[headerIdx]
    nCols = len(header)

    # 컬럼 인덱스
    colCategory = None
    colHeadcount = None
    colTotalPay = None
    colAvgPay = None

    for i, h in enumerate(header):
        h = h.replace(" ", "")
        if re.search(r"구분", h):
            colCategory = i
        elif re.search(r"인원", h):
            colHeadcount = i
        elif re.search(r"보수총액", h):
            colTotalPay = i
        elif re.search(r"1인당|평균보수", h):
            colAvgPay = i

    if colCategory is None:
        colCategory = 0
    if colHeadcount is None or colTotalPay is None:
        return []

    dataStart = headerIdx + 1

    result = []
    for row in rows[dataStart:]:
        if len(row) < 3:
            continue
        while len(row) < nCols:
            row.append("")

        category = row[colCategory].strip()
        if not category or re.search(r"비\s*고|합\s*계", category):
            continue

        headcount = _parseFloat(row[colHeadcount])
        totalPay = _parseFloat(row[colTotalPay])
        avgPay = _parseFloat(row[colAvgPay]) if colAvgPay is not None else None

        if headcount is None and totalPay is None:
            continue

        result.append({
            "category": _normalizeCategory(category),
            "headcount": int(headcount) if headcount is not None else None,
            "totalPay": totalPay,
            "avgPay": avgPay,
        })

    return result


def _normalizeCategory(raw: str) -> str:
    """보수 카테고리 정규화."""
    raw = raw.strip()
    if re.search(r"등기이사.*사외.*제외|사내이사", raw):
        return "등기이사"
    if re.search(r"사외이사.*감사.*제외", raw):
        return "사외이사"
    if re.search(r"감사위원", raw):
        return "감사위원"
    if re.search(r"사외이사", raw):
        return "사외이사"
    if re.search(r"감사", raw):
        return "감사"
    if re.search(r"등기이사", raw):
        return "등기이사"
    return raw


# ──────────────────────────────────────────────
# 5억 초과 개인별 파서
# ──────────────────────────────────────────────

def parsePayIndividualBlock(block: list[str]) -> list[dict]:
    """5억 초과 개인별 보수 테이블 파싱.

    Returns: [{"name": str, "position": str, "totalPay": float}]
    """
    rows = []
    for line in block:
        cells = _cellsFromLine(line)
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 3:
        return []

    headerIdx = None
    for i, row in enumerate(rows):
        text = " ".join(row)
        if "이름" in text and "보수총액" in text:
            headerIdx = i
            break

    if headerIdx is None:
        return []

    header = rows[headerIdx]
    nCols = len(header)

    colName = None
    colPosition = None
    colTotalPay = None

    for i, h in enumerate(header):
        h = h.strip()
        if "이름" in h:
            colName = i
        elif "직위" in h:
            colPosition = i
        elif "보수총액" in h:
            colTotalPay = i

    if colName is None or colTotalPay is None:
        return []

    dataStart = headerIdx + 1

    result = []
    for row in rows[dataStart:]:
        while len(row) < nCols:
            row.append("")

        name = row[colName].strip()
        if not name:
            continue

        position = row[colPosition].strip() if colPosition is not None else ""
        totalPay = _parseFloat(row[colTotalPay])

        if totalPay is None:
            continue

        result.append({
            "name": name,
            "position": position,
            "totalPay": totalPay,
        })

    return result


# ──────────────────────────────────────────────
# 통합 파싱 + 시계열
# ──────────────────────────────────────────────

def parsePaySection(content: str) -> dict:
    """임원 보수 섹션 전체를 파싱."""
    blocks = extractTableBlocks(content)

    payByType = []
    payIndividuals = []

    for block in blocks:
        kind = classifyBlock(block)
        if kind == "payByType" and not payByType:
            payByType = parsePayByTypeBlock(block)
        elif kind == "payIndividual" and not payIndividuals:
            payIndividuals = parsePayIndividualBlock(block)

    return {
        "payByType": payByType,
        "payIndividuals": payIndividuals,
    }


def buildPayTimeSeries(stockCode: str) -> dict | None:
    """임원 보수 시계열 생성.

    Returns:
        {
            "corpName": str,
            "nYears": int,
            "payByTypeDf": pl.DataFrame | None,
            "topPayDf": pl.DataFrame | None,
        }
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    typeRows: list[dict] = []
    topPayRows: list[dict] = []

    for year in years:
        content = findPaySection(df, year)
        if content is None:
            continue

        result = parsePaySection(content)

        if result["payByType"]:
            for item in result["payByType"]:
                item["year"] = year
                typeRows.append(item)

        if result["payIndividuals"]:
            for item in result["payIndividuals"]:
                item["year"] = year
                topPayRows.append(item)

    if not typeRows and not topPayRows:
        return None

    payByTypeDf = _buildPayByTypeDf(typeRows) if typeRows else None
    topPayDf = _buildTopPayDf(topPayRows) if topPayRows else None

    nYears = len(set(r["year"] for r in typeRows)) if typeRows else len(set(r["year"] for r in topPayRows))

    return {
        "corpName": corpName,
        "nYears": nYears,
        "payByTypeDf": payByTypeDf,
        "topPayDf": topPayDf,
    }


def _buildPayByTypeDf(rows: list[dict]) -> pl.DataFrame:
    data = []
    for r in sorted(rows, key=lambda x: (x["year"], x["category"]), reverse=True):
        data.append({
            "year": r["year"],
            "category": r["category"],
            "headcount": r["headcount"],
            "totalPay": r["totalPay"],
            "avgPay": r["avgPay"],
        })
    schema = {
        "year": pl.Utf8,
        "category": pl.Utf8,
        "headcount": pl.Int64,
        "totalPay": pl.Float64,
        "avgPay": pl.Float64,
    }
    return pl.DataFrame(data, schema=schema)


def _buildTopPayDf(rows: list[dict]) -> pl.DataFrame:
    data = []
    for r in sorted(rows, key=lambda x: (x["year"], -x["totalPay"]), reverse=True):
        data.append({
            "year": r["year"],
            "name": r["name"],
            "position": r["position"],
            "totalPay": r["totalPay"],
        })
    schema = {
        "year": pl.Utf8,
        "name": pl.Utf8,
        "position": pl.Utf8,
        "totalPay": pl.Float64,
    }
    return pl.DataFrame(data, schema=schema)


if __name__ == "__main__":
    # 샘플 테스트
    targets = [
        ("005930", "삼성전자"),
        ("005380", "현대자동차"),
        ("000660", "SK하이닉스"),
        ("035720", "카카오"),
    ]

    for code, name in targets:
        print(f"\n{'='*60}")
        print(f"{name} ({code})")
        print(f"{'='*60}")

        result = buildPayTimeSeries(code)
        if result is None:
            print("  결과 없음")
            continue

        print(f"  {result['corpName']} — {result['nYears']}년")

        if result["payByTypeDf"] is not None:
            print("\n  [유형별 보수 시계열]")
            print(result["payByTypeDf"])

        if result["topPayDf"] is not None:
            print("\n  [5억 초과 개인별 보수] (최근 3명만)")
            print(result["topPayDf"].head(6))

    # 대량 테스트
    print(f"\n\n{'='*60}")
    print("267개 대량 테스트")
    print(f"{'='*60}")

    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    hasType = 0
    hasIndiv = 0
    noData = 0
    errors = []

    for code in codes:
        try:
            result = buildPayTimeSeries(code)
            if result is None:
                noData += 1
            else:
                if result["payByTypeDf"] is not None:
                    hasType += 1
                if result["topPayDf"] is not None:
                    hasIndiv += 1
        except Exception as e:
            errors.append((code, str(e)[:100]))

    total = len(codes)
    print(f"  유형별 보수: {hasType}/{total}")
    print(f"  5억 초과 개인: {hasIndiv}/{total}")
    print(f"  NoData: {noData}")
    print(f"  에러: {len(errors)}")

    if errors:
        for code, msg in errors[:10]:
            print(f"    {code}: {msg}")
