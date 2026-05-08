---
id: "engines.analysis.macroSensitivity"
title: "Analysis - 매크로민감도"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 매크로민감도 축 응용 — 이 회사의 매출은 어떤 매크로 변수에 민감한가."
whenToUse:
  - 매크로민감도
  - macroSensitivity
  - 거시 민감도
  - 금리 영향
  - 환율 영향
  - GDP 베타
  - 경기 사이클 노출
inputs:
  - Company 또는 종목코드
  - 기준 기간 (회귀 추정 기간)
  - 거시 변수 (금리·환율·GDP·유가)
outputs:
  - 축별 dict (macroBeta · pValue · regressionPeriod)
  - 거시 변수별 베타 표
  - evidence refs
  - 가정 (회귀 모델·기간·벤치마크)
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.macroSensitivity"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "tableRef"
  - "valueRef"
  - "dateRef"
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
  - 근거 없는 숫자를 만들지 않는다.
  - 결손값을 0 으로 채우지 않는다.
  - 단일 axis 결과를 최종 투자 결론으로 제시하지 않는다.
  - 회귀 추정 기간·벤치마크·p-value 명시 없이 베타 단정 금지.
  - 시장 매크로 (`engines.macro`) 와 *기업 단위* 민감도 (본 skill) 혼동 금지 — c.macro 는 시장, c.analysis("macro", "매크로민감도") 는 기업.
failureModes:
  - 회귀 기간 (3년/5년/10년) 변경 시 베타 큰 변동 — 단일 기간 결과로 단정 위험
  - 사이클 회사 (반도체·정유) 의 베타가 cycle phase 에 따라 변함 — 평균 베타 한계 명시 필요
  - p-value 낮은 (통계 유의성 미달) 베타를 결론에 사용
  - 한국 회사인데 KOSPI 가 아닌 S&P 베타 사용 — benchmark 일치 필수
  - 외화 매출 회사의 환율 베타가 *원화 기준* 과 *USD 기준* 다름 — currency 명시
  - 신생 회사 (상장 1 년 미만) 베타 추정 시도 — 회귀 표본 부족
examples:
  - 삼성전자 환율 민감도
  - 고려아연 LME 가격 베타
  - 신한지주 금리 베타 (NIM 민감도)
  - 회귀 기간별 베타 변동
  - KOSPI vs SPY 벤치마크 비교
  - 외화 매출 비중에 따른 환율 영향
linkedSkills:
  - engines.macro
  - engines.macro.cycle
  - engines.scan.macroBeta
  - engines.quant.beta
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 매크로민감도 축 응용 skill — 이 회사의 매출은 어떤 매크로 변수에 민감한가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("macro", "매크로민감도")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("macro", "매크로민감도", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 매크로민감도 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

## 대표 반환 형태

dict 반환. 공통 키:

- `items`: 축별 계산 항목과 결과
- `history`: 기간별 시계열
- `displayHints`: 표/차트 표시 힌트
- `turningPoints`: 전환점 (해당 시)
- `dataAsOf`, `assumptions`, `flags`: 데이터 기준일, 가정, 결손/이상 신호
- `_summary`: 사람이 읽을 요약
- `tableRef` / `valueRef` / `dateRef` / `executionRef`: evidence 참조

전체 반환 키는 base SKILL `engines.analysis` 표 + `_analysisImpl` docstring 으로 검산.

## 기본 실행 순서

1. 대상, 기간, 원천 데이터 확정.
2. 위 공개 호출을 그대로 실행.
3. `dataAsOf`, 결손 값, `flags`, `assumptions` 점검.
4. 숫자 claim 은 `tableRef` / `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 보고서 조립은 `engines.story` 또는 상위 recipe 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 대표 반환 키, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).
