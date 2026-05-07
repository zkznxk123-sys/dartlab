---
id: engines.viz
title: Viz
kind: curated
scope: builtin
status: observed
category: engines
purpose: Viz 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다. 트리거 — '시각화', '차트', '표 시각화', 'compile_visual'.
whenToUse:
  - Viz
  - viz
  - Appendix. Visual Explanation Engine
  - 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다
  - 2. VizSpec 프로토콜 — 이 구조로 넘긴다
  - 3. AI → 차트 파이프라인 — stdout 마커로 전달한다
  - 4. Company → ChartSpec 자동 생성기 22 종 (8 + 6 + 8)
  - 5. landing/company SSOT — 정적 ChartSpec JSON dump → ChartRenderer 단일 렌더
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - ChartResult
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.viz
procedure:
  - Appendix. Visual Explanation Engine 기준을 확인한다.
  - 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다 기준을 확인한다.
  - 2. VizSpec 프로토콜 — 이 구조로 넘긴다 기준을 확인한다.
  - 3. AI → 차트 파이프라인 — stdout 마커로 전달한다 기준을 확인한다.
  - 4. Company → ChartSpec 자동 생성기 22 종 (8 핵심 + 6 추가 + 8 신규).
  - 5. landing/company 정적 빌드 — `scripts/build/buildCompanyCharts.py --code <stockCode>` → `landing/static/charts/{code}/manifest.json` + section JSON.
  - '`emit_chart(spec)` — ChartSpec dict 를 stdout 마커로 출력. evidenceBinding 또는 evidenceIds 필수.'
  - '`emit_diagram(type, source)` — 다이어그램 소스를 stdout 마커로 출력.'
  - '`extract_viz_specs(stdout)` — 마커 추출 + 텍스트 정제.'
  - '`AnalysisEvent("chart", {"charts": [spec]})` — SSE 로 전달.'
  - '`tableRef(source, topic, periodKind)` / `valueRef(...)` / `chartEvidenceBinding(...)` / `seriesPointRefs(...)` — refs.py 의 evidence helper.'
  - '`filingDeepLink(rcept_no, page=None)` — DART 정기보고서 원문 URL.'
requiredEvidence:
  - skillRef
expectedOutputs:
  - 작업 경로
  - 확인한 근거
  - 검증 결과
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
    notes:
      - 실제 실행 가능 여부는 연결된 capability와 데이터 snapshot 범위를 따른다.
failureModes:
  - Skill OS 검색 없이 과거 문서 경로를 직접 찾음
  - API schema를 skill 본문에 중복해 docstring/capability와 어긋남
  - 검증 게이트 없이 변경 또는 답변을 완료 처리함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
examples:
  - Viz 규칙 확인
  - viz 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: viz
  format: markdown
lastUpdated: '2026-05-07'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- Appendix. Visual Explanation Engine 기준을 확인한다.
- 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다 기준을 확인한다.
- 2. VizSpec 프로토콜 — 이 구조로 넘긴다 기준을 확인한다.
- 3. AI → 차트 파이프라인 — stdout 마커로 전달한다 기준을 확인한다.
- 4. Company → ChartSpec 자동 생성기 22 종 (8 핵심 + 6 추가 + 8 신규) 기준을 확인한다.
- 5. landing/company 정적 빌드 → `scripts/build/buildCompanyCharts.py` → `landing/static/charts/{code}/`.
- `emit_chart(spec)` — ChartSpec dict 를 stdout 마커로 출력. evidenceBinding 또는 evidenceIds 누락 시 거부.
- `emit_diagram(type, source)` — 다이어그램 소스를 stdout 마커로 출력.
- `extract_viz_specs(stdout)` — 마커 추출 + 텍스트 정제.
- `AnalysisEvent("chart", {"charts": [spec]})` — SSE 로 전달.

## 등록 chartType (16 종)

- 기존 8 종: `combo` · `bar` · `line` · `radar` · `waterfall` · `heatmap` · `sparkline` · `pie`.
- 신규 8 종 (Phase 1.5): `six-act-radar` · `peer-matrix` · `kpi-ribbon` · `hover-spark` · `evidence-coverage` · `income-trend-matrix` · `balance-structure-trend` · `cashflow-signed-matrix`.

## 등록 generator (22 종)

- 8 핵심 — `spec_revenue_trend` · `spec_balance_sheet` · `spec_profitability` · `spec_cashflow_waterfall` · `spec_dividend` · `spec_insight_radar` · `spec_ratio_sparklines` · `spec_diff_heatmap`. (Company 입력)
- 6 추가 — `spec_peer_radar` · `spec_sensitivity_heatmap` · `spec_margin_trend` · `spec_leverage_trend` · `spec_growth_yoy_bar` · `spec_revenue_scenario_band`. (history dict 입력)
- 8 신규 — `spec_six_act_radar(score)` · `spec_peer_matrix(rows, metrics)` · `spec_kpi_ribbon(items)` · `spec_hover_spark(...)` · `spec_evidence_coverage(items)` · `spec_income_trend_matrix(view)` · `spec_balance_structure_trend(view)` · `spec_cashflow_signed_matrix(view)`. (view dict 또는 raw 입력)

## evidence 회로 (필수)

- 모든 ChartSpec 은 `evidenceBinding: {tableRef, source, stockCode, topic, periodKind?, periods?}` 또는 legacy `evidenceIds: [...]` 가 채워져야 한다.
- 둘 다 비면 `emit_chart` 가 거부 (해결책 포함 경고).
- datapoint 단위 drill-back 은 `series[].pointRefs[i] = {period, valueRef, rcept_no?, filingUrl?, pdfPage?}`.
- DART 정기보고서 deep-link: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}` (+ `#page={n}`).
- helper: `dartlab.viz.refs` 의 `tableRef` · `valueRef` · `filingDeepLink` · `chartEvidenceBinding` · `seriesPointRefs`.

## landing 통합

- 단일 svelte 렌더러: `ui/shared/chart/ChartRenderer.svelte` (alias `$chart/ChartRenderer.svelte`). 16 종 chartType 모두 분기.
- 데이터 흐름: Python `auto_chart(c)` + 신규 generator → `scripts/build/buildCompanyCharts.py` → `landing/static/charts/{code}/manifest.json` + section JSON → svelte `loadChartManifest` / `loadAllChartSpecs` (`$lib/browser/charts.ts`) → `<ChartRenderer spec={...} onPointClick={...} />`.
- drill-back: `onPointClick(ref)` 콜백이 `pointRef` 또는 `evidenceBinding` 를 받아 EvidencePanel 진입.

## 공개 호출 방식

- `result = c.analysis("financial", "수익성")`
- `chart = result.chart() 또는 dartlab.viz.tableBackedChart(table)`

## 호출 동작

- 표에서 파생 가능한 차트만 만든다. 단일값/근거 없는 장식 시각화는 만들지 않는다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- ChartResult 또는 visual spec dict를 반환한다. 핵심 키는 data/tableRef, marks, x, y, unit, title, warnings, evidenceBinding 다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.



