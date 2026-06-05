"""EDGAR XBRL tag → DART canonical snakeId 매핑 (옛 ``EdgarMapper``).

SSOT ``edgar`` 소스 (accounts/learnedTags/stmtOverrides) 만 읽어 tagMap·stmtTagMap
을 파생. commonTags 가 learnedTags 를 덮어쓴다 (의미 우선). DART alias 변환은
``aliases.SNAKEID_ALIASES`` 단일 객체 사용.

매핑 우선순위:
1. stmtOverrides — 같은 태그가 stmt 따라 다른 snakeId (예: NetIncomeLoss → IS/CF 분리)
2. stmtTagMap — stmt 충돌 해소 (commonTags 기반)
3. tagMap — learnedTags + commonTags 병합본
"""

from __future__ import annotations

import threading
from typing import Optional

from dartlab.core.accounts.aliases import SNAKEID_ALIASES
from dartlab.core.accounts.data import loadAccounts

# DART 호환 alias (옛 EDGAR_TO_DART_ALIASES) — 동일 객체 identity 보존
EDGAR_TO_DART_ALIASES = SNAKEID_ALIASES


class EdgarTagMapper:
    """EDGAR XBRL 태그를 DART canonical snakeId 로 변환하는 매퍼."""

    _accounts: Optional[list[dict]] = None
    _tagMap: Optional[dict[str, str]] = None
    _stmtTagMap: Optional[dict[str, dict[str, str]]] = None
    _commonTags: Optional[set[str]] = None
    _stmtOverrides: Optional[dict[str, str]] = None
    _lock = threading.Lock()

    @classmethod
    def _ensureLoaded(cls) -> None:
        if cls._tagMap is not None:
            return
        with cls._lock:
            if cls._tagMap is not None:
                return
            cls._loadData()

    @classmethod
    def _loadData(cls) -> None:
        edgar = loadAccounts().get("edgar", {})
        cls._accounts = edgar.get("accounts", [])
        cls._stmtOverrides = edgar.get("stmtOverrides", {})

        stmtTagMap: dict[str, dict[str, str]] = {}
        commonTags: set[str] = set()
        commonTagMap: dict[str, str] = {}
        for acct in cls._accounts:
            sid = acct["snakeId"]
            stmt = acct["stmt"]
            for tag in acct.get("commonTags", []):
                tagLower = tag.lower()
                commonTagMap[tagLower] = sid
                commonTags.add(tagLower)
                stmtTagMap.setdefault(tagLower, {})[stmt] = sid
        cls._commonTags = commonTags
        cls._stmtTagMap = stmtTagMap

        tagMap: dict[str, str] = {}
        for tag, sid in edgar.get("learnedTags", {}).items():
            tagMap[tag.lower()] = sid
        for tag, sid in commonTagMap.items():
            tagMap[tag] = sid  # commonTags 우선
        cls._tagMap = tagMap

    @classmethod
    def release(cls) -> None:
        """class-level 캐시 리셋 — 다음 호출에서 SSOT 재로드.

        Args:
            없음.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.release()
        """
        cls._accounts = None
        cls._tagMap = None
        cls._stmtTagMap = None
        cls._commonTags = None
        cls._stmtOverrides = None

    @classmethod
    def isCommonTag(cls, tag: str) -> bool:
        """태그가 standardAccounts 의 commonTags 에 포함되는지.

        Args:
            tag: XBRL 태그.

        Returns:
            common 태그면 True.

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.isCommonTag("Assets")
            True
        """
        cls._ensureLoaded()
        return tag.lower() in cls._commonTags

    @classmethod
    def tagMap(cls) -> dict[str, str]:
        """전체 tag(lower) → snakeId 매핑 (learnedTags + commonTags 병합본) 사본.

        Args:
            없음.

        Returns:
            ``{tag_lower: snakeId}`` dict (commonTags 가 learnedTags 우선).

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.tagMap()["revenues"]
            'sales'
        """
        cls._ensureLoaded()
        return dict(cls._tagMap)

    @classmethod
    def map(cls, tag: str, stmtType: str = "") -> Optional[str]:
        """EDGAR 태그 → snakeId, stmt 충돌 시 override 적용.

        Args:
            tag: XBRL 태그.
            stmtType: 재무제표 유형 (BS/IS/CF/CI), 충돌 해소용.

        Returns:
            snakeId 또는 None.

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.map("Revenues", "IS")
            'sales'
        """
        cls._ensureLoaded()

        overrideKey = f"{tag}|{stmtType}"
        if overrideKey in cls._stmtOverrides:
            return cls._stmtOverrides[overrideKey]

        tagLower = tag.lower()
        if stmtType and tagLower in cls._stmtTagMap:
            stmtMap = cls._stmtTagMap[tagLower]
            if stmtType in stmtMap:
                return stmtMap[stmtType]

        return cls._tagMap.get(tagLower)

    @classmethod
    def mapToDart(cls, tag: str, stmtType: str = "") -> Optional[str]:
        """EDGAR 태그 → DART 호환 snakeId (alias 적용 포함).

        Args:
            tag: XBRL 태그.
            stmtType: 재무제표 유형.

        Returns:
            DART snakeId 또는 None.

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.mapToDart("CostOfGoodsSold", "IS")
            'cost_of_sales'
        """
        sid = cls.map(tag, stmtType)
        if sid is None:
            return None
        return SNAKEID_ALIASES.get(sid, sid)

    @classmethod
    def classifyTagsByStmt(cls) -> dict[str, set[str]]:
        """재무제표 유형 (IS/BS/CF/CI) 별 commonTags 분류.

        Args:
            없음.

        Returns:
            ``{"IS": {tags...}, ...}`` dict.

        Raises:
            없음.

        Example:
            >>> "IS" in EdgarTagMapper.classifyTagsByStmt()
            True
        """
        cls._ensureLoaded()
        stmtTags: dict[str, set[str]] = {"IS": set(), "BS": set(), "CF": set(), "CI": set()}
        for acct in cls._accounts:
            stmt = acct["stmt"]
            if stmt in stmtTags:
                for tag in acct.get("commonTags", []):
                    stmtTags[stmt].add(tag)
        return stmtTags

    @classmethod
    def getPrimaryStmtMap(cls) -> dict[str, str]:
        """commonTag → primary stmt (1:1). notes/equity 제외.

        Args:
            없음.

        Returns:
            ``{tag: stmt}`` dict.

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.getPrimaryStmtMap()["Revenues"]
            'IS'
        """
        cls._ensureLoaded()
        result: dict[str, str] = {}
        for acct in cls._accounts:
            stmt = acct["stmt"]
            if stmt in ("NT", "EQ"):
                continue
            for tag in acct.get("commonTags", []):
                if tag not in result:
                    result[tag] = stmt
        return result

    @classmethod
    def getLineOrder(cls) -> dict[str, int]:
        """snakeId → line 번호 (표준 순서). alias 변환 snakeId 포함.

        Args:
            없음.

        Returns:
            ``{snakeId: lineNumber}`` dict.

        Raises:
            없음.

        Example:
            >>> isinstance(EdgarTagMapper.getLineOrder(), dict)
            True
        """
        cls._ensureLoaded()
        result = {a["snakeId"]: a.get("line", 9999) for a in cls._accounts}
        for src, tgt in EDGAR_TO_DART_ALIASES.items():
            if src in result and tgt not in result:
                result[tgt] = result[src]
            if tgt in result and src not in result:
                result[src] = result[tgt]
        return result

    @classmethod
    def getAccountStmt(cls, snakeId: str) -> str | None:
        """snakeId 의 정식 재무제표 유형 (BS/IS/CF/CI/NT/EQ). alias 역참조 포함.

        Args:
            snakeId: dartlab 표준 snake_case 계정 ID.

        Returns:
            stmt 유형 또는 None.

        Raises:
            없음.

        Example:
            >>> EdgarTagMapper.getAccountStmt("revenue")
            'IS'
        """
        cls._ensureLoaded()
        for acct in cls._accounts:
            if acct["snakeId"] == snakeId:
                return acct.get("stmt")
        for src, tgt in EDGAR_TO_DART_ALIASES.items():
            if tgt == snakeId or src == snakeId:
                other = src if tgt == snakeId else tgt
                for acct in cls._accounts:
                    if acct["snakeId"] == other:
                        return acct.get("stmt")
        return None

    @classmethod
    def getTagsForSnakeIds(cls, snakeIds: list[str]) -> set[str]:
        """지정 snakeId 에 매핑된 모든 원본 태그 (alias 양방향 fixed-point 확장).

        Args:
            snakeIds: snake_case 계정 ID 리스트.

        Returns:
            매핑된 XBRL 태그 set.

        Raises:
            없음.

        Example:
            >>> isinstance(EdgarTagMapper.getTagsForSnakeIds(["revenue"]), set)
            True
        """
        cls._ensureLoaded()
        sidSet = set(snakeIds)
        while True:
            prevSize = len(sidSet)
            for aliasSid, primarySid in EDGAR_TO_DART_ALIASES.items():
                if aliasSid in sidSet:
                    sidSet.add(primarySid)
                if primarySid in sidSet:
                    sidSet.add(aliasSid)
            if len(sidSet) == prevSize:
                break
        tags: set[str] = set()
        for acct in cls._accounts:
            if acct["snakeId"] in sidSet:
                for tag in acct.get("commonTags", []):
                    tags.add(tag)
        return tags
