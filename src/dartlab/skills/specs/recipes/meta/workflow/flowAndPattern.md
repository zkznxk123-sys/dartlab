---
id: recipes.meta.workflow.flowAndPattern
title: 수급·패턴 결합 (외인/기관 flow + 차트 패턴 + 모멘텀)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 단일 종목의 수급 (외인/기관 매매) + 차트 패턴 + 모멘텀 신호를 결합해 단기 entry/exit 보조 신호를 만드는 절차. 트리거 — '수급', '외인 기관 매매', '차트 패턴', '단기 entry/exit'.
whenToUse:
  - 수급 분석
  - 외인 기관 매매
  - flow analysis
  - 차트 패턴 모멘텀
  - 단기 매매 신호
  - 수급 패턴
linkedSkills:
  - engines.company
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
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.priceChart"
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "가격·수급 반응은 engines.viz.priceChart로만 그리며 OHLCV 기간·벤치마크·latestAsOf가 맞지 않으면 본문 차트로 쓰지 않는다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."

forbidden:
  - 수급 한 방향 (외인 매수) 단일 신호로 매수 단정 금지 — 패턴 / 모멘텀 동반.
  - 단기 entry / exit 신호를 장기 투자 추천으로 오인 금지.
  - 수급 데이터 (외인 / 기관) 의 보고 시점 (T+1) 명시 없이 실시간으로 인용 금지.
  - 단일 종목 수급 결과를 시장 전체 추세로 단정 금지.
failureModes:
  - 프로그램 매매 / 차익거래 / 자기자본 매매 분리 누락
  - 외국인 비중 변화의 인덱스 리밸런싱 영향 미반영
  - 차트 패턴의 false positive (사후 매칭) 위험
  - 모멘텀 신호의 short-term reversal 효과 무시
  - 단기 수급 + 장기 fundamental 혼동
examples:
  - 삼성전자 수급 + 패턴 + 모멘텀
  - 단기 entry 보조 신호
  - 수급 + 차트 패턴 결합
  - 외인 매수 + 모멘텀 결합
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

1. engines.company — 회사 진입 (KR 만)
2. engines.quant — 패턴
3. engines.quant — 모멘텀
4. engines.quant — 가격·거래량 결합

## 기본 검증

- KR 전용 — US ticker 에는 flow 데이터 없음 명시.
- "매수 신호" 단정 X — 신호 + 신뢰 구간 + 상충 신호 함께.
- 펀더멘털과 분리 — 단기 보조 신호로만.
