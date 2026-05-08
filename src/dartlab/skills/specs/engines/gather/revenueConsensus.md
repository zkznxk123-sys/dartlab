---
id: "engines.gather.revenueConsensus"
title: "Gather - 매출 컨센서스"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "gather 엔진의 매출 컨센서스 응용 — 매출 추정 컨센서스 시계열 (Gather.revenue_consensus 메서드)."
whenToUse:
  - "gather"
  - "revenueConsensus"
  - "매출 컨센서스"
  - "매출 추정 컨센서스 시계열 (Gather.revenue_consensus 메서드)."
inputs:
  - "종목코드 또는 검색어"
  - "market (KR / US, default KR)"
  - "기간 / 옵션 (해당 시)"
outputs:
  - "DataFrame · list · snapshot 객체"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "gather"
  - "Company.gather"
knowledgeRefs:
  - "engines.gather"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.gather.revenueConsensus"
requiredEvidence:
  - "target"
  - "provider"
  - "latestAsOf"
  - "source"
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
  - "API 키 / 인증정보 답변 노출 금지."
  - "provider · source · latestAsOf 명시 없이 최신 데이터라고 말하지 않는다."
  - "원자료를 그대로 분석 결론으로 포장 금지 — 해석은 analysis · macro · scan · story."
  - "컨센서스 mean 한 값으로 점추정 단정 금지 — high/low spread + 추정기관 수 동반."
  - "consensus 와 실적 차이 (surprise) 를 자동 신호로 단정 금지 — 일회성 / 가이던스 차이 구분."
failureModes:
  - "추정기관 수 (2 곳 vs 20 곳) 와 신뢰도 차이 무시"
  - "컨센서스 추정 시점 (실적발표 후 vs 분기 중) 미구분"
  - "high/low spread 가 큰 (편차 30%+) 종목의 mean 인용"
  - "회계 기준 변경 / 사업부 매각 후 컨센서스 재산정 미반영"
  - "한국 회계 vs 글로벌 분석가 추정 (USD 기준) 환율 차이 미보정"
examples:
  - "삼성전자 매출 컨센서스 시계열"
  - "분기별 매출 surprise 추적"
  - "consensus 분산 (편차) 큰 종목 식별"
  - "실적발표 후 consensus 재조정 폭"
linkedSkills:
  - engines.gather
  - engines.gather.consensus
  - engines.analysis.revenueForecast
  - engines.analysis.growth
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

gather 엔진의 매출 컨센서스 응용 skill — 매출 추정 컨센서스 시계열 (Gather.revenue_consensus 메서드). SSOT 는 `Gather` class (`src/dartlab/gather/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. KR 기본
result = dartlab.gather("revenueConsensus", "005930")

# 2. US 시장
result = dartlab.gather("revenueConsensus", "AAPL", market="US")
```

## 호출 동작

provider / cache / snapshot 데이터를 읽어 매출 컨센서스 결과를 반환한다. 캐시 hit 시 즉시 반환, miss 시 외부 API 호출 (실패 시 fallback chain). API 키가 필요한 provider 는 누락 시 `None` / 빈 결과 + 안내 — 결과 없음으로 오해하지 않는다. 자세한 동작은 base SKILL `engines.gather` + `Gather.revenueConsensus` 메서드 docstring 참조.

## 대표 반환 형태

DataFrame · list · snapshot 객체 또는 `None` 반환. 공통 키:

- `provider` / `source`: 데이터 출처 (Naver · ECOS · FRED · FMP 등)
- `latestAsOf` / `date`: 데이터 기준일
- `target` / `market`: 대상 종목 / 시장
- 축 고유 metric · value · unit · flags

전체 키는 `Gather.revenueConsensus` docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 검색어 / indicator), 시장, 기간 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `provider` · `source` · 결손 / `flags` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 해석은 `engines.analysis` · `engines.macro` · `engines.scan` · `engines.story` 가 담당 — gather 원자료를 결론으로 포장 금지.

## 기본 검증

이 skill 은 공개 실행 문서다. `Gather.revenueConsensus` 메서드의 호출 시그니처, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `Gather` class docstring + base SKILL `engines.gather`.
