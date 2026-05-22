---
id: recipes.macro.liquidityCycle
title: 매크로 유동성 사이클 (금리 + 환율 + 유동성)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 매크로 유동성 환경을 금리 + 환율 + 유동성 지표 + 위기 신호 4 축으로 종합 판정하는 절차. 종목 없이 매크로 분석 가능. 트리거 — '매크로 유동성', '금리 환율 위기 신호', '거시 사이클'.
whenToUse:
  - 매크로 유동성
  - 금리 환경
  - 환율 환경
  - 유동성 사이클
  - 매크로 종합
  - 위기 신호
  - 거시 환경
linkedSkills:
  - engines.macro
  - engines.company
  - engines.scan
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

forbidden:
  - 금리 한 변수만으로 매크로 사이클 단정 금지 — 4 축 (금리 + 환율 + 유동성 + 위기) 결합.
  - 미국 금리와 KR 금리 시차 / 디커플링 무시 금지.
  - 위기 신호 (Credit-to-GDP / Minsky) 한 지표로 위기 임박 단정 금지.
  - 매크로 사이클 결과를 자동 자산배분 결정으로 단정 금지.
failureModes:
  - 금리 (정책 vs 시장 vs 회사 조달) 별 단계 차이
  - 환율 (USDKRW vs DXY) 의 글로벌 / 양자 차이
  - 유동성 (M2 vs 본원통화) 정의 차이
  - 매크로 변수 간 상관 (금리 ↑ → 환율) 무시한 단순 인과
  - 시점 (월 / 분기) 빈도 차이로 사이클 식별 변동
examples:
  - KR 매크로 유동성 사이클 진단
  - 금리 + 환율 + 유동성 + 위기 4 축
  - 미국 vs KR 사이클 디커플링
  - 사이클 위치 + 자산 영향 (참고용)
lastUpdated: '2026-05-13'
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 공개 호출 방식

```python
import dartlab

summary = dartlab.macro()
rates = dartlab.macro("rates")
liquidity = dartlab.macro("liquidity")
crisis = dartlab.macro("crisis")
final = dartlab.macro("summary")
```

## 호출 동작

매크로 종합 → 금리 곡선 → M2/유동성 → 위기 신호 → 최종 종합 판정.

1. macro() — 매크로 환경 한 시점
2. macro("rates") — 단기/장기 금리 + 곡선 형태
3. macro("liquidity") — M2 / 본원통화 / 신용 사이클
4. macro("crisis") — VIX / 신용스프레드 / 환율 변동성
5. macro("summary") — 최종 종합 판정

## 대표 반환 형태

- `tableRef` 5 개 (각 axis 별 시계열)
- `dateRef` 1 개 (최신 관측 시점)
- 답변 본문: 매크로 단계 (확장/둔화/침체/회복) + 근거 지표

## 연계 절차

1. engines.macro — 매크로 환경 종합
2. engines.macro — 금리 곡선
3. engines.macro — 유동성 지표
4. engines.macro — 위기 신호
5. engines.macro — 최종 종합

## 기본 검증

- 사이클 위치 (확장/둔화/침체/회복) + 근거 지표 (PMI/금리곡선/VIX).
- 금리 곡선 inversion 신호 명시.
- "유동성 풍부" 단정 X — M2 증가율 + 신용 스프레드 함께.
