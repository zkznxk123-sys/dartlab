"""viz 통합 스키마 — View / Series / CatalogEntry / SeriesPlan SSOT.

frontend (web · cli · jupyter · blog · mcp) 가 단일 계약으로 분기.

레이어:
- CatalogEntry / SeriesPlan: catalog dict 의 *선언적* 스펙. 모양 + 색상.
- View / Series: builder 가 만든 *실행 결과*. 데이터까지 채워진 JSON.
- EvidenceBinding / Meta: drill-back + 생성 컨텍스트.

원칙:
- 모든 key 영문 camelCase. 한국어는 `label` 한 곳.
- catalog 의 color (hex) 는 *기본값*. 소비처가 paletteOverride 로 치환 가능.
- intent 는 의미 슬롯 (Intent enum) — color 가 없을 때 또는 override 매핑 키로 사용.
- categories.length == series[i].data.length 일관 (kind="breakdown" 은 series.data 직접).
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from dartlab.viz.palette import Intent

PeriodKind = Literal["annual", "quarterly"]

ViewKind = Literal[
    "trend",  # 시계열 (line/bar) — categories=기간, series=지표
    "snapshot",  # 단일 기간 막대 — categories=항목, series 1 개
    "breakdown",  # 구성 (pie) — categories=항목, series 1 개 (data=값)
    "table",  # 표 — categories=기간, series=행
    "waterfall",  # 폭포 — categories=단계, series=값+측정종류
    "matrix",  # 2D 행렬 (heatmap) — categories=X축, series=Y축×values
    "radar",  # 레이더 — categories=축, series 1+
    # === analysis 8 탭 확장 (카드 다양성) ===
    "sankey",  # 노드·링크 flow — 매출→비용→이익
    "scatter",  # 산점·사분면 — categories=항목, series 별 (x,y) 페어
    "gauge",  # 단일 점수 + 색 띠 (Altman Z 등)
    "phaseIndicator",  # 다단계 indicator (생애주기 6 단계 + 신뢰도)
    "comparisonTable",  # peer 백분위 표 (TanStack Table, row 색 highlight)
    "diffView",  # 전년대비 변화 KPI (값+%+화살표)
    "topList",  # 상위/하위 N 항목 list + inline bar
    "kpiTile",  # 큰 숫자 + sparkline + delta
    "narrativeBridge",  # 6 막 전환 자연어 5 줄 (1→2 / 2→3 ... 5→6)
    "scoreBadge",  # 5 차원 종합 점수 + 등급 + 한 줄 서사
    "candle",  # OHLC 캔들스틱 + volume — quant 가격 카드 (lightweight-charts)
]

SeriesAxis = Literal["left", "right"]
SeriesType = Literal["bar", "line", "area"]


class SeriesPoint(TypedDict, total=False):
    """waterfall 단일 스텝."""

    value: float | None
    measure: Literal["absolute", "relative", "total"]


class SeriesPlan(TypedDict, total=False):
    """catalog 안의 시리즈 모양 + 데이터 정의 *선언*.

    builder 가 이걸 받아 norm DataFrame 에서 직접 데이터 추출 + 합성/비율/YoY
    계산. statements 함수 신설 0 — catalog 가 차트 SSOT.

    표시 필드:
        - key: 영문 식별자 (recharts dataKey, UI row key).
        - label: 표시명 (한국어).
        - color: 기본 hex. paletteOverride 미지정 시.
        - intent: 의미 슬롯 (primary/positive/negative/neutral/accent).
        - unit: "원" | "%" | "회" | "일" | "배".
        - type: bar/line/area (combo 차트).
        - axis: left/right.
        - stack: stackId — 같은 stack 의 시리즈는 합산되어 한 막대.

    데이터 정의 (아래 중 하나, 우선순위 순):
        - ratio: 비율 — {num: {accountKey: sign}, den: {accountKey: sign}, scale?: int}
                 ex: ROE = {num: {netIncome: 1}, den: {equity: 1}, scale: 100}
        - yoy: 단일 account 의 YoY (%) — ex: "revenue"
        - compose: 가산 — {accountKey: sign}
                   ex: 영업부채 = {liabilities: 1, shortDebt: -1, longDebt: -1}
        - account: 단일 표준 항목 — ex: "revenue" / "cash" / "equity"
                   accounts.py 의 STANDARD 키 또는 norm 의 표준 ID.

    셋 다 없으면 raw dict 의 key 직접 lookup (legacy statementsCall fallback).
    """

    key: str
    label: str
    color: str
    intent: Intent
    unit: str
    type: SeriesType
    axis: SeriesAxis
    stack: str
    # 데이터 정의 — 한 series 마다 하나.
    account: str
    compose: dict[str, int]
    ratio: dict[str, Any]
    yoy: str
    # 확장: analysis/* 모듈 호출 (peerBenchmark / lifeCycle / disclosureDelta 등).
    # builder 가 모듈 import + 함수 호출 + outputKey 로 결과 추출.
    analysisCall: dict[str, Any]


class Series(TypedDict, total=False):
    """builder 가 만든 *실행 결과* 시리즈. data 가 채워져 있다.

    SeriesPlan 의 모든 필드 + `data` 또는 `points` (waterfall).
    """

    key: str
    label: str
    color: str
    intent: Intent
    unit: str
    type: SeriesType
    axis: SeriesAxis
    stack: str
    data: list[float | None]
    points: list[SeriesPoint]


class EvidenceBinding(TypedDict, total=False):
    """차트 → 원본 표 drill-back 진입점.

    - source: "dart" | "edgar"
    - topic: "IS" | "BS" | "CF" | "ratios"
    - tableRef: e.g. "finance:005930:IS:annual"
    """

    source: str
    stockCode: str
    topic: str
    periodKind: PeriodKind
    periods: list[str]
    tableRef: str


class Meta(TypedDict, total=False):
    """view 생성 컨텍스트."""

    stockCode: str
    corpName: str | None
    periodKind: PeriodKind
    periods: list[str]
    generatedAt: str


class LayoutSpec(TypedDict, total=False):
    """카드 종류별 면적 권한 — 4 col grid + rowSpan."""

    colSpan: Literal[1, 2, 3, 4]
    rowSpan: Literal[1, 2, 3, 4, 5, 6]


class CatalogEntry(TypedDict, total=False):
    """catalog dict 의 단일 카드 *선언*.

    - kind: ViewKind — 차트 모양.
    - title: 카드 제목 (한국어).
    - topic: "IS"|"BS"|"CF"|"ratios" — builder 가 어떤 데이터 모듈 호출할지.
    - statementsCall: 호출할 함수명 (statements 또는 ratios 모듈의).
    - seriesPlan: 시리즈 메타 리스트. 색·intent·stack·axis SSOT.
    - options: kind 별 부가 (stacked, dual, secondaryY, refLines 등).
    - xlSpan: web grid col-span 힌트 (legacy 1/2/3 — layout 미지정 시 fallback).
    - layout: bento packing 권한 (colSpan 1~4, rowSpan 1~3). 미지정 시 kind default.
    """

    kind: ViewKind
    title: str
    topic: str
    statementsCall: str
    seriesPlan: list[SeriesPlan]
    options: dict[str, Any]
    xlSpan: Literal[1, 2, 3]
    layout: LayoutSpec
    help: str
    # 기업분석 3 탭. 옛 8 탭 (portfolio/valuation/governance/peer/lifecycle/
    # macro) 은 financial 안의 관점별 view 에 흡수.
    # quant = 가격 시계열 + 기술/팩터/리스크/예측 (재무 알파 X — financial owner).
    tab: Literal["financial", "quant", "viewer"]
    # 재무제표분석 view = 7 가지 *분석 방법론* (lens). 같은 회사를 그레이엄·
    # 린치·S&P·Sloan 같은 서로 다른 학파 시각으로 본다. 객체 분류도, 6 막
    # 쪼개기도 아님.
    # legacy 6 (performance/capitalStructure/cashflow/risk/growth/profitability)
    # 은 frontend 리다이렉트용으로 유지.
    subCategory: Literal[
        "story",  # 서사 — dartlab 6 막 인과 (사업→수익→현금→안정→배분→미래)
        "dupont",  # DuPont 분해 — ROE = 순이익률 × 자산회전 × 레버리지
        "value",  # 가치투자 — Graham·Buffett·Damodaran (PER/PBR/DCF/Owner Earnings/Moat)
        "growth",  # 성장투자 — Lynch·Fisher (매출 CAGR/PEG/세그먼트/시장점유)
        "credit",  # 신용분석 — Moody's·S&P·Altman (Z/이자보상/부채만기)
        "quality",  # 이익품질 — Beneish·Sloan·Dechow (M/발생액/CF·NI 디버전스)
        "snowflake",  # 종합 — Simply Wall St (Value·Future·Past·Health·Dividend 5 차원)
        # legacy (redirect only)
        "performance",
        "capitalStructure",
        "cashflow",
        "risk",
        "profitability",
    ]
    # 비-시계열 kind 의 데이터 소스 선언. adapter dispatch 가 이걸 보고 호출.
    # 예: {"adapter": "distressGauge"} / {"adapter": "lifeCyclePhase"} /
    #     {"adapter": "kpiFromNorm", "tilePlans": [...]}.
    dataSpec: dict[str, Any]
    # TTM 변환 무력화. True 면 quarterlyTtm 모드에서도 raw norm 사용 — 분기
    # raw 비교 (e.g. 분기-on-분기 매출 YoY) 가 의도인 카드 전용. default False
    # (= flow 시리즈 자동 TTM, stock 시리즈 pass-through, ratio 자동 분기).
    ttmOptOut: bool


class KpiTile(TypedDict, total=False):
    """단일 KPI 한 칸 — kpiTile / diffView 내부 항목.

    - sparkline: 8 분기 mini line 데이터 (카드 우측).
    - rangeMin/rangeMax: 자체 5y range (카드 하단 percentile bar).
    """

    label: str
    value: float | None
    prev: float | None
    unit: str
    intent: Literal["primary", "positive", "negative", "neutral", "accent"]
    subtitle: str
    sparkline: list[float]
    rangeMin: float | None
    rangeMax: float | None


class TopListItem(TypedDict, total=False):
    """topList 한 행."""

    label: str
    value: float | None
    unit: str
    delta: float | None
    description: str


class ComparisonRow(TypedDict, total=False):
    """comparisonTable 한 행 — 회사 vs 동종 분위."""

    label: str
    self: float | None
    peerMedian: float | None
    peerP25: float | None
    peerP75: float | None
    percentile: float | None
    unit: str
    higherIsBetter: bool


class GaugeBand(TypedDict, total=False):
    """gauge 색 띠."""

    fromValue: float
    toValue: float
    label: str
    intent: Literal["primary", "positive", "negative", "neutral", "accent"]


class SankeyNodeSpec(TypedDict, total=False):
    """sankey 차트 노드 한 개 — 이름만 보유, 인덱스로 link 참조."""

    name: str


class SankeyLinkSpec(TypedDict, total=False):
    """sankey 차트 링크 한 개 — source/target 은 nodes 리스트 인덱스."""

    source: int
    target: int
    value: float


class ScatterPointSpec(TypedDict, total=False):
    """scatter 산점도 한 점 — 회사 본인은 self=True 로 별표 표시."""

    x: float
    y: float
    label: str
    self: bool


class HeatmapCell(TypedDict, total=False):
    """heatmap 한 셀 — 행/열 label + 값 + 단위."""

    row: str
    col: str
    value: float | None
    unit: str


class View(TypedDict, total=False):
    """builder 가 만든 표준 출력. 매체별 render.* 의 입력.

    frontend ChartRenderer 가 kind 만 보고 분기. kind 별 추가 필드는 옵셔널 —
    한 TypedDict 안에 union 형태로 들고 다님 (Python 측 단순성 우선).
    """

    kind: ViewKind
    title: str
    categories: list[str]
    series: list[Series]
    evidenceBinding: EvidenceBinding
    meta: Meta
    options: dict[str, Any]
    # kind 별 추가 필드 (옵셔널) — 각 kind 가 자기 필드만 채움.
    # kpiTile · diffView
    tiles: list[KpiTile]
    periodLabel: str
    # topList
    items: list[TopListItem]
    direction: Literal["asc", "desc"]
    # comparisonTable
    rows: list[ComparisonRow]
    peerCount: int
    # gauge
    value: float | None
    minValue: float
    maxValue: float
    bands: list[GaugeBand]
    subtitle: str
    # phaseIndicator
    phases: list[str]
    current: int
    confidence: float | None
    phaseHistory: list[int]
    # sankey
    nodes: list[SankeyNodeSpec]
    links: list[SankeyLinkSpec]
    # scatter
    points: list[ScatterPointSpec]
    xLabel: str
    yLabel: str
    xUnit: str
    yUnit: str
    xRef: float | None
    yRef: float | None
    # heatmap (matrix 확장)
    cells: list[HeatmapCell]
    rowOrder: list[str]
    colOrder: list[str]
    tone: Literal["sequential", "diverging"]
    # narrativeBridge — 6 막 전환 자연어 (story view 의 인과 흐름)
    transitions: list[dict[str, str]]  # [{from: "1막", to: "2막", text: "..."}, ...]
    summaryLine: str  # 종합 한 줄
    # scoreBadge — Snowflake 5 차원 종합
    grade: str  # "A+" / "B" 등
    overallScore: float | None  # 0~100
    dimensions: list[dict[str, Any]]  # [{key, label, score(0~5), note}]
    # bento layout pass-through (renderer 가 grid 배치에 사용).
    layout: LayoutSpec


def makeBinding(
    stockCode: str,
    topic: str,
    periodKind: PeriodKind,
    periods: list[str],
    *,
    source: str = "dart",
) -> EvidenceBinding:
    """EvidenceBinding 표준 생성."""
    return {
        "source": source,
        "stockCode": str(stockCode),
        "topic": topic,
        "periodKind": periodKind,
        "periods": list(periods),
        "tableRef": f"finance:{stockCode}:{topic}:{periodKind}",
    }


def makeMeta(
    stockCode: str,
    *,
    corpName: str | None = None,
    periodKind: PeriodKind | None = None,
    periods: list[str] | None = None,
    generatedAt: str | None = None,
) -> Meta:
    """Meta 표준 생성."""
    out: Meta = {"stockCode": str(stockCode)}
    if corpName is not None:
        out["corpName"] = corpName
    if periodKind is not None:
        out["periodKind"] = periodKind
    if periods is not None:
        out["periods"] = list(periods)
    if generatedAt is not None:
        out["generatedAt"] = generatedAt
    return out


__all__ = [
    "CatalogEntry",
    "EvidenceBinding",
    "Intent",
    "LayoutSpec",
    "Meta",
    "PeriodKind",
    "Series",
    "SeriesAxis",
    "SeriesPlan",
    "SeriesPoint",
    "SeriesType",
    "View",
    "ViewKind",
    "makeBinding",
    "makeMeta",
]
