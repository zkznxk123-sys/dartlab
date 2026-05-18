"""Research 리포트 렌더링 + 직렬화 — facade. 본체는 `_typesResearchRenderRich` / `_typesResearchRenderSummary`.

ResearchResult 의 ``__repr__`` / ``_repr_html_`` / ``summary`` / ``toDict`` 가
본 facade 의 함수를 호출 (lazy import).
"""

from __future__ import annotations

from dartlab.analysis.financial.research._typesResearchRenderRich import (
    _assessColor,
    _distressColor,
    _opinionColor,
    _profileBadge,
    _renderFinancial,
    _renderForecast,
    _renderMarket,
    _renderNarrative,
    _renderPeer,
    _renderQuantAndQuality,
    _renderRisk,
    _renderThesis,
    _renderValuation,
    _richPrint,
    _verdictColor,
)
from dartlab.analysis.financial.research._typesResearchRenderSummary import (
    _renderSectorKpis,
    summary,
    toDict,
)

__all__ = [
    "_assessColor",
    "_distressColor",
    "_opinionColor",
    "_profileBadge",
    "_renderFinancial",
    "_renderForecast",
    "_renderMarket",
    "_renderNarrative",
    "_renderPeer",
    "_renderQuantAndQuality",
    "_renderRisk",
    "_renderSectorKpis",
    "_renderThesis",
    "_renderValuation",
    "_richPrint",
    "_verdictColor",
    "summary",
    "toDict",
]
