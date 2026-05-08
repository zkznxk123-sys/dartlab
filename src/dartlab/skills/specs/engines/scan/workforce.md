---
id: "engines.scan.workforce"
title: "Scan - 인력/급여"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 workforce 축 응용 — 직원수, 평균급여, 인건비율, 1인당부가가치, 성장률, 고액보수."
whenToUse:
  - "scan"
  - "workforce"
  - "인력/급여"
  - "직원수, 평균급여, 인건비율, 1인당부가가치, 성장률, 고액보수"
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
  - "dartlab://skills/engines.scan.workforce"
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
  - 직원수 / 평균급여 / 인건비율 분류 미명시 답변 금지.
  - CEO/임원 보수와 평균 직원 보수 동치 처리 금지.
failureModes:
  - 산업별 정상 인건비율 차이 (IT 高 / 제조 中 / 자원 低) 무시
  - 비정규직 비중 누락
  - 1 인당 부가가치 분모 정의 미명시
  - 고액보수 5 명 기준 산업별 차이 무시
examples:
  - 인건비율 상위 (인력 집약)
  - 1 인당 부가가치 산업 평균 대비
  - 평균 급여 + 직원수 추세
  - CEO 보수 vs 평균 직원 보수
linkedSkills:
  - engines.analysis.costStructure
  - engines.analysis.governance
  - engines.scan.governance
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 인력/급여 축 응용 skill — 직원수, 평균급여, 인건비율, 1인당부가가치, 성장률, 고액보수. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scan_workforce()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
df = dartlab.scan("workforce")

# 2. accessor (동등)
df = dartlab.scan.workforce()
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 인력/급여 축 지표를 산출한다. 직원수, 평균급여, 인건비율, 1인당부가가치, 성장률, 고액보수. 결손 종목은 결과 DataFrame 의 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.scan` + `scan_workforce()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scan_workforce()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scan_workforce()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scan_workforce()` docstring.
