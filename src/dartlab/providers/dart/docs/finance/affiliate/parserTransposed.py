"""affiliate parser 횡전개 (기업명=열) 파서 — parser.py 분할 (규칙 3 LoC).

`parser.py` 1032 LoC 가 규칙 3 임계 (>800) 위반. 횡전개 (transposed: 기업명을 열로
배치) 파서 (~310 줄) 를 본 모듈로 분리. 호출자 호환 — parser.py 재내보내기.
"""

from __future__ import annotations

import re

from dartlab.providers.dart.docs.finance.affiliate.parser import (
    _isNameCell,
    _parseAmount,
)
from dartlab.providers.dart.docs.finance.affiliate.types import (
    AffiliateMovement,
    AffiliateProfile,
)
from dartlab.providers.mappers.parserMapper import loadAffiliate

# ── 횡전개(기업명=열) 파서 ────────────────────────────────────


_TRANSPOSED_PROFILE_MAP = loadAffiliate().get("profile", {})
_TRANSPOSED_MOVEMENT_MAP = loadAffiliate().get("transposedMovement", {})

_TRANSPOSED_NON_NAME_KEYWORDS = [
    "장부금액",
    "취득원가",
    "순자산",
    "순자산지분금액",
    "순자산(부채)",
    "내부거래",
    "보유주식수",
    "유동자산",
    "비유동자산",
    "자산",
    "부채",
    "자본",
    "매출액",
    "당기순이익",
    "당기순손실",
    "당기손익",
    "지분법적용",
    "지분법 적용",
    "투자지분",
    "주요 사업 소재지",
    "주요사업소재지",
    "주된 사업장",
    "주요 영업활동",
    "주요영업활동",
    "결산월",
    "지분율",
    "소유지분율",
    "관계의 성격",
    "기업의 영업",
    "의결권",
    "영향력",
    "종속기업 명칭",
    "담보",
    "보증",
]


def _isTransposedNameCell(text: str) -> bool:
    """횡전개용 기업명 판정. _isNameCell보다 엄격."""
    if not _isNameCell(text):
        return False
    s = text.strip()
    sClean = re.sub(r"\(\*?\d*\)", "", s).strip()
    for kw in _TRANSPOSED_NON_NAME_KEYWORDS:
        if kw in sClean:
            return False
    return True


def _findTransposedBlocks(rows: list[list[str]]) -> list[dict]:
    """횡전개 블록 탐색.

    블록: 기업명 행(첫 셀 비어있고 나머지에 기업명 다수) + 항목 행들.
    """
    blocks: list[dict] = []
    currentPeriod = None

    i = 0
    while i < len(rows):
        cells = rows[i]

        if len(cells) <= 2:
            c0 = cells[0].strip()
            if c0 == "당기":
                currentPeriod = "당기"
            elif c0 == "전기":
                currentPeriod = "전기"
            i += 1
            continue

        if len(cells) >= 8:
            first = cells[0].strip()
            isFirstEmpty = not first or first in (
                "전체 관계기업 투자금액",
                "전체 관계기업 및 공동기업",
                "관계기업",
                "공동기업",
                "전체 공동기업",
            )
            if isFirstEmpty:
                nameCount = sum(1 for c in cells[1:] if _isTransposedNameCell(c))
                if nameCount >= 3 and nameCount >= len(cells) * 0.3:
                    names: list[str | None] = []
                    for c in cells[1:]:
                        n = c.strip()
                        if _isTransposedNameCell(n):
                            n = re.sub(r"\(\*?\d+[,\d]*\)", "", n).strip()
                            n = re.sub(r"\(주\d+[,\d]*\)", "", n).strip()
                            names.append(n)
                        else:
                            names.append(None)

                    items: dict[str, list[str]] = {}
                    j = i + 1
                    while j < len(rows):
                        jcells = rows[j]
                        if len(jcells) < 3:
                            break
                        jfirst = jcells[0].strip()
                        jnameCount = sum(1 for c in jcells[1:] if _isTransposedNameCell(c))
                        if not jfirst and jnameCount >= 3:
                            break
                        if len(jcells) <= 2 and jcells[0].strip() in ("당기", "전기"):
                            break

                        itemName = jfirst
                        if not itemName:
                            j += 1
                            continue

                        vals = [jcells[k].strip() if k < len(jcells) else "" for k in range(1, len(jcells))]
                        items[itemName] = vals
                        j += 1

                    # 블록 타입 판별
                    hasOpening = False
                    hasClosing = False
                    movCount = 0
                    profCount = 0
                    for itemName in items:
                        normItem = re.sub(r"[\s·ㆍ\u3000]", "", itemName)
                        for mk, field in _TRANSPOSED_MOVEMENT_MAP.items():
                            mkNorm = re.sub(r"[\s·ㆍ\u3000]", "", mk)
                            if mkNorm in normItem or normItem in mkNorm:
                                movCount += 1
                                if field == "opening":
                                    hasOpening = True
                                elif field == "closing":
                                    hasClosing = True
                                break
                        for pk in _TRANSPOSED_PROFILE_MAP:
                            pkNorm = re.sub(r"[\s·ㆍ\u3000]", "", pk)
                            if pkNorm in normItem or normItem in pkNorm:
                                profCount += 1
                                break

                    if hasOpening and hasClosing and movCount >= 2:
                        blockType = "movement"
                    elif profCount >= 1:
                        blockType = "profile"
                    else:
                        blockType = None

                    if items and blockType:
                        blocks.append(
                            {
                                "period": currentPeriod or "당기",
                                "names": names,
                                "items": items,
                                "blockType": blockType,
                                "startRow": i,
                            }
                        )

                    i = j
                    continue

        i += 1

    return blocks


def extractTransposedProfiles(rows: list[list[str]]) -> list[AffiliateProfile]:
    """횡전개 포맷에서 투자현황 추출.

    Args:
        rows: 인자.

    Raises:
        없음.

    Example:
        >>> extractTransposedProfiles(...)

    Returns:
        list[AffiliateProfile] — 결과.
    """
    blocks = _findTransposedBlocks(rows)
    results: list[AffiliateProfile] = []
    seen: set[tuple[str, str]] = set()

    for block in blocks:
        if block["blockType"] != "profile":
            continue

        names = block["names"]
        items = block["items"]

        fieldMap: dict[str, str] = {}
        for itemName in items:
            normItem = re.sub(r"[\s·ㆍ\u3000]", "", itemName)
            for pk, field in _TRANSPOSED_PROFILE_MAP.items():
                pkNorm = re.sub(r"[\s·ㆍ\u3000]", "", pk)
                if pkNorm in normItem or normItem in pkNorm:
                    fieldMap[itemName] = field
                    break

        if not fieldMap:
            continue

        for idx, name in enumerate(names):
            if name is None:
                continue
            if (name, block["period"]) in seen:
                continue
            seen.add((name, block["period"]))

            profile = AffiliateProfile(name=name)

            for itemName, field in fieldMap.items():
                vals = items[itemName]
                if idx >= len(vals):
                    continue
                valStr = vals[idx].strip()
                if not valStr:
                    continue

                if field == "ownership":
                    v = valStr.rstrip("%")
                    amt = _parseAmount(v)
                    if amt is not None:
                        if 0 < amt < 1:
                            amt *= 100
                        if 0 < amt <= 100:
                            profile.ownership = amt
                elif field == "bookValue":
                    profile.bookValue = _parseAmount(valStr)
                elif field == "acquisitionCost":
                    profile.acquisitionCost = _parseAmount(valStr)
                elif field == "location":
                    profile.location = valStr or None
                elif field == "activity":
                    profile.activity = valStr or None

            results.append(profile)

    return results


def extractTransposedMovements(rows: list[list[str]]) -> list[AffiliateMovement]:
    """횡전개 포맷에서 변동내역 추출.

    Args:
        rows: 인자.

    Raises:
        없음.

    Example:
        >>> extractTransposedMovements(...)

    Returns:
        list[AffiliateMovement] — 결과.
    """
    blocks = _findTransposedBlocks(rows)
    results: list[AffiliateMovement] = []
    seen: set[tuple[str, str]] = set()

    for block in blocks:
        if block["blockType"] != "movement":
            continue

        names = block["names"]
        items = block["items"]

        fieldMap: dict[str, str] = {}
        for itemName in items:
            normItem = re.sub(r"[\s·ㆍ\u3000]", "", itemName)
            for mk, field in _TRANSPOSED_MOVEMENT_MAP.items():
                mkNorm = re.sub(r"[\s·ㆍ\u3000]", "", mk)
                if mkNorm in normItem or normItem in mkNorm:
                    fieldMap[itemName] = field
                    break

        if not fieldMap:
            continue

        for idx, name in enumerate(names):
            if name is None:
                continue
            key = (name, block["period"])
            if key in seen:
                continue
            seen.add(key)

            mv = AffiliateMovement(name=name)

            for itemName, field in fieldMap.items():
                vals = items[itemName]
                if idx >= len(vals):
                    continue
                valStr = vals[idx].strip()
                if not valStr:
                    continue

                val = _parseAmount(valStr)
                if val is not None:
                    setattr(mv, field, val)

            results.append(mv)

    return results
