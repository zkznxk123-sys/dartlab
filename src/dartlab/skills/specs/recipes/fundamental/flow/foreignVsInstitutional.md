---
id: recipes.fundamental.flow.foreignVsInstitutional
title: Foreign vs Institutional Flow Divergence
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 외국인 vs 기관 순매수 divergence — 두 그룹 매매 방향 반대 + cumulative net 누적 z 정량화. 정보 비대칭 신호 (외국인 ahead 가설 학술). **status=drafted — KRX 투자자별 데이터 수집 인프라 선결**. 트리거 — '외국인 vs 기관', 'flow divergence', '투자자별 매매', '외국인 순매수'.
whenToUse:
  - 외국인 vs 기관
  - foreign vs institutional
  - flow divergence
  - 외국인 순매수
  - 기관 순매수
linkedSkills:
  - engines.flow
  - engines.scan
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - engines.viz.tableBackedChart
gap:
  primary:
    - flow
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
  asOfPolicy: latest
falsifier:
  description: 두 그룹 매매 방향 항상 일치 = signal 가치 0. historical divergence rate 30-40% expectable.
  pythonCheck: |
    assert divergence_rate >= 0.2
expectedNovelty:
  - foreignNet
  - institutionalNet
  - divergence
forbidden:
  - 외국인 매수 = 상승 신호 X (lag 큼, alpha 약).
  - 단일 시점 divergence 절대 신호 X — cumulative + z 동행.
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
import dartlab
fg = dartlab.flow("investorBalance", code="005930", group="foreign", days=30)
ins = dartlab.flow("investorBalance", code="005930", group="institutional", days=30)
divergence = (fg["cumNet"] > 0) != (ins["cumNet"] > 0)
```

## 호출 동작

종목별 외국인/기관 일별 net + 30 일 cumulative + 252 일 z. divergence flag (방향 반대).

## 대표 반환 형태

DataFrame — `date · foreignNet · institutionalNet · cumNetForeign · cumNetInst · divergenceFlag`.

## 연계 절차

1. 본 recipe → 두 그룹 divergence.
2. 외국인 매수 + 기관 매도 → 외국인 정보 우위 가설.
3. 산업 차원 결합 → `recipes.industry.sectorFlowConcentration`.
