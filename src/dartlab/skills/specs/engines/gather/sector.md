---
id: "engines.gather.sector"
title: "Gather - 섹터"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "gather 엔진의 섹터 응용 — 종목의 섹터 / 산업 분류 정보."
whenToUse:
  - "gather"
  - "sector"
  - "섹터"
  - "종목의 섹터 / 산업 분류 정보."
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
  - "dartlab://skills/engines.gather.sector"
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
  - 원자료를 그대로 분석 결론으로 포장 금지.
  - sectorCode (KRX) vs industryCode (Yahoo) 혼동 금지.
  - sector / industry 단계별 차이 무시 금지.
failureModes:
  - KRX 분류 (대분류 11 / 중분류 / 세부) 단계 명시 누락
  - Yahoo asset profile (industry vs sector) 미국 분류와 한국 매칭 차이
  - 신생 회사 sector 미분류 — None 처리 필요
  - 다각화 회사 (지주) 의 sector 단일 분류 한계
examples:
  - 삼성전자 sector / industry
  - KRX 분류 vs Yahoo
  - 다각화 회사 sector 한계
  - 신생 회사 None 처리
linkedSkills:
  - engines.industry
  - engines.gather.industryPeers
  - engines.scan.governance
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

gather 엔진의 섹터 응용 skill — 종목의 섹터 / 산업 분류 정보. SSOT 는 `Gather` class (`src/dartlab/gather/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. KR 기본
result = dartlab.gather("sector", "005930")

# 2. US 시장
result = dartlab.gather("sector", "AAPL", market="US")
```

## 호출 동작

provider / cache / snapshot 데이터를 읽어 섹터 결과를 반환한다. 캐시 hit 시 즉시 반환, miss 시 외부 API 호출 (실패 시 fallback chain). API 키가 필요한 provider 는 누락 시 `None` / 빈 결과 + 안내 — 결과 없음으로 오해하지 않는다. 자세한 동작은 base SKILL `engines.gather` + `Gather.sector` 메서드 docstring 참조.

## 대표 반환 형태

DataFrame · list · snapshot 객체 또는 `None` 반환. 공통 키:

- `provider` / `source`: 데이터 출처 (Naver · ECOS · FRED · FMP 등)
- `latestAsOf` / `date`: 데이터 기준일
- `target` / `market`: 대상 종목 / 시장
- 축 고유 metric · value · unit · flags

전체 키는 `Gather.sector` docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 검색어 / indicator), 시장, 기간 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `provider` · `source` · 결손 / `flags` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 해석은 `engines.analysis` · `engines.macro` · `engines.scan` · `engines.story` 가 담당 — gather 원자료를 결론으로 포장 금지.

## 기본 검증

이 skill 은 공개 실행 문서다. `Gather.sector` 메서드의 호출 시그니처, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `Gather` class docstring + base SKILL `engines.gather`.
