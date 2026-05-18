---
id: recipes.screen.industryDeepDive
title: 산업 deep-dive (산업 지도 + 섹터 매크로 + 핵심 종목)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 단일 산업의 가치 사슬 + 매크로 영향 + 핵심 종목 3 축으로 산업 자체를 분석하는 절차. 종목 없이도 가능. 트리거 — '산업 깊이 분석', '가치 사슬', '핵심 종목', '업종 분석'.
whenToUse:
  - 산업 분석
  - 업종 분석
  - 가치 사슬
  - 산업 구조
  - 산업 deep dive
  - 섹터 분석
  - 산업 지도
linkedSkills:
  - engines.industry
  - engines.macro
  - engines.scan
  - engines.analysis
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
visualRefs:
  - "engines.viz.peerMatrix"
  - "engines.viz.tableBackedChart"
  - "engines.viz.priceChart"
visualGuidance:
  - "동종 비교는 engines.viz.peerMatrix를 사용하고 universe·peerCount·metric 결손률을 답변에 함께 노출한다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "가격·수급 반응은 engines.viz.priceChart로만 그리며 OHLCV 기간·벤치마크·latestAsOf가 맞지 않으면 본문 차트로 쓰지 않는다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 industry stage 단일 호출만
forbidden:
  - 가치 사슬 (upstream / midstream / downstream) 명시 없이 산업 단정 금지.
  - 핵심 종목 5 미만 sample size 로 산업 평균 단정 금지.
  - 매크로 영향 (산업 elasticity) 가정 없이 산업 영향 단정 금지.
  - 단일 stage (예 — upstream 만) 결과로 전체 산업 결론 금지.
failureModes:
  - 가치 사슬 stage 정의 (KRX 산업 분류 vs 사업) 차이"
  - 산업 sub-segment (반도체 메모리 vs 비메모리) 무시한 단일 평균
  - 산업 전체와 KRX 시장 평균 비교 시 size weight 영향
  - 산업 매크로 elasticity 의 시점 / 윈도우 차이"
  - 신규 / 폐업 종목의 industry 매핑 시점 차이
examples:
  - 반도체 산업 deep dive
  - 자동차 가치 사슬 + 핵심 종목
  - 산업 매크로 영향 + peer 횡단
  - 단계별 (upstream / downstream) 비교
gap:
  primary:
    - industry
    - macro
  secondary:
    - scan
    - analysis
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab

industry_map = dartlab.industry("반도체")
upstream = dartlab.industry("반도체", "upstream")
macro = dartlab.macro()
peer_scan = dartlab.scan("profitability")
```

## 호출 동작

산업 가치 사슬 (upstream → midstream → downstream) → 매크로 영향 → peer 횡단 수익성 종합. 종목 없이 산업 자체 분석.

1. industry(industry_name) — 산업 가치 사슬 지도
2. industry(industry_name, stage) — 단계별 종목 (upstream/midstream/downstream)
3. macro() — 매크로 환경 (산업 영향 변수)
4. scan("profitability") — peer 횡단 수익성

## 대표 반환 형태

- `tableRef` 4 개 (industry 지도 + stage 종목 + macro + peer scan)
- `dateRef` 1 개

## 연계 절차

1. engines.industry — 산업 가치 사슬 + stage 별 종목
2. engines.macro — 매크로 환경
3. engines.scan — peer 횡단 수익성
4. engines.analysis — 핵심 종목 비교

## 기본 검증

- 가치 사슬 (upstream/midstream/downstream) 명시.
- 핵심 종목 5~10 (각 stage 별).
- 매크로 영향은 산업 elasticity (예: 반도체 → 환율 / 수요 사이클).
