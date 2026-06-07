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

# 옛 in-code 상수 — SSOT layers 에서 로드하되 module-level 단일 객체 identity 보존
# (facade `_EDGAR_LABELS`/`_KR_SYNONYMS` re-export 대상). reset() 이 in-place 갱신.
_EDGAR_LABELS: dict[str, str] = {}
_KR_SYNONYMS: dict[str, str] = {}


def _populate() -> None:
    layers = loadAccounts().get("layers", {})
    _EDGAR_LABELS.clear()
    _EDGAR_LABELS.update(layers.get("labelEn", {}))
    _KR_SYNONYMS.clear()
    _KR_SYNONYMS.update(layers.get("korSynonym", {}))


_populate()


def _edgarKorNames() -> dict[str, str]:
    """SSOT ``edgar.accounts`` 에서 snakeId → korName (US-GAAP 계정)."""
    return {a["snakeId"]: a["korName"] for a in loadAccounts().get("edgar", {}).get("accounts", []) if a.get("korName")}


@lru_cache(maxsize=1)
def koreanLabels() -> dict[str, str]:
    """snakeId → 한글 라벨 SSOT (6 단계 우선순위 cascade).

    1. standardAccounts.korName (정본 큐레이션)
    2. edgar.accounts korName (DART 에 없는 US-GAAP 계정 — 큐레이션)
    3. labelSupplements 보충 (큐레이션)
    4. mappings 역인덱스 — 가장 짧은 한국어명 (휴리스틱, degenerate 행만 채움)
    5. snakeAlias — degenerate 한 src 만 canonical 라벨로 통일(동의어) + canonical 역채움
    6. 선행 '*' 큐레이션 마커 제거 후 선행 번호 제거

    큐레이션 소스(1~3)를 휴리스틱(4)보다 먼저 둬 garbage(예: net_income→'중단영업')가
    정답(당기순이익)을 덮는 회귀를 차단한다. 5 의 동의어 통일은 4 이후에도 degenerate 한
    (라벨 없음 또는 라벨==snakeId) src 에만 적용 — 자기 고유명을 가진 lump(이자수익 등)는 보존.

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

    # 2. edgar.accounts korName (큐레이션) — degenerate 행만 채움
    for snakeId, korName in _edgarKorNames().items():
        if korName and result.get(snakeId) in (None, snakeId):
            result[snakeId] = korName

    # 3. labelSupplements (큐레이션) — degenerate 행만 채움
    for sid, name in loadSupplements().items():
        if result.get(sid) in (None, sid):
            result[sid] = name

    # 4. mappings 역인덱스 최단명 (휴리스틱) — 큐레이션 라벨은 보존하되 raw-snakeId placeholder 는 갱신
    if mappings:
        reverse: dict[str, list[str]] = {}
        for name, snakeId in mappings.items():
            if any("가" <= ch <= "힣" for ch in name):
                reverse.setdefault(snakeId, []).append(name)
        for snakeId, names in reverse.items():
            if snakeId in result and result[snakeId] != snakeId:
                continue
            candidate = min(names, key=len)
            if candidate in used:
                alt = sorted(names, key=len)
                chosen = next((n for n in alt if n not in used), snakeId)
                result[snakeId] = chosen
            else:
                result[snakeId] = candidate
            used.add(result[snakeId])

    # 5. snakeAlias — degenerate src 동의어 통일(canonical 라벨 상속) + canonical 역채움
    for src, tgt in SNAKEID_ALIASES.items():
        if tgt in result and result.get(src) in (None, src):
            result[src] = result[tgt]
    for src, tgt in SNAKEID_ALIASES.items():
        if src in result and result.get(tgt) in (None, tgt):
            result[tgt] = result[src]

    # 6. 선행 '*' 큐레이션 마커 제거 후 선행 번호 제거
    for sid in result:
        val = result[sid]
        if val and val.startswith("*"):
            val = val[1:]
        if val and val[0].isdigit():
            cleaned = _NUM_PREFIX.sub("", val)
            if cleaned:
                val = cleaned
        result[sid] = val

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
    return dict(_EDGAR_LABELS)


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
    for synonym, sid in _KR_SYNONYMS.items():
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
    """라벨 cascade lru_cache 리셋 — SSOT 편집 후.

    Args:
        없음.

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> from dartlab.core.accounts import labels
        >>> labels.reset()
    """
    _populate()  # 모듈 상수 in-place 갱신 (identity 보존, facade re-export stale 차단)
    koreanLabels.cache_clear()
    englishLabels.cache_clear()
    reverseKoreanLabels.cache_clear()
