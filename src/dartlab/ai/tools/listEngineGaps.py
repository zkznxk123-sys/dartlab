"""ListEngineGaps — recipe 카탈로그에서 비어있는 엔진 페어 식별 (chat-native).

recipe 가 격리된 분석엔진을 묶어주는 lightweight 조합층이라는 전제에서, 어떤 엔진 페어가
아직 bridging 되지 않았는지 (또는 1 개 미만) 알려주는 stateless 도구.

사용 흐름: AI 가 사용자 질문 ("엔진 조합 어디 비어있나" 같은) 에 자율 호출 → 출력으로
다리 0~minBridges 인 페어 + 샘플 질문 → AI 가 ProposeRecipe 로 보강.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from .types import ToolResult

_RECIPE_DIR = Path(__file__).resolve().parents[2] / "skills" / "specs" / "engines" / "recipe"

# facade · meta · 인프라 엔진은 페어 후보에서 제외 (recipe_schema_migrate.py 와 동일).
_EXCLUDED_FROM_GAP = frozenset({"recipe", "company", "mappers", "dashboard", "viz", "data"})

# gap 페어별 샘플 사용자 질문 — AI 가 적절한 recipe 작성 트리거 텍스트로 사용.
_SAMPLE_QUESTIONS: dict[frozenset[str], str] = {
    frozenset({"credit", "macro"}): "삼성전자 신용등급 +200bp 금리 충격에서 유지 가능?",
    frozenset({"credit", "quant"}): "Altman Z + Ohlson + Beneish 3-source 부도 합의 종목",
    frozenset({"quant", "macro"}): "1997/2008/2020 macro 시나리오 별 quality 팩터 IR",
    frozenset({"industry", "scan"}): "도입기/후행기 산업 + 가치 + 퀄리티 + 생존가능 종목",
    frozenset({"industry", "quant"}): "동종업체 macroBeta 분포 outlier 탐지",
    frozenset({"search", "analysis"}): "최근 8-K 비정상 키워드 빈도 → predictionSignal",
    frozenset({"gather", "story"}): "공시 tone change → story.risk 블럭 자동 발행",
    frozenset({"scan", "credit"}): "dCR 등급 전월비 하락 + sentiment z 약세 동시 적신호",
    frozenset({"scan", "analysis"}): "거버넌스 + 계열사밀도 + 감사변경 triple flag",
    frozenset({"macro", "story"}): "매크로 사이클 위치별 회사 narrative 변경",
    frozenset({"analysis", "credit"}): "현금흐름 품질 × 거버넌스 감사 동시 적신호",
    frozenset({"analysis", "macro"}): "P&L 매크로 elasticity → DCF 적정가치 분포",
    frozenset({"analysis", "quant"}): "회계품질 + factor risk 동시 약화 종목",
    frozenset({"analysis", "industry"}): "산업 stage × 회사 valuation regime",
    frozenset({"gather", "quant"}): "내부자 매수 클러스터 → 다음 분기 surprise IC",
}


def _readFrontmatterEngines(path: Path) -> list[str]:
    """recipe md 의 frontmatter linkedSkills 에서 engine 이름만 추출."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    if not text.startswith("---"):
        return []
    parts = text.split("---", 2)
    if len(parts) < 3:
        return []
    frontmatter = parts[1]
    engines: list[str] = []
    in_section = False
    indent: int | None = None
    for line in frontmatter.splitlines():
        if line.rstrip() == "linkedSkills:":
            in_section = True
            continue
        if not in_section:
            continue
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        current_indent = len(line) - len(stripped)
        if indent is None:
            indent = current_indent
        if not stripped.startswith("- "):
            if current_indent <= 0 and ":" in stripped:
                break
            if current_indent < indent:
                break
            continue
        item = stripped[2:].strip().strip("\"'")
        if item.startswith("engines."):
            parts2 = item.split(".")
            if len(parts2) >= 2:
                engine = parts2[1]
                if engine and engine not in _EXCLUDED_FROM_GAP:
                    engines.append(engine)
    return engines


def _buildAdjacency(recipeDir: Path) -> Counter:
    """recipe 디렉터리에서 모든 페어 빈도 누적."""
    bridge_counts: Counter[frozenset[str]] = Counter()
    for path in sorted(recipeDir.glob("*.md")):
        engines = list(set(_readFrontmatterEngines(path)))
        for a, b in combinations(sorted(engines), 2):
            bridge_counts[frozenset({a, b})] += 1
    return bridge_counts


def listEngineGaps(
    engines: list[str] | None = None,
    minBridges: int = 1,
    limit: int = 30,
) -> ToolResult:
    """recipe 카탈로그에서 다리 ≤ minBridges 인 엔진 페어 식별.

    Parameters
    ----------
    engines : list[str], optional
        관심 엔진 목록. 미지정시 전체 분석엔진 (analysis/credit/macro/quant/industry/scan/
        gather/search/story/edgar) 대상.
    minBridges : int
        포함 임계 — bridgeCount ≤ minBridges 인 페어만 반환. 기본 1 (1 개 이하).
    limit : int
        최대 결과 개수 (정렬 후 head N).

    Returns
    -------
    ToolResult
        ``data.gaps``: ``[{pair: [a,b], bridgeCount: int, sampleQuestion: str}]``,
        bridgeCount 오름차순.
    """
    if not _RECIPE_DIR.is_dir():
        return ToolResult(
            False,
            f"recipe 디렉터리 없음: {_RECIPE_DIR}",
            error="recipeDir_missing",
        )

    target_engines: set[str] | None = None
    if engines:
        target_engines = {e for e in engines if e and e not in _EXCLUDED_FROM_GAP}
        if not target_engines:
            return ToolResult(
                False,
                "유효한 엔진 이름이 없다 (facade/meta 엔진은 제외됨)",
                error="invalid_engines",
            )

    # 모든 분석엔진 후보 (engines.<name> 으로 등장 가능한 것).
    candidate_engines = (
        target_engines
        if target_engines
        else {
            "analysis",
            "credit",
            "macro",
            "quant",
            "industry",
            "scan",
            "gather",
            "search",
            "story",
            "edgar",
        }
    )

    bridge_counts = _buildAdjacency(_RECIPE_DIR)

    gaps: list[dict[str, Any]] = []
    for a, b in combinations(sorted(candidate_engines), 2):
        pair_key = frozenset({a, b})
        count = bridge_counts.get(pair_key, 0)
        if count <= minBridges:
            sample = _SAMPLE_QUESTIONS.get(pair_key, f"{a} × {b} 조합 분석")
            gaps.append(
                {
                    "pair": [a, b],
                    "bridgeCount": count,
                    "sampleQuestion": sample,
                }
            )

    gaps.sort(key=lambda item: (item["bridgeCount"], item["pair"]))
    gaps = gaps[:limit]

    return ToolResult(
        True,
        f"엔진 페어 {len(gaps)} 개 (bridgeCount ≤ {minBridges})",
        data={
            "gaps": gaps,
            "totalRecipes": sum(bridge_counts.values()) if bridge_counts else 0,
            "engines": sorted(candidate_engines),
        },
    )


__all__ = ["listEngineGaps"]
