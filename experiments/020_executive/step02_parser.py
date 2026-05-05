"""
실험 ID: 020-02
실험명: 임원 현황 파서 — 등기임원 리스트 + 직원현황 + 보수 테이블

목적:
- "1. 임원 및 직원 등의 현황" 섹션에서 3가지 핵심 테이블 파싱
- 1) 등기임원 리스트 → 사내이사/사외이사/기타 인원수 집계
- 2) 직원 현황 → 총 직원수, 평균근속, 1인평균급여
- 3) 미등기임원 보수 → 인원수, 1인평균급여

가설:
1. 등기임원 테이블은 "성명|성별|출생년월|직위|등기임원여부|상근여부" 헤더를 가짐
2. 직원 현황 테이블은 "직원|소속 외근로자" 또는 "사업부문|성별|직원수" 헤더
3. 미등기임원 보수 테이블은 "구분|인원수|연간급여 총액|1인평균 급여액" 헤더

방법:
1. 섹션 content에서 테이블 블록 추출
2. 헤더 패턴으로 테이블 분류
3. 각 테이블 파서 구현
4. 267개 전수 테스트

결과 (실험 후 작성):

결론:

실험일: 2026-03-07
"""
import os
import re
import sys

import polars as pl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dartlab.core.dataLoader import loadData
from dartlab.core.reportSelector import selectReport

DATA_DIR = r"C:\Users\MSI\OneDrive\Desktop\sideProject\nicegui\eddmpython\data\dartData\docsData"

EXECUTIVE_SECTION_PATTERNS = [
    r"임원.*직원.*현황",
    r"임원.*현황",
]


# ──────────────────────────────────────────────
# 섹션 탐색
# ──────────────────────────────────────────────

def findExecutiveSection(df: pl.DataFrame, year: str) -> str | None:
    """임원 현황 섹션의 content 반환. 소분류('1. 임원 및 직원 등의 현황') 우선."""
    report = selectReport(df, year, reportKind="annual")
    if report is None:
        return None

    candidates = []
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if any(re.search(p, title) for p in EXECUTIVE_SECTION_PATTERNS):
            candidates.append({
                "title": title,
                "content": row.get("section_content", "") or "",
                "isSubSection": not title.startswith(("V", "VI", "VII", "VIII", "IX")),
            })

    if not candidates:
        return None

    # 소분류(번호로 시작) 우선
    sub = [c for c in candidates if c["isSubSection"]]
    if sub:
        return sub[0]["content"]
    return candidates[0]["content"]


# ──────────────────────────────────────────────
# 테이블 블록 추출 + 분류
# ──────────────────────────────────────────────

def extractTableBlocks(content: str) -> list[list[str]]:
    """content에서 연속된 파이프라인 블록 추출."""
    lines = content.split("\n")
    blocks = []
    current = []
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


def _cellsFromLine(line: str) -> list[str]:
    """파이프 라인에서 셀 추출."""
    return [c.strip() for c in line.split("|")[1:-1]]


def _isSeparator(cells: list[str]) -> bool:
    """--- 구분선 여부."""
    return all(re.match(r"^-+$", c.strip()) or c.strip() == "" for c in cells)


def _flatText(cells: list[str]) -> str:
    """셀 합쳐서 하나의 텍스트."""
    return " ".join(c for c in cells if c.strip())


def classifyBlock(block: list[str]) -> str:
    """테이블 블록 분류.

    Returns: "executive" | "employee" | "unregisteredPay" | "other"
    """
    allText = ""
    for line in block[:8]:
        cells = _cellsFromLine(line)
        if not _isSeparator(cells):
            allText += " " + _flatText(cells)

    # 등기임원 테이블: "성명" + "등기임원" + ("상근" 또는 "출생")
    if re.search(r"성명", allText) and re.search(r"등기임원", allText):
        if re.search(r"상근|출생|직위", allText):
            return "executive"

    # 직원 현황: "직원" + "근속" or "급여"
    if re.search(r"직\s*원\s*수|직\s*원", allText) and re.search(r"근속|급여|평\s*균", allText):
        return "employee"

    # 미등기임원 보수: "미등기" + "인원" + "급여"
    if re.search(r"미등기", allText) and re.search(r"인원|급여|보수", allText):
        return "unregisteredPay"

    return "other"


# ──────────────────────────────────────────────
# 등기임원 테이블 파서
# ──────────────────────────────────────────────

def _parseNum(text: str) -> int | None:
    """숫자 파싱 (쉼표 제거)."""
    if not text or text.strip() in ("-", "", "—", "해당없음"):
        return None
    text = text.replace(",", "").replace(" ", "").strip()
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return None


def _parseFloat(text: str) -> float | None:
    """실수 파싱."""
    if not text or text.strip() in ("-", "", "—", "해당없음"):
        return None
    text = text.replace(",", "").replace(" ", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def parseExecutiveBlock(block: list[str]) -> list[dict]:
    """등기임원 테이블에서 임원 리스트 추출.

    Returns: [{name, gender, birthDate, position, registrationType,
               fullTime, duty, career, shares, relationship, tenure, expiryDate}]
    """
    rows = []
    for line in block:
        cells = _cellsFromLine(line)
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 3:
        return []

    # 헤더 찾기: "성명" 포함 행
    headerIdx = None
    for i, row in enumerate(rows):
        if any("성명" in c for c in row):
            headerIdx = i
            break

    if headerIdx is None:
        return []

    # 서브헤더 확인 (의결권있는 주식 | 의결권없는 주식)
    subHeaderIdx = None
    if headerIdx + 1 < len(rows):
        nextRow = rows[headerIdx + 1]
        if any("의결권" in c for c in nextRow):
            subHeaderIdx = headerIdx + 1

    dataStart = (subHeaderIdx or headerIdx) + 1

    # 헤더 분석 — 컬럼 매핑
    header = rows[headerIdx]
    nCols = len(header)

    # 컬럼 인덱스 찾기
    colMap = {}
    for i, h in enumerate(header):
        h = h.strip()
        if "성명" in h:
            colMap["name"] = i
        elif "성별" in h:
            colMap["gender"] = i
        elif "출생" in h:
            colMap["birthDate"] = i
        elif "직위" in h and "담당" not in h:
            colMap["position"] = i
        elif "등기" in h:
            colMap["registrationType"] = i
        elif "상근" in h:
            colMap["fullTime"] = i
        elif "담당" in h:
            colMap["duty"] = i
        elif "경력" in h:
            colMap["career"] = i
        elif "주식" in h or "소유" in h:
            colMap["shares"] = i
        elif "최대주주" in h or "관계" in h:
            colMap["relationship"] = i
        elif "재직" in h or "재임" in h:
            colMap["tenure"] = i
        elif "만료" in h:
            colMap["expiryDate"] = i

    result = []
    for row in rows[dataStart:]:
        if len(row) < 4:
            continue
        # 빈 행 스킵
        filled = [c for c in row if c.strip() and c.strip() != "-"]
        if len(filled) < 2:
            continue

        while len(row) < nCols:
            row.append("")

        entry = {
            "name": row[colMap["name"]].strip() if "name" in colMap else "",
            "gender": row[colMap["gender"]].strip() if "gender" in colMap else "",
            "birthDate": row[colMap["birthDate"]].strip() if "birthDate" in colMap else "",
            "position": row[colMap["position"]].strip() if "position" in colMap else "",
            "registrationType": row[colMap["registrationType"]].strip() if "registrationType" in colMap else "",
            "fullTime": row[colMap["fullTime"]].strip() if "fullTime" in colMap else "",
        }

        # 이름이 비었으면 스킵
        if not entry["name"]:
            continue

        result.append(entry)

    return result


def aggregateExecutives(executives: list[dict]) -> dict:
    """임원 리스트에서 집계 통계 생성.

    Returns:
        {
            "totalRegistered": int,
            "insideDirectors": int,    # 사내이사
            "outsideDirectors": int,   # 사외이사
            "otherNonexec": int,       # 기타비상무이사
            "fullTimeCount": int,      # 상근
            "partTimeCount": int,      # 비상근
            "maleCount": int,
            "femaleCount": int,
        }
    """
    total = len(executives)
    inside = sum(1 for e in executives if "사내" in e.get("registrationType", ""))
    outside = sum(1 for e in executives if "사외" in e.get("registrationType", ""))
    otherNonexec = sum(1 for e in executives if "기타" in e.get("registrationType", ""))
    fullTime = sum(1 for e in executives if e.get("fullTime", "") == "상근")
    partTime = sum(1 for e in executives if e.get("fullTime", "") == "비상근")
    male = sum(1 for e in executives if e.get("gender", "") == "남")
    female = sum(1 for e in executives if e.get("gender", "") == "여")

    return {
        "totalRegistered": total,
        "insideDirectors": inside,
        "outsideDirectors": outside,
        "otherNonexec": otherNonexec,
        "fullTimeCount": fullTime,
        "partTimeCount": partTime,
        "maleCount": male,
        "femaleCount": female,
    }


# ──────────────────────────────────────────────
# 직원 현황 테이블 파서
# ──────────────────────────────────────────────

def parseEmployeeBlock(block: list[str]) -> dict | None:
    """직원 현황 테이블에서 총 직원수, 평균근속, 1인평균급여 추출.

    Returns:
        {
            "totalEmployees": int,
            "avgTenure": float,        # 평균근속연수 (년)
            "totalSalary": float,      # 연간급여총액 (백만원)
            "avgSalary": float,        # 1인평균급여 (백만원)
        }
    """
    rows = []
    for line in block:
        cells = _cellsFromLine(line)
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 4:
        return None

    # 이 테이블은 복잡한 다중 헤더 구조
    # 마지막 행이 "합계" 또는 마지막 데이터행
    # 전략: "합계" 행을 찾아서 총 직원수 등 추출

    # 또 다른 전략: 모든 데이터행의 숫자를 합산
    # 일단 합계 행 찾기
    totalRow = None
    for row in rows:
        if any("합" in c and "계" in c for c in row[:3]):
            totalRow = row
            break

    if totalRow is None:
        # 합계 없으면 마지막 데이터행 시도
        return None

    # 합계 행에서 숫자 추출
    nums = []
    for cell in totalRow:
        n = _parseFloat(cell)
        if n is not None:
            nums.append(n)

    if not nums:
        return None

    # 전형적 구조: 합계 행 = ... | 합계남 | 합계여 | 합계계 | ... | 평균근속 | 연간급여총액 | 1인평균급여
    # 숫자가 4개 이상이면: 직원수, 평균근속, 급여총액, 1인평균 추정
    # 하지만 구조가 기업마다 다를 수 있으므로 보수적으로 처리

    return {
        "rawNums": nums,
        "rawRow": totalRow,
    }


# ──────────────────────────────────────────────
# 미등기임원 보수 테이블 파서
# ──────────────────────────────────────────────

def parseUnregisteredPayBlock(block: list[str]) -> dict | None:
    """미등기임원 보수 테이블 파싱.

    Returns:
        {
            "headcount": int,
            "totalSalary": float,      # 연간급여총액 (백만원)
            "avgSalary": float,        # 1인평균급여 (백만원)
        }
    """
    rows = []
    for line in block:
        cells = _cellsFromLine(line)
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 3:
        return None

    # 미등기임원 행 찾기
    for row in rows:
        if any("미등기" in c for c in row):
            nums = []
            for cell in row:
                n = _parseFloat(cell)
                if n is not None:
                    nums.append(n)
            if len(nums) >= 3:
                return {
                    "headcount": int(nums[0]),
                    "totalSalary": nums[1],
                    "avgSalary": nums[2],
                }
            elif len(nums) == 2:
                return {
                    "headcount": int(nums[0]),
                    "totalSalary": nums[1],
                    "avgSalary": None,
                }
    return None


# ──────────────────────────────────────────────
# 통합 파싱
# ──────────────────────────────────────────────

def parseExecutiveSection(content: str) -> dict:
    """임원 현황 섹션 전체를 파싱.

    Returns:
        {
            "executives": list[dict],      # 등기임원 리스트
            "stats": dict,                 # 집계 통계
            "employeeRaw": dict | None,    # 직원 현황 원시 데이터
            "unregisteredPay": dict | None, # 미등기임원 보수
        }
    """
    blocks = extractTableBlocks(content)

    executives = []
    employeeRaw = None
    unregisteredPay = None

    for block in blocks:
        kind = classifyBlock(block)
        if kind == "executive":
            parsed = parseExecutiveBlock(block)
            if parsed:
                executives = parsed  # 첫 번째(등기임원) 테이블만 사용
                break  # 미등기 리스트가 아닌 등기임원만

    for block in blocks:
        kind = classifyBlock(block)
        if kind == "employee" and employeeRaw is None:
            employeeRaw = parseEmployeeBlock(block)
        elif kind == "unregisteredPay" and unregisteredPay is None:
            unregisteredPay = parseUnregisteredPayBlock(block)

    stats = aggregateExecutives(executives) if executives else None

    return {
        "executives": executives,
        "stats": stats,
        "employeeRaw": employeeRaw,
        "unregisteredPay": unregisteredPay,
    }


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

        df = loadData(code)
        years = sorted(df["year"].unique().to_list(), reverse=True)

        content = findExecutiveSection(df, years[0])
        if content is None:
            print("  섹션 없음")
            continue

        result = parseExecutiveSection(content)

        if result["stats"]:
            s = result["stats"]
            print(f"  등기임원: {s['totalRegistered']}명")
            print(f"    사내이사: {s['insideDirectors']}, 사외이사: {s['outsideDirectors']}, 기타: {s['otherNonexec']}")
            print(f"    상근: {s['fullTimeCount']}, 비상근: {s['partTimeCount']}")
            print(f"    남: {s['maleCount']}, 여: {s['femaleCount']}")

            print("\n  [등기임원 리스트]")
            for e in result["executives"][:5]:
                print(f"    {e['name']:8s} | {e['gender']} | {e['position']:10s} | {e['registrationType']:10s} | {e['fullTime']}")
            if len(result["executives"]) > 5:
                print(f"    ... ({len(result['executives'])-5}명 더)")

        if result["unregisteredPay"]:
            p = result["unregisteredPay"]
            print(f"\n  미등기임원 보수: {p['headcount']}명, 총 {p.get('totalSalary', '?')}백만원, 1인평균 {p.get('avgSalary', '?')}백만원")

        if result["employeeRaw"]:
            print(f"\n  직원현황 원시: {result['employeeRaw']}")

    # 전수 테스트
    print(f"\n\n{'='*60}")
    print("267개 전수 테스트")
    print(f"{'='*60}")

    codes = sorted([f.replace(".parquet", "") for f in os.listdir(DATA_DIR) if f.endswith(".parquet")])

    hasExec = 0
    hasEmployee = 0
    hasUnregPay = 0
    noSection = 0
    errors = []

    for code in codes:
        try:
            df = loadData(code)
            years = sorted(df["year"].unique().to_list(), reverse=True)
            if not years:
                noSection += 1
                continue

            content = findExecutiveSection(df, years[0])
            if content is None:
                noSection += 1
                continue

            result = parseExecutiveSection(content)

            if result["stats"] and result["stats"]["totalRegistered"] > 0:
                hasExec += 1
            if result["employeeRaw"]:
                hasEmployee += 1
            if result["unregisteredPay"]:
                hasUnregPay += 1

        except Exception as e:
            errors.append((code, str(e)[:100]))

    total = len(codes)
    print(f"  등기임원 파싱 성공: {hasExec}/{total} ({hasExec*100//total}%)")
    print(f"  직원현황 파싱 성공: {hasEmployee}/{total} ({hasEmployee*100//total}%)")
    print(f"  미등기보수 파싱 성공: {hasUnregPay}/{total} ({hasUnregPay*100//total}%)")
    print(f"  섹션 없음: {noSection}")
    print(f"  에러: {len(errors)}")

    if errors:
        for code, msg in errors[:10]:
            print(f"    {code}: {msg}")
