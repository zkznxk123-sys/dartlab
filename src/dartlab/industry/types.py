"""산업 매퍼엔진 데이터 모델.

taxonomy.json, nodes.json, edges.json의 행 단위 타입.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StageInfo:
    """taxonomy.json의 한 공정 단계."""

    key: str
    name: str
    role: str  # 제조 / 도매 / 소매 / 연구 / 서비스
    stream: str  # upstream / midstream / downstream
    keywords: list[str]


@dataclass
class IndustryDef:
    """taxonomy.json의 한 산업 정의."""

    industryId: str
    name: str
    ksicCodes: list[str]
    stages: list[StageInfo]

    def stageByKey(self, key: str) -> StageInfo | None:
        for s in self.stages:
            if s.key == key:
                return s
        return None

    def allKeywords(self) -> dict[str, list[str]]:
        """stage key → keywords 매핑."""
        return {s.key: s.keywords for s in self.stages}


@dataclass
class IndustryNode:
    """nodes.json의 한 행 — 회사의 산업 내 위치."""

    stockCode: str
    corpName: str
    industry: str  # taxonomy의 industry ID
    stage: str  # taxonomy의 stage key
    role: str = ""
    stream: str = ""
    confidence: float = 0.0
    source: str = ""  # kindlist / product / docs / ai / manual
    primary: bool = True
    updatedAt: str = ""
    revenue: float | None = None  # 매출액 (원)

    def toDict(self) -> dict:
        return {
            "stockCode": self.stockCode,
            "corpName": self.corpName,
            "industry": self.industry,
            "stage": self.stage,
            "role": self.role,
            "stream": self.stream,
            "confidence": self.confidence,
            "source": self.source,
            "primary": self.primary,
            "updatedAt": self.updatedAt,
            "revenue": self.revenue,
        }

    @staticmethod
    def fromDict(d: dict) -> IndustryNode:
        return IndustryNode(
            stockCode=d.get("stockCode", ""),
            corpName=d.get("corpName", ""),
            industry=d.get("industry", ""),
            stage=d.get("stage", ""),
            role=d.get("role", ""),
            stream=d.get("stream", ""),
            confidence=d.get("confidence", 0.0),
            source=d.get("source", ""),
            primary=d.get("primary", True),
            updatedAt=d.get("updatedAt", ""),
            revenue=d.get("revenue"),
        )


@dataclass
class IndustryEdge:
    """edges.json의 한 행 — 공급-수요 관계."""

    fromCode: str
    fromName: str
    toCode: str
    toName: str
    edgeType: str  # supplier / customer / affiliate / competitor
    industry: str
    confidence: float = 0.0
    source: str = ""  # docs / network / ai / manual
    evidence: str = ""

    def toDict(self) -> dict:
        return {
            "fromCode": self.fromCode,
            "fromName": self.fromName,
            "toCode": self.toCode,
            "toName": self.toName,
            "type": self.edgeType,
            "industry": self.industry,
            "confidence": self.confidence,
            "source": self.source,
            "evidence": self.evidence,
        }

    @staticmethod
    def fromDict(d: dict) -> IndustryEdge:
        return IndustryEdge(
            fromCode=d.get("fromCode", ""),
            fromName=d.get("fromName", ""),
            toCode=d.get("toCode", ""),
            toName=d.get("toName", ""),
            edgeType=d.get("type", ""),
            industry=d.get("industry", ""),
            confidence=d.get("confidence", 0.0),
            source=d.get("source", ""),
            evidence=d.get("evidence", ""),
        )
