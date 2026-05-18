---
id: engines.synth
title: Synth (분석 후처리 · 매칭 · 시나리오)
kind: curated
scope: builtin
status: skeleton
category: engines
purpose: Synth 는 L1.5 4 형제 중 *분석 후처리 · 매칭 · 시나리오* 담당. 분석 결과 + scan 결과 + 룰 (reference) 을 결합해 매칭·분류·시나리오 후처리를 수행. raw 생산 0, 횡단면 0, 룩업 0 — 결합·매칭·후처리 책임. 현 단계 (P-CORE A) 는 디렉토리 골격만 존재, 모듈 이동은 후속 단계 (P-CORE B) 에서 진행. 트리거 — '시나리오 후처리', '룰 매칭', '분석 결과 결합'.
whenToUse:
  - synth
  - 시나리오 후처리
  - 분석 결과 매칭
  - 룰 기반 분류
  - scan + analysis 결합
inputs:
  - 분석엔진 (L2) 결과 dict / DataFrame
  - scan 결과 후처리 입력 (L2 가 전달)
  - reference 룰 JSON
outputs:
  - 매칭/분류 결과 DataFrame
  - 시나리오 overlay 결과
  - 분석 후처리 narrative
capabilityRefs: []
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.scan
  - engines.analysis
sourceRefs:
  - dartlab://skills/engines.synth
requiredEvidence:
  - inputAnalysisRef
  - scenarioRef
  - executionRef
expectedOutputs:
  - 후처리 결과 표
  - 매칭 결과 분류
  - 시나리오 overlay 결과
runtimeCompatibility:
  server:
    status: limited
    notes:
      - P-CORE B 이전까지 모듈 비어있음 — 호출 불가.
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
failureModes:
  - 모듈 이동 전 호출 시 ImportError
  - L1.5 cross import 시도 (scan/frame/reference 직접 import) 시 architecture lint 차단
forbidden:
  - L1.5 4 형제 cross import 금지 — scan/frame/reference 직접 import 안 함.
  - raw 생산 (gather/providers 직접 호출) 금지 — L2 또는 frame 이 제공한 결과만 받음.
  - 자체 ratio/score 계산 금지 — L2 결과를 받아 결합·매칭·시나리오만 수행.
examples:
  - dalio48Match (예정 이동 대상)
  - dalioCaseMatch (예정 이동 대상)
  - 시나리오 overlay 후처리 (예정 이동 대상)
procedure:
  - 본 엔진은 P-CORE A 단계에서 *디렉토리 골격* 만 존재. 진입 조건 — ≥ 2 분석엔진 (L2) 이 같은 형태로 사용해야 모듈 이동.
  - 현재 위치한 candidate 모듈 — `src/dartlab/scan/dalio48Match.py`, `src/dartlab/scan/dalioCaseMatch.py` (scan 안 임시 거주, synth 로 이전 예정).
  - 본 SKILL 은 P-CORE B 단계에서 capability 추가 + procedure 확장.
linkedSkills:
  - engines.scan
  - engines.frame
  - engines.reference
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-18'
---

## 엔진 역할

`synth` 는 L1.5 4 형제 중 *분석 후처리 · 매칭 · 시나리오 결합* 담당. 다른 L1.5 형제와의 책임 분리:

- **scan**: 횡단면 (universe 전수 필터)
- **frame**: raw 결합 → 분석 ready
- **synth**: *분석 후처리 · 매칭 · 시나리오* (본 엔진)
- **reference**: 정적 JSON 룩업 + 매핑

L2 분석엔진 (analysis · credit · macro · quant · industry) 결과 + scan 결과 + reference 룰을 결합해 *매칭 결과 분류* · *시나리오 overlay* · *후처리 narrative* 를 만든다.

## 현 단계 상태 — skeleton (P-CORE A)

`src/dartlab/synth/__init__.py` 만 존재. 모듈 이동은 P-CORE B 단계에서:

- `src/dartlab/scan/dalio48Match.py` → `src/dartlab/synth/dalio48Match.py` (예정)
- `src/dartlab/scan/dalioCaseMatch.py` → `src/dartlab/synth/dalioCaseMatch.py` (예정)
- `src/dartlab/{scan,analysis}/overrides.py` → `src/dartlab/synth/overrides.py` (예정)

본 SKILL 은 P-CORE B 단계 이전 *진입 조건 명시* + *L1.5 cross 금지 룰* 만 박는다. capability/procedure 는 모듈 이동 시 본 SKILL 갱신.

## 공개 호출 방식

본 단계 (P-CORE A) 는 디렉토리 골격만. 모듈 비어 있어 호출 불가:

```python
# P-CORE B 이전 호출 시 ImportError
# from dartlab.synth import dalio48Match  # → ImportError
```

P-CORE B 이전 완료 후 본 SKILL 갱신 시 추가 — `dalio48Match`, `dalioCaseMatch`, `overrides` 등.

## 호출 동작

현재 모듈 미존재 — 모든 호출 ImportError. architecture lint (`tests/architecture/test_l15_no_cross_import.py`) 가 L1.5 cross import 차단 강제.

## 대표 반환 형태

P-CORE B 이전 완료 후 갱신. 예정 형태:

```text
synth.match{...}() → pl.DataFrame 또는 dict
   matchedRule  : str               # 매칭 룰 이름
   matchScore   : f64               # 매칭 강도
   inputRefs    : list[Ref]         # L2 결과 ref 전달
```

## 강행 호출 룰 (architecture lint 가드)

1. **L1.5 4 형제 cross import 금지** — synth 가 scan/frame/reference 직접 import 안 함. import 룰 강제: `tests/architecture/test_l15_no_cross_import.py`.
2. **raw 생산 금지** — gather/providers 직접 호출 안 함. L2 또는 frame 이 제공한 결과만 받음.
3. **자체 ratio/score 계산 금지** — L2 결과를 받아 *결합·매칭·시나리오* 만. 계산 표면 = L2.
4. **진입 조건** — ≥ 2 분석엔진이 *같은 형태* 로 사용해야 synth 진입.

## 후속 작업

P-CORE B 모듈 이동 + 본 SKILL 갱신 1 commit 동행. 현재 단계는 *엔진 격리 선언* 만.
