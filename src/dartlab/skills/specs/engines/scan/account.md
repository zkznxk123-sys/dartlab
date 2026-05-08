---
id: "engines.scan.account"
title: "Scan - 계정"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 account 축 응용 — 전종목 단일 계정 시계열 (매출액, 영업이익 등)."
whenToUse:
  - "scan"
  - "account"
  - "계정"
  - "전종목 단일 계정 시계열 (매출액, 영업이익 등)"
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
  - "dartlab://skills/engines.scan.account"
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
  - account snake_id 임의 추측 금지 — scanAccountList 또는 normalizeColumn 으로 정확 매칭.
  - 단일 계정 (매출액 만) 으로 비율 추정 금지 — 비율은 ratio axis.
failureModes:
  - snake_id 추측 (revenue vs sales vs total_revenue 혼용)
  - freq (Q/Y) 명시 없이 결과 인용
  - 산업별 정상 매출 규모 차이 무시
  - 결손 분기 (재무제표 미공시) 처리 미명시
examples:
  - 매출액 시계열 횡단
  - 영업이익 분기별
  - 산업별 평균 매출 대비
  - snake_id 정확 매칭 (normalizeColumn)
linkedSkills:
  - engines.scan.ratio
  - engines.scan.fields
  - engines.analysis
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 계정 축 응용 skill — 전종목 단일 계정 시계열 (매출액, 영업이익 등). SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scanAccount()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# snakeId 필수
df = dartlab.scan("account", "매출액")

# accessor (동등)
df = dartlab.scan.account("매출액")
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 계정 축 지표를 산출한다. 전종목 단일 계정 시계열 (매출액, 영업이익 등). 결손 종목은 결과 DataFrame 의 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.scan` + `scanAccount()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scanAccount()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scanAccount()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scanAccount()` docstring.
