---
id: recipes.valuation.bandTrack
title: valuation band 추적 (역사 평균 ±σ vs 현재가)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 회사 valuation multiple (PER/PBR/EV/EBITDA) 의 역사 평균 ±σ 밴드 안 현재 위치를 추적하는 절차. 단순 스냅샷이 아닌 시계열 추적. 트리거 — '밸류에이션 band 추적', '시계열 valuation', '멀티플 변천'.
whenToUse:
  - valuation 밴드
  - PER 밴드
  - PBR 밴드
  - 역사 평균 비교
  - valuation 추적
  - 현재가 적정 여부
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.valuationBand
  - engines.quant
  - engines.scan
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.priceChart"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
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
      - browser 안에서는 historic 시계열 일부 한정
forbidden:
  - valuation band 의 역사 평균 윈도우 (3Y vs 10Y) 명시 없이 위치 단정 금지.
  - 단일 multiple (PER 만) 결과로 valuation 단정 금지 — 다지표 결합.
  - 시장 환경 변화 (금리 / 유동성) 미반영한 역사 mean 비교 금지.
  - band ±σ 위치만으로 매수 / 매도 자동 단정 금지.
failureModes:
  - 역사 평균 윈도우 시작점 (코로나 / 금융위기 포함 여부) 의 영향
  - 분기 vs 연간 multiple 빈도 차이로 변동성 차이"
  - mean reversion 가정의 KR 시장 적합성 차이"
  - 산업 구조 변화 (사업 전환) 시 mean 의미 변동
  - peer band 와 회사 band 의 산업 동질성 차이
examples:
  - 삼성전자 PER 5Y band
  - PBR + EV/EBITDA + ±σ 위치
  - 시장 환경 + band 결합
  - 회사 band + peer band 비교
gap:
  primary:
    - analysis
    - quant
  secondary:
    - scan
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

band = c.analysis("financial", "밸류에이션밴드")
qval = c.quant("가치")
peer_band = dartlab.scan("valuation")
```

## 호출 동작

회사 valuation multiple 시계열 → 역사 평균 + σ → 현재 위치 (- 1σ / 평균 / + 1σ 등) → peer 횡단 비교.

1. 회사 진입
2. analysis("financial", "밸류에이션밴드") — 시계열 + 역사 평균 ±σ
3. quant("가치") — 기술적 가치 신호 (역사 평균 대비)
4. scan("valuation") — peer 횡단 멀티플

## 대표 반환 형태

- `tableRef` 3 개 (band 시계열 + qvalue + peer)
- `valueRef` 4+ (현재 PER / 5 년 평균 / σ 위치 / peer median)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.valuationBand — 역사 ±σ 밴드
3. engines.quant — 기술적 가치 신호
4. engines.scan — peer 횡단

## 기본 검증

- 시계열 N 년 (3/5/10) 명시.
- "현재 저평가" 단정 X — σ 위치 + 가정 (역사 평균 = 적정 여부) 함께.
- peer median 과 함께 — 단일 회사 시계열 만으로는 부족.
