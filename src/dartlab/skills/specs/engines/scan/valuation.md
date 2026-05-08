---
id: "engines.scan.valuation"
title: "Scan - 밸류에이션"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 valuation 축 응용 — PER/PBR/PSR + 시가총액 + 등급 (네이버 실시간)."
whenToUse:
  - "scan"
  - "valuation"
  - "밸류에이션"
  - "PER/PBR/PSR + 시가총액 + 등급 (네이버 실시간)"
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
  - "dartlab://skills/engines.scan.valuation"
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
  - 단일 멀티플 (PER 만) 로 *저평가* 단정 금지 — PBR · PSR 교차 검증.
  - 적자 회사에 PER 적용 금지 (음수 또는 NaN — PSR / EV/Sales 권장).
  - 산업 분기 무시 통합 PER 랭킹 금지 (제조 평균 vs 금융 평균 다름).
failureModes:
  - 사이클 회사 (반도체·정유) PER 가 cycle peak 에 낮게 나옴 — *value trap* 위험
  - 적자 회사 PER null 처리 안 함 — 랭킹 왜곡
  - 시가총액 작은 종목 (소형주) 이 멀티플 상하단 점령 — 시총 필터 필요
  - 산업 평균 멀티플 미참조 — 절대값만으로 판단
  - PER trailing vs forward 혼용 — 명시 필요
  - 배당주의 PBR 1 미만이 *진짜 저평가* 인지 ROE 함께 확인 필요
examples:
  - PER 하위 50 (저평가 후보)
  - 산업 평균 PBR 대비 위치
  - 시가총액 1조 이상 PER 5 미만
  - 사이클 회사 PER trap 점검
  - 배당주 PBR + ROE 교차
  - 멀티플 분포 (PER · PBR · PSR)
linkedSkills:
  - engines.analysis.valuation
  - engines.analysis.valuationBand
  - engines.scan.profitability
  - engines.quant.value
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 valuation 축 응용 skill — PER/PBR/PSR + 시가총액 + 등급 (네이버 실시간). SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scanValuation()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
df = dartlab.scan("valuation")

# 2. accessor 호출 (동등)
df = dartlab.scan.valuation()
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 valuation 축 지표를 산출한다. PER/PBR/PSR + 시가총액 + 등급 (네이버 실시간). 결손 종목은 결과 DataFrame 에서 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작 + 인자는 base SKILL `engines.scan` + `scanValuation()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scanValuation()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scanValuation()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scanValuation()` docstring.
