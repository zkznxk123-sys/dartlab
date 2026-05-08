---
id: "engines.gather.majorShareholders"
title: "Gather - 주요주주"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "gather 엔진의 주요주주 응용 — 5% 이상 주요주주 list 와 지분율."
whenToUse:
  - "gather"
  - "majorShareholders"
  - "주요주주"
  - "5% 이상 주요주주 list 와 지분율."
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
  - "dartlab://skills/engines.gather.majorShareholders"
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
  - "주요주주 (5% 룰) list 의 보고 기준일 (filing date) 명시 없이 현 시점 지분율로 인용 금지."
  - "특수관계자 묶음 지분 (오너 + 가족 + 재단) 을 단일 주주 지분으로 단순 합산 금지."
failureModes:
  - "5% 보고 면제 (외인 펀드 익명 등) 영향 무시"
  - "최근 변동 (5% → 4.99%) 보고 의무 해제로 추세 단절"
  - "특수관계자 그룹 정의 (직계 / 친인척 / 재단 / 계열사) 모호"
  - "차명 주식 / 의결권 위임 (위임장 대결권) 미반영"
  - "분기말 vs 사업보고서 vs 5% 보고 시점 차이"
examples:
  - "삼성전자 5% 이상 주요주주 list"
  - "오너 일가 합산 지분"
  - "외국계 펀드 보유 5% 이상"
  - "특수관계자 그룹별 지분율"
linkedSkills:
  - engines.gather
  - engines.gather.ownership
  - engines.gather.insiderTrading
  - engines.analysis.governance
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

gather 엔진의 주요주주 응용 skill — 5% 이상 주요주주 list 와 지분율. SSOT 는 `Gather` class (`src/dartlab/gather/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. KR 기본
result = dartlab.gather("majorShareholders", "005930")

# 2. US 시장
result = dartlab.gather("majorShareholders", "AAPL", market="US")
```

## 호출 동작

provider / cache / snapshot 데이터를 읽어 주요주주 결과를 반환한다. 캐시 hit 시 즉시 반환, miss 시 외부 API 호출 (실패 시 fallback chain). API 키가 필요한 provider 는 누락 시 `None` / 빈 결과 + 안내 — 결과 없음으로 오해하지 않는다. 자세한 동작은 base SKILL `engines.gather` + `Gather.majorShareholders` 메서드 docstring 참조.

## 대표 반환 형태

DataFrame · list · snapshot 객체 또는 `None` 반환. 공통 키:

- `provider` / `source`: 데이터 출처 (Naver · ECOS · FRED · FMP 등)
- `latestAsOf` / `date`: 데이터 기준일
- `target` / `market`: 대상 종목 / 시장
- 축 고유 metric · value · unit · flags

전체 키는 `Gather.majorShareholders` docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 검색어 / indicator), 시장, 기간 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `provider` · `source` · 결손 / `flags` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 해석은 `engines.analysis` · `engines.macro` · `engines.scan` · `engines.story` 가 담당 — gather 원자료를 결론으로 포장 금지.

## 기본 검증

이 skill 은 공개 실행 문서다. `Gather.majorShareholders` 메서드의 호출 시그니처, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `Gather` class docstring + base SKILL `engines.gather`.
