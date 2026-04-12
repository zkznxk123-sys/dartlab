"""CapabilityIndex — CAPABILITIES dict 위의 질문 관련 API 검색.

핵심 사상: 700줄 매뉴얼을 AI에게 주입하지 않고,
질문에 관련된 상위 k개 API 설명만 동적으로 주입한다.
(Gorilla, AnyTool 2024 SOTA 패턴)

하부 엔진이 새 API를 추가해도 generateSpec.py 실행 후 자동 반영.
매뉴얼 수정 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class CapabilityHit:
    """검색 결과 항목."""

    key: str  # 예: "Company.analysis"
    summary: str
    guide: str  # 사용 예시 (guide 필드)
    kind: str  # "function" / "method" / "property" / "class"
    score: float

    def toPromptText(self) -> str:
        """프롬프트 주입용 텍스트. 간결한 형식 + 예시 포함."""
        lines = [f"### {self.key}"]
        if self.summary:
            lines.append(self.summary)
        if self.guide:
            lines.append(self.guide)
        return "\n".join(lines)


class CapabilityIndex:
    """CAPABILITIES dict 위의 키워드 기반 검색 인덱스.

    임베딩 없이 BM25 스타일 키워드 매칭. cold start 0ms.
    CAPABILITIES는 lru_cache로 한번만 로드.
    """

    def __init__(self) -> None:
        self._loaded = False

    @lru_cache(maxsize=1)
    def _load(self) -> dict[str, dict]:
        """CAPABILITIES dict 로드 (캐시)."""
        try:
            from dartlab.guide._generated import CAPABILITIES
            return CAPABILITIES
        except ImportError:
            return {}

    def search(self, query: str, k: int = 5, *, aiRelevantOnly: bool = True) -> list[CapabilityHit]:
        """질문과 관련된 상위 k개 API 반환.

        매칭 필드 (가중치):
        - key 이름 (3.0): "Company.analysis" 자체
        - summary (2.0): 한 줄 요약
        - guide (1.5): 사용 예시
        - capabilities (1.0): 긴 설명
        - aicontext (1.0): AI 힌트

        Args:
            query: 사용자 질문
            k: 반환 개수
            aiRelevantOnly: kind="method"/"function"/"property"만 반환 (class 제외)

        Returns:
            score 내림차순 상위 k개 CapabilityHit
        """
        caps = self._load()
        if not caps:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        hits: list[CapabilityHit] = []
        for key, cap in caps.items():
            kind = cap.get("kind", "")
            if aiRelevantOnly and kind == "class":
                continue

            score = self._score(tokens, key, cap)
            if score <= 0:
                continue

            hits.append(
                CapabilityHit(
                    key=key,
                    summary=cap.get("summary", ""),
                    guide=cap.get("guide", ""),
                    kind=kind,
                    score=score,
                )
            )

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    # 한글 질문 → dartlab 개념 키워드 확장
    _SYNONYMS: dict[str, list[str]] = {
        "수익성": ["analysis", "수익성", "profitability", "마진", "영업이익률"],
        "영업이익": ["analysis", "수익성", "operating"],
        "마진": ["analysis", "수익성", "margin"],
        "현금흐름": ["analysis", "현금흐름", "cashflow", "OCF", "FCF"],
        "현금": ["analysis", "현금흐름", "cashflow"],
        "안정성": ["analysis", "안정성", "stability", "부채비율", "leverage"],
        "부채": ["analysis", "안정성", "debt"],
        "성장": ["analysis", "성장성", "growth"],
        "매출": ["analysis", "수익구조", "revenue"],
        "배당": ["capital", "dividend"],
        "자사주": ["capital"],
        "주주환원": ["capital"],
        "신용": ["credit"],
        "등급": ["credit"],
        "가치": ["valuation", "DCF"],
        "적정주가": ["valuation"],
        "PER": ["valuation"],
        "ROE": ["analysis"],
        "시장": ["scan"],
        "업종": ["scan"],
        "비교": ["scan", "compare"],
        "매크로": ["macro"],
        "금리": ["macro"],
        "환율": ["macro"],
        "주가": ["gather", "price"],
        "차트": ["gather"],
        "뉴스": ["gather", "news"],
        "공시": ["search", "filings"],
        "재무제표": ["IS", "BS", "CF", "show", "select"],
        "계정": ["show", "select"],
        "재무비율": ["ratios"],
        "기술적": ["quant"],
        "추세": ["quant", "trend"],
        "지배구조": ["governance"],
        "감사": ["audit"],
    }

    def _tokenize(self, text: str) -> list[str]:
        """한글/영문 혼합 토큰화 + 동의어 확장. 2자 이상만."""
        # 한글 단어 + 영문 단어 추출
        tokens = re.findall(r"[가-힣]+|[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
        tokens = [t for t in tokens if len(t) >= 2]

        # 동의어 확장
        expanded: list[str] = list(tokens)
        for t in tokens:
            syns = self._SYNONYMS.get(t)
            if syns:
                expanded.extend(s.lower() for s in syns)
        return expanded

    def _score(self, tokens: list[str], key: str, cap: dict) -> float:
        """매칭 스코어. 필드별 가중치 적용."""
        key_lower = key.lower()
        summary = cap.get("summary", "").lower()
        guide = cap.get("guide", "").lower()
        capabilities = cap.get("capabilities", "").lower()
        aicontext = cap.get("aicontext", "").lower()

        score = 0.0
        for tok in tokens:
            if tok in key_lower:
                score += 3.0
            if tok in summary:
                score += 2.0
            if tok in guide:
                score += 1.5
            if tok in capabilities:
                score += 1.0
            if tok in aicontext:
                score += 1.0
        return score

    def formatForPrompt(self, hits: list[CapabilityHit]) -> str:
        """검색 결과를 프롬프트 주입용 마크다운으로 포맷."""
        if not hits:
            return ""
        lines = ["## 질문 관련 dartlab API (상위 검색 결과)"]
        for hit in hits:
            lines.append("")
            lines.append(hit.toPromptText())
        return "\n".join(lines)

    def rebuild(self) -> None:
        """CAPABILITIES가 갱신됐을 때 캐시 무효화.

        generateSpec.py 실행 후 호출하면 AI가 즉시 새 API 인식.
        """
        self._load.cache_clear()


# 싱글턴 인스턴스
_instance: CapabilityIndex | None = None


def getCapabilityIndex() -> CapabilityIndex:
    """싱글턴 CapabilityIndex 인스턴스."""
    global _instance
    if _instance is None:
        _instance = CapabilityIndex()
    return _instance
