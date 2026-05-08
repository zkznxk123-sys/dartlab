---
id: "engines.scan.cashflow"
title: "Scan - 현금흐름"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 cashflow 축 응용 — OCF/ICF/FCF + 현금흐름 패턴 분류 (8종)."
whenToUse:
  - "scan"
  - "cashflow"
  - "현금흐름"
  - "OCF/ICF/FCF + 현금흐름 패턴 분류 (8종)"
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
  - "dartlab://skills/engines.scan.cashflow"
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
  - 8 종 현금흐름 패턴 분류 (Healthy / Growing / Distressed / Mature / ...) 명시 없이 *위험* 단정 금지.
  - capex 음수 vs 양수 의미 회사별 다름 — 부호 임의 해석 금지.
failureModes:
  - 성장형 capex (OCF + / ICF - / FCF -) 와 부실 (OCF - / ICF + / FCF -) 패턴 혼동
  - FCF 정의 차이 (OCF - capex vs OCF - capex - 인수합병) 미명시
  - 분기 vs 연 합산 혼용 — period 일치 필요
  - 산업별 정상 capex 강도 차이 무시 (제조 高 / 서비스 低)
  - 일회성 자산 매각 (ICF +) 을 정상 영업으로 오해
examples:
  - FCF 양수 + 성장 패턴 회사
  - 8 종 현금흐름 패턴 분포
  - capex/OCF 비율 (재투자 강도)
  - 산업별 평균 FCF 마진
  - Distressed 패턴 의심 종목
linkedSkills:
  - engines.analysis.cashflow
  - engines.analysis.capitalAllocation
  - engines.scan.quality
  - engines.scan.liquidity
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 cashflow 축 응용 skill — OCF/ICF/FCF + 현금흐름 패턴 분류 (8종). SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scanCashflow()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
df = dartlab.scan("cashflow")

# 2. accessor 호출 (동등)
df = dartlab.scan.cashflow()
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 cashflow 축 지표를 산출한다. OCF/ICF/FCF + 현금흐름 패턴 분류 (8종). 결손 종목은 결과 DataFrame 에서 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작 + 인자는 base SKILL `engines.scan` + `scanCashflow()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scanCashflow()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scanCashflow()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scanCashflow()` docstring.
