"""dartlab.help — 자연어 query 로 관련 API 발견 (T8-2).

진입점:
    >>> import dartlab
    >>> dartlab.help("외인 매수")
    [관련 API 5 개, ref count desc + docstring summary]

내부 구현: ``__all__`` 심볼 + (선택) Skill OS capability index 를 query 토큰
substring 매칭. 정확도가 낮으면 ReadCapability skill 호출 (운영자 명시 옵션).

목적:
    - 외부 사용자 / LLM 첫 진입 시 "어디서 시작?" 의사결정 비용 0
    - 30+ public API 의 *발견 가능성* 향상 (T8 KPI 가중 20 percent)

실행::

    import dartlab
    dartlab.help("재무비율")
    dartlab.help("신용 점수")
    dartlab.help("매크로")

CLI 통합:
    dartlab help "외인 매수"
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass


@dataclass
class HelpResult:
    """단일 매칭 결과 — 심볼명 + 시그니처 + 요약."""

    name: str
    kind: str  # "function" / "class" / "module" / "attribute"
    summary: str
    score: float  # 0.0~1.0


def _splitTokens(query: str) -> list[str]:
    """공백/구두점 분리 후 lowercase 토큰."""
    tokens = []
    for raw in query.replace(",", " ").replace("/", " ").split():
        t = raw.strip().lower()
        if t:
            tokens.append(t)
    return tokens


def _matchScore(name: str, doc: str, tokens: list[str]) -> float:
    """이름 (가중 2) + docstring (가중 1) substring 매칭 score 0~1."""
    if not tokens:
        return 0.0
    nameLower = name.lower()
    docLower = (doc or "").lower()
    nameMatches = sum(1 for t in tokens if t in nameLower)
    docMatches = sum(1 for t in tokens if t in docLower)
    raw = (nameMatches * 2 + docMatches) / (len(tokens) * 3)
    return min(raw, 1.0)


def _extractSummary(obj: object) -> str:
    """docstring 첫 줄 또는 빈 문자열."""
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    # 첫 줄 또는 첫 paragraph
    firstLine = doc.split("\n", 1)[0].strip()
    return firstLine[:200]


def help(query: str, *, limit: int = 5) -> list[HelpResult]:  # noqa: A001
    """dartlab 공개 API 검색 — 자연어 query 매칭 9 섹션 docstring (T10-4).

    Capabilities:
        dartlab.__all__ 안 모든 심볼의 docstring 첫 줄 + 이름을 자연어 query 토큰
        과 substring 매칭하여 관련 API 5 개 (또는 limit) 를 score 순서로 반환.

    Args:
        query: 자연어 또는 키워드 (예: "외인 매수", "재무비율", "신용 점수").
            빈 문자열 시 전체 __all__ 둘러보기 (score 0.5).
        limit: 반환 결과 최대 개수 (기본 5).

    Returns:
        score (0.0~1.0) desc 정렬된 HelpResult 리스트. score = (name match × 2 + doc
        match) / (len(tokens) × 3). HelpResult 는 name / kind / summary / score 4
        필드 dataclass.

    Example:
        >>> import dartlab
        >>> results = dartlab.help("재무비율")
        >>> for r in results:
        ...     print(f"{r.name} ({r.score:.2f}) — {r.summary}")

    Guide:
        결과가 0 이면 query 토큰을 줄여 재시도. 정확한 API 모를 때는
        ``dartlab.help("")`` 로 전체 ``__all__`` 둘러보기 가능. CLI 등가 명령:
        ``dartlab help <query>``.

    SeeAlso:
        - dartlab.ask: 자연어 질문 → AI 워크벤치 답변 + ref
        - dartlab.core.plugins.listPlugins: 외부 plugin 목록 (T5-5)
        - dartlab.skills.readSkill: Skill OS 257 노드 검색

    Requires:
        dartlab 패키지가 import 가능해야 한다. lazy import 패턴이라 순환 import
        회피.

    AIContext:
        외부 LLM / 신규 사용자의 *어디서 시작?* 질문에 답하는 진입점. T8-2 의
        핵심. README "세 가지 시작점" 의 3 분기 중 자연어 진입을 보강.

    LLM Specifications:
        - AntiPatterns: 본 함수가 LLM tool registry 가 아니다 — 단순 검색 only.
          실제 tool 호출은 dartlab.ai.tools 또는 MCP server.
        - OutputSchema: list[HelpResult] / HelpResult = {name, kind, summary, score}.
        - Prerequisites: dartlab 패키지가 sys.path 안.
        - Freshness: 매 호출 시 __all__ 최신 상태 반영 (캐시 X).
        - Dataflow: query → tokens → __all__ 순회 → score 계산 → top N.
        - TargetMarkets: 외부 사용자 + LLM agent + CLI dartlab help.
    """
    tokens = _splitTokens(query)

    # lazy import — 본 함수가 dartlab 초기화의 순환에 들어가지 않도록.
    try:
        dl = importlib.import_module("dartlab")
    except ImportError:
        return []

    symbols = list(getattr(dl, "__all__", []))
    if not symbols:
        return []

    results: list[HelpResult] = []
    for symName in symbols:
        try:
            obj = getattr(dl, symName)
        except AttributeError:
            continue
        kind = (
            "class"
            if inspect.isclass(obj)
            else "function"
            if inspect.isfunction(obj) or inspect.isbuiltin(obj)
            else "module"
            if inspect.ismodule(obj)
            else "attribute"
        )
        summary = _extractSummary(obj)
        score = _matchScore(symName, summary, tokens) if tokens else 0.5
        if not tokens or score > 0:
            results.append(HelpResult(name=symName, kind=kind, summary=summary, score=score))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


__all__ = ["help", "HelpResult"]
