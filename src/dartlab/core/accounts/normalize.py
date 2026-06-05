"""DART account → snakeId 정규화 — 12 단계 fallback (옛 ``AccountMapper.map``).

SSOT ``layers.idSynonym``/``layers.nameSynonym`` + ``mappings`` 만 읽어 정규화.
단계 순서(early-return 단락)가 결과를 좌우하므로 보존이 핵심:

1. account_id prefix 제거 → normalizedId
2. 사전 직접 hit — accountNm / normalizedId (synonym 우회 X · 의미 보존 우선)
3. nameSynonym 정규화 후 재조회
4. idSynonym 정규화 후 재조회
5. 입력 공백 제거 후 사전 조회
6. 사전 공백 변형 역인덱스 (사전 키 공백/tab/ZWSP 흡수)
7. 입력 괄호+공백 제거 후 사전 조회
8. 사전 괄호 변형 역인덱스 (``'X(Y)'`` ↔ 입력 ``'X'``)
9. 입력 하이픈 제거 후 사전 조회
10. 사전 하이픈 변형 역인덱스
11. 입력 짧은 한국어 suffix 흡수 — '액'/'등'/'외' 1글자
12. 미매핑 → None

(2) 사전 직접 hit 우선 — 사전 ``'현금배당' → cash_dividends_paid`` 가 있을 때
nameSynonym ``'현금배당' → '배당금'`` 우회가 ``mappings['배당금'] = dividends`` 로
정보 손실하는 것을 차단.
"""

from __future__ import annotations

import re
from typing import Optional

from dartlab.core.accounts.data import loadAccounts

_PREFIX_RE = re.compile(r"^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)")
_PAREN_RE = re.compile(r"\([^)]*\)")

# 한국어 짧은 명사 suffix — 의미 손실 없는 fold 대상 (길이 1 만)
_KOR_TRIM_SUFFIXES = ("액", "등", "외")


def stripPrefix(accountId: str) -> str:
    """IFRS/dart prefix 제거 (``ifrs-full_Revenue`` → ``Revenue``).

    Args:
        accountId: XBRL account_id (prefix 포함 가능).

    Returns:
        prefix(ifrs-full_/ifrs_/dart_/ifrs-smes_) 제거된 id.

    Raises:
        없음 — 순수 문자열 변환.

    Example:
        >>> stripPrefix("ifrs-full_Revenue")
        'Revenue'
    """
    return _PREFIX_RE.sub("", accountId)


# 옛 in-code 동의어 dict — SSOT layers 에서 로드하되 *module-level 단일 객체* 의
# identity 를 보존 (facade·scanAccount 가 by-reference import). ``reset()`` 은
# rebind 가 아닌 in-place clear+update 로 release 후에도 같은 객체에 최신 내용 반영
# (aliases.SNAKEID_ALIASES 와 동일 패턴 — release 후 stale 차단).
ID_SYNONYMS: dict[str, str] = {}
ACCOUNT_NAME_SYNONYMS: dict[str, str] = {}


def _populate() -> None:
    layers = loadAccounts().get("layers", {})
    ID_SYNONYMS.clear()
    ID_SYNONYMS.update(layers.get("idSynonym", {}))
    ACCOUNT_NAME_SYNONYMS.clear()
    ACCOUNT_NAME_SYNONYMS.update(layers.get("nameSynonym", {}))


_populate()


class AccountNormalizer:
    """DART account_id + account_nm → snakeId 정규화기 (12 단계 fallback).

    SSOT 단일 소유 — 흩어진 ``ID_SYNONYMS``/``ACCOUNT_NAME_SYNONYMS`` in-code dict 를
    ``layers`` 로 흡수. process 당 1 인스턴스 (class-level 캐시).
    """

    _instance: Optional[AccountNormalizer] = None
    _mappings: Optional[dict[str, str]] = None
    _noHyphenIndex: Optional[dict[str, str]] = None
    _noSpaceIndex: Optional[dict[str, str]] = None
    _noParenIndex: Optional[dict[str, str]] = None

    @classmethod
    def get(cls) -> AccountNormalizer:
        """싱글턴 인스턴스 반환.

        Args:
            없음.

        Returns:
            동일 process 안 항상 같은 ``AccountNormalizer``.

        Raises:
            없음.

        Example:
            >>> AccountNormalizer.get().normalize("ifrs-full_Revenue", "매출액")
            'sales'
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def release(cls) -> None:
        """class-level 캐시 리셋 — 다음 ``get()`` 에서 SSOT 재로드.

        Args:
            없음.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> AccountNormalizer.release()
        """
        cls._instance = None
        cls._mappings = None
        cls._noHyphenIndex = None
        cls._noSpaceIndex = None
        cls._noParenIndex = None
        _populate()  # 모듈 synonym dict in-place 갱신 (identity 보존, stale 차단)

    def __init__(self) -> None:
        if AccountNormalizer._mappings is None:
            AccountNormalizer._mappings = loadAccounts().get("mappings", {})

    def _getNoHyphenIndex(self) -> dict[str, str]:
        if AccountNormalizer._noHyphenIndex is None:
            idx: dict[str, str] = {}
            for key, snakeId in self._mappings.items():
                stripped = key.replace("-", "").replace("–", "").replace("—", "")
                if stripped != key and stripped not in self._mappings:
                    idx[stripped] = snakeId
            AccountNormalizer._noHyphenIndex = idx
        return AccountNormalizer._noHyphenIndex

    def _getNoSpaceIndex(self) -> dict[str, str]:
        if AccountNormalizer._noSpaceIndex is None:
            idx: dict[str, str] = {}
            for key, snakeId in self._mappings.items():
                stripped = key.replace(" ", "").replace("\t", "").replace("​", "")
                if stripped != key and stripped not in self._mappings:
                    idx[stripped] = snakeId
            AccountNormalizer._noSpaceIndex = idx
        return AccountNormalizer._noSpaceIndex

    def _getNoParenIndex(self) -> dict[str, str]:
        if AccountNormalizer._noParenIndex is None:
            idx: dict[str, str] = {}
            for key, snakeId in self._mappings.items():
                noSpace = key.replace(" ", "")
                stripped = _PAREN_RE.sub("", noSpace)
                if stripped != noSpace and stripped and stripped not in self._mappings:
                    idx[stripped] = snakeId
            AccountNormalizer._noParenIndex = idx
        return AccountNormalizer._noParenIndex

    def normalize(self, accountId: str, accountNm: str) -> Optional[str]:
        """``account_id`` + ``account_nm`` → snakeId (12 단계 fallback).

        Args:
            accountId: XBRL account_id (prefix 포함 raw, 예 ``"ifrs-full_Revenue"``).
            accountNm: 한글 account_nm (예 ``"매출액"`` / ``"매출액(연결)"``).

        Returns:
            snakeId (예 ``"sales"``) 또는 None (12 단계 모두 미매핑).

        Raises:
            없음 — 미매핑은 None.

        Example:
            >>> AccountNormalizer.get().normalize("ifrs-full_Revenue", "매출액")
            'sales'
        """
        m = self._mappings
        stripped = _PREFIX_RE.sub("", accountId) if accountId else ""
        normalizedId = ID_SYNONYMS.get(stripped, stripped)

        # 1. 사전 직접 hit (synonym 정규화 전) — 의미 보존 우선
        if accountNm and accountNm in m:
            return m[accountNm]
        if stripped and stripped in m:
            return m[stripped]

        # 2. nameSynonym 정규화 후 재조회 — 사전에 없는 변형 흡수
        normalizedNm = ACCOUNT_NAME_SYNONYMS.get(accountNm, accountNm) if accountNm else ""
        if normalizedNm and normalizedNm in m:
            return m[normalizedNm]
        if normalizedId and normalizedId in m:
            return m[normalizedId]

        if normalizedNm:
            noSpace = normalizedNm.replace(" ", "")
            if noSpace != normalizedNm and noSpace in m:
                return m[noSpace]
            nsIdx = self._getNoSpaceIndex()
            if noSpace in nsIdx:
                return nsIdx[noSpace]

            noParen = _PAREN_RE.sub("", noSpace)
            if noParen != noSpace and noParen in m:
                return m[noParen]
            npIdx = self._getNoParenIndex()
            if noParen in npIdx:
                return npIdx[noParen]
            if noSpace != noParen and noSpace in npIdx:
                return npIdx[noSpace]

            noHyphen = noSpace.replace("-", "").replace("–", "").replace("—", "")
            if noHyphen in m:
                return m[noHyphen]
            nhIdx = self._getNoHyphenIndex()
            if noHyphen in nhIdx:
                return nhIdx[noHyphen]

            for sfx in _KOR_TRIM_SUFFIXES:
                if not noSpace.endswith(sfx):
                    continue
                trimmed = noSpace[: -len(sfx)]
                if not trimmed:
                    continue
                if trimmed in m:
                    return m[trimmed]
                if trimmed in nsIdx:
                    return nsIdx[trimmed]
                if trimmed in npIdx:
                    return npIdx[trimmed]
                if trimmed in nhIdx:
                    return nhIdx[trimmed]

        return None
