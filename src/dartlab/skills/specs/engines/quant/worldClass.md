---
id: engines.quant.worldClass
title: Quant - 세계 수준 quality bar
kind: curated
scope: builtin
status: observed
category: engines
purpose: quant 엔진 답변의 세계 수준 품질 게이트 — 학술 출처 / 가정 / OOS 검증 / Sharpe 인용 기준 + dartlab quant 의 사상 위반 회귀 가드.
whenToUse:
  - quant 답변 품질 게이트
  - OOS / DSR / PBO 인용 기준 확인
  - 학술 출처 + 표본 차이 명시 검증
  - quant 사상 위반 회귀 (alpha 디렉터리 추가 / 5 패스 강박 등) 점검
inputs:
  - 검증 대상 quant 결과
  - 검증 범위 (단일 axis / 결합 / 전략)
outputs:
  - 품질 게이트 통과 여부
  - 미흡 항목 list
  - 보강 권장 axis
capabilityRefs:
  - quant
toolRefs:
  - search_reference
  - RunPython
knowledgeRefs:
  - engines.quant
  - engines.quant.signalReview
  - engines.quant.walkforward
sourceRefs:
  - dartlab://skills/engines.quant.worldClass
requiredEvidence:
  - target
  - period
  - benchmark
  - assumptions
  - executionRef
expectedOutputs:
  - 게이트 통과 / 미흡 항목
  - 보강 권장 axis
  - 학술 인용 검증
forbidden:
  - 학술 인용 (Fama-French / Asness / Frazzini-Pedersen 등) 없이 팩터 수익률 단정 금지.
  - in-sample 결과를 OOS 약속으로 단정 금지 — walkforward / cpcv 검증 동반.
  - 미국 표본 결과를 KR 시장 동일 가정으로 인용 금지 — reproducibility 차이 명시.
  - 가정 (윈도우 / 가중치 / 리밸런싱) 명시 없이 Sharpe / IR 인용 금지.
  - quant 본체 (engines.quant) 의 axis_registry 외 임의 디렉터리 (alpha / strategies / signals) 추가 금지.
failureModes:
  - 단일 학술 논문 결과를 KR 시장에 그대로 적용 (reproducibility crisis 무시)
  - 가정 미명시 (lookback / rebalancing / cost) 로 결과 비교 불가
  - 합성 점수 (composite) 의 가중치 임의 선택 + 노이즈로 보임
  - factor zoo (300+ factor) 에서 사후 cherry-picking
  - DSR / PBO / Reality Check 미수행으로 false discovery 위험
examples:
  - 신규 axis 추가 전 학술 출처 / OOS 검증 게이트
  - quant 답변의 가정 / 표본 차이 명시 점검
  - 합성 점수 가중치 결정 근거 검증
  - quant 사상 위반 (디렉터리 추가 / 5 패스) 회귀 가드
linkedSkills:
  - engines.quant
  - engines.quant.signalReview
  - engines.quant.walkforward
  - engines.quant.benchmark
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
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-08'
---

## 엔진 역할

quant 엔진 답변의 세계 수준 품질 게이트. 본 skill 은 axis 응용이 아니라 *품질 검증 메타 skill* 이다. 답변 작성 후 본 게이트로 검증한 다음 finalize.

## 공개 호출 방식

본 skill 은 직접 호출되는 axis 가 아니다. 다른 quant axis 결과를 검증할 때 본 skill 의 게이트 5 항목을 답변에 적용한다.

```python
import dartlab

# quant axis 결과
result = dartlab.quant("damodaranValuation", "005930")

# 답변 finalize 전 본 skill 의 게이트 5 항목 (학술 출처 / 표본 / 가정 / OOS / 벤치마크) 확인
```

## 호출 동작

게이트 5 항목 (학술 출처 / 표본 차이 / 가정 / OOS 검증 / 벤치마크) 의 통과 여부를 답변에 명시. 미통과 항목은 답변에 한계로 노출.

## 대표 반환 형태

본 skill 자체는 결과를 반환하지 않는다. 다른 quant axis 의 결과 답변 본문에 게이트 5 항목 통과 여부 표 (또는 한계 문장) 가 포함되어야 한다.

## 게이트 항목

1. **학술 출처 명시** — Sloan accruals / Beneish / Frazzini-Pedersen / Hou-Xue-Zhang / Asness QMJ 등 인용 시 논문 (저자 + 연도) 명시.
2. **표본 차이 명시** — 미국 표본 결과를 KR 시장에 적용 시 reproducibility 차이 한 줄 명시.
3. **가정 명시** — 윈도우 (60D / 252D), 리밸런싱 빈도 (월 / 분기), 거래비용 가정.
4. **OOS 검증** — in-sample 백테스트 외 walkforward / cpcv / DSR / PBO 동반.
5. **벤치마크 명시** — KOSPI / 동일가중 universe / 섹터 지수 — 어느 벤치마크 대비 outperformance.

## quant 사상 위반 회귀 가드

dartlab quant 의 진짜 사상 (engines.quant SKILL):

- **단일 SSOT**: `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`). 외부에서 임의 디렉터리 추가 금지 (alpha / strategies / signals).
- **2 호출 경로**: `dartlab.quant(axis, target)` 문자열 / `dartlab.quant.axis(target)` accessor — 동등.
- **3 형태 지원**: 단일 종목 / 횡단면 (universe) / 포트폴리오.
- **story 조립**: 본 skill 은 axis 결과만 — narrative 조립은 `engines.story`.

## 기본 검증

답변 finalize 전 본 게이트 5 항목 확인. 미흡 항목은 답변에 한계로 명시 + 보강 권장 axis 안내.
