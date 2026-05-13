---
id: "engines.scan.governance"
title: "Scan - 거버넌스"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 governance 축 응용 — 지배구조 (지분율, 사외이사, 보수비율, 감사의견, 소액주주 분산)."
whenToUse:
  - "scan"
  - "governance"
  - "거버넌스"
  - "지배구조 (지분율, 사외이사, 보수비율, 감사의견, 소액주주 분산)"
inputs:
  - "축 이름 (axis)"
  - "필요 시 axis-specific target"
outputs:
  - "DataFrame (전종목 횡단)"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "scan"
knowledgeRefs:
  - "engines.scan"
  - "engines.data.foundation"
  - "engines.analysis"
sourceRefs:
  - "dartlab://skills/engines.scan.governance"
requiredEvidence:
  - "universe"
  - "datasetAsOf"
  - "filter"
  - "formula"
  - "table"
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
  - universe / datasetAsOf 없이 후보 나열 금지.
  - 기업명만 나열 금지 — 랭킹 / evidence 표 동반.
  - screening 결과를 심층 분석으로 제시 금지.
  - 최대주주 지분율만으로 *경영권 안정* 단정 금지.
  - 사외이사 비율을 산업 평균과 비교 없이 답변 금지.
failureModes:
  - 최대주주 지분 절대값만 보고 안정성 단정
  - 사외이사 비율 산업 평균 미참조
  - 감사위원회 독립성 누락
  - 보수비율 산업별 차이 무시
  - 소액주주 분산도 무시
examples:
  - 최대주주 지분 + 사외이사
  - 감사위원회 독립성 비율
  - CEO 보수 산업 평균 대비
  - 소액주주 분산도 상위
linkedSkills:
  - engines.analysis.governance
  - recipes.governance.auditComposite
  - engines.scan.insider
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 거버넌스 축 응용 skill — 지배구조 (지분율, 사외이사, 보수비율, 감사의견, 소액주주 분산). SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scanGovernance()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
df = dartlab.scan("governance")

# 2. accessor (동등)
df = dartlab.scan.governance()
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 거버넌스 축 지표를 산출한다. 지배구조 (지분율, 사외이사, 보수비율, 감사의견, 소액주주 분산). 결손 종목은 결과 DataFrame 의 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.scan` + `scanGovernance()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scanGovernance()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scanGovernance()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scanGovernance()` docstring.
