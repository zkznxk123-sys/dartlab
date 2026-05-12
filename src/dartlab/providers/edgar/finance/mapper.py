"""EDGAR 태그 → DART canonical snakeId 매핑.

매핑 파이프라인:
1. STMT_OVERRIDES (stmt 기반 충돌 해결, 예: NetIncomeLoss → IS/CF 분리)
2. commonTags (standardAccounts.json, 344개 태그 → 179개 snakeId)
3. learnedSynonyms (tagMappings, 11,375개 태그)
4. EDGAR→DART alias 변환 (L0 SNAKEID_ALIASES 참조)

commonTags는 learnedSynonyms보다 우선한다.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from dartlab.core.utils.labels import SNAKEID_ALIASES

_DATA_DIR = Path(__file__).parent / "mapperData"

# L0 통합 dict를 그대로 사용 — 하위 호환
EDGAR_TO_DART_ALIASES = SNAKEID_ALIASES

STMT_OVERRIDES: dict[tuple[str, str], str] = {
    ("NetIncomeLoss", "IS"): "net_profit",
    ("NetIncomeLoss", "CF"): "net_income_cf",
    ("DepreciationDepletionAndAmortization", "IS"): "depreciation_amortization",
    ("DepreciationDepletionAndAmortization", "CF"): "depreciation_cf",
    ("IncomeTaxExpenseBenefit", "IS"): "income_tax_expense",
    ("IncomeTaxExpenseBenefit", "CF"): "income_tax_cf",
    ("ShareBasedCompensation", "IS"): "stock_compensation_expense",
    ("ShareBasedCompensation", "CF"): "stock_compensation_cf",
}


class EdgarMapper:
    """EDGAR XBRL 태그를 DART canonical snakeId로 변환하는 매퍼."""

    _tagMap: Optional[dict[str, str]] = None
    _stmtTagMap: Optional[dict[str, dict[str, str]]] = None
    _commonTags: Optional[set[str]] = None
    _accounts: Optional[list[dict]] = None
    _lock = threading.Lock()

    @classmethod
    def _ensureLoaded(cls):
        if cls._tagMap is not None:
            return
        with cls._lock:
            if cls._tagMap is not None:
                return
            cls._loadData()

    @classmethod
    def _loadData(cls):
        stdPath = _DATA_DIR / "standardAccounts.json"
        with open(stdPath, encoding="utf-8") as f:
            stdData = json.load(f)

        cls._accounts = stdData["accounts"]

        cls._stmtTagMap = {}
        cls._commonTags = set()
        commonTagMap: dict[str, str] = {}
        for acct in cls._accounts:
            sid = acct["snakeId"]
            stmt = acct["stmt"]
            for tag in acct.get("commonTags", []):
                tagLower = tag.lower()
                commonTagMap[tagLower] = sid
                cls._commonTags.add(tagLower)
                cls._stmtTagMap.setdefault(tagLower, {})[stmt] = sid

        learnedPath = _DATA_DIR / "learnedSynonyms.json"
        with open(learnedPath, encoding="utf-8") as f:
            learnedData = json.load(f)

        cls._tagMap = {}
        for tag, sid in learnedData.get("tagMappings", {}).items():
            cls._tagMap[tag.lower()] = sid

        for tag, sid in commonTagMap.items():
            cls._tagMap[tag] = sid

    @classmethod
    def isCommonTag(cls, tag: str) -> bool:
        """태그가 standardAccounts 의 commonTags 에 포함되는지 확인.

        Args:
            tag: XBRL 태그.

        Returns:
            ``True`` — common 태그.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.isCommonTag("Revenues")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cls._ensureLoaded()
        return tag.lower() in cls._commonTags

    @classmethod
    def map(cls, tag: str, stmtType: str = "") -> Optional[str]:
        """EDGAR 태그를 snakeId 로 매핑하고, stmt 충돌 시 오버라이드 적용.

        Args:
            tag: XBRL 태그.
            stmtType: 재무제표 유형 (BS/IS/CF/CI), 충돌 해소용.

        Returns:
            snakeId 또는 None.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.map("Revenues", "IS")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cls._ensureLoaded()

        overrideKey = (tag, stmtType)
        if overrideKey in STMT_OVERRIDES:
            return STMT_OVERRIDES[overrideKey]

        tagLower = tag.lower()

        if stmtType and tagLower in cls._stmtTagMap:
            stmtMap = cls._stmtTagMap[tagLower]
            if stmtType in stmtMap:
                return stmtMap[stmtType]

        return cls._tagMap.get(tagLower)

    @classmethod
    def mapToDart(cls, tag: str, stmtType: str = "") -> Optional[str]:
        """EDGAR 태그를 DART 호환 snakeId 로 변환 (alias 적용 포함).

        Args:
            tag: XBRL 태그.
            stmtType: 재무제표 유형.

        Returns:
            DART snakeId 또는 None.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.mapToDart("CostOfGoodsSold", "IS")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        sid = cls.map(tag, stmtType)
        if sid is None:
            return None
        return EDGAR_TO_DART_ALIASES.get(sid, sid)

    @classmethod
    def classifyTagsByStmt(cls) -> dict[str, set[str]]:
        """재무제표 유형 (IS/BS/CF/CI) 별로 commonTags 분류 반환.

        Returns:
            ``{"IS": {tags...}, ...}`` dict.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.classifyTagsByStmt()

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
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
        """commonTag → 해당 계정의 primary stmt (1:1). 충돌 태그는 계정의 stmt 우선.

        Returns:
            ``{tag: stmt}`` dict.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.getPrimaryStmtMap()["Revenues"]
            'IS'

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cls._ensureLoaded()
        result: dict[str, str] = {}
        for acct in cls._accounts:
            stmt = acct["stmt"]
            if stmt in ("NT", "EQ"):
                continue  # notes/equity는 IS/BS/CF에 넣지 않음
            for tag in acct.get("commonTags", []):
                if tag not in result:
                    result[tag] = stmt
        return result

    @classmethod
    def getLineOrder(cls) -> dict[str, int]:
        """snakeId → line 번호 (재무제표 표준 순서). SNAKEID_ALIASES 변환 후 snakeId 도 포함.

        Returns:
            ``{snakeId: lineNumber}`` dict.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.getLineOrder()["revenue"]

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cls._ensureLoaded()
        result = {a["snakeId"]: a.get("line", 9999) for a in cls._accounts}
        # SNAKEID_ALIASES로 변환된 snakeId에도 원본 line 적용
        for src, tgt in EDGAR_TO_DART_ALIASES.items():
            if src in result and tgt not in result:
                result[tgt] = result[src]
            if tgt in result and src not in result:
                result[src] = result[tgt]
        return result

    @classmethod
    def getAccountStmt(cls, snakeId: str) -> str | None:
        """snakeId 의 정식 재무제표 유형 (BS/IS/CF/CI/NT/EQ). SNAKEID_ALIASES 역참조 포함.

        Args:
            snakeId: dartlab 표준 snake_case 계정 ID.

        Returns:
            stmt 유형 ``"BS"``/``"IS"``/``"CF"``/``"CI"``/``"NT"``/``"EQ"`` 또는 None.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.getAccountStmt("revenue")
            'IS'

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cls._ensureLoaded()
        for acct in cls._accounts:
            if acct["snakeId"] == snakeId:
                return acct.get("stmt")
        # alias 원본에서 찾기
        for src, tgt in EDGAR_TO_DART_ALIASES.items():
            if tgt == snakeId or src == snakeId:
                other = src if tgt == snakeId else tgt
                for acct in cls._accounts:
                    if acct["snakeId"] == other:
                        return acct.get("stmt")
        return None

    @classmethod
    def getTagsForSnakeIds(cls, snakeIds: list[str]) -> set[str]:
        """지정한 snakeId 에 매핑된 모든 원본 태그를 반환.

        SNAKEID_ALIASES 양방향 확장:
        - 입력 snakeId 가 alias 의 key → value(primary) 도 검색
        - 입력 snakeId 가 alias 의 value → key(alias) 도 검색
        이렇게 하면 DART 식 이름("cost_of_goods_sold") 을 넣어도
        EDGAR primary ("cost_of_sales") 의 commonTags 를 수집한다.

        Args:
            snakeIds: snake_case 계정 ID 리스트.

        Returns:
            매핑된 XBRL 태그 set.

        Raises:
            없음.

        Example:
            >>> EdgarMapper.getTagsForSnakeIds(["revenue", "operating_income"])

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - threading

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cls._ensureLoaded()
        sidSet = set(snakeIds)
        # fixed-point 확장 — A→B→C 같은 2-hop alias 체인도 해결.
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
