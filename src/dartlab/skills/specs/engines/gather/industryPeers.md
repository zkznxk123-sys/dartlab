---
id: "engines.gather.industryPeers"
title: "Gather - 동종 peer"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "gather 엔진의 동종 peer 응용 — 동종업종 peer 종목 후보 list (KRX 산업 분류 기준)."
whenToUse:
  - "gather"
  - "industryPeers"
  - "동종 peer"
  - "동종업종 peer 종목 후보 list (KRX 산업 분류 기준)."
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
  - "dartlab://skills/engines.gather.industryPeers"
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
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

gather 엔진의 동종 peer 응용 skill — 동종업종 peer 종목 후보 list (KRX 산업 분류 기준). SSOT 는 `Gather` class (`src/dartlab/gather/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. KR 기본
result = dartlab.gather("industryPeers", "005930")

# 2. US 시장
result = dartlab.gather("industryPeers", "AAPL", market="US")
```

## 호출 동작

provider / cache / snapshot 데이터를 읽어 동종 peer 결과를 반환한다. 캐시 hit 시 즉시 반환, miss 시 외부 API 호출 (실패 시 fallback chain). API 키가 필요한 provider 는 누락 시 `None` / 빈 결과 + 안내 — 결과 없음으로 오해하지 않는다. 자세한 동작은 base SKILL `engines.gather` + `Gather.industryPeers` 메서드 docstring 참조.

## 대표 반환 형태

DataFrame · list · snapshot 객체 또는 `None` 반환. 공통 키:

- `provider` / `source`: 데이터 출처 (Naver · ECOS · FRED · FMP 등)
- `latestAsOf` / `date`: 데이터 기준일
- `target` / `market`: 대상 종목 / 시장
- 축 고유 metric · value · unit · flags

전체 키는 `Gather.industryPeers` docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 검색어 / indicator), 시장, 기간 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `provider` · `source` · 결손 / `flags` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 해석은 `engines.analysis` · `engines.macro` · `engines.scan` · `engines.story` 가 담당 — gather 원자료를 결론으로 포장 금지.

## 기본 검증

이 skill 은 공개 실행 문서다. `Gather.industryPeers` 메서드의 호출 시그니처, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `Gather` class docstring + base SKILL `engines.gather`.
