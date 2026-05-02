---
id: engines.macroUsage
title: macro 엔진 거시 환경 사용 지도
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 금리, 환율, 경기, 유동성 환경을 macro로 해석하고 기업/섹터 분석에 연결하는 절차를 설명한다.
whenToUse:
  - 금리, 환율, 경기, 유동성, 침체확률이 분석에 필요한 때
  - 기업 분석 전에 시장 환경을 먼저 고정해야 할 때
  - top-down 논제를 scan, analysis, credit로 이어갈 때
capabilityRefs:
  - macro
  - gather
  - scan
  - analysis
  - credit
toolRefs:
  - search_reference
  - run_python
datasetRefs:
  - macro.raw
requiredEvidence:
  - asOf
  - metric
  - period
  - value
  - direction
expectedOutputs:
  - macro regime evidence
  - top-down implication map
  - company or sector follow-up plan
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
    notes:
      - Web AI는 snapshot과 public macro provider 접근 가능성에 따른다.
  pyodide:
    status: limited
    limitations:
      - 실시간 FRED/ECOS 접근과 장기 시계열은 서버 경유가 필요할 수 있다.
failureModes:
  - macro raw data와 macro 해석 결과 혼동
  - asOf 없이 현재 거시 환경이라고 단정
  - 거시 결론을 개별 기업 결론으로 바로 치환
forbidden:
  - API parameters/returns를 SkillSpec에 중복하지 않는다.
  - 거시 방향성만으로 종목 매수/매도 결론을 내지 않는다.
examples:
  - 금리 상승 국면은 macro rates/cycle을 보고 scan 업종 비교, analysis 안정성/현금흐름으로 이어간다.
  - 환율 민감도 질문은 macro FX 방향성과 기업 매출/비용 노출을 분리한다.
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 가능한 분석

- macro를 쓰면 기업 숫자를 경기, 금리, 유동성, 환율 환경 안에 배치할 수 있다.
- macro 단독은 시장 환경 설명이고, 투자 논제는 scan/analysis/credit과 조합해야 한다.

## 절차

- `basic.macro`와 `macro` capability에서 시장, axis, asOf 기준을 확인한다.
- 질문의 거시 축을 cycle/rates/liquidity/trade/fx/sentiment 중 하나 이상으로 분해한다.
- asOf와 지표 방향성을 evidence로 남긴다.
- 기업/섹터 질문이면 macro → scan → analysis/credit 순서로 연결한다.
- 최종 답변에는 거시 환경과 기업 고유 요인을 분리해 쓴다.
