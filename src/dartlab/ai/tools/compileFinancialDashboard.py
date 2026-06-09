"""CompileFinancialDashboard — 종목 한 화면 dashboard (3 template).

마스터 플랜 트랙 1 PR-3 (cryptic-discovering-kettle.md). 단일 종목의 핵심 KPI +
시계열 차트를 template 별로 한 도구 호출로 답변. companyMetrics + compileVisual
+ RunPython 다단 우회 회귀 차단.

template 3 종:
- growth : 매출/영업이익/순이익 3Y CAGR + 영업현금흐름 추세
- value  : ROE/ROIC/PER/PBR/PSR (밸류) + FCF yield
- credit : 부채비율/이자보상/유동비율/현금흐름 (신용)

신뢰도 80 (ratio method) — 결정적 비율 계산.

graph 회귀 방지: agent.py 본체·노드 추가 0. LLM 자율 호출 도구.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref
from dartlab.core.confidence import baseScore

from .companyMetrics import companyMetrics
from .companyResolve import resolveCompanyOrNone
from .creditBadge import getDcrBadge
from .industryContext import getIndustryBadge
from .types import ToolResult

_TEMPLATE_METRIC_SETS: dict[str, tuple[str, ...]] = {
    "growth": ("revenue", "operatingProfit", "netIncome"),
    "value": ("revenue", "netIncome", "totalEquity", "roe"),
    "credit": ("totalAssets", "totalLiabilities", "totalEquity", "debtRatio"),
}

_TEMPLATE_LABELS: dict[str, str] = {
    "growth": "성장성 dashboard",
    "value": "가치평가 dashboard",
    "credit": "신용/안정성 dashboard",
}


def _buildDashboardSpec(template: str, corpName: str, stockCode: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """template 별 chartSpec (compileVisual 호환) 생성.

    spec 양식:
        {
            chartType: 'bar' | 'line' | 'table',
            title: str,
            data: [{label: ..., value: ...}, ...],
        }
    실제 viz pipeline (PR-3 후속) 이 spec 을 받아 React chart 변환. 본 PR 은 spec
    구조만 박음 (CompileVisual 도구의 기존 11 chartType 호환).
    """
    metric_keys = _TEMPLATE_METRIC_SETS.get(template, _TEMPLATE_METRIC_SETS["growth"])
    data_points: list[dict[str, Any]] = []
    for key in metric_keys:
        v = metrics.get(key)
        if v is None:
            continue
        data_points.append({"label": key, "value": v})
    return {
        "chartType": "bar",
        "title": f"{corpName or stockCode} {_TEMPLATE_LABELS.get(template, template)}",
        "data": data_points,
        "stockCode": stockCode,
        "template": template,
    }


def compileFinancialDashboard(
    stockCode: str = "",
    template: str = "growth",
    periods: int = 8,
) -> ToolResult:
    """종목 한 화면 dashboard — growth/value/credit 3 template.

    Capabilities:
        Company.panel 의 IS/BS 데이터 + ratio 계산 → template 별 dashboard spec
        + ref. companyMetrics.companyMetrics 재사용 (단일 종목 path).

    Parameters
    ----------
    stockCode : str
        6 자리 KR 또는 US ticker. 필수.
    template : str
        'growth' / 'value' / 'credit'. 기본 'growth'. 외 값은 'growth' fallback.
    periods : int
        시계열 기간 (분기/연 수). 기본 8. 정보성 — 본 PR 은 최신 1 기간만 spec 박음.

    Returns
    -------
    ToolResult
        - data.template : str
        - data.metrics : dict (template 별 metric set)
        - data.spec : dict (chartSpec)
        - data.confidence : 80 (ratio method)
        - refs : visualRef (dashboard spec) + tableRef (metrics)

    Example
    -------
        CompileFinancialDashboard(stockCode="005930", template="growth")
        CompileFinancialDashboard(stockCode="AAPL", template="credit", periods=12)

    Raises
    ------
    없음 — 모든 실패 ToolResult(ok=False, error=...).

    Guide
    -----
        template 3 종 — growth/value/credit. 후속 PR 에서 viz/catalog/finance 의
        풀 chart catalog (assetComposition/marginTrend 등) 활용 확장.

    SeeAlso
    -------
        - companyMetrics.companyMetrics : 본 도구가 재사용
        - CompileVisual : 기존 11 chartType 본체 (본 도구는 spec 구조만 박음)
        - viz/catalog/finance.py : 후속 PR 확장 catalog SSOT

    Requires
    --------
        DART/EDGAR 사전 다운로드.

    AIContext
    ---------
        "삼성전자 대시보드", "한 화면 요약", "성장성 차트", "가치평가 패널" 류 질문에
        본 도구 호출. template 사용자 명시 시 그대로, 없으면 'growth'.

    LLM Specifications
    ------------------
        AntiPatterns:
            - template='invalid' — 'growth' fallback.
            - periods > 20 — 정보성 cap 없음 (spec 본문에 reflect 안 됨).
        OutputSchema:
            spec = {chartType, title, data, stockCode, template}.
        Prerequisites:
            DART/EDGAR 사전 다운로드.
        Freshness:
            분기 결산 발표 후.
        Dataflow:
            stockCode → Company → IS/BS show → companyMetrics → template 별
            metric subset → spec + visualRef.
        TargetMarkets:
            KR (DART) · US (EDGAR).
    """
    if not stockCode:
        return ToolResult(False, "stockCode 필수.", error="missing_stock_code")

    if template not in _TEMPLATE_METRIC_SETS:
        template = "growth"

    company = resolveCompanyOrNone(stockCode)
    if company is None:
        return ToolResult(False, f"company_not_resolved: {stockCode}", error="company_not_resolved")

    corpName = str(getattr(company, "corpName", None) or "")
    metrics = companyMetrics(company)
    spec = _buildDashboardSpec(template, corpName, stockCode, metrics)

    confidence = baseScore("ratio")
    payload: dict[str, Any] = {
        "stockCode": stockCode,
        "corpName": corpName,
        "template": template,
        "periods": periods,
        "metrics": metrics,
        "spec": spec,
        "badges": {
            "dcr": getDcrBadge(company),
            "industry": getIndustryBadge(company),
        },
        "confidence": confidence,
        "confidenceMethod": "ratio",
    }

    refs: list[Ref] = [
        Ref(
            id=f"dashboard:{stockCode}:{template}:spec",
            kind="visualRef",
            title=f"{corpName or stockCode} {_TEMPLATE_LABELS.get(template, template)}",
            source="compileFinancialDashboard",
            payload={"spec": spec, "template": template, "stockCode": stockCode, "confidence": confidence},
        ),
        Ref(
            id=f"dashboard:{stockCode}:{template}:metrics",
            kind="tableRef",
            title=f"{corpName or stockCode} {template} metrics",
            source="compileFinancialDashboard",
            payload=payload,
        ),
    ]

    return ToolResult(
        True,
        f"{corpName or stockCode} {_TEMPLATE_LABELS.get(template, template)} (template={template}, metric={len([v for v in metrics.values() if v is not None])} 종)",
        refs=refs,
        data=payload,
    )


__all__ = ["compileFinancialDashboard"]
