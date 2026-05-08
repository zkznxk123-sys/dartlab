---
id: "engines.quant.piotroski"
title: "Quant - Piotroski F"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 Piotroski F 축 응용 — Piotroski 2000 — 9 신호 합 (0~9점) 전종목 분포 + 9 신호 시장 통과율."
whenToUse:
  - "quant"
  - "piotroski"
  - "Piotroski F"
  - "Piotroski 2000 — 9 신호 합 (0~9점) 전종목 분포 + 9 신호 시장 통과율"
inputs:
  - "종목코드 또는 종목 리스트"
  - "기준 기간"
  - "benchmark / 가정 (해당 시)"
outputs:
  - "축별 dict 또는 DataFrame"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "quant"
  - "Company.quant"
knowledgeRefs:
  - "engines.quant"
  - "engines.gather"
  - "engines.analysis"
sourceRefs:
  - "dartlab://skills/engines.quant.piotroski"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "benchmark"
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
  - 성과 보장 표현 금지.
  - 기간 / benchmark / 가정 명시 없이 수익률 인용 금지.
  - 정량 신호를 인과 분석 결론으로 제시 금지.
  - Piotroski F-score (0-9) 임계값 8+ 만으로 *우량* 단정 금지 — 시가총액 / 산업 분기 함께.
  - 단일 분기 F-score 만으로 판단 금지 — 4+ 분기 시계열 권장.
failureModes:
  - 9 항목 중 산업 부적합 항목 (제조 외 회사의 자산회전율 등) 미보정
  - 신생 회사의 YoY 성장 항목 base 부재로 점수 왜곡
  - 일회성 손익이 ROA · CFO 항목 왜곡
  - 사이클 회사의 cycle phase 별 F-score 변동 미반영
  - F-score 단일 metric 만으로 *value* 결론 — 멀티플 (PER · PBR) 함께 필요
examples:
  - 삼성전자 Piotroski F-score
  - F-score 8+ 우량 후보 + 멀티플 교차
  - 4 분기 F-score 시계열
  - 산업 평균 F-score 대비 위치
  - 사이클 phase 별 F-score 변동
linkedSkills:
  - engines.quant.altman
  - engines.quant.qmj
  - engines.analysis.profitability
  - engines.scan.quality
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 Piotroski F 축 응용 skill — Piotroski 2000 — 9 신호 합 (0~9점) 전종목 분포 + 9 신호 시장 통과율. fundamental 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출 (횡단면 / 시장 레벨 — 종목 불필요)
result = dartlab.quant("piotroski")

# 2. accessor 호출 (동등)
result = dartlab.quant.piotroski()
```

## 호출 동작

전종목 universe 의 가격 · 재무 · 시계열 snapshot 을 읽어 Piotroski F 축 계산을 수행한다. Piotroski 2000 — 9 신호 합 (0~9점) 전종목 분포 + 9 신호 시장 통과율. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['piotroski'].fn` 함수 docstring 참조.

## 대표 반환 형태

fundamental 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['piotroski'].fn` 함수 docstring 검산)
- `flags` / `assumptions`: 결손 · 가정

전체 키는 base SKILL `engines.quant` 표 + 함수 docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 종목 리스트), 기준일, benchmark 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` / 결손 종목 / `flags` / `assumptions` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 narrative 조립은 `engines.story` 또는 상위 recipe 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`) + 함수 docstring.
