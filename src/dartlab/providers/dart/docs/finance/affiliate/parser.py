"""관계기업/공동기업 투자 파싱.

일반 테이블(2023↓, 2025) 및 XBRL 횡전개(2024) 포맷 지원.
"""

import re

from dartlab.providers._common.tableParser import parseAmount as _coreParseAmount
from dartlab.providers.dart.docs.finance.affiliate.types import AffiliateMovement, AffiliateProfile

# ── 금액 파싱 ──────────────────────────────────────────────────
# affiliate-specific: "0" → 0.0 (지분율 0% 유효 값) + "−" (U+2212) → None (no data marker).
# 그 외는 core.tableParser.parseAmount 위임 — 음수 / 괄호 / △ / % / 천단위 콤마 공통 처리.


def _parseAmount(text: str) -> float | None:
    """금액 문자열 → float. affiliate 전용 — 0 보존 + U+2212 no-data 처리."""
    s = text.strip().replace("\xa0", "").replace(" ", "")
    if s == "0":
        return 0.0
    if s == "−":
        return None
    return _coreParseAmount(text)


# ── 기업명 판별 상수 ──────────────────────────────────────────


_META_NAMES = {
    "구 분",
    "구분",
    "회사명",
    "기업명",
    "종 목",
    "기 업 명",
    "지분율(%)",
    "지분율",
    "소유지분율",
    "관계기업",
    "공동기업",
    "관계기업 및 공동기업",
    "소 계",
    "소계",
    "합 계",
    "합계",
    "계",
    "단위",
    "비 고",
    "비고",
    "기초",
    "기 초",
    "기말",
    "기 말",
    "취득",
    "취 득",
    "처분",
    "처 분",
    "배당",
    "배 당",
    "배당금",
    "손상",
    "손상차손",
    "기타",
    "기타변동",
    "기타증감액",
    "장부금액",
    "취득원가",
}


_MOVEMENT_ITEM_KEYWORDS = [
    "기초",
    "기말",
    "취득",
    "처분",
    "배당",
    "손상",
    "기타",
    "지분법",
    "이익 중",
    "자본변동",
    "연결범위",
    "환율변동",
    "대체",
    "원금회수",
]


def _isNameCell(text: str) -> bool:
    """셀이 기업명인지 판정."""
    s = text.strip()
    if not s:
        return False
    sClean = re.sub(r"\(\*?\d*\)", "", s).strip()
    if s in _META_NAMES or sClean in _META_NAMES:
        return False
    if any(sClean.startswith(kw) or sClean == kw for kw in _MOVEMENT_ITEM_KEYWORDS):
        return False
    if len(sClean) >= 20 and any(kw in sClean for kw in ["에 대한", "설명", "기술", "내역에 대한", "여부", "판단"]):
        return False
    if _parseAmount(s) is not None and s != "0":
        cleaned = re.sub(r"[,.\-%()△\s]", "", s)
        if cleaned.isdigit() or not cleaned:
            return False
    alphaChars = sum(1 for c in s if c.isalpha())
    return alphaChars >= 2


# ── 투자현황 (프로필) ─────────────────────────────────────────


_PROFILE_NAME_KEYWORDS = [
    "회사명",
    "회 사 명",
    "기업명",
    "기 업 명",
    "종 목",
    "구 분",
]
_PROFILE_SUBHEADER_KEYWORDS = [
    "지분율",
    "소유지분율",
    "연결회사지분율",
    "장부금액",
    "취득원가",
    "순자산",
]


def _findHeaderColumns(headers: list[str], subHeaders: list[str] | None = None) -> dict:
    """헤더(1~2행)에서 이름/지분율/장부금액/소재지 열 인덱스."""
    mapping: dict[str, int | None] = {
        "nameIdx": 0,
        "ownershipIdx": None,
        "bookValueIdx": None,
        "acquisitionIdx": None,
        "locationIdx": None,
        "activityIdx": None,
    }

    for j, h in enumerate(headers):
        hc = h.strip()
        if any(kw in hc for kw in ["지분율", "소유지분율"]):
            mapping["ownershipIdx"] = j
        elif any(kw in hc for kw in ["장부금액", "투자자산", "투자금액"]):
            mapping["bookValueIdx"] = j
        elif "취득원가" in hc:
            mapping["acquisitionIdx"] = j
        elif any(kw in hc for kw in ["소재지", "소재국가", "주사업장", "사업 소재지"]):
            mapping["locationIdx"] = j
        elif any(
            kw in hc
            for kw in [
                "주요 영업활동",
                "주요영업활동",
                "관계의 성격",
                "영업과 주요 활동",
            ]
        ):
            mapping["activityIdx"] = j

    if subHeaders:
        for j, h in enumerate(subHeaders):
            hc = h.strip()
            if any(kw in hc for kw in ["지분율", "소유지분율"]):
                if mapping["ownershipIdx"] is None:
                    offset = len(headers) - len(subHeaders)
                    mapping["ownershipIdx"] = j + offset
            elif "장부금액" in hc:
                if mapping["bookValueIdx"] is None:
                    offset = len(headers) - len(subHeaders)
                    mapping["bookValueIdx"] = j + offset
            elif "취득원가" in hc:
                if mapping["acquisitionIdx"] is None:
                    offset = len(headers) - len(subHeaders)
                    mapping["acquisitionIdx"] = j + offset

    return mapping


def _cleanName(text: str) -> str:
    """기업명에서 주석번호 제거."""
    name = re.sub(r"\(\*?\d+\)", "", text).strip()
    name = re.sub(r"\(주\d+[,\d]*\)", "", name).strip()
    return name


_CATEGORY_KEYWORDS = [("관계기업", "관계기업"), ("공동기업", "공동기업")]

_LOCATION_COUNTRIES = [
    "한국",
    "대한민국",
    "미국",
    "중국",
    "일본",
    "독일",
    "프랑스",
    "싱가포르",
    "영국",
    "인도",
    "베트남",
]

_PROFILE_DETAIL_KEYWORDS_EXT = _PROFILE_SUBHEADER_KEYWORDS + [
    "소재지",
    "소재국가",
    "관계의 성격",
    "주요영업활동",
    "주요 영업활동",
]


def _detectCategory(text: str, currentCategory: str | None) -> str | None:
    """관계기업/공동기업 키워드가 있으면 업데이트, 없으면 기존값 유지."""
    for kw, cat in _CATEGORY_KEYWORDS:
        if kw in text:
            return cat
    return currentCategory


def _isHeaderRow(cells: list[str], cellStr: str) -> bool:
    """헤더 행 판정: 3가지 패턴 (이름+세부 / 빈첫셀+세부2+ / 세부2+만)."""
    hasName = any(kw in cellStr for kw in _PROFILE_NAME_KEYWORDS)
    hasDetail = any(kw in cellStr for kw in _PROFILE_DETAIL_KEYWORDS_EXT + ["결산월"])
    firstEmpty = len(cells) >= 3 and not cells[0].strip()
    detailCount = sum(1 for kw in _PROFILE_DETAIL_KEYWORDS_EXT if kw in cellStr)
    uniqueNonEmpty = set(c.strip() for c in cells if c.strip())
    isRepeating = len(uniqueNonEmpty) * 2 < len([c for c in cells if c.strip()])
    if isRepeating:
        return False
    return (
        (hasName and hasDetail)
        or (firstEmpty and detailCount >= 2 and len(cells) <= 12)
        or (not hasName and detailCount >= 2 and 3 <= len(cells) <= 12)
    )


def _isGroupSeparator2Cell(cells: list[str], cellStr: str, rows: list[list[str]], i: int) -> bool:
    """'구 분 | 당기말' 같은 2셀 헤더 여부 — 다음 행이 실제 프로필 헤더이면 skip."""
    if len(cells) != 2 or not any(kw in cellStr for kw in ["구 분", "구분"]):
        return False
    if not any(kw in cellStr for kw in ["당기", "전기"]):
        return False
    if i + 1 >= len(rows):
        return False
    nextStr = " ".join(rows[i + 1])
    return any(kw in nextStr for kw in _PROFILE_SUBHEADER_KEYWORDS)


def _applyDirectMapping(profile: AffiliateProfile, cells: list[str], headers: list[str], mapping: dict) -> None:
    """헤더에 이름열 명시된 경우 — 컬럼 매핑으로 필드 추출."""
    offset = len(headers) - len(cells)

    def _adj(idx: int | None) -> int | None:
        if idx is None:
            return None
        adj = idx - offset
        return adj if 0 <= adj < len(cells) else None

    idx = _adj(mapping["ownershipIdx"])
    if idx is not None:
        val = cells[idx].strip().rstrip("%")
        amt = _parseAmount(val)
        if amt is not None and 0 < amt <= 100:
            profile.ownership = amt

    idx = _adj(mapping["bookValueIdx"])
    if idx is not None:
        profile.bookValue = _parseAmount(cells[idx])

    idx = _adj(mapping["acquisitionIdx"])
    if idx is not None:
        profile.acquisitionCost = _parseAmount(cells[idx])

    idx = _adj(mapping["locationIdx"])
    if idx is not None:
        profile.location = cells[idx].strip() or None

    idx = _adj(mapping["activityIdx"])
    if idx is not None:
        profile.activity = cells[idx].strip() or None


def _fallbackOwnership(profile: AffiliateProfile, cells: list[str]) -> None:
    """fallback 지분율 추출: % 또는 0<v<=100 소수."""
    if profile.ownership is not None:
        return
    for c in cells[1:]:
        cs = c.strip()
        if cs.endswith("%"):
            val = _parseAmount(cs.rstrip("%"))
            if val is not None and 0 < val <= 100:
                profile.ownership = val
                return
        elif "." in cs and cs.replace(".", "").replace(",", "").isdigit():
            val = _parseAmount(cs)
            if val is not None and 0 < val <= 100:
                profile.ownership = val
                return


def _fallbackBookValue(profile: AffiliateProfile, cells: list[str]) -> None:
    """fallback 장부금액: 마지막 숫자 셀."""
    if profile.bookValue is not None:
        return
    for j in range(len(cells) - 1, 0, -1):
        val = _parseAmount(cells[j])
        if val is not None:
            profile.bookValue = val
            return


def _fallbackLocation(profile: AffiliateProfile, cells: list[str]) -> None:
    """fallback 소재지: 국가명 키워드 포함 셀."""
    if profile.location is not None:
        return
    for c in cells[1:]:
        cs = c.strip()
        if cs and not _parseAmount(cs) and len(cs) <= 10:
            if any(kw in cs for kw in _LOCATION_COUNTRIES):
                profile.location = cs
                return


def _fallbackActivity(profile: AffiliateProfile, cells: list[str], headerHasName: bool) -> None:
    """fallback 영업활동: 기업명 다음 텍스트 셀 (헤더 없는 경우)."""
    if profile.activity is not None or headerHasName:
        return
    for c in cells[1:]:
        cs = c.strip()
        if cs and _parseAmount(cs) is None and not cs.endswith("%"):
            if len(cs) >= 2 and cs != profile.location:
                profile.activity = cs
                return


def _shouldSkipDataRow(firstCell: str) -> bool:
    """계·합계·소계 행 스킵 여부."""
    return firstCell in ("계", "합 계", "합계", "소 계", "소계")


def _shouldResetHeaders(firstCell: str) -> bool:
    """헤더 리셋 행: (*1/(주1 주석, 기간 구분."""
    if re.match(r"^\(\*?\d", firstCell) or re.match(r"^\(주\d", firstCell):
        return True
    return firstCell in ("당기", "전기", "당기말", "전기말")


def _parseProfileDataRow(
    cells: list[str],
    headers: list[str],
    subHeaders: list[str] | None,
    category: str | None,
) -> AffiliateProfile | None:
    """데이터 행에서 AffiliateProfile 생성. 무효 행이면 None."""
    firstCell = cells[0].strip()
    if _shouldSkipDataRow(firstCell) or not firstCell:
        return None

    if firstCell.startswith("전체 "):
        category = _detectCategory(firstCell, category)
        if len(cells) >= 3 and _isNameCell(cells[1].strip()):
            firstCell = cells[1].strip()
        else:
            return None

    if not _isNameCell(firstCell):
        return None

    mapping = _findHeaderColumns(headers, subHeaders)
    headerHasName = any(kw in headers[0].strip() for kw in _PROFILE_NAME_KEYWORDS) if headers[0].strip() else False

    profile = AffiliateProfile(name=_cleanName(firstCell), category=category)
    if headerHasName:
        _applyDirectMapping(profile, cells, headers, mapping)

    _fallbackOwnership(profile, cells)
    _fallbackBookValue(profile, cells)
    _fallbackLocation(profile, cells)
    _fallbackActivity(profile, cells, headerHasName)
    return profile


def extractProfiles(rows: list[list[str]]) -> list[AffiliateProfile]:
    """투자현황 추출 orchestrator — 2행 헤더 + 카테고리 + fallback 매핑 (Q3.1e).

    Args:
        rows: 인자.

    Raises:
        없음.

    Example:
        >>> extractProfiles(...)

    Returns:
        list[AffiliateProfile] — 결과.
    """
    results: list[AffiliateProfile] = []
    headers: list[str] | None = None
    subHeaders: list[str] | None = None
    headerIdx: int | None = None
    category: str | None = None

    for i, cells in enumerate(rows):
        cellStr = " ".join(cells)

        if len(cells) <= 2:
            category = _detectCategory(cellStr, category)

        if len(cells) > 30:
            continue

        # 헤더 감지
        if _isHeaderRow(cells, cellStr):
            headers = cells
            headerIdx = i
            subHeaders = None
            continue

        # 서브헤더
        if (
            headers
            and headerIdx is not None
            and i == headerIdx + 1
            and any(kw in cellStr for kw in _PROFILE_SUBHEADER_KEYWORDS)
        ):
            subHeaders = cells
            continue

        # 2셀 구분 헤더 skip
        if _isGroupSeparator2Cell(cells, cellStr, rows, i):
            continue

        if headers is None:
            continue

        # 짧은 셀 — 주석/카테고리 업데이트
        if len(cells) < 2:
            s = cells[0].strip() if cells else ""
            if s.startswith("(") and ("*" in s or "주" in s):
                headers = None
                subHeaders = None
            elif any(kw in s for kw in ("관계기업", "공동기업")):
                category = _detectCategory(s, category)
            continue

        firstCell = cells[0].strip()
        if _shouldResetHeaders(firstCell):
            headers = None
            subHeaders = None
            continue

        profile = _parseProfileDataRow(cells, headers, subHeaders, category)
        if profile is not None:
            results.append(profile)

    return results


# ── 변동내역 ──────────────────────────────────────────────────


from dartlab.providers.mappers.parserMapper import loadAffiliate

MOVEMENT_COL_MAP = loadAffiliate().get("movement", {})

_MOVEMENT_HEADER_KEYWORDS = ["기초", "기 초"]


def _normalizeColName(name: str) -> str:
    """열 이름 정규화: 주석번호·공백 제거."""
    s = re.sub(r"\(\*\d*\)", "", name)
    s = re.sub(r"\(주\d*\)", "", s)
    s = re.sub(r"[\s·ㆍ\u3000]", "", s)
    return s.strip()


def _mapMovementColumns(headers: list[str]) -> dict[int, str]:
    """헤더 열 → AffiliateMovement 필드 매핑."""
    colMap: dict[int, str] = {}
    for j, h in enumerate(headers):
        norm = _normalizeColName(h)
        if not norm:
            continue
        matched = False
        for kw, field in MOVEMENT_COL_MAP.items():
            kwNorm = re.sub(r"[\s·ㆍ\u3000]", "", kw)
            if norm == kwNorm:
                colMap[j] = field
                matched = True
                break
        if matched:
            continue
        for kw, field in MOVEMENT_COL_MAP.items():
            kwNorm = re.sub(r"[\s·ㆍ\u3000]", "", kw)
            if kwNorm in norm or norm in kwNorm:
                colMap[j] = field
                break
    return colMap


def _mergeSubHeader(headers: list[str], subHeaders: list[str]) -> list[str]:
    """메인헤더의 빈 셀에 서브헤더 값을 채워 병합."""
    merged = list(headers)
    emptyStart = None
    emptyEnd = None
    for j, h in enumerate(merged):
        if not h.strip():
            if emptyStart is None:
                emptyStart = j
            emptyEnd = j
        else:
            if emptyStart is not None:
                break
    if emptyStart is None:
        return merged

    nEmpty = emptyEnd - emptyStart + 1

    if nEmpty >= len(subHeaders):
        for k, sh in enumerate(subHeaders):
            merged[emptyStart + k] = sh.strip()
    elif nEmpty + 1 >= len(subHeaders):
        startIdx = emptyStart - 1
        for k, sh in enumerate(subHeaders):
            idx = startIdx + k
            if 0 <= idx < len(merged):
                merged[idx] = sh.strip()
    else:
        startIdx = max(0, emptyStart - 1)
        for k, sh in enumerate(subHeaders):
            idx = startIdx + k
            if idx < len(merged):
                merged[idx] = sh.strip()

    return merged


def extractMovements(rows: list[list[str]]) -> list[AffiliateMovement]:
    """변동내역 추출. 범용 헤더 매칭.

    Args:
        rows: 인자.

    Raises:
        없음.

    Example:
        >>> extractMovements(...)

    Returns:
        list[AffiliateMovement] — 결과.
    """
    results: list[AffiliateMovement] = []
    headers = None
    colMap: dict[int, str] | None = None
    inTable = False
    tableRows = 0
    headerIdx = None

    for i, cells in enumerate(rows):
        cellStr = " ".join(cells)

        hasOpening = any(kw in cellStr for kw in _MOVEMENT_HEADER_KEYWORDS)
        if hasOpening and 3 <= len(cells) <= 30:
            movKws = sum(1 for kw in MOVEMENT_COL_MAP if kw in cellStr)
            if movKws >= 2:
                headers = cells
                colMap = _mapMovementColumns(headers)
                inTable = True
                tableRows = 0
                headerIdx = i
                continue

        if not inTable and len(cells) == 3:
            c0, c1, c2 = cells[0].strip(), cells[1].strip(), cells[2].strip()
            if ("구 분" in c0 or "구분" in c0) and "당기" in c1 and "전기" in c2:
                headers = cells
                colMap = {1: "current", 2: "prior"}
                inTable = True
                tableRows = 0
                headerIdx = i
                continue

        if not inTable:
            continue

        if tableRows == 0 and headerIdx is not None and i == headerIdx + 1:
            subKws = sum(1 for kw in MOVEMENT_COL_MAP if kw in cellStr)
            if subKws >= 2 and len(cells) < len(headers):
                headers = _mergeSubHeader(headers, cells)
                colMap = _mapMovementColumns(headers)
                continue

        if len(cells) < 2:
            s = cells[0].strip() if cells else ""
            if s.startswith("(") and ("*" in s or "주" in s):
                inTable = False
                headers = None
            continue

        firstCell = cells[0].strip()
        if firstCell in ("계", "합 계", "합계", "소 계", "소계"):
            continue
        if not firstCell:
            continue
        if re.match(r"^\(\*?\d", firstCell) or re.match(r"^\(주\d", firstCell):
            inTable = False
            headers = None
            continue

        isCategory = firstCell in ("관계기업", "공동기업")
        if not _isNameCell(firstCell) and not isCategory:
            if tableRows == 0:
                subKws = sum(1 for kw in MOVEMENT_COL_MAP if kw in cellStr)
                if subKws >= 2:
                    if len(cells) < len(headers or []):
                        headers = _mergeSubHeader(headers, cells)
                        colMap = _mapMovementColumns(headers)
                    continue
            continue

        if firstCell in ("관계기업", "공동기업") and len(cells) > 2:
            firstCell = cells[1].strip() if len(cells) > 1 else firstCell
            if not _isNameCell(firstCell):
                continue

        name = _cleanName(firstCell)
        mv = AffiliateMovement(name=name)

        if colMap:
            if headers:
                firstH = _normalizeColName(headers[0])
                headerHasName = not any(
                    re.sub(r"[\s·ㆍ\u3000]", "", kw) in firstH or firstH in re.sub(r"[\s·ㆍ\u3000]", "", kw)
                    for kw in MOVEMENT_COL_MAP
                )
                if headerHasName:
                    offset = len(headers) - len(cells)
                else:
                    offset = -(len(cells) - len(headers))
            else:
                offset = 0

            for j, fieldName in colMap.items():
                dataIdx = j - offset
                if 0 <= dataIdx < len(cells):
                    val = _parseAmount(cells[dataIdx])
                    if fieldName in ("current", "prior"):
                        pass
                    else:
                        setattr(mv, fieldName, val)

        if mv.closing is None and "closing" not in (colMap or {}).values():
            for j in range(len(cells) - 1, 0, -1):
                val = _parseAmount(cells[j])
                if val is not None:
                    mv.closing = val
                    break

        tableRows += 1
        results.append(mv)

    return results


# ── 3열 변동표 (삼성전자 형태) ────────────────────────────────


def extractSimpleMovement(rows: list[list[str]]) -> list[dict]:
    """구 분|당기|전기 형태의 간단한 변동표.

    Args:
        rows: 인자.

    Raises:
        없음.

    Example:
        >>> extractSimpleMovement(...)

    Returns:
        list[dict] — 결과.
    """
    results: list[dict] = []
    inTable = False

    for cells in rows:
        if len(cells) != 3:
            if inTable and len(cells) < 3:
                inTable = False
            continue

        c0, c1, c2 = cells[0].strip(), cells[1].strip(), cells[2].strip()

        if ("구 분" in c0 or "구분" in c0) and ("당기" in c1 or "당분기" in c1):
            inTable = True
            continue

        if not inTable:
            continue

        if not c0 or c0.startswith("("):
            if c0.startswith("(") and ("*" in c0 or "주" in c0):
                inTable = False
            continue

        curAmt = _parseAmount(c1)
        prevAmt = _parseAmount(c2)

        if curAmt is not None or prevAmt is not None:
            results.append(
                {
                    "항목": c0,
                    "당기": curAmt,
                    "전기": prevAmt,
                }
            )

    return results


# ── 횡전개 재내보내기 (분리: parserTransposed.py) ──────────────────
from dartlab.providers.dart.docs.finance.affiliate.parserTransposed import (  # noqa: E402  re-export
    extractTransposedMovements,
    extractTransposedProfiles,
)
