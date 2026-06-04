"""snakeId → 사람이 읽는 라벨 (옛 ``labels.getKoreanLabels`` 등 6 단계 cascade).

SSOT 단일 소유 — standardAccounts.korName + mappings 역인덱스 + edgar.accounts
korName (이제 SSOT ``edgar`` 에서, providers/edgar 파일 직접 read 소멸) + supplements
+ snakeAlias 전파. 우선순위 순서가 결과를 좌우하므로 보존.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from dartlab.core.accounts.aliases import SNAKEID_ALIASES
from dartlab.core.accounts.data import loadAccounts, loadSupplements

_NUM_PREFIX = re.compile(r"^\d+[.\s·]+")


def _edgarKorNames() -> dict[str, str]:
    """SSOT ``edgar.accounts`` 에서 snakeId → korName (US-GAAP 계정)."""
    return {a["snakeId"]: a["korName"] for a in loadAccounts().get("edgar", {}).get("accounts", []) if a.get("korName")}


@lru_cache(maxsize=1)
def koreanLabels() -> dict[str, str]:
    """snakeId → 한글 라벨 SSOT (6 단계 우선순위 cascade).

    1. standardAccounts.korName (정본)
    2. mappings 역인덱스 — 가장 짧은 한국어명 (충돌 시 alt)
    3. edgar.accounts korName (DART 에 없는 US-GAAP 계정)
    4. labelSupplements 보충
    5. snakeAlias 양방향 전파
    6. 선행 번호 제거

    Args:
        없음.

    Returns:
        ``{snakeId: 한글 라벨}`` dict.

    Raises:
        없음.

    Example:
        >>> koreanLabels()["sales"]
        '매출액'
    """
    data = loadAccounts()
    stdAccounts: dict[str, dict] = data.get("standardAccounts", {})
    mappings: dict[str, str] = data.get("mappings", {})

    result: dict[str, str] = {}
    used: set[str] = set()

    for snakeId, meta in stdAccounts.items():
        korName = meta.get("korName")
        if korName:
            result[snakeId] = korName
            used.add(korName)

    if mappings:
        reverse: dict[str, list[str]] = {}
        for name, snakeId in mappings.items():
            if any("가" <= ch <= "힣" for ch in name):
                reverse.setdefault(snakeId, []).append(name)
        for snakeId, names in reverse.items():
            if snakeId in result:
                continue
            candidate = min(names, key=len)
            if candidate in used:
                alt = sorted(names, key=len)
                chosen = next((n for n in alt if n not in used), snakeId)
                result[snakeId] = chosen
            else:
                result[snakeId] = candidate
            used.add(result[snakeId])

    for snakeId, korName in _edgarKorNames().items():
        if not korName:
            continue
        current = result.get(snakeId)
        if current is None or current == snakeId:
            result[snakeId] = korName

    for sid, name in loadSupplements().items():
        if sid not in result:
            result[sid] = name

    for src, tgt in SNAKEID_ALIASES.items():
        if tgt not in result and src in result:
            result[tgt] = result[src]
        if src not in result and tgt in result:
            result[src] = result[tgt]

    for sid in result:
        val = result[sid]
        if val and val[0].isdigit():
            cleaned = _NUM_PREFIX.sub("", val)
            if cleaned:
                result[sid] = cleaned

    return result


@lru_cache(maxsize=1)
def englishLabels() -> dict[str, str]:
    """snakeId → 영문 readable 라벨 (SSOT ``layers.labelEn``).

    Args:
        없음.

    Returns:
        ``{snakeId: 영문 라벨}`` dict.

    Raises:
        없음.

    Example:
        >>> englishLabels()["sales"]
        'Revenue'
    """
    return dict(loadAccounts().get("layers", {}).get("labelEn", {}))


def _snakeToTitle(snakeId: str) -> str:
    """snake_case → Title Case. 영문 fallback."""
    return snakeId.replace("_", " ").strip().title()


@lru_cache(maxsize=1)
def reverseKoreanLabels() -> dict[str, str]:
    """한글 라벨 → snakeId 역조회 (정규화 키 + korSynonym 줄임말 포함).

    Args:
        없음.

    Returns:
        ``{한글 라벨/정규화 키/줄임말: snakeId}`` dict.

    Raises:
        없음.

    Example:
        >>> reverseKoreanLabels()["매출액"]
        'sales'
    """
    forward = koreanLabels()
    reverse: dict[str, str] = {}
    for sid, kr in forward.items():
        if kr not in reverse:
            reverse[kr] = sid
        nk = unicodedata.normalize("NFKC", kr)
        nk = re.sub(r"\s+", "", nk).lower()
        if nk not in reverse:
            reverse[nk] = sid
    korSynonym = loadAccounts().get("layers", {}).get("korSynonym", {})
    for synonym, sid in korSynonym.items():
        if synonym not in reverse:
            reverse[synonym] = sid
    return reverse


def accountLabels(locale: str = "kr") -> dict[str, str]:
    """snakeId → 라벨 (locale 별).

    Args:
        locale: ``"kr"`` 한글, 그 외 영문.

    Returns:
        ``{snakeId: label}`` dict.

    Raises:
        없음.

    Example:
        >>> accountLabels("kr")["sales"]
        '매출액'
    """
    if locale == "kr":
        return koreanLabels()
    return englishLabels()


def resolveLabel(snakeId: str, market: str = "KR") -> str:
    """단일 snakeId → 라벨. 실패 시 snake_to_title fallback.

    Args:
        snakeId: 표준 snake_case 계정 ID.
        market: ``"KR"`` 한글, 그 외 영문.

    Returns:
        라벨 문자열.

    Raises:
        없음.

    Example:
        >>> resolveLabel("sales")
        '매출액'
    """
    labels = accountLabels("kr" if market == "KR" else "en")
    label = labels.get(snakeId)
    if label:
        return label
    if market != "KR":
        return _snakeToTitle(snakeId)
    return snakeId


def reset() -> None:
    """라벨 cascade lru_cache 리셋 — SSOT 편집 후."""
    koreanLabels.cache_clear()
    englishLabels.cache_clear()
    reverseKoreanLabels.cache_clear()
