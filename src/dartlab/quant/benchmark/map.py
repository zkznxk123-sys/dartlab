"""KRX 벤치마크 매핑 SSOT — taxonomy 산업을 검증 가능한 지수명으로 연결."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

INDEX_ALIASES: dict[str, tuple[str, str]] = {
    "KOSPI": ("KOSPI", "코스피"),
    "코스피": ("KOSPI", "코스피"),
    "KOSPI200": ("KOSPI", "코스피 200"),
    "KPI200": ("KOSPI", "코스피 200"),
    "코스피200": ("KOSPI", "코스피 200"),
    "코스피 200": ("KOSPI", "코스피 200"),
    "KOSDAQ": ("KOSDAQ", "코스닥"),
    "코스닥": ("KOSDAQ", "코스닥"),
    "KOSDAQ150": ("KOSDAQ", "코스닥 150"),
    "코스닥150": ("KOSDAQ", "코스닥 150"),
    "코스닥 150": ("KOSDAQ", "코스닥 150"),
    "KRX300": ("KRX", "KRX 300"),
    "KRX 300": ("KRX", "KRX 300"),
}


SECTOR_INDEX_MAP: dict[str, tuple[tuple[str, str, float], ...]] = {
    "semiconductor": (("KRX", "KRX 반도체", 0.92), ("KRX", "KRX 정보기술", 0.82), ("KOSPI", "전기전자", 0.74)),
    "electronics": (("KRX", "KRX 정보기술", 0.86), ("KOSPI", "전기전자", 0.78), ("KOSDAQ", "전기전자", 0.72)),
    "telecom": (("KRX", "KRX 방송통신", 0.82), ("KOSPI", "통신", 0.76), ("KOSDAQ", "통신", 0.72)),
    "software": (("KRX", "KRX 정보기술", 0.82), ("KOSPI", "IT 서비스", 0.76), ("KOSDAQ", "IT 서비스", 0.76)),
    "pharma": (("KRX", "KRX 헬스케어", 0.88), ("KOSPI", "제약", 0.78), ("KOSDAQ", "제약", 0.78)),
    "medicalDevice": (
        ("KRX", "KRX 헬스케어", 0.82),
        ("KOSPI", "의료·정밀기기", 0.78),
        ("KOSDAQ", "의료·정밀기기", 0.78),
    ),
    "auto": (("KRX", "KRX 자동차", 0.9), ("KOSPI", "운송장비·부품", 0.74), ("KOSDAQ", "운송장비·부품", 0.72)),
    "battery": (("KRX", "KRX 에너지화학", 0.8), ("KOSPI", "화학", 0.72), ("KOSDAQ", "화학", 0.72)),
    "chemical": (("KRX", "KRX 에너지화학", 0.78), ("KOSPI", "화학", 0.74), ("KOSDAQ", "화학", 0.74)),
    "steel": (("KRX", "KRX 철강", 0.88), ("KOSPI", "금속", 0.76), ("KOSDAQ", "금속", 0.72)),
    "machinery": (("KRX", "KRX 기계장비", 0.82), ("KOSPI", "기계·장비", 0.78), ("KOSDAQ", "기계·장비", 0.78)),
    "electrical": (("KRX", "KRX 정보기술", 0.74), ("KOSPI", "전기전자", 0.76), ("KOSDAQ", "전기전자", 0.72)),
    "shipbuilding": (("KOSPI", "운송장비·부품", 0.72), ("KOSDAQ", "운송장비·부품", 0.68), ("KRX", "KRX 운송", 0.64)),
    "aerospace": (("KRX", "KRX 기계장비", 0.7), ("KOSPI", "기계·장비", 0.68), ("KOSDAQ", "기계·장비", 0.68)),
    "construction": (("KRX", "KRX 건설", 0.86), ("KOSPI", "건설", 0.78), ("KOSDAQ", "건설", 0.72)),
    "food": (("KRX", "KRX 필수소비재", 0.78), ("KOSPI", "음식료·담배", 0.76), ("KOSDAQ", "음식료·담배", 0.72)),
    "textile": (("KOSPI", "섬유·의류", 0.76), ("KOSDAQ", "섬유·의류", 0.72), ("KRX", "KRX 경기소비재", 0.66)),
    "plastic": (("KOSPI", "화학", 0.7), ("KOSDAQ", "화학", 0.7), ("KRX", "KRX 에너지화학", 0.66)),
    "buildingMaterials": (("KOSPI", "비금속", 0.74), ("KOSDAQ", "비금속", 0.72), ("KRX", "KRX 건설", 0.66)),
    "paper": (("KOSPI", "종이·목재", 0.76), ("KOSDAQ", "종이·목재", 0.72)),
    "finance": (("KOSPI", "금융", 0.78), ("KOSDAQ", "금융", 0.72), ("KRX", "KRX 300 금융", 0.7)),
    "media": (("KRX", "KRX K콘텐츠", 0.76), ("KOSPI", "오락·문화", 0.72), ("KOSDAQ", "오락·문화", 0.72)),
    "retail": (("KOSPI", "유통", 0.76), ("KOSDAQ", "유통", 0.72), ("KRX", "KRX 필수소비재", 0.66)),
    "logistics": (("KRX", "KRX 운송", 0.78), ("KOSPI", "운송·창고", 0.76), ("KOSDAQ", "운송·창고", 0.72)),
    "energy": (("KRX", "KRX 유틸리티", 0.78), ("KOSPI", "전기·가스", 0.76), ("KRX", "KRX 에너지화학", 0.7)),
    "realestate": (("KOSPI", "부동산", 0.76), ("KRX", "KRX 건설", 0.64)),
    "education": (("KOSPI", "일반서비스", 0.68), ("KOSDAQ", "일반서비스", 0.68)),
    "leisure": (("KOSPI", "오락·문화", 0.72), ("KOSDAQ", "오락·문화", 0.72), ("KRX", "KRX 경기소비재", 0.66)),
    "environment": (("KOSPI", "일반서비스", 0.64), ("KOSDAQ", "일반서비스", 0.64)),
    "consulting": (("KOSPI", "일반서비스", 0.64), ("KOSDAQ", "일반서비스", 0.64)),
    "agriculture": (("KOSPI", "음식료·담배", 0.68), ("KOSDAQ", "음식료·담배", 0.68)),
    "railroad": (("KRX", "KRX 운송", 0.72), ("KOSPI", "운송·창고", 0.68)),
    "cosmetics": (("KRX", "KRX 필수소비재", 0.7), ("KOSPI", "화학", 0.66), ("KOSDAQ", "화학", 0.66)),
}


@lru_cache(maxsize=1)
def availableIndexNames() -> set[tuple[str, str]]:
    """로컬 KRX 지수 데이터에 실제 존재하는 ``(시장군, 지수명)`` 집합.

    Capabilities:
        - data/krx/indices/raw-*.parquet 최신 2 파일에서 (MARKET_GROUP, IDX_NM) unique 집합
        - lru_cache 로 세션 내 단 1 회 IO

    Returns:
        set[tuple[str, str]] — (indexMarket, indexName) 쌍.

    Guide:
        벤치 indexExists 검증의 데이터 소스. 빈 집합 = krx 데이터 없음 (test/dev 환경).

    When:
        Sector 후보 검증 + AI 사용 가능 벤치 답변.

    How:
        ``_getDataRoot`` → krx/indices/raw-*.parquet → ``MARKET_GROUP/IDX_NM`` unique.

    Requires:
        ``data/krx/indices/`` raw parquet ≥ 1.

    Raises:
        없음 — 파일 없음 시 빈 집합.

    Example:
        >>> ("KOSPI", "코스피 200") in availableIndexNames()
        True

    SeeAlso:
        - indexExists : 존재 검증
        - sectorCandidates : 후보 변환

    AIContext:
        "이 지수 데이터 있는가" 답변 시 집합 lookup.
    """
    import polars as pl

    from dartlab.core.dataLoader import _getDataRoot

    root = Path(_getDataRoot()) / "krx" / "indices"
    files = sorted(root.glob("raw-*.parquet"), reverse=True)
    names: set[tuple[str, str]] = set()
    for path in files[:2]:
        df = pl.read_parquet(path, columns=["MARKET_GROUP", "IDX_NM"])
        names.update((str(m), str(n)) for m, n in df.unique().iter_rows())
    return names


def indexExists(indexMarket: str, indexName: str) -> bool:
    """KRX 지수 데이터에 지수명이 존재하는지 확인한다.

    Capabilities:
        - ``availableIndexNames`` 캐시 lookup → 존재 boolean
        - 빈 캐시 (데이터 없음) 시 True 반환 (개발 환경 fallback)

    Args:
        indexMarket: ``"KOSPI" | "KOSDAQ" | "KRX"``.
        indexName: 지수명.

    Returns:
        bool — 존재 여부.

    Guide:
        sector/style 후보 생성 후 가용성 검증. False 면 fallback 필요.

    When:
        벤치 후보 검증 + AI 데이터 없음 안내.

    How:
        ``availableIndexNames`` cache → tuple in set 비교.

    Requires:
        없음 (캐시 자동 채움).

    Raises:
        없음.

    Example:
        >>> indexExists("KOSPI", "코스피 200")
        True

    SeeAlso:
        - availableIndexNames : 캐시
        - sectorCandidates : 후보 생성

    AIContext:
        "이 지수 데이터 가용" 답변 시 boolean 인용.
    """
    names = availableIndexNames()
    if not names:
        return True
    return (indexMarket, indexName) in names


def sectorCandidates(industryId: str | None, preferredMarket: str | None = None) -> list[dict[str, Any]]:
    """taxonomy industry ID를 KRX 섹터 벤치마크 후보로 변환한다.

    Capabilities:
        - SECTOR_INDEX_MAP 룩업 → 산업 ID → KRX 섹터 지수 후보 list
        - preferredMarket 우선순위 정렬 (해당 시장 후보 앞으로)

    Args:
        industryId: industry node taxonomy id.
        preferredMarket: 우선 시장 (``"KOSPI"`` | ``"KOSDAQ"``).

    Returns:
        list[dict] — benchmarkType/source/indexMarket/indexName/confidence/industry.

    Guide:
        벤치 stack 의 sector 차원 입력. industryId None 시 빈 list.

    When:
        Sector benchmark 선택 + AI 섹터 벤치 추천.

    How:
        SECTOR_INDEX_MAP[industryId] → row 정렬 → dict 변환.

    Requires:
        industryId 매핑 등록.

    Raises:
        없음 — 미등록 ID 시 빈 list.

    Example:
        >>> sectorCandidates("semiconductor")[0]["indexName"]
        'KRX 반도체'

    SeeAlso:
        - resolveBenchmarkStack : sector 후보 소비
        - SECTOR_INDEX_MAP : 매핑 SSOT

    AIContext:
        "이 산업의 벤치 후보" 답변 시 list 인용.
    """
    if not industryId:
        return []
    rows = SECTOR_INDEX_MAP.get(industryId, ())
    if preferredMarket in {"KOSPI", "KOSDAQ"}:
        rows = tuple(sorted(rows, key=lambda r: 0 if r[0] in {"KRX", preferredMarket} else 1))
    result = []
    for indexMarket, indexName, confidence in rows:
        result.append(
            {
                "benchmarkType": "sector",
                "source": "krxIndex",
                "mappingSource": "industryTaxonomy",
                "indexMarket": indexMarket,
                "indexName": indexName,
                "symbol": indexName,
                "confidence": confidence,
                "industry": industryId,
            }
        )
    return result


@lru_cache(maxsize=1)
def loadIndustryNodes() -> list[dict[str, Any]]:
    """industry nodes.json을 읽는다.

    quant는 industry 엔진 코드를 import하지 않고 패키지 데이터만 읽는다. L2 엔진
    간 함수 의존을 만들지 않기 위한 경계다.

    Example:
        >>> nodes = loadIndustryNodes()
        >>> nodes[0]["stockCode"]
        '005930'

    Requires:
        dartlab/industry/nodes.json 정적 자산.

    Raises:
        FileNotFoundError — nodes.json 누락.
    """
    path = Path(__file__).resolve().parents[2] / "industry" / "nodes.json"
    return json.loads(path.read_text(encoding="utf-8"))


def primaryIndustryNode(stockCode: str | None) -> dict[str, Any] | None:
    """종목의 primary industry node를 반환한다.

    Capabilities:
        - loadIndustryNodes 캐시에서 stockCode 매칭 → primary=True 우선 + confidence max 선택
        - 매칭 0 건 시 None

    Args:
        stockCode: 6 자리 종목코드.

    Returns:
        dict | None — industry node (taxonomy id/sector 등).

    Guide:
        벤치 stack 의 sector 차원 입력 (industryId 추출). L2 quant → L2 industry import 회피
        목적 — 정적 nodes.json 만 읽음.

    When:
        Sector 벤치 결정 + AI 산업 분류 답변.

    How:
        loadIndustryNodes → stockCode filter → primary=True 우선 → confidence top.

    Requires:
        nodes.json 에 stockCode 등록.

    Raises:
        없음.

    Example:
        >>> primaryIndustryNode("005930")["industryId"]
        'semiconductor'

    SeeAlso:
        - loadIndustryNodes : 캐시
        - sectorCandidates : industry → 벤치 후보

    AIContext:
        "이 종목 산업" 답변 시 node 의 industryId/sector 인용.
    """
    if not stockCode:
        return None
    matches = [n for n in loadIndustryNodes() if n.get("stockCode") == stockCode]
    if not matches:
        return None
    primary = [n for n in matches if n.get("primary", True)]
    rows = primary or matches
    return max(rows, key=lambda n: float(n.get("confidence") or 0.0))
