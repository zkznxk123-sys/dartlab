"""dartlab.viz — 통합 시각화 엔진.

차트(ChartSpec), 다이어그램(Mermaid), AI 시각화 emit을 하나의 엔진에서 관리한다.

사용법::

    import dartlab

    # Company → ChartSpec 자동 생성
    specs = dartlab.viz.auto_chart(c)
    spec = dartlab.viz.spec_revenue_trend(c)

    # DataFrame → Plotly Figure (Jupyter용)
    dartlab.viz.line(df, x="year", y=["매출액"])
    dartlab.viz.bar(df, x="year", y=["영업이익"])
    dartlab.viz.revenue(c).show()

    # AI 코드에서 차트/다이어그램 출력
    from dartlab.viz import emit_chart, emit_diagram
    emit_chart({"chartType": "combo", "title": "...", ...})
    emit_diagram("mermaid", "graph LR\\n  A-->B")

    # ChartSpec → Plotly Figure 변환
    from dartlab.viz.plotly import from_spec
    fig = from_spec(spec)
"""

from __future__ import annotations

import json

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


from dartlab.viz.charts import (
    balance_sheet as balance_sheet_chart,
)

# ── DataFrame → Plotly Figure (Jupyter) ──
from dartlab.viz.charts import (  # noqa: F401
    balance_sheet_composition,
    bar,
    cashflow,
    cashflow_pattern,
    dividend_analysis,
    line,
    pie,
    profitability_ratios,
    revenue,
    # 하위호환 alias
    revenue_trend,
    waterfall,
)
from dartlab.viz.charts import (
    dividend as dividend_chart,
)
from dartlab.viz.charts import (
    profitability as profitability_chart,
)

# ── AI stdout 마커 추출 ──
from dartlab.viz.extract import extract_viz_specs  # noqa: F401

# ── Company → ChartSpec 생성기 ──
from dartlab.viz.generators import (  # noqa: F401
    SPEC_GENERATORS,
    auto_chart,
    spec_balance_sheet,
    spec_cashflow_waterfall,
    spec_diff_heatmap,
    spec_dividend,
    spec_insight_radar,
    spec_profitability,
    spec_ratio_sparklines,
    spec_revenue_trend,
)

# ── 팔레트 ──
from dartlab.viz.palette import COLORS  # noqa: F401

# ── ChartSpec → Plotly Figure 변환 ──
from dartlab.viz.plotly import from_spec as chart_from_spec  # noqa: F401

# ── VizSpec ──
from dartlab.viz.spec import VizSpec  # noqa: F401

# ══════════════════════════════════════
# AI 코드용 emit 함수
# ══════════════════════════════════════

_MARKER_START = "<!--DARTLAB_VIZ:"
_MARKER_END = ":VIZ_END-->"

# dartlab.analysis() 가이드 dataframe 의 axis 컬럼 값 (22 축).
# 이걸 categories 로 쓴 차트는 메타데이터 차트라 사용자 가치 0 → 거부.
_GUIDE_AXIS_NAMES = frozenset(
    {
        "수익구조",
        "자금조달",
        "자산구조",
        "현금흐름",
        "수익성",
        "성장성",
        "안정성",
        "효율성",
        "종합평가",
        "이익품질",
        "비용구조",
        "자본배분",
        "투자효율",
        "재무정합성",
        "가치평가",
        "지배구조",
        "공시변화",
        "비교분석",
        "매출전망",
        "예측신호",
        "매크로민감도",
        "밸류에이션밴드",
    }
)


def _is_meta_guide_chart(spec: dict) -> bool:
    """analysis() 가이드 dataframe 으로 만든 의미 없는 메타 차트 감지.

    시그널: categories 가 dartlab 22축 이름과 5개 이상 겹치고
    series data 가 모두 0~25 범위의 작은 값 (= items 컬럼).
    """
    cats = spec.get("categories")
    if not isinstance(cats, list) or len(cats) < 5:
        return False
    cat_set = {str(c).strip() for c in cats}
    overlap = cat_set & _GUIDE_AXIS_NAMES
    if len(overlap) < 5:
        return False
    series = spec.get("series") or []
    for s in series:
        if not isinstance(s, dict):
            continue
        data = s.get("data")
        if not isinstance(data, list) or not data:
            continue
        nums = [v for v in data if isinstance(v, (int, float))]
        if nums and all(0 <= v <= 25 for v in nums):
            return True
    return False


def emit_chart(spec: dict) -> None:
    """AI 코드에서 차트 출력.

    런타임이 stdout에서 마커를 자동 추출하여 CHART 이벤트로 전환한다.

    Args:
        spec: ChartSpec dict. chartType, title, series, categories 필수.

    Example::

        emit_chart({
            "chartType": "combo",
            "title": "삼성전자 매출 추이",
            "series": [{"name": "매출", "data": [100, 120, 150], "type": "bar"}],
            "categories": ["2022", "2023", "2024"],
        })
    """
    # R32-1: 빈 spec 거부 — chartType 없으면 webview 가 렌더 못 함
    if not spec or "chartType" not in spec and "vizType" not in spec:
        _log.warning(
            "[차트 거부] emit_chart 에 chartType 이 필요합니다. "
            "예: emit_chart({'chartType': 'line', 'title': '...', "
            "'categories': [...], 'series': [{'name': '...', 'data': [...]}]})"
        )
        return

    # 메타 가이드 차트 거부 — AI 가 dartlab.analysis() 가이드 dataframe 의
    # items 컬럼을 막대로 그리는 패턴 차단. 사용자 가치 0.
    if _is_meta_guide_chart(spec):
        _log.warning(
            "[차트 거부] analysis() 가이드 dataframe 의 'items' 컬럼은 사용자에게 "
            "가치 없는 메타데이터입니다. 차트를 그리지 말고, 진짜 종목 데이터로 "
            "다시 시각화하세요. 예시:\n"
            "  hist = c.analysis('financial', '수익성')['marginTrend']['history']\n"
            "  emit_chart({'chartType':'line', 'title':'영업이익률 추이',\n"
            "              'categories':[h['period'] for h in hist],\n"
            "              'series':[{'name':'영업이익률',\n"
            "                         'data':[h['operatingMargin'] for h in hist]}]})"
        )
        return
    spec.setdefault("vizType", "chart")
    _log.info(f"{_MARKER_START}{json.dumps(spec, ensure_ascii=False)}{_MARKER_END}")


def emit_diagram(diagram_type: str, source: str, *, title: str = "") -> None:
    """AI 코드에서 다이어그램 출력.

    Args:
        diagram_type: 다이어그램 종류 ("mermaid" 등).
        source: 다이어그램 소스 코드.
        title: 제목 (선택).

    Example::

        emit_diagram("mermaid", "graph LR\\n  매출-->영업이익-->순이익-->FCF")
    """
    spec = {
        "vizType": "diagram",
        "diagramType": diagram_type,
        "source": source,
        "title": title,
    }
    _log.info(f"{_MARKER_START}{json.dumps(spec, ensure_ascii=False)}{_MARKER_END}")


__all__ = [
    # palette
    "COLORS",
    # spec
    "VizSpec",
    # generators
    "auto_chart",
    "spec_revenue_trend",
    "spec_cashflow_waterfall",
    "spec_balance_sheet",
    "spec_profitability",
    "spec_dividend",
    "spec_insight_radar",
    "spec_ratio_sparklines",
    "spec_diff_heatmap",
    "SPEC_GENERATORS",
    # charts (Plotly)
    "line",
    "bar",
    "pie",
    "waterfall",
    "revenue",
    "cashflow",
    "dividend_chart",
    "balance_sheet_chart",
    "profitability_chart",
    # plotly
    "chart_from_spec",
    # extract
    "extract_viz_specs",
    # emit
    "emit_chart",
    "emit_diagram",
]
