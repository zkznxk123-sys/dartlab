"""1단계: KindList 업종(KSIC) + 주요제품 → 산업 대분류.

KindList의 업종·주요제품을 taxonomy.json + sectorParams.json과 매칭하여
각 회사가 어떤 산업에 속하는지 대분류한다.

우선순위:
1. manualOverrides (삼성전자→semiconductor 등 116사)
2. 주요제품 키워드 (제품에 "반도체"→semiconductor)
3. KSIC 업종명 매핑 ("반도체 제조업"→semiconductor)
"""

from __future__ import annotations

from dartlab.industry.taxonomy import findIndustryByKsic, loadTaxonomy
from dartlab.industry.types import IndustryNode


def _loadManualOverrides() -> dict[str, str]:
    """sectorParams.json의 manualOverrides → {회사명: industryId} 매핑.

    manualOverrides는 (sector, industryGroup) 형태인데,
    industryGroup → taxonomy industryId로 역매핑한다.
    """
    import json
    from pathlib import Path

    data = json.loads((Path(__file__).resolve().parents[1] / "sectorParams.json").read_text(encoding="utf-8"))
    overrides = data.get("manualOverrides", {})
    igToSector = data.get("industryGroupToSector", {})

    # industryGroup.value → taxonomy industryId 매핑 구축
    taxonomy = loadTaxonomy()
    igToIndustry: dict[str, str] = {}

    # taxonomy 각 산업의 stages keywords에서 연결
    # 직접 매핑: WICS IndustryGroup → taxonomy industryId
    _IG_MAP = {
        "반도체와반도체장비": "semiconductor",
        "디스플레이": "electronics",
        "소프트웨어와서비스": "software",
        "IT서비스": "software",
        "기술하드웨어와장비": "electronics",
        "제약과바이오": "pharma",
        "건강관리장비와서비스": "medicalDevice",
        "은행": "finance",
        "보험": "finance",
        "다각화된금융": "finance",
        "자동차와부품": "auto",
        "조선": "shipbuilding",
        "건설": "construction",
        "항공우주와국방": "aerospace",
        "화학": "chemical",
        "금속과광물": "steel",
        "게임엔터테인먼트": "software",
        "인터넷과카탈로그소매": "software",
        "미디어": "media",
        "전기통신서비스": "telecom",
        "소매(유통)": "retail",
        "식품,음료,담배": "food",
        "석유와가스": "chemical",
        "전력": "energy",
        "가스": "energy",
        "종이와목재": "paper",
        "건설자재": "buildingMaterials",
        "기계": "machinery",
        "운송": "logistics",
    }

    result: dict[str, str] = {}
    for name, ov in overrides.items():
        ig = ov.get("industryGroup", "")
        indId = _IG_MAP.get(ig)
        if indId:
            result[name] = indId

    return result


def _buildProductIndex() -> dict[str, list[tuple[str, str]]]:
    """taxonomy의 모든 stage keywords → (industryId, stageKey) 인덱스."""
    taxonomy = loadTaxonomy()
    index: dict[str, list[tuple[str, str]]] = {}
    for indId, ind in taxonomy.items():
        for stage in ind.stages:
            for kw in stage.keywords:
                kwLower = kw.lower()
                index.setdefault(kwLower, []).append((indId, stage.key))
    return index


def classify(kindList: list[dict]) -> list[IndustryNode]:
    """KindList 전종목을 산업 대분류한다.

    Capabilities:
        KindList (상장사 메타) 전 종목에 대해 우선순위 (manualOverrides → 주요제품 키워드 →
        KSIC 업종명) 로 산업 대분류 매핑. 첫 매칭 단계가 confidence 결정. stage 키는 후속
        stage2_product 가 채움.

    Parameters
    ----------
    kindList : list[dict]
        KindList raw row 리스트 (종목코드/회사명/업종/주요제품 컬럼).

    Returns
    -------
    list[IndustryNode]
        대분류 매핑된 IndustryNode 리스트. industry 채워짐 + stage 빈 문자열.

    Raises:
        없음 — 매칭 실패 종목은 결과에서 제외.

    Example:
        >>> from dartlab.industry.build.stage1_ksic import classify
        >>> nodes = classify(kindList)
        >>> sum(1 for n in nodes if n.industry == "semiconductor")
        62

    Guide:
        본 함수는 ``buildIndustryMap`` 의 1 단계. manualOverrides 는 ``manualOverrides.json``
        파일 — 부분명 매칭도 허용. confidence 0.95~1.0 (override) / 0.6~0.8 (KSIC) / 0.5~0.7
        (제품 키워드).

    When:
        manifest 빌드 1 단계. 일반 분석 흐름 호출 없다.

    How:
        KindList 행 루프 → manualOverrides 우선 매칭 → 부분명 매칭 → 제품 키워드 인덱스 →
        KSIC 업종명 룩업 → IndustryNode 생성.

    Requires:
        - L1 raw: KindList (DART 상장사 메타)
        - reference: taxonomy.json + manualOverrides.json

    See Also:
        - ``dartlab.industry.build.stage2_product.classify`` : stage 채우기 2 단계
        - ``dartlab.industry.build.pipeline.buildIndustryMap`` : 본 함수 사용자

    AIContext:
        AI 가 직접 호출하지 않는다 (배치). 답변에서 ``source=="override"`` 노드는 "운영자 확정",
        ``"ksic"`` 노드는 "KSIC 업종명 기준" 으로 단서 인용.
    """
    manualOv = _loadManualOverrides()
    productIdx = _buildProductIndex()

    nodes: list[IndustryNode] = []

    for row in kindList:
        code = row.get("종목코드", "")
        name = row.get("회사명", "")
        ksic = row.get("업종", "")
        products = row.get("주요제품", "")

        if not code:
            continue

        # 1. manualOverrides
        if name in manualOv:
            nodes.append(
                IndustryNode(
                    stockCode=code,
                    corpName=name,
                    industry=manualOv[name],
                    stage="",
                    confidence=1.0,
                    source="override",
                )
            )
            continue

        # 부분명 매칭
        matched = False
        for ovName, indId in manualOv.items():
            if ovName in name or name in ovName:
                nodes.append(
                    IndustryNode(
                        stockCode=code,
                        corpName=name,
                        industry=indId,
                        stage="",
                        confidence=0.95,
                        source="override",
                    )
                )
                matched = True
                break
        if matched:
            continue

        # 2. 주요제품 키워드 → taxonomy 매칭
        if products:
            prodLower = products.lower()
            bestInd = None
            bestScore = 0
            for kw, targets in productIdx.items():
                if kw in prodLower:
                    for indId, _ in targets:
                        # 같은 industry의 키워드가 많을수록 점수 높음
                        if bestInd != indId:
                            score = sum(
                                1 for k, ts in productIdx.items() if k in prodLower and any(t[0] == indId for t in ts)
                            )
                            if score > bestScore:
                                bestScore = score
                                bestInd = indId

            if bestInd and bestScore > 0:
                nodes.append(
                    IndustryNode(
                        stockCode=code,
                        corpName=name,
                        industry=bestInd,
                        stage="",
                        confidence=min(0.9, 0.6 + bestScore * 0.1),
                        source="product",
                    )
                )
                continue

        # 3. KSIC 업종명
        industryId = findIndustryByKsic(ksic)
        if industryId:
            nodes.append(
                IndustryNode(
                    stockCode=code,
                    corpName=name,
                    industry=industryId,
                    stage="",
                    confidence=0.7,
                    source="kindlist",
                )
            )

    return nodes
