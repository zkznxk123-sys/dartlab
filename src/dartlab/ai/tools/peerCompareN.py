"""PeerCompareN — N (default 5) 종목 wide-format 비교 + peer-internal percentile rank.

마스터 플랜 트랙 1 PR-2 (cryptic-discovering-kettle.md). 기존 compareCompanies max 3 한계 +
peer ranking 부재 회귀 차단. 내부 자산 재사용 — compareCompanies._companyMetrics 그대로
호출 (N 처리만 추가) + percentile rank helper 신규.

신뢰도 80 (ratio method) — 결정적 비율 계산.

graph 회귀 방지: agent.py 본체·노드 추가 0. LLM 자율 호출 도구.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref
from dartlab.core.confidence import baseScore

from .companyResolve import resolveCompanyOrNone
from .compareCompanies import _companyMetrics
from .creditBadge import getDcrBadge
from .industryContext import getIndustryBadge
from .types import ToolResult

_MAX_SLOTS = 12
_DEFAULT_METRICS = (
    "revenue",
    "operatingProfit",
    "netIncome",
    "totalAssets",
    "totalEquity",
    "totalLiabilities",
    "debtRatio",
    "roe",
)

# percentile rank 방향 — higher_is_better (높을수록 1.0 에 근접) 인지 lower_is_better 인지.
# 부채는 낮을수록 좋고, ROE 는 높을수록 좋음.
_HIGHER_IS_BETTER: set[str] = {
    "revenue",
    "operatingProfit",
    "netIncome",
    "totalAssets",
    "totalEquity",
    "roe",
}
_LOWER_IS_BETTER: set[str] = {
    "totalLiabilities",
    "debtRatio",
}


def _calcPercentileRanks(rows: list[dict[str, Any]], metric: str) -> dict[str, float]:
    """주어진 N rows 안에서 metric 별 percentile rank (0.0 ~ 1.0, 1.0 = best).

    metric 이 None / 비숫자인 row 는 제외. higher_is_better 방향 자동 적용.
    반환 dict: stockCode → rank (제외된 row 는 키 부재).
    """
    valid: list[tuple[str, float]] = []
    for r in rows:
        code = r.get("stockCode")
        v = r.get(metric)
        if not code or v is None or not isinstance(v, (int, float)):
            continue
        valid.append((str(code), float(v)))
    if not valid:
        return {}
    reverse = metric in _HIGHER_IS_BETTER  # True 면 큰 값이 best
    sorted_vals = sorted(valid, key=lambda x: x[1], reverse=reverse)
    n = len(sorted_vals)
    out: dict[str, float] = {}
    if n == 1:
        out[sorted_vals[0][0]] = 1.0
        return out
    for i, (code, _v) in enumerate(sorted_vals):
        # rank 1 = best → percentile 1.0, last → 0.0
        out[code] = round(1.0 - (i / (n - 1)), 4)
    return out


def peerCompareN(
    stockCodes: list[str] | str | None = None,
    metrics: list[str] | None = None,
) -> ToolResult:
    """N 종목 비교 + peer-internal percentile rank.

    Capabilities:
        compareCompanies max 3 한계 확장 (N ≤ 12) + peer-internal percentile rank
        (각 metric 별 0.0 ~ 1.0, 1.0 = best) 신규. higher_is_better/lower_is_better
        방향 자동 적용. 동종 업종 peer 자동 추가 옵션은 별 PR.

    Parameters
    ----------
    stockCodes : list[str] | str
        2~12 개 종목 코드. 초과 시 앞 12 개만.
    metrics : list[str] | None
        기본 8 종 — revenue, operatingProfit, netIncome, totalAssets, totalEquity,
        totalLiabilities, debtRatio, roe. 일부만 필요 시 명시.

    Returns
    -------
    ToolResult
        - data.stockCodes : list[str]
        - data.metrics : list[str]
        - data.rows : list[dict] — 각 종목 metric + percentileRanks
        - data.badges : list[dict] — dCR + industry
        - data.confidence : 80 (ratio method)
        - refs : tableRef (N × metric wide + percentile)

    Example
    -------
        PeerCompareN(stockCodes=["005930", "000660", "035420", "035720", "207940"])

    Raises
    ------
    없음 — 모든 실패 경로는 ToolResult(ok=False, error=...) 로 반환.

    Guide
    -----
        N=2 도 허용. 각 종목 _companyMetrics 호출 (Company.show 의 IS/BS 1 회씩).
        percentile rank 는 N 종목 *내부* — 외부 sector peer 자동 비교는 후속 PR.

    SeeAlso
    -------
        - compareCompanies : 기존 max 3 도구 (호환 유지)
        - industry.taxonomy.getIndustry : sector peer 자동 추가 (후속 PR)
        - DCFValuation : 단일 종목 가치평가

    Requires
    --------
        DART/EDGAR 사전 다운로드 (자동). Company.show("IS"|"BS") 가 정상 동작.

    AIContext
    ---------
        "5 개 회사 비교", "삼성 vs SK vs LG vs ...", "peer 분석" 류 질문에 본 도구
        호출. compareCompanies 대비 N 확장 + percentile rank 명시.

    LLM Specifications
    ------------------
        AntiPatterns:
            - stockCodes=[1개만] — peer 비교 의미 0, 단일 종목은 DCFValuation 사용.
            - stockCodes > 12 — 앞 12 개만 처리, 경고.
        OutputSchema:
            rows[i] = {stockCode, corpName, ...metrics, percentileRanks: {metric: 0.0~1.0}}.
        Prerequisites:
            DART/EDGAR 사전 다운로드. Company.show 정상 동작.
        Freshness:
            분기 결산 발표 후 갱신.
        Dataflow:
            stockCodes → Company × N → IS/BS show × N → _companyMetrics × N →
            _calcPercentileRanks × M metric → tableRef.
        TargetMarkets:
            KR (DART) · US (EDGAR). JP (EDINET) 미가용.
    """
    if isinstance(stockCodes, str):
        stockCodes = [stockCodes]
    codes = [str(c).strip() for c in (stockCodes or []) if str(c).strip()]
    if len(codes) < 2:
        return ToolResult(
            False,
            "stockCodes 필수 (2~12 개). 단일 종목은 DCFValuation 사용.",
            error="insufficient_stock_codes",
        )
    if len(codes) > _MAX_SLOTS:
        codes = codes[:_MAX_SLOTS]

    requested_metrics = tuple(metrics) if metrics else _DEFAULT_METRICS

    rows: list[dict[str, Any]] = []
    badges: list[dict[str, Any]] = []
    for code in codes:
        company = resolveCompanyOrNone(code)
        if company is None:
            rows.append({"stockCode": code, "corpName": None, "error": "company_not_resolved"})
            continue
        corpName = str(getattr(company, "corpName", None) or "")
        row: dict[str, Any] = {"stockCode": code, "corpName": corpName}
        row.update(_companyMetrics(company))
        rows.append(row)
        badges.append(
            {
                "stockCode": code,
                "corpName": corpName,
                "dcr": getDcrBadge(company),
                "industry": getIndustryBadge(company),
            }
        )

    # peer-internal percentile rank — 각 metric 별 0.0 ~ 1.0.
    rank_by_metric: dict[str, dict[str, float]] = {}
    for m in requested_metrics:
        rank_by_metric[m] = _calcPercentileRanks(rows, m)

    # rows 에 percentileRanks 부착
    for r in rows:
        code = r.get("stockCode")
        if not code:
            continue
        r["percentileRanks"] = {m: rank_by_metric.get(m, {}).get(str(code)) for m in requested_metrics}

    confidence = baseScore("ratio")
    payload = {
        "stockCodes": codes,
        "metrics": list(requested_metrics),
        "rows": rows,
        "badges": badges,
        "confidence": confidence,
        "confidenceMethod": "ratio",
    }
    title = f"{len(codes)} 종목 peer 비교"
    ref = Ref(
        id=f"peer:{':'.join(codes)}",
        kind="tableRef",
        title=title,
        source="peerCompareN",
        payload=payload,
    )
    return ToolResult(
        True,
        f"{len(codes)} 종목 peer 비교 + percentile rank — {', '.join(r.get('corpName') or r['stockCode'] for r in rows[:5])}",
        refs=[ref],
        data=payload,
    )


__all__ = ["peerCompareN"]
