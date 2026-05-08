---
id: "engines.quant.bab"
title: "Quant - BAB 저베타"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 BAB 저베타 축 응용 — Frazzini-Pedersen 2014 — 252일 beta 저베타 랭킹 + 60일 realized vol 보조."
whenToUse:
  - "quant"
  - "bab"
  - "BAB 저베타"
  - "Frazzini-Pedersen 2014 — 252일 beta 저베타 랭킹 + 60일 realized vol 보조"
inputs:
  - "종목코드 또는 종목 리스트"
  - "기준 기간"
  - "benchmark / 가정 (해당 시)"
outputs:
  - "축별 dict 또는 DataFrame"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "quant"
  - "Company.quant"
knowledgeRefs:
  - "engines.quant"
  - "engines.gather"
  - "engines.analysis"
sourceRefs:
  - "dartlab://skills/engines.quant.bab"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "benchmark"
  - "valueRef"
  - "dateRef"
  - "executionRef"
expectedOutputs:
  - "공개 호출"
  - "대표 반환 형태"
  - "검증 결과"
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
forbidden:
  - "성과 보장 표현 금지."
  - "기간 / benchmark / 가정 명시 없이 수익률 인용 금지."
  - "정량 신호를 인과 분석 결론으로 제시 금지."
  - "BAB (Betting Against Beta) 의 레버리지 가정 미명시로 수익률 인용 금지."
  - "252 일 beta 가 미래 beta 와 일치한다고 가정 금지."
failureModes:
  - "beta 추정 윈도우 (60D / 252D / 750D) 별 결과 차이 무시"
  - "산업 / 시총별 정상 beta 분포 차이 무시"
  - "낮은 beta 종목의 size / liquidity 편향"
  - "BAB 의 long/short 양방향 거래비용 미반영"
  - "60 일 realized vol 보조 지표의 수렴 속도 차이"
examples:
  - "KR 시장 BAB 저베타 랭킹"
  - "저베타 + 저변동성 결합"
  - "KOSPI200 내 BAB 적용"
  - "BAB 의 leverage 가정 명시"
linkedSkills:
  - engines.quant
  - engines.quant.beta
  - engines.quant.factor
  - engines.quant.style
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 BAB 저베타 축 응용 skill — Frazzini-Pedersen 2014 — 252일 beta 저베타 랭킹 + 60일 realized vol 보조. risk 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출 (횡단면 / 시장 레벨 — 종목 불필요)
result = dartlab.quant("bab")

# 2. accessor 호출 (동등)
result = dartlab.quant.bab()
```

## 호출 동작

전종목 universe 의 가격 · 재무 · 시계열 snapshot 을 읽어 BAB 저베타 축 계산을 수행한다. Frazzini-Pedersen 2014 — 252일 beta 저베타 랭킹 + 60일 realized vol 보조. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['bab'].fn` 함수 docstring 참조.

## 대표 반환 형태

risk 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['bab'].fn` 함수 docstring 검산)
- `flags` / `assumptions`: 결손 · 가정

전체 키는 base SKILL `engines.quant` 표 + 함수 docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 종목 리스트), 기준일, benchmark 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` / 결손 종목 / `flags` / `assumptions` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 narrative 조립은 `engines.story` 또는 상위 recipe 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`) + 함수 docstring.
