---
id: recipes.macro.sectorRotation
title: 섹터 로테이션 분석 (매크로 + scan + industry)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 매크로 사이클 위치 + 섹터 횡단 스캔 + 산업 위치 3 축으로 섹터 로테이션 후보를 평가하는 절차. 종목 없이도 가능. 트리거 — '섹터 로테이션', '업종 순환', '경기 사이클별 섹터'.
whenToUse:
  - 섹터 로테이션
  - 어떤 섹터가 좋아
  - 매크로 사이클 섹터
  - 산업 위치
  - 섹터 비교
  - 업종 분석
  - 사이클별 유망 섹터
linkedSkills:
  - engines.macro
  - engines.scan
  - engines.company
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
  - 매크로 사이클 (확장 / 둔화 / 수축) 단계 명시 없이 섹터 단정 금지.
  - 사이클별 유망 섹터 (확장 → 경기민감 / 둔화 → 방어주) 단순 적용 금지 — KR 시장 reproducibility.
  - 섹터 횡단 스캔 결과 평균만 보고 섹터 단정 금지 — 분포 (편차) 동반.
  - 단일 매크로 변수 (금리만) 기반 섹터 결정 금지 — 4 축 (cycle / 금리 / 환율 / 위기) 결합.
failureModes:
  - 사이클 phase 식별의 시점 (확장 / 둔화 경계) 모호
  - KRX 산업 분류와 실제 섹터 동질성 차이
  - 섹터 평균과 시총가중 (대형주 편향) 차이
  - 외국 시장 (미국 sector rotation) 결과를 KR 에 동일 적용
  - 사이클 식별 lag (3M / 6M) 무시한 즉시 결정"
examples:
  - KR 매크로 사이클 + 섹터 후보
  - 사이클 phase + 섹터 횡단 스캔
  - 미국 sector rotation 적합성 검증
  - 섹터 + 산업 sub-segment 분리
gap:
  primary:
    - macro
    - scan
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

macro_summary = dartlab.macro()
cycle = dartlab.macro("cycle")
profit_scan = dartlab.scan("profitability")
growth_scan = dartlab.scan("growth")
```

## 호출 동작

매크로 환경 종합 → 경기 사이클 위치 (확장/둔화/침체/회복) → 섹터별 수익성·성장성 횡단 → 사이클 위치 적합 섹터 후보. 종목 없이 매크로·섹터 분석 가능.

1. macro() — 금리·환율·경기 사이클 종합 한 시점
2. macro("cycle") — 경기 사이클 위치 + 시계열
3. scan("profitability") — 섹터 횡단 수익성 (상위 10~20)
4. scan("growth") — 섹터 횡단 성장성 (상위 10~20)
5. 결합: 사이클 위치 → 적합 섹터 그룹 (예: 회복기 → 산업재·소재, 침체기 → 필수소비재·헬스케어)

## 대표 반환 형태

- `tableRef` 4 개 (macro snapshot + cycle 시계열 + profitability scan + growth scan)
- `dateRef` 1 개 (분석 기준 시점)
- 답변 본문 markdown evidence table — 사이클 위치 + 섹터 후보 5~10 행

## 연계 절차

1. engines.macro — 매크로 환경 종합
2. engines.macro — 경기 사이클 위치
3. engines.scan — 섹터 횡단 수익성
4. engines.scan — 섹터 횡단 성장성

## 기본 검증

- 사이클 위치 (확장/둔화/침체/회복) 명시 + 근거 지표 (PMI / GDP / 금리 곡선).
- 섹터 후보 추천 시 historic 평균 수익률 함께 (사이클별).
- "이 사이클 = 이 섹터" 단정 X — 가정 + 시나리오.
