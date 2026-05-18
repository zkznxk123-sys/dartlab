---
id: engines.viz
title: Viz (차트·다이어그램 spec)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Viz 는 분석 결과를 19 종 차트 spec (line · bar · table · radar · waterfall · heatmap · histogram · combo · sparkline · pie + DartLab 특화 차트) 으로 변환하는 시각화 엔진이다. RunPython 안에서 `emit_chart(spec)` · `emit_diagram(type, source)` 로 stdout 마커 출력 → AI 도구 결과로 인라인 렌더. 트리거 — '시각화', '차트', 'emit_chart', 'CompileVisual'.
whenToUse:
  - viz
  - 시각화
  - 차트
  - emit_chart
  - emit_diagram
  - CompileVisual
  - line / bar / radar / waterfall / heatmap
  - landing 차트 빌드
  - 시계열 시각화
  - peer 비교 차트
  - 주가차트
inputs:
  - chartType (등록 chartType 중 하나)
  - data (행 list 또는 series dict)
  - title · xAxis · yAxis
  - evidenceBinding 또는 evidenceIds (필수)
outputs:
  - ChartSpec dict (stdout 마커)
  - landing static JSON (회사 페이지)
  - visualRef (CompileVisual 도구 경로)
capabilityRefs:
  - ChartResult
toolRefs:
  - CompileVisual
  - EngineCall
  - RunPython
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.analysis
  - engines.dashboard
sourceRefs:
  - dartlab://skills/engines.viz
requiredEvidence:
  - chartType
  - tableRef
  - evidenceBinding
  - executionRef
expectedOutputs:
  - 차트 spec dict
  - 메시지 흐름 인라인 차트
  - 회사 페이지 정적 차트 manifest
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
failureModes:
  - evidenceBinding · evidenceIds 둘 다 없는 spec — emit_chart 가 거부
  - 단일값 또는 근거 없는 장식 시각화 시도
  - ChartRenderer 미등록 chartType 사용 — 등록 chartType 만 허용
  - period 없는 시계열 차트 (x 축 라벨 없음)
forbidden:
  - evidenceBinding 또는 evidenceIds 누락된 ChartSpec emit 금지.
  - DataFrame 원본 없이 추측 데이터로 차트 만들지 않는다.
  - 등록 chartType 외 임의 chartType 발급 금지 (ChartRenderer 매칭 실패).
examples:
  - 영업이익률 시계열 line chart
  - peer ROE 비교 bar chart
  - 6 막 인과 radar
  - 현금흐름 waterfall
  - peer-matrix 다축 비교
  - kpi-ribbon 스냅샷
  - balance-structure-trend 자산·조달 구조
  - price-chart 주가와 거래량
  - financial-structure 재무제표 구조 묶음
  - peer-matrix 업종 비교 행렬
  - evidence-coverage 근거 커버리지
  - kpi-ribbon 보고서 KPI 요약
  - scenario visuals 시나리오·민감도
  - cashflow waterfall 현금 bridge
  - mermaid 다이어그램
procedure:
  - RunPython 안에서 `from dartlab.viz import emit_chart, emit_diagram`.
  - DataFrame 으로 데이터 확보 후 emit_chart 호출 — chartType / title / data / evidenceBinding 키 필수 (본문 코드 예시 참조).
  - 회사 페이지 정적 빌드는 `landing/_scripts/buildCompanyCharts.py --code <stockCode>`.
  - AI tool 경로는 `CompileVisual` (registry) — 자동 evidenceBinding 묶음.
  - drill-back 은 `series[].pointRefs[i] = {period, valueRef, rcept_no?, filingUrl?}`.
linkedSkills:
  - engines.analysis
  - engines.dashboard
  - engines.viz.balanceStructureTrend
  - engines.viz.priceChart
  - engines.viz.financialStructureCharts
  - engines.viz.peerMatrix
  - engines.viz.evidenceCoverage
  - engines.viz.kpiRibbon
  - engines.viz.scenarioVisuals
  - engines.viz.cashflowWaterfall
  - engines.viz.mermaidDiagram
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-17'
---

## 엔진 역할

`viz` 는 분석 결과를 차트 spec 으로 변환한다. 직접 차트 이미지를 그리지 않고 — *spec dict* 를 만들어 (a) `emit_chart(spec)` 로 stdout 마커 출력 → AI tool result 로 인라인 렌더 또는 (b) `landing/static/charts/{code}/manifest.json` 정적 빌드 → svelte `ChartRenderer` 가 등록 chartType 단일 분기 렌더.

**evidence 회로 강제** — 모든 ChartSpec 은 `evidenceBinding` 또는 `evidenceIds` 가 채워져야 emit. drill-back 으로 차트 점 클릭 시 source 데이터 패널 진입.

## 공개 호출 방식

```python
# RunPython 안에서
from dartlab.viz import emit_chart, emit_diagram
import dartlab

c = dartlab.Company("005930")
ratios = c.show("ratios", freq="Q")

# 1. 시계열 line
emit_chart({
    "chartType": "line",
    "title": "영업이익률 추이",
    "data": [{"period": p, "value": v}
             for p, v in zip(ratios["period"], ratios["operatingMargin"])],
    "xAxis": "period",
    "yAxis": "value",
    "unit": "%",
    "evidenceBinding": {
        "tableRef": "table:005930:ratios:Q",
        "source": "dart",
        "stockCode": "005930",
        "topic": "ratios",
    },
})

# 2. peer 비교 bar
emit_chart({
    "chartType": "bar",
    "title": "peer ROE",
    "data": peer_rows,
    "xAxis": "stockCode",
    "yAxis": "roe",
    "evidenceIds": ["scan:profitability:2025Q3"],
})

# 3. 다이어그램 (mermaid)
emit_diagram("mermaid", "graph LR\n  A-->B\n  B-->C")

# 4. CompileVisual tool (AI 도구 경로 — auto evidence)
# LLM 이 자율 호출
```

```bash
# 회사 페이지 정적 차트 빌드
uv run python -X utf8 landing/_scripts/buildCompanyCharts.py --code 005930
# → landing/static/charts/005930/manifest.json + section JSON
```

## 강행 호출 룰 (agent 답변 품질 회귀 차단)

차트 시각화에서 다음 4 룰 강행:

1. **차트 생성은 `CompileVisual` tool 1 회** — chartType + data + 인자. RunPython 직접 matplotlib/plotly 호출 금지 (visualRef 미발급 → UI 렌더 실패).
2. **모든 차트의 `evidenceBinding` 필수** — 차트 안 모든 값에 ref 박힌 source 명시. evidenceBinding 누락 시 거부 (해결책 포함 경고).
3. **데이터 부족 시 차트 만들지 마라** — 표 + coverage note 로 낮춘다. 환각 차트 (X 값 없는 그래프, peer 4 개 미만 분포 등) 금지.
4. **본문 안 차트 인용에 `[visualRef:...]` 표기** — UI 가 inline 렌더링하므로 ref id 필수.

## 호출 동작

`emit_chart(spec)` — ChartSpec dict 를 stdout 에 `[VIZ_SPEC_START]...[VIZ_SPEC_END]` 마커로 출력. agent 가 `extract_viz_specs(stdout)` 로 추출 → `view_spec` TraceEvent → 클라이언트 `ChartRenderer` 가 인라인 렌더. `evidenceBinding` 또는 `evidenceIds` 누락 시 거부 (해결책 포함 경고).

`emit_diagram(type, source)` — mermaid · graphviz 같은 다이어그램 소스. 같은 마커 패턴.

CompileVisual tool (registry) — LLM 이 분석 결과를 자율적으로 차트로 elevate. `chartType` + `data` 인자 받아 visualRef 발급, agent 가 VIEW_SPEC 이벤트로 인라인.

## 등록 chartType (19 종)

| 그룹 | chartType | 용도 |
| --- | --- | --- |
| 기본 (10) | `line` `bar` `table` `radar` `waterfall` `heatmap` `histogram` `combo` `sparkline` `pie` | 시계열 · 비교 · 분포 등 표준 |
| Phase 1.5 (6) | `six-act-radar` `peer-matrix` `kpi-ribbon` `hover-spark` `evidence-coverage` `income-trend-matrix` | dartlab 특화 — 6막 인과 / peer 비교 / KPI 스냅샷 |
| Phase 1.5 (계속) | `balance-structure-trend` `cashflow-signed-matrix` | 재무구조 추이 / 현금흐름 부호 |
| Market | `price-chart` | OHLCV 주가 · 거래량 · 이동평균 · 벤치마크 |

ChartRenderer (`ui/shared/chart/ChartRenderer.svelte`) 가 등록 chartType 을 단일 분기한다. 등록 외 chartType 은 매칭 실패.

## recipe 연결 원칙

Recipe 에서 공식 `visualRefs[]` 로 연결하는 viz skill 은 `status: observed` 인 것만 쓴다. 현재 recipe 에 바로 연결 가능한 observed 표면은 다음 경로다.

| skill | 주 용도 | recipe 연결 조건 |
| --- | --- | --- |
| `engines.viz.financialStructureCharts` | IS/BS/CF 구조 묶음 | 원표 기간·연결 기준·evidenceBinding 이 모두 맞을 때 |
| `engines.viz.balanceStructureTrend` | 자산·부채·자본 추이 | `자산총계 = 부채총계 + 자본총계` 검산 가능할 때 |
| `engines.viz.cashflowWaterfall` | 현금흐름 bridge | CF 원표와 부호 convention 을 검산했을 때 |
| `engines.viz.evidenceCoverage` | coverage/blocker/falsifier 상태 | 표 ref 가 있고 coverage note 를 함께 둘 때 |
| `engines.viz.scenarioVisuals` | DCF·민감도·시나리오 | tableRef/valueRef/dateRef 로 scenario grid 를 묶을 수 있을 때 |
| `engines.viz.priceChart` | 가격·거래량 맥락 | 가격 source와 기준시각이 확인될 때 |
| `engines.viz.mermaidDiagram` | 인과·절차 diagram | 8노드 이하, 모든 edge 가 sourceRef/skillRef 근거를 가질 때 |

`engines.viz.tableBackedChart` 처럼 `unverified` 인 skill 은 공식 visualRef 가 아니라 후속 후보 또는 fallback 설명으로만 둔다. 데이터가 없거나 evidenceBinding 이 없으면 차트를 만들지 않고 표·coverage note 로 낮춘다.

## 등록 generator (23 종)

| 그룹 | 함수 | 입력 |
| --- | --- | --- |
| 8 핵심 | `spec_revenue_trend` · `spec_balance_sheet` · `spec_profitability` · `spec_cashflow_waterfall` · `spec_dividend` · `spec_insight_radar` · `spec_ratio_sparklines` · `spec_diff_heatmap` | Company 객체 |
| 6 추가 | `spec_peer_radar` · `spec_sensitivity_heatmap` · `spec_margin_trend` · `spec_leverage_trend` · `spec_growth_yoy_bar` · `spec_revenue_scenario_band` | history dict |
| 9 신규 | `spec_six_act_radar(score)` · `spec_peer_matrix(rows, metrics)` · `spec_kpi_ribbon(items)` · `spec_hover_spark(...)` · `spec_evidence_coverage(items)` · `spec_income_trend_matrix(view)` · `spec_balance_structure_trend(view)` · `spec_cashflow_signed_matrix(view)` · `specPriceChart(rows)` | view dict / raw |

`auto_chart(c)` 가 Company 입력에서 핵심 generator 일괄 실행 → ChartSpec list. `buildCompanyCharts.py` 가 landing 정적 빌드.

## evidence 회로 (필수)

모든 ChartSpec 은 다음 중 하나 필수:

```python
"evidenceBinding": {
    "tableRef": "table:005930:BS:Q",     # 표 ref
    "source": "dart",                     # provider
    "stockCode": "005930",
    "topic": "BS",                        # 또는 "ratios" · "IS" · ...
    "periodKind": "quarterly",            # 또는 "yearly" / "snapshot"
    "periods": ["2025Q3", "2025Q2", ...]
}
# 또는 legacy
"evidenceIds": ["table:005930:BS:Q", "value:005930:BS:total_assets"]
```

datapoint drill-back:

```python
"series": [{
    "name": "영업이익률",
    "data": [...],
    "pointRefs": [
        {"period": "2025Q3", "valueRef": "value:...:operating_margin",
         "rcept_no": "20251115000543", "filingUrl": "https://...", "pdfPage": 18},
        ...
    ]
}]
```

DART 정기보고서 deep-link 헬퍼: `dartlab.viz.refs.filingDeepLink(rcept_no, page=None)`. 다른 helper — `tableRef` · `valueRef` · `chartEvidenceBinding` · `seriesPointRefs`.

## 대표 반환 형태

`emit_chart` / `emit_diagram` 은 stdout 출력 — 반환 없음 (None). spec dict 가 마커 안에 직렬화돼 agent 가 추출.

`auto_chart(c)` → ChartSpec list. `dartlab.viz.refs.chartEvidenceBinding(...)` → dict.

## landing 통합

```
Python emit_chart / auto_chart / generators
        │
        ↓
landing/_scripts/buildCompanyCharts.py
        │
        ↓
landing/static/charts/{code}/manifest.json + section JSON
        │
        ↓
$lib/browser/charts.ts (loadChartManifest / loadAllChartSpecs)
        │
        ↓
<ChartRenderer spec={...} onPointClick={...} />
        │
        ↓ (drill-back)
EvidencePanel (pointRef 또는 evidenceBinding 패널)
```

## 기본 실행 순서

1. RunPython 안에서 DataFrame 또는 dict 데이터 확보.
2. `emit_chart(spec)` — chartType + data + evidenceBinding 필수.
3. AI 답변에 인라인 차트 자동 노출 (agent VIEW_SPEC 이벤트).
4. 회사 페이지 정적 차트는 `buildCompanyCharts.py` 운영자 절차.
5. drill-back 시 `pointRefs` 가 EvidencePanel 진입점.

## 기본 검증

등록 chartType · generator · evidence 회로 강제 정책이 바뀌면 본 skill + ChartRenderer 단일 진입 + buildCompanyCharts 빌드 스크립트 동시 갱신.
