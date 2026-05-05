"""
실험 ID: 019-03
실험명: 감사의견 + 감사보수 파서 (최종)

목적:
- step02 문제 해결
  1) extractMarkdownTables: separator 포함하여 연속 파이프라인을 하나의 블록으로 묶기
  2) 1셀 제목행 스킵, 서브헤더(보수/시간) 스킵
  3) classifyTable: 전체 블록 텍스트 기반 분류
  4) parseFeeTable: 서브헤더 아래 데이터 정확 매핑
  5) 중복 제거 (같은 fiscalPeriod+auditor+reportType 중복 제거)

가설:
1. 감사의견 + 보수 테이블 95% 이상 파싱 성공
2. 시계열 DataFrame으로 깔끔하게 정리 가능

방법:
1. 파이프 라인 연속 블록 → 하나의 "raw block" (separator 제거)
2. 1셀 행 → 메타(제목/단위)로 분리
3. 실제 데이터 행만 남겨서 파싱
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
    """사업보고서에서 감사 관련 섹션 내용 반환. 원본 우선, 기재정정 fallback."""
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


def _isSeparator(cells: list[str]) -> bool:
    return all(re.match(r"^-+$|^:?-+:?$", c) for c in cells if c)


def extractTableBlocks(text: str) -> list[dict]:
    """마크다운 테이블 블록 추출.

    연속 파이프 라인을 수집한 뒤, 1셀 제목행 기준으로 서브블록 분리.
    반환: [{"meta": [str], "header": [str], "subheader": [str]|None, "rows": [[str]]}]
    """
    rawGroups = []
    currentLines = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            currentLines.append(stripped)
        else:
            if currentLines:
                rawGroups.append(currentLines[:])
                currentLines = []
    if currentLines:
        rawGroups.append(currentLines[:])

    blocks = []
    for rawLines in rawGroups:
        parsed = _splitAndParseBlocks(rawLines)
        blocks.extend(parsed)

    return blocks


def _splitAndParseBlocks(lines: list[str]) -> list[dict]:
    """연속 파이프 라인을 1셀 제목행 기준으로 서브블록 분리 후 각각 파싱."""
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 2:
        return []

    subGroups = []
    current = []

    for row in rows:
        nCells = len([c for c in row if c.strip()])
        if nCells <= 1 and current:
            hasHeader = any(len([c for c in r if c.strip()]) > 1 for r in current)
            if hasHeader:
                subGroups.append(current)
                current = []
        current.append(row)

    if current:
        subGroups.append(current)

    results = []
    for group in subGroups:
        block = _parseSubBlock(group)
        if block:
            results.append(block)

    return results


def _parseSubBlock(rows: list[list[str]]) -> dict | None:
    """서브블록 → 구조화된 블록."""
    meta = []
    dataRows = []
    header = None
    subheader = None

    for row in rows:
        nCells = len([c for c in row if c.strip()])
        if nCells <= 1:
            if header is None:
                meta.append(row[0].strip() if row else "")
            continue

        if header is None:
            header = row
            continue

        if subheader is None and header:
            isSubheader = all(
                c.strip() in ("보수", "시간", "") for c in row
            )
            if isSubheader and "보수" in " ".join(row):
                subheader = row
                continue

        dataRows.append(row)

    if not header or not dataRows:
        return None

    return {
        "meta": meta,
        "header": header,
        "subheader": subheader,
        "rows": dataRows,
    }


def classifyBlock(block: dict) -> str:
    """블록 분류: opinion, fee, nonAuditFee, internalControl, schedule, communication, unknown."""
    headerStr = " ".join(block["header"])
    metaStr = " ".join(block["meta"]) if block["meta"] else ""
    allText = metaStr + " " + headerStr

    row1Str = " ".join(block["rows"][0]) if block["rows"] else ""
    allText += " " + row1Str

    if "비감사" in allText:
        return "nonAuditFee"

    if "커뮤니케이션" in allText or "참석자" in headerStr or "논의 내용" in headerStr:
        return "communication"

    if "검토기간" in allText or "사전검토" in allText:
        return "schedule"
    if "일 정" in headerStr and ("구 분" in headerStr or "구분" in headerStr):
        return "schedule"

    if ("보수" in headerStr and "시간" in headerStr) or block["subheader"]:
        return "fee"
    if "감사계약" in allText and "보수" in allText:
        return "fee"

    if "내부회계" in metaStr and "감사의견" not in allText:
        return "internalControl"

    if "감사의견" in headerStr:
        return "opinion"
    if "감사인" in headerStr and ("의견" in headerStr or "감사의견" in allText):
        return "opinion"
    if "사업연도" in headerStr and "감사인" in headerStr:
        if "적정" in " ".join(" ".join(r) for r in block["rows"][:3]):
            return "opinion"

    if "변경" in allText and "감사인" in allText:
        return "auditorChange"

    return "unknown"


def parseOpinionBlock(block: dict) -> list[dict]:
    """감사의견 블록 파싱."""
    header = block["header"]
    nCols = len(header)
    results = []
    currentPeriod = ""

    hasReportType = any("구분" in h for h in header)
    isWide = nCols >= 7

    for row in block["rows"]:
        while len(row) < max(nCols, 8):
            row.append("")

        firstCell = row[0].strip()
        if firstCell and "기" in firstCell:
            currentPeriod = firstCell

        if isWide and hasReportType:
            reportType = row[1].strip()
            auditor = row[2].strip()
            opinion = row[3].strip()
            goingConcern = row[5].strip() if len(row) > 5 else ""
            emphasis = row[6].strip() if len(row) > 6 else ""
            keyMatters = row[7].strip() if len(row) > 7 else ""

            if not firstCell and reportType:
                pass
        elif isWide:
            reportType = ""
            auditor = row[1].strip()
            opinion = row[2].strip()
            goingConcern = ""
            emphasis = row[3].strip() if len(row) > 3 else ""
            keyMatters = row[4].strip() if len(row) > 4 else ""
        else:
            reportType = ""
            auditor = row[1].strip()
            opinion = row[2].strip()
            goingConcern = ""
            emphasis = row[3].strip() if len(row) > 3 else ""
            keyMatters = row[4].strip() if len(row) > 4 else ""

        if not _isAuditor(auditor):
            continue

        period = currentPeriod if currentPeriod else firstCell

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


def parseFeeBlock(block: dict) -> list[dict]:
    """감사보수 블록 파싱."""
    results = []
    currentPeriod = ""

    for row in block["rows"]:
        while len(row) < 7:
            row.append("")

        firstCell = row[0].strip()
        if firstCell and "기" in firstCell:
            currentPeriod = firstCell

        auditor = row[1].strip()
        content = row[2].strip()

        if not _isAuditor(auditor):
            continue

        contractFee = _parseNum(row[3])
        contractHours = _parseNum(row[4])
        actualFee = _parseNum(row[5])
        actualHours = _parseNum(row[6])

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


def _isAuditor(s: str) -> bool:
    if not s or s in ("-", ""):
        return False
    if "회계법인" in s or "감사법인" in s:
        return True
    if re.search(r"(EY|KPMG|PwC|PWC|Deloitte)", s, re.IGNORECASE):
        return True
    return False


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
    """한 연도의 감사 데이터 파싱."""
    sections = findAuditSections(df, year)
    if not sections:
        return None

    allOpinions = []
    allFees = []
    totalBlocks = 0

    for content in sections:
        blocks = extractTableBlocks(content)
        totalBlocks += len(blocks)

        for block in blocks:
            kind = classifyBlock(block)
            if kind == "opinion":
                parsed = parseOpinionBlock(block)
                allOpinions.extend(parsed)
            elif kind == "fee":
                parsed = parseFeeBlock(block)
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

    allOpinions = _dedup(allOpinions, ["fiscalPeriod", "reportType", "auditor"])
    allFees = _dedup(allFees, ["fiscalPeriod", "auditor"])

    return {
        "opinions": allOpinions,
        "fees": allFees,
        "nBlocks": totalBlocks,
    }


def _dedup(items: list[dict], keys: list[str]) -> list[dict]:
    """중복 제거 (첫 출현 유지)."""
    seen = set()
    result = []
    for item in items:
        k = tuple(item.get(key, "") for key in keys)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


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

            print(f"\n  [{year}] 블록 {result['nBlocks']}개")

            if result["opinions"]:
                print(f"  감사의견 {len(result['opinions'])}건:")
                for op in result["opinions"]:
                    print(f"    {op['fiscalPeriod']} → {op['year']} | {op['reportType'] or '(단일)'} | {op['auditor']} | {op['opinion']}")

            if result["fees"]:
                print(f"  감사보수 {len(result['fees'])}건:")
                for fee in result["fees"]:
                    print(f"    {fee['fiscalPeriod']} → {fee['year']} | {fee['auditor']} | 계약={fee['contractFee']} 실제={fee['actualFee']} 시간={fee['actualHours']}")
            else:
                print("  감사보수: 없음")

    print(f"\n\n{'='*60}")
    print("267개 대량 테스트")
    print(f"{'='*60}")

    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])
    ok = 0
    fail = 0
    noFee = 0
    hasFeeOk = 0
    errors = []
    noData = 0

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
                if result["fees"]:
                    hasFeeOk += 1
                else:
                    noFee += 1
                break

        if not found:
            hasAuditSection = False
            for year in years[:3]:
                sections = findAuditSections(df, year)
                if sections:
                    hasAuditSection = True
                    break
            if hasAuditSection:
                fail += 1
                corp = df["corp_name"][0] if "corp_name" in df.columns else code
                errors.append(f"{corp}({code})")
            else:
                noData += 1

    total = ok + fail
    print(f"\n감사 섹션 있는 기업: {total}/{total+noData}")
    print(f"감사의견 파싱 성공: {ok}/{total} ({100*ok/total:.1f}%)" if total else "")
    print(f"감사보수도 성공: {hasFeeOk}/{ok}")
    print(f"감사보수 없음: {noFee}건")
    print(f"데이터 없음 (감사 섹션 자체 없음): {noData}건")
    if errors:
        print(f"파싱 실패 ({len(errors)}건): {', '.join(errors[:20])}")
