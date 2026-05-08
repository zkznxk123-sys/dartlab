---
id: "engines.gather.macro"
title: "Gather - 거시 지표"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "gather 엔진의 거시 지표 응용 — FRED · ECOS · BOK 매크로 시계열 (전체 wide 또는 단일 indicator)."
whenToUse:
  - "gather"
  - "macro"
  - "거시 지표"
  - "FRED · ECOS · BOK 매크로 시계열 (전체 wide 또는 단일 indicator)."
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
  - "dartlab://skills/engines.gather.macro"
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
  - API 키 / 인증정보 답변 노출 금지.
  - provider · source · latestAsOf 명시 없이 최신 데이터라고 말하지 않는다.
  - 원자료를 그대로 분석 결론으로 포장 금지 — 해석은 analysis · macro · scan · story.
  - 시장 (KR/US) 자동 감지 무시 — 지표 코드 오류 시 명시적 market 인자 사용.
  - HF SSOT 갱신 시점 (월/분기) 미명시 *최신* 단정 금지.
failureModes:
  - 지표 코드 (CPI, FEDFUNDS) 의 시장 자동 감지 실패 시 ValueError
  - HF 카탈로그 외 지표 호출 — apiKey 명시 필요
  - 분기 vs 월 vs 일 주기 혼용 — period 명시 필요
  - 한국 KR macro 와 US macro 동시 표시 시 단위 혼용 (% vs bp 등)
  - 명목 vs 실질 (CPI 보정) 혼용
  - HF 데이터 최신성 (월말 갱신) 에 vs 직접 API (일 갱신) 차이
examples:
  - KR 거시지표 전체 (CPI · 기준금리 · USDKRW)
  - US 거시지표 전체 (GDP · CPI · FEDFUNDS)
  - 단일 지표 시계열 (CPI YoY)
  - KR vs US 같은 지표 비교
  - 명목 vs 실질
  - HF SSOT vs 직접 API
linkedSkills:
  - engines.macro
  - engines.macro.cycle
  - engines.macro.summary
  - engines.analysis.macroSensitivity
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

gather 엔진의 거시 지표 응용 skill — FRED · ECOS · BOK 매크로 시계열 (전체 wide 또는 단일 indicator). SSOT 는 `Gather` class (`src/dartlab/gather/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 전체 wide DataFrame (KR 기본)
result = dartlab.gather("macro")

# 2. 단일 indicator (자동 시장 감지)
result = dartlab.gather("macro", "CPI")

# 3. US 시장
result = dartlab.gather("macro", "FEDFUNDS")
```

## 호출 동작

provider / cache / snapshot 데이터를 읽어 거시 지표 결과를 반환한다. 캐시 hit 시 즉시 반환, miss 시 외부 API 호출 (실패 시 fallback chain). API 키가 필요한 provider 는 누락 시 `None` / 빈 결과 + 안내 — 결과 없음으로 오해하지 않는다. 자세한 동작은 base SKILL `engines.gather` + `Gather.macro` 메서드 docstring 참조.

## 대표 반환 형태

DataFrame · list · snapshot 객체 또는 `None` 반환. 공통 키:

- `provider` / `source`: 데이터 출처 (Naver · ECOS · FRED · FMP 등)
- `latestAsOf` / `date`: 데이터 기준일
- `target` / `market`: 대상 종목 / 시장
- 축 고유 metric · value · unit · flags

전체 키는 `Gather.macro` docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 검색어 / indicator), 시장, 기간 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `provider` · `source` · 결손 / `flags` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 해석은 `engines.analysis` · `engines.macro` · `engines.scan` · `engines.story` 가 담당 — gather 원자료를 결론으로 포장 금지.

## 기본 검증

이 skill 은 공개 실행 문서다. `Gather.macro` 메서드의 호출 시그니처, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `Gather` class docstring + base SKILL `engines.gather`.
