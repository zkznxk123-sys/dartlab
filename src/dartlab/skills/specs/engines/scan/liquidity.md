---
id: "engines.scan.liquidity"
title: "Scan - 유동성"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 liquidity 축 응용 — 유동비율 + 당좌비율 — 단기 지급능력."
whenToUse:
  - "scan"
  - "liquidity"
  - "유동성"
  - "유동비율 + 당좌비율 — 단기 지급능력"
inputs:
  - "축 이름 (axis)"
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
  - "dartlab://skills/engines.scan.liquidity"
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
  - 금융사 (은행·보험) 에 일반 유동비율 적용 금지 — LCR · NSFR 별도 지표.
  - 유동비율 단일 metric 으로 단정 금지 — 당좌비율 + 사채만기 교차.
failureModes:
  - 산업별 정상 유동비율 차이 무시 (제조 150~200% / 서비스 100~150%)
  - 재고 비중 큰 회사의 유동비율이 *과대평가* — 당좌비율 (재고 제외) 함께
  - 단기 차입금 만기 구조 무시
  - 1 년 내 만기 사채 비중을 본 위험 신호 미반영
  - 운전자본 동결 (매출채권 회수 지연) 영향 미고려
examples:
  - 단기 지급능력 하위 50 (위험 의심)
  - 당좌비율 100% 미만 회사
  - 산업 평균 유동비율 대비 위치
  - 단기차입금 의존도 + 사채 만기
  - 운전자본 회수 사이클
linkedSkills:
  - engines.analysis.stability
  - engines.analysis.cashflow
  - engines.credit
  - engines.scan.cashflow
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 liquidity 축 응용 skill — 유동비율 + 당좌비율 — 단기 지급능력. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scanLiquidity()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
df = dartlab.scan("liquidity")

# 2. accessor 호출 (동등)
df = dartlab.scan.liquidity()
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 liquidity 축 지표를 산출한다. 유동비율 + 당좌비율 — 단기 지급능력. 결손 종목은 결과 DataFrame 에서 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작 + 인자는 base SKILL `engines.scan` + `scanLiquidity()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scanLiquidity()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scanLiquidity()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scanLiquidity()` docstring.
