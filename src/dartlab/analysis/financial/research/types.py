"""Research 엔진 데이터 타입 — 종합 기업분석 리포트 (슬림화 본체).

작은 dataclass 들은 도메인별 sub-module 로 분리 (BC 위해 re-export):
- ``_typesScoring.py``: 정량 스코어 (Piotroski/MagicFormula/QMJ/Lynch/DuPont/QuantScores)
- ``_typesSection.py``: 섹션 dataclass (Meta/Executive/Thesis/Overview/Sector/Financial 외)
- ``_typesNarrative.py``: 서사 (NarrativeParagraph/NarrativeAnalysis)
- ``_typesResearchRender.py``: rich rendering + summary + toDict 함수

``ResearchResult`` 는 데이터 필드 + 3 종 magic method (delegate to render module).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 분리된 dataclass re-export (BC)
from dartlab.analysis.financial.research._typesNarrative import NarrativeAnalysis, NarrativeParagraph  # noqa: F401
from dartlab.analysis.financial.research._typesScoring import (  # noqa: F401
    DuPontResult,
    LynchFairValue,
    MagicFormulaScore,
    PiotroskiScore,
    QmjScore,
    QuantScores,
)
from dartlab.analysis.financial.research._typesSection import (  # noqa: F401
    AnomalySection,
    BeneishDetail,
    CompanyOverview,
    DistressSection,
    EarningsQuality,
    ExecutiveSummary,
    FinancialAnalysis,
    ForecastData,
    InsightDetail,
    InvestmentThesis,
    MarketData,
    PeerSection,
    ResearchMeta,
    RiskSection,
    SectorKpi,
    SectorKpis,
    ValuationSection,
)


@dataclass
class ResearchResult:
    """종합 기업분석 리포트.

    Capabilities:
        analysis.research 엔진의 단일 결과 컨테이너. Executive summary + 5 축 분석 +
        정량 스코어 + 시장 데이터 + 예측 + 서사 를 통합하는 fat dataclass. rich
        rendering (Jupyter / 콘솔), summary 텍스트, dict 직렬화 진입점.

    Returns:
        Self.

    Example:
        >>> from dartlab.analysis.financial import Analysis
        >>> r = Analysis("005930").research()
        >>> print(r)  # rich 렌더 (콘솔)
        >>> r._repr_html_()  # Jupyter
        >>> r.toDict()  # dict
    """

    # 기존 섹션
    meta: ResearchMeta = field(default_factory=ResearchMeta)
    executive: ExecutiveSummary = field(default_factory=ExecutiveSummary)
    thesis: InvestmentThesis = field(default_factory=InvestmentThesis)
    overview: CompanyOverview | None = None
    sectorKpis: SectorKpis | None = None
    financial: FinancialAnalysis | None = None
    earningsQuality: EarningsQuality | None = None
    quantScores: QuantScores | None = None
    marketData: MarketData | None = None
    forecast: ForecastData | None = None

    # v2 새 섹션
    insightDetails: list[InsightDetail] = field(default_factory=list)
    valuationAnalysis: ValuationSection | None = None
    riskAnalysis: RiskSection | None = None
    peerAnalysis: PeerSection | None = None

    # v3 교차분석 서술
    narrativeAnalysis: NarrativeAnalysis | None = None

    DISCLAIMER: str = "본 분석은 투자 참고용이며 투자 권유가 아닙니다."

    def __repr__(self) -> str:
        """rich 콘솔 렌더 → 캡처 (rich 미설치 시 summary 텍스트 fallback)."""
        try:
            from rich.console import Console

            from dartlab.analysis.financial.research._typesResearchRender import _richPrint

            console = Console(highlight=False, force_terminal=True)
            with console.capture() as capture:
                _richPrint(self, console)
            return capture.get()
        except ImportError:
            return self.summary()

    def _repr_html_(self) -> str:
        """Jupyter / Colab / Marimo HTML 렌더링."""
        try:
            from rich.console import Console

            from dartlab.analysis.financial.research._typesResearchRender import _richPrint

            console = Console(record=True, force_jupyter=True, width=100)
            _richPrint(self, console)
            return console.export_html(inline_styles=True)
        except ImportError:
            return f"<pre>{self.summary()}</pre>"

    def summary(self) -> str:
        """텍스트 summary (rich 없이도 작동)."""
        from dartlab.analysis.financial.research._typesResearchRender import summary as _s

        return _s(self)

    def toDict(self) -> dict:
        """dict 직렬화 (asdict + DISCLAIMER 포함)."""
        from dartlab.analysis.financial.research._typesResearchRender import toDict as _d

        return _d(self)
