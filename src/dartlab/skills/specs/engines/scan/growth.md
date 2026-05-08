---
id: "engines.scan.growth"
title: "Scan - 성장성"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "scan 엔진의 growth 축 응용 — 매출/영업이익/순이익 CAGR + 성장 패턴 분류 (6종)."
whenToUse:
  - "scan"
  - "growth"
  - "성장성"
  - "매출/영업이익/순이익 CAGR + 성장 패턴 분류 (6종)"
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
  - "dartlab://skills/engines.scan.growth"
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
  - 6 종 성장 패턴 분류 (Acceleration / Steady / Deceleration / Cyclical / Recovery / Decline) 명시 없이 *고성장* 단정 금지.
  - 단일 분기 YoY 로 성장 단정 금지 — 4 분기 평균 또는 CAGR 권장.
  - 사이클 회사의 cycle peak/trough 영향 미고려 금지.
failureModes:
  - 신생 회사 (상장 2 년 미만) 의 5 년 CAGR 계산 시도 — 표본 부족
  - M&A 효과 (인수 후 연결 재무제표 변화) 를 유기적 성장으로 오인
  - 외화 매출 회사 환율 변동 영향 미분리
  - 분기 매출 spike 를 구조적 성장으로 오해
  - base effect (전년 동기 일회성) 미보정
  - 산업 평균 성장률 미참조 — 절대 CAGR 만으로 *고성장* 단정
examples:
  - 매출 5 년 CAGR 상위 50
  - 영업이익 가속 (Acceleration 패턴) 종목
  - 산업 평균 성장률 대비 위치
  - 사이클 회사 성장 패턴 분류
  - YoY vs CAGR 시계열 비교
  - 신생 회사 단기 성장률
linkedSkills:
  - engines.analysis.growth
  - engines.analysis.revenueForecast
  - engines.analysis.predictionSignal
  - engines.scan.profitability
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

scan 엔진의 growth 축 응용 skill — 매출/영업이익/순이익 CAGR + 성장 패턴 분류 (6종). SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/scan/__init__.py`) + `scanGrowth()` 함수 docstring.

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
df = dartlab.scan("growth")

# 2. accessor 호출 (동등)
df = dartlab.scan.growth()
```

## 호출 동작

전종목 finance / disclosure / market universe 를 읽어 growth 축 지표를 산출한다. 매출/영업이익/순이익 CAGR + 성장 패턴 분류 (6종). 결손 종목은 결과 DataFrame 에서 null 또는 별도 flag 로 표현하며 0 으로 채우지 않는다. 자세한 동작 + 인자는 base SKILL `engines.scan` + `scanGrowth()` docstring 참조.

## 대표 반환 형태

DataFrame 반환. 공통 column:

- `stockCode` / `corpName`: 종목 식별자
- `market`: KOSPI / KOSDAQ / KONEX
- `latestAsOf` / `asOf`: 데이터 기준일
- 축 고유 metric / score / rank / grade column (정확한 spec 은 `scanGrowth()` docstring 검산)
- `flags`: 결손 / 이상 / 비교 불가 신호

전체 column 은 `scanGrowth()` docstring 으로 검산. 코드 변경 시 본 skill 도 같이 갱신.

## 기본 실행 순서

1. universe 와 datasetAsOf 확정.
2. 위 공개 호출 그대로 실행.
3. 결손 종목 / `flags` / 이상치 점검.
4. 랭킹 / 후보 답변은 universe + datasetAsOf + 핵심 column 표를 evidence 로 묶음.
5. 심층 해석은 `engines.analysis` 또는 `engines.story` 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 column, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` + `scanGrowth()` docstring.
