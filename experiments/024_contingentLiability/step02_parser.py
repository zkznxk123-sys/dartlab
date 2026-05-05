"""
실험 ID: 024
실험명: 우발부채·채무보증·소송 파서

목적:
- 채무보증 테이블에서 보증금액 합계 추출
- 담보 테이블에서 담보금액 추출
- 소송 테이블에서 소송 정보 추출 (비정형)
- 267개 배치 테스트

가설:
1. 채무보증 테이블은 "보증금액|채무보증|지급보증" 키워드로 식별 가능
2. 소송은 "소제기일|소송당사자|소송가액" 키워드로 식별 가능
3. 220/267 이상에서 최소 하나의 데이터 추출 가능

방법:
1. 채무보증 테이블 파서
2. 소송 정보 파서
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


def parseAmount(text: str) -> int | None:
    """숫자 문자열을 정수로 변환."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None
    neg = False
    if text.startswith("(") and text.endswith(")"):
        neg = True
        text = text[1:-1]
    elif text.startswith("-") or text.startswith("△") or text.startswith("▲"):
        neg = True
        text = text.lstrip("-△▲")
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        return -val if neg else val
    except ValueError:
        return None


def extractTableBlocks(content: str) -> list[list[str]]:
    """content에서 |(pipe) 구분 테이블 블록들 추출."""
    lines = content.split("\n")
    blocks = []
    current = []
    for line in lines:
        stripped = line.strip()
        if "|" in stripped:
            current.append(stripped)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks


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


# ──────────────────────────────────────────────
# 1. 채무보증 파서
# ──────────────────────────────────────────────

def classifyBlock(block: list[str]) -> str:
    """블록 타입 분류."""
    text = " ".join(block[:8])

    # 소송 테이블 (key-value 형태)
    if "소제기일" in text or "소송 당사자" in text or "소송당사자" in text:
        return "lawsuit"

    # 소송 변형 (사건명/구상금 등)
    if "사건명" in text and ("원고" in text or "피고" in text or "소송" in text):
        return "lawsuit"

    # 소송 변형 ("구 분 | 내 용" 형태에서 소송 키워드 포함)
    if "소송" in text and ("원고" in text or "피고" in text):
        return "lawsuit"

    # 채무보증 상세 (기초/기말)
    if ("채무보증" in text or "보증금액" in text or "지급보증" in text) and "기초" in text and "기말" in text:
        return "guaranteeDetail"

    # 채무보증 요약
    if "보증금액" in text or "채무보증" in text or "지급보증" in text or "보증내역" in text:
        return "guaranteeSummary"

    # 담보
    if "담보" in text and ("자산" in text or "금액" in text or "제공" in text):
        return "collateral"

    # 약정 (한도 + 실행)
    if "약정" in text and ("한도" in text or "실행" in text):
        return "commitment"

    # 당기말/전기말 보증 테이블
    if ("당기말" in text or "당 기 말" in text) and ("전기말" in text or "전 기 말" in text):
        if "보증" in text or "채무" in text:
            return "guaranteeSummary"

    return "other"


def parseGuaranteeSummary(block: list[str]) -> dict | None:
    """채무보증 요약 테이블에서 총 보증금액 추출."""
    dataRows = [line for line in block if not isSeparatorRow(line)]

    totalAmount = 0
    count = 0

    for row in dataRows:
        cells = splitCells(row)
        if any("단위" in c for c in cells):
            continue

        # 숫자 셀 추출
        for cell in cells:
            c = cell.strip()
            if re.match(r"^[\d,]+$", c):
                val = parseAmount(c)
                if val and val > 0:
                    totalAmount += val
                    count += 1

    if count == 0:
        return None

    return {"totalGuaranteeAmount": totalAmount, "lineCount": count}


def parseGuaranteeDetail(block: list[str]) -> dict | None:
    """채무보증 상세 테이블에서 기말 보증금액 합계 추출."""
    dataRows = [line for line in block if not isSeparatorRow(line)]

    # 기말 컬럼 인덱스 찾기
    endColIdx = None
    for row in dataRows:
        cells = splitCells(row)
        for i, cell in enumerate(cells):
            if "기말" in cell:
                endColIdx = i
                break
        if endColIdx is not None:
            break

    if endColIdx is None:
        return None

    total = 0
    count = 0
    foundHeader = False

    for row in dataRows:
        cells = splitCells(row)
        if "기말" in " ".join(cells):
            foundHeader = True
            continue
        if not foundHeader:
            continue
        if len(cells) <= endColIdx:
            continue

        val = parseAmount(cells[endColIdx])
        if val and val > 0:
            total += val
            count += 1

    if count == 0:
        return None

    return {"totalGuaranteeAmount": total, "lineCount": count}


def parseLawsuit(block: list[str]) -> dict | None:
    """소송 정보 추출 (key-value 형태).

    | 구분 | 내용 |
    | 소제기일 | 2016.07.22 |
    | 소송 당사자 | 원고: xxx, 피고: 당사 |
    | 소송가액 | 12,274 (백만원) |
    | 진행상황 | ... |
    """
    result = {}

    for line in block:
        if isSeparatorRow(line):
            continue
        cells = splitCells(line)
        if len(cells) < 2:
            continue

        key = cells[0].strip()
        value = cells[1].strip()

        if "소제기일" in key:
            result["filingDate"] = value
        elif "당사자" in key:
            result["parties"] = value
        elif "내용" in key and "소송" in key:
            result["description"] = value
        elif "가액" in key or "금액" in key:
            result["amount"] = value
            # 금액 파싱 시도
            m = re.search(r"([\d,]+)", value)
            if m:
                result["amountValue"] = parseAmount(m.group(1))
        elif "진행" in key:
            result["status"] = value

    if not result:
        return None

    return result


# ──────────────────────────────────────────────
# 통합 파이프라인
# ──────────────────────────────────────────────

def parseContingentLiability(stockCode: str) -> dict | None:
    """우발부채 통합 파서."""
    try:
        df = loadData(stockCode)
    except Exception:
        return None

    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    guarantees = []
    lawsuits = []

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        content = None
        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if re.search(r"우발부채", title):
                content = row.get("section_content", "") or ""
                break

        if not content or len(content) < 50:
            continue

        # "해당사항 없음" 감지 — 데이터는 없지만 섹션은 존재
        if len(content) < 200 and ("없습니다" in content or "해당" in content):
            # 빈 결과 — 섹션 있지만 데이터 없음 (성공으로 카운트)
            if not guarantees and not lawsuits:
                return {
                    "corpName": corpName,
                    "nYears": len(years),
                    "guarantees": [],
                    "lawsuits": [],
                    "hasSection": True,
                    "noData": True,
                }

        blocks = extractTableBlocks(content)
        yearGuarantee = None
        yearLawsuits = []

        for block in blocks:
            kind = classifyBlock(block)

            if kind == "guaranteeDetail" and yearGuarantee is None:
                parsed = parseGuaranteeDetail(block)
                if parsed:
                    yearGuarantee = parsed
                    yearGuarantee["year"] = year

            elif kind == "guaranteeSummary" and yearGuarantee is None:
                parsed = parseGuaranteeSummary(block)
                if parsed:
                    yearGuarantee = parsed
                    yearGuarantee["year"] = year

            elif kind == "lawsuit":
                parsed = parseLawsuit(block)
                if parsed:
                    parsed["year"] = year
                    yearLawsuits.append(parsed)

        if yearGuarantee:
            guarantees.append(yearGuarantee)

        lawsuits.extend(yearLawsuits)

    if not guarantees and not lawsuits:
        return None

    return {
        "corpName": corpName,
        "nYears": len(years),
        "guarantees": guarantees,
        "lawsuits": lawsuits,
    }


# ──────────────────────────────────────────────
# 배치 테스트
# ──────────────────────────────────────────────

def batchTest():
    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    ok = noData = errors = 0
    guaranteeCount = lawsuitCount = 0

    for code in codes:
        try:
            result = parseContingentLiability(code)
            if result is None:
                noData += 1
            else:
                ok += 1
                if result["guarantees"]:
                    guaranteeCount += 1
                if result["lawsuits"]:
                    lawsuitCount += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR {code}: {e}")

    print(f"\n=== 배치 테스트 결과 ({len(codes)}개) ===")
    print(f"성공: {ok}, 데이터없음: {noData}, 에러: {errors}")
    print(f"채무보증: {guaranteeCount}, 소송: {lawsuitCount}")


def testSingle(stockCode: str):
    result = parseContingentLiability(stockCode)
    if result is None:
        print(f"  {stockCode}: 데이터 없음")
        return

    print(f"\n=== {result['corpName']} ({stockCode}) ===")

    for g in result["guarantees"][:3]:
        print(f"  [{g['year']}] 채무보증: {g['totalGuaranteeAmount']:,} ({g['lineCount']} 건)")

    for l in result["lawsuits"][:3]:
        print(f"  [{l['year']}] 소송: {l.get('parties', 'N/A')} 가액={l.get('amount', 'N/A')} 상태={l.get('status', 'N/A')[:50]}")


if __name__ == "__main__":
    testSingle("005930")
    testSingle("005380")
    testSingle("035720")
    print()
    batchTest()
