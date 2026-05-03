"""Searchable knowledge references for DartLab workbench surfaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KnowledgeRef:
    id: str
    title: str
    summary: str
    tags: list[str]
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


_BUILTINS = [
    KnowledgeRef(
        id="dartlabCausalSixActs",
        title="DartLab 6막 인과",
        summary="경제 -> 섹터 -> 기업 -> 재무 -> 가치 신호를 연결해 판단한다.",
        tags=["macro", "sector", "company", "analysis", "valuation", "story", "6막"],
        source="CLAUDE.md / operation.philosophy",
    ),
    KnowledgeRef(
        id="krxDatasetStructure",
        title="KRX 런타임 데이터 구조",
        summary="KRX 가격/지수 데이터는 런타임 dataset schema/latest/entity/metric 확인 후 사용한다. 주가지수 강세와 종목 상승 검색의 기준 구조다.",
        tags=["krx", "index", "price", "dataset", "BAS_DD", "IDX_NM", "ISU_SRT_CD", "주가지수", "강세", "종목"],
        source="RuntimeDatasetCatalog",
    ),
    KnowledgeRef(
        id="dartDisclosureStructure",
        title="DART 공시 구조",
        summary="공시 판단은 접수일, 제목, 유형, 가능한 경량 본문 근거를 구분한다.",
        tags=["dart", "disclosure", "filing", "readFiling", "rcept_dt"],
        source="engines.company / Company.disclosure docstring",
    ),
    KnowledgeRef(
        id="financialStatementConcepts",
        title="재무제표 항목 의미",
        summary="재무 판단은 대상, 기간, metric, 단위가 있는 원본 또는 계산 ref에 연결한다.",
        tags=["financial", "statement", "revenue", "margin", "cashflow", "ratio"],
        source="engines.analysis / public docstrings",
    ),
    KnowledgeRef(
        id="valuationPrinciples",
        title="가치평가 가정 원칙",
        summary="가치평가는 성장, 마진, 재투자, 할인율, 터미널 가정과 민감도 한계를 함께 본다.",
        tags=["valuation", "dcf", "discount", "sensitivity", "terminal"],
        source="engines.quant / valuation docstrings",
    ),
    KnowledgeRef(
        id="quantSignalConcepts",
        title="퀀트 신호 해석 원칙",
        summary="모멘텀, 변동성, 밸류에이션 신호는 기준일과 metric이 맞을 때만 비교한다.",
        tags=["quant", "momentum", "volatility", "valuation", "signal"],
        source="engines.quant",
    ),
]


def listKnowledge() -> list[KnowledgeRef]:
    """Knowledge reference 목록 반환."""

    return list(_BUILTINS)


def getKnowledge(knowledgeId: str) -> KnowledgeRef:
    """id 로 KnowledgeRef 조회."""

    for item in _BUILTINS:
        if item.id == knowledgeId:
            return item
    raise KeyError(f"unknown DartLab knowledge ref: {knowledgeId}")


def searchKnowledge(query: str, *, limit: int = 8) -> list[KnowledgeRef]:
    """Knowledge reference 검색."""

    terms = [term.lower() for term in query.replace(".", " ").replace("/", " ").split() if len(term) >= 2]
    if not terms:
        return list(_BUILTINS[:limit])

    def score(item: KnowledgeRef) -> tuple[int, str]:
        hay = " ".join([item.id, item.title, item.summary, *item.tags]).lower()
        return (sum(1 for term in terms if term in hay), item.id)

    return [item for item in sorted(_BUILTINS, key=score, reverse=True) if score(item)[0] > 0][:limit]
