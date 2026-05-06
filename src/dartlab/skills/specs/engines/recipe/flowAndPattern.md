---
id: engines.recipe.flowAndPattern
title: 수급·패턴 결합 (외인/기관 flow + 차트 패턴 + 모멘텀)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 단일 종목의 수급 (외인/기관 매매) + 차트 패턴 + 모멘텀 신호를 결합해 단기 entry/exit 보조 신호를 만드는 절차.
whenToUse:
  - 수급 분석
  - 외인 기관 매매
  - flow analysis
  - 차트 패턴 모멘텀
  - 단기 매매 신호
  - 수급 패턴
linkedSkills:
  - engines.company.researchStarter
  - engines.quant.chartPatterns
  - engines.quant.momentum
  - engines.quant.flow
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 flow KR 전용
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

flow = c.gather("flow")  # 외인/기관 수급
patterns = c.quant("패턴")
momentum = c.quant("모멘텀")
qflow = c.quant("플로우")
```

## 호출 동작

외인/기관 수급 + 차트 패턴 + 모멘텀 + quant flow 결합. KR 종목만.

1. 회사 진입
2. gather("flow") — 외인/기관 일별 순매수
3. quant("패턴") — 차트 패턴
4. quant("모멘텀") — 단/중/장기 모멘텀
5. quant("플로우") — 가격·거래량 결합 신호

## 대표 반환 형태

- `tableRef` 3 개 (flow / patterns / momentum)
- `valueRef` 4+ (외인 누적 / 기관 누적 / 패턴 신호 / 모멘텀)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입 (KR 만)
2. engines.quant.chartPatterns — 패턴
3. engines.quant.momentum — 모멘텀
4. engines.quant.flow — 가격·거래량 결합

## 기본 검증

- KR 전용 — US ticker 에는 flow 데이터 없음 명시.
- "매수 신호" 단정 X — 신호 + 신뢰 구간 + 상충 신호 함께.
- 펀더멘털과 분리 — 단기 보조 신호로만.
