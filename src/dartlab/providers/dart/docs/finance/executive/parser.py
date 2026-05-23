"""임원 현황 테이블 파서."""

import re

# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────


def _cellsFromLine(line: str) -> list[str]:
    """파이프 라인에서 셀 추출."""
    return [c.strip() for c in line.split("|")[1:-1]]


def _isSeparator(cells: list[str]) -> bool:
    """--- 구분선 여부."""
    return all(re.match(r"^-+$", c.strip()) or c.strip() == "" for c in cells)


def _flatText(cells: list[str]) -> str:
    """셀 합쳐서 하나의 텍스트."""
    return " ".join(c for c in cells if c.strip())


def _parseFloat(text: str) -> float | None:
    """실수 파싱."""
    if not text or text.strip() in ("-", "", "—", "해당없음"):
        return None
    text = text.replace(",", "").replace(" ", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


# ──────────────────────────────────────────────
# 테이블 블록 추출 + 분류
# ──────────────────────────────────────────────


def extractTableBlocks(content: str) -> list[list[str]]:
    """content에서 연속된 파이프라인 블록 추출.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> extractTableBlocks(...)

    Returns:
        <TODO: return desc> (list[list[str]])
    """
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


def classifyBlock(block: list[str]) -> str:
    """테이블 블록 분류.

    Returns: "executive" | "unregisteredPay" | "other"

    Raises:
        없음.

    Example:
        >>> classifyBlock(...)

    Args:
        block: <TODO: param desc> (list[str])
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

    # 미등기임원 보수: "미등기" + "인원" + "급여"
    if re.search(r"미등기", allText) and re.search(r"인원|급여|보수", allText):
        return "unregisteredPay"

    return "other"


# ──────────────────────────────────────────────
# 등기임원 테이블 파서
# ──────────────────────────────────────────────


_POSITION_KEYWORDS = ("회장", "부회장", "사장", "부사장", "전무", "상무", "이사", "감사", "대표")
_REGISTRATION_KEYWORDS = ("사내이사", "사외이사", "기타비상무이사", "비상무이사", "감사위원", "상근감사")
_GENDER_VALUES = {"남", "여"}
_FULLTIME_VALUES = {"상근", "비상근"}


def _looksLikePosition(text: str) -> bool:
    """직위 키워드 포함 여부."""
    if not text:
        return False
    return any(k in text for k in _POSITION_KEYWORDS)


def _looksLikeRegistration(text: str) -> bool:
    """등기임원 구분 키워드 포함 여부."""
    if not text:
        return False
    return any(k in text for k in _REGISTRATION_KEYWORDS)


def parseExecutiveBlock(block: list[str]) -> list[dict]:
    """등기임원 테이블에서 임원 리스트 추출.

    DART 사업보고서 임원 표는 기업·연도별로 컬럼 수·순서·셀 병합이 다양하다.
    헤더 위치 매핑만으로는 대기업 케이스에서 컬럼이 밀려 gender·position 이 뒤섞인다.
    헤더 매핑 + 값 타입 키워드 fallback 하이브리드로 안정화한다.

    Returns:
        [{name, gender, position, registrationType, fullTime, responsibility, isCeo}]

    Raises:
        없음.

    Example:
        >>> parseExecutiveBlock(...)

    Args:
        block: <TODO: param desc> (list[str])
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
        if any("성명" in c for c in row):
            headerIdx = i
            break

    if headerIdx is None:
        return []

    subHeaderIdx = None
    if headerIdx + 1 < len(rows):
        nextRow = rows[headerIdx + 1]
        if any("의결권" in c for c in nextRow):
            subHeaderIdx = headerIdx + 1

    dataStart = (subHeaderIdx or headerIdx) + 1

    header = rows[headerIdx]
    nCols = len(header)

    colMap: dict[str, int] = {}
    for i, h in enumerate(header):
        h = h.strip()
        if "성명" in h:
            colMap["name"] = i
        elif "성별" in h:
            colMap["gender"] = i
        elif "직위" in h and "담당" not in h:
            colMap["position"] = i
        elif "담당업무" in h or "담당" in h:
            colMap["responsibility"] = i
        elif "등기" in h:
            colMap["registrationType"] = i
        elif "상근" in h:
            colMap["fullTime"] = i

    result = []
    for row in rows[dataStart:]:
        if len(row) < 4:
            continue
        filled = [c for c in row if c.strip() and c.strip() != "-"]
        if len(filled) < 2:
            continue

        while len(row) < nCols:
            row.append("")

        name = row[colMap["name"]].strip() if "name" in colMap else ""
        if not name:
            continue

        # 헤더 매핑 1차 시도
        gender = row[colMap["gender"]].strip() if "gender" in colMap else ""
        position = row[colMap["position"]].strip() if "position" in colMap else ""
        registrationType = row[colMap["registrationType"]].strip() if "registrationType" in colMap else ""
        fullTime = row[colMap["fullTime"]].strip() if "fullTime" in colMap else ""
        responsibility = row[colMap["responsibility"]].strip() if "responsibility" in colMap else ""

        # 값 타입 fallback — 대기업 케이스: 셀 병합으로 헤더 위치가 어긋날 때 값으로 재분류
        allCells = [c.strip() for c in row if c.strip()]
        if gender not in _GENDER_VALUES:
            gender = next((c for c in allCells if c in _GENDER_VALUES), gender)
        if not _looksLikePosition(position):
            # position 칸에 직위 대신 경력이 들어온 케이스 → 다른 셀에서 직위 후보 찾기
            picked = next((c for c in allCells if _looksLikePosition(c) and len(c) <= 10), position)
            if _looksLikePosition(picked) or not position:
                position = picked
        if not _looksLikeRegistration(registrationType):
            reg = next((c for c in allCells if _looksLikeRegistration(c)), registrationType)
            registrationType = reg
        if fullTime not in _FULLTIME_VALUES:
            fullTime = next((c for c in allCells if c in _FULLTIME_VALUES), fullTime)

        # 대표이사 여부 — 모든 셀에서 "대표이사" 문자열 탐색
        rowText = " ".join(allCells)
        isCeo = "대표이사" in rowText or "CEO" in rowText

        result.append(
            {
                "name": name,
                "gender": gender,
                "position": position,
                "registrationType": registrationType,
                "fullTime": fullTime,
                "responsibility": responsibility,
                "isCeo": isCeo,
            }
        )

    return result


def aggregateExecutives(executives: list[dict]) -> dict:
    """임원 리스트에서 집계 통계 생성.

    Args:
        executives: 인자.

    Raises:
        없음.

    Example:
        >>> aggregateExecutives(...)

    Returns:
        <TODO: return desc> (dict)
    """
    total = len(executives)
    inside = sum(1 for e in executives if "사내" in e.get("registrationType", ""))
    outside = sum(1 for e in executives if "사외" in e.get("registrationType", ""))
    otherNonexec = sum(1 for e in executives if "기타" in e.get("registrationType", ""))
    fullTime = sum(1 for e in executives if e.get("fullTime", "") == "상근")
    partTime = sum(1 for e in executives if e.get("fullTime", "") == "비상근")
    male = sum(1 for e in executives if e.get("gender", "") == "남")
    female = sum(1 for e in executives if e.get("gender", "") == "여")
    ceo = sum(1 for e in executives if e.get("isCeo"))

    return {
        "totalRegistered": total,
        "insideDirectors": inside,
        "outsideDirectors": outside,
        "otherNonexec": otherNonexec,
        "fullTimeCount": fullTime,
        "partTimeCount": partTime,
        "maleCount": male,
        "femaleCount": female,
        "ceoCount": ceo,
    }


# ──────────────────────────────────────────────
# 미등기임원 보수 테이블 파서
# ──────────────────────────────────────────────


def parseUnregisteredPayBlock(block: list[str]) -> dict | None:
    """미등기임원 보수 테이블 파싱.

    Returns:
        {
            "headcount": int,
            "totalSalary": float,      # 백만원
            "avgSalary": float,        # 백만원
        }

    Raises:
        없음.

    Example:
        >>> parseUnregisteredPayBlock(...)

    Args:
        block: <TODO: param desc> (list[str])
    """
    rows = []
    for line in block:
        cells = _cellsFromLine(line)
        if _isSeparator(cells):
            continue
        rows.append(cells)

    if len(rows) < 3:
        return None

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
