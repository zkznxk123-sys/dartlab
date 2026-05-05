"""
실험 ID: 019-02
실험명: 감사의견 + 감사보수 파서 (개선)

목적:
- step01 문제점 수정
  1) 테이블 분류 개선 — opinion/fee/nonAuditFee/schedule/communication 정확 분리
  2) 현대차 패턴B (당기/전기 없이 제N기만) → 제N기 숫자 기반 연도 매핑
  3) 기재정정 보고서 fallback
  4) 감사보수 테이블 파싱 확인

가설:
1. 개선된 분류로 opinion/fee 테이블 정확 분리 가능
2. 267개 기업 95% 이상 파싱 성공

방법:
1. classifyTable 강화 — 헤더 첫 행으로 분류
2. fiscalPeriodToYear 개선 — 제N기 숫자 기반 당기=최대N, 전기=N-1
3. findAuditSection 개선 — 원본 없으면 기재정정 fallback
4. 267개 대량 테스트

결과 (실험 후 작성):

결론:

실험일: 2026-03-07
"""
import os
import re
import sys

import polars as pl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

AUDIT_TITLE_KEYWORDS = [
    "외부감사에 관한 사항",
    "감사인의 감사의견",
    "회계감사인의 감사의견",
    "감사인(공인회계사)의 감사의견",
]


def findAuditSections(df: pl.DataFrame, year: str) -> list[str]:
    """사업보고서에서 감사 관련 섹션 내용 목록 반환. 원본 우선, 기재정정 fallback."""
    report = df.filter(
        (pl.col("year") == year)
        & (pl.col("report_type").str.contains("사업보고서"))
        & (~pl.col("report_type").str.contains("기재정정|첨부"))
    )
    if report.height == 0:
        report = df.filter(
            (pl.col("year") == year)
            & (pl.col("report_type").str.contains("사업보고서"))
        )
        if report.height > 0:
            latest = report.sort("rcept_date", descending=True)
            latestType = latest["report_type"][0]
            report = report.filter(pl.col("report_type") == latestType)

    if report.height == 0:
        return []

    results = []
    for row in report.iter_rows(named=True):
        title = row["section_title"]
        for kw in AUDIT_TITLE_KEYWORDS:
            if kw in title:
                content = row["section_content"]
                if content:
                    results.append(content)
                break

    return results


def extractMarkdownTables(text: str) -> list[list[list[str]]]:
    """마크다운 텍스트에서 테이블들을 추출."""
    tables = []
    currentTable = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if all(re.match(r"^-+$|^:?-+:?$", c) for c in cells if c):
                continue
            currentTable.append(cells)
        else:
            if currentTable and len(currentTable) >= 2:
                tables.append(currentTable)
            currentTable = []
    if currentTable and len(currentTable) >= 2:
        tables.append(currentTable)
    return tables


def classifyTable(table: list[list[str]]) -> str:
    """테이블 분류: opinion, fee, nonAuditFee, internalControl, schedule, communication, unknown."""
    if len(table) < 2:
        return "unknown"

    header = table[0]
    headerStr = " ".join(header)
    allFirst3 = " ".join(" ".join(row) for row in table[:min(3, len(table))])

    if "비감사" in allFirst3:
        return "nonAuditFee"

    if "커뮤니케이션" in allFirst3 or "참석자" in headerStr:
        return "communication"

    if "검토기간" in allFirst3 or "사전검토" in allFirst3 or ("일 정" in headerStr and "구 분" in headerStr):
        return "schedule"

    if ("내부회계" in allFirst3 or "내부통제" in allFirst3) and "감사의견" not in allFirst3:
        if "감사인" in headerStr and ("의견" in headerStr or "감사의견" in headerStr):
            return "internalControl"

    if "보수" in headerStr and "시간" in headerStr:
        return "fee"
    if "감사계약" in allFirst3 and "보수" in allFirst3:
        return "fee"

    if "감사의견" in headerStr:
        return "opinion"
    if "감사인" in headerStr and ("의견" in headerStr or "감사의견" in allFirst3):
        return "opinion"
    if "사업연도" in headerStr and "감사인" in headerStr and "적정" in allFirst3:
        return "opinion"

    return "unknown"


def parseOpinionTable(table: list[list[str]]) -> list[dict]:
    """감사의견 테이블 파싱.

    8열 패턴: 사업연도 | 구분 | 감사인 | 감사의견 | 의견변형사유 | 계속기업 | 강조사항 | 핵심감사사항
    5열 패턴: 사업연도 | 감사인 | 감사의견 | 강조사항 | 핵심감사사항
    """
    header = table[0]
    nCols = len(header)
    results = []
    currentPeriod = ""

    isWide = nCols >= 7
    hasReportType = any("구분" in h for h in header)

    for row in table[1:]:
        while len(row) < max(nCols, 8):
            row.append("")

        firstCell = row[0].strip()
        if firstCell and "기" in firstCell:
            currentPeriod = firstCell

        if isWide and hasReportType:
            auditor = row[2].strip()
            opinion = row[3].strip()
            goingConcern = row[5].strip() if len(row) > 5 else ""
            emphasis = row[6].strip() if len(row) > 6 else ""
            keyMatters = row[7].strip() if len(row) > 7 else ""
            reportType = row[1].strip()

            if firstCell == "" and reportType:
                pass
            elif firstCell and not reportType:
                reportType = ""
        elif isWide:
            auditor = row[1].strip()
            opinion = row[2].strip()
            goingConcern = ""
            emphasis = row[3].strip() if len(row) > 3 else ""
            keyMatters = row[4].strip() if len(row) > 4 else ""
            reportType = ""
        else:
            auditor = row[1].strip()
            opinion = row[2].strip()
            goingConcern = ""
            emphasis = row[3].strip() if len(row) > 3 else ""
            keyMatters = row[4].strip() if len(row) > 4 else ""
            reportType = ""

        if not auditor or auditor in ("-", ""):
            continue
        if "회계법인" not in auditor and "감사" not in auditor and "법인" not in auditor:
            if not re.search(r"(EY|KPMG|PwC|PWC|Deloitte)", auditor, re.IGNORECASE):
                continue

        period = currentPeriod
        if firstCell and "기" in firstCell:
            period = firstCell
        elif not firstCell and not reportType:
            continue

        results.append({
            "fiscalPeriod": period,
            "reportType": reportType,
            "auditor": auditor,
            "opinion": opinion,
            "goingConcern": goingConcern,
            "emphasis": emphasis,
            "keyAuditMatters": keyMatters,
        })

    return results


def parseFeeTable(table: list[list[str]]) -> list[dict]:
    """감사용역 체결 현황 테이블 파싱."""
    headerRow = 0
    for i, row in enumerate(table):
        rowStr = " ".join(row)
        if "보수" in rowStr and "시간" in rowStr and i > 0:
            headerRow = i
            break

    results = []
    currentPeriod = ""

    for row in table[headerRow + 1:]:
        if len(row) < 4:
            continue

        firstCell = row[0].strip()
        if firstCell and "기" in firstCell:
            currentPeriod = firstCell

        auditor = row[1].strip() if len(row) > 1 else ""
        content = row[2].strip() if len(row) > 2 else ""

        contractFee = _parseNum(row[3]) if len(row) > 3 else None
        contractHours = _parseNum(row[4]) if len(row) > 4 else None
        actualFee = _parseNum(row[5]) if len(row) > 5 else None
        actualHours = _parseNum(row[6]) if len(row) > 6 else None

        if not auditor or "회계법인" not in auditor:
            if not re.search(r"(EY|KPMG|PwC|PWC|Deloitte)", auditor, re.IGNORECASE):
                continue

        results.append({
            "fiscalPeriod": currentPeriod if currentPeriod else firstCell,
            "auditor": auditor,
            "content": content,
            "contractFee": contractFee,
            "contractHours": contractHours,
            "actualFee": actualFee,
            "actualHours": actualHours,
        })

    return results


def _parseNum(s: str) -> float | None:
    if not s:
        return None
    s = s.strip()
    if s in ("-", "", "해당사항없음", "해당사항 없음"):
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "").replace(" ", "")
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return None


_FISCAL_NUM_RE = re.compile(r"제?(\d+)기")


def fiscalPeriodToYear(fiscalPeriod: str, baseYear: str, allPeriods: list[str] | None = None) -> str | None:
    """제N기(당기/전기) → 실제 연도 변환.

    방법 1: 당기/전기/전전기 마커 기반 (baseYear 기준)
    방법 2: 마커 없으면 제N기 숫자 비교 (allPeriods에서 최대 N = 당기)
    """
    base = int(baseYear)

    if re.search(r"당기|당분기|당반기", fiscalPeriod):
        return str(base)
    if re.search(r"전전기", fiscalPeriod):
        return str(base - 2)
    if re.search(r"전기", fiscalPeriod):
        return str(base - 1)

    m = _FISCAL_NUM_RE.search(fiscalPeriod)
    if m and allPeriods:
        thisNum = int(m.group(1))
        maxNum = 0
        for p in allPeriods:
            pm = _FISCAL_NUM_RE.search(p)
            if pm:
                maxNum = max(maxNum, int(pm.group(1)))
        if maxNum > 0:
            diff = maxNum - thisNum
            return str(base - diff)

    return None


def parseAuditData(df: pl.DataFrame, year: str) -> dict | None:
    """한 연도의 감사 데이터 전체 파싱."""
    sections = findAuditSections(df, year)
    if not sections:
        return None

    allOpinions = []
    allFees = []
    totalTables = 0

    for content in sections:
        tables = extractMarkdownTables(content)
        totalTables += len(tables)

        for table in tables:
            kind = classifyTable(table)
            if kind == "opinion":
                parsed = parseOpinionTable(table)
                if parsed:
                    allOpinions.extend(parsed)
            elif kind == "fee":
                parsed = parseFeeTable(table)
                if parsed:
                    allFees.extend(parsed)

    if not allOpinions and not allFees:
        return None

    allPeriods = list({op["fiscalPeriod"] for op in allOpinions})
    allPeriods.extend(fee["fiscalPeriod"] for fee in allFees)
    allPeriods = list(set(allPeriods))

    for op in allOpinions:
        op["year"] = fiscalPeriodToYear(op["fiscalPeriod"], year, allPeriods)
    for fee in allFees:
        fee["year"] = fiscalPeriodToYear(fee["fiscalPeriod"], year, allPeriods)

    return {
        "opinions": allOpinions,
        "fees": allFees,
        "nTables": totalTables,
    }


if __name__ == "__main__":
    targets = [
        ("005930", "삼성전자"),
        ("005380", "현대자동차"),
        ("000660", "SK하이닉스"),
        ("035720", "카카오"),
        ("003550", "LG"),
        ("055550", "신한지주"),
    ]

    for code, name in targets:
        path = os.path.join(DATA_DIR, f"{code}.parquet")
        if not os.path.exists(path):
            continue
        df = pl.read_parquet(path)
        years = sorted(df["year"].unique().to_list(), reverse=True)

        print(f"\n{'='*60}")
        print(f"{name} ({code})")
        print(f"{'='*60}")

        for year in years[:2]:
            result = parseAuditData(df, year)
            if result is None:
                print(f"  {year}: 파싱 실패")
                continue

            print(f"\n  [{year}] 테이블 {result['nTables']}개")

            if result["opinions"]:
                print(f"  감사의견 {len(result['opinions'])}건:")
                for op in result["opinions"]:
                    print(f"    {op['fiscalPeriod']} → {op['year']} | {op['reportType'] or '(단일)'} | {op['auditor']} | {op['opinion']}")
                    if op["keyAuditMatters"] and op["keyAuditMatters"] not in ("해당사항 없음", "해당사항없음", "-"):
                        km = op["keyAuditMatters"][:80]
                        print(f"      핵심감사: {km}...")

            if result["fees"]:
                print(f"  감사보수 {len(result['fees'])}건:")
                for fee in result["fees"]:
                    print(f"    {fee['fiscalPeriod']} → {fee['year']} | {fee['auditor']} | 계약보수={fee['contractFee']} 실제보수={fee['actualFee']} 시간={fee['actualHours']}")
            else:
                print("  감사보수: 없음")

    print(f"\n\n{'='*60}")
    print("267개 대량 테스트")
    print(f"{'='*60}")

    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])
    ok = 0
    fail = 0
    noOpinion = 0
    noFee = 0
    errors = []

    for f in files:
        code = f.replace(".parquet", "")
        df = pl.read_parquet(os.path.join(DATA_DIR, f))
        years = sorted(df["year"].unique().to_list(), reverse=True)

        found = False
        for year in years[:3]:
            result = parseAuditData(df, year)
            if result and result["opinions"]:
                ok += 1
                found = True
                if not result["fees"]:
                    noFee += 1
                break

        if not found:
            fail += 1
            corp = df["corp_name"][0] if "corp_name" in df.columns else code
            errors.append(f"{corp}({code})")

    print(f"\n감사의견 파싱 성공: {ok}/{ok+fail} ({100*ok/(ok+fail):.1f}%)")
    print(f"감사보수 없음: {noFee}건")
    if errors:
        print(f"실패 ({len(errors)}건): {', '.join(errors[:20])}")
