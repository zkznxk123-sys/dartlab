---
id: engines.reference
title: Reference (정적 JSON 룩업 + 매핑 엔진)
kind: curated
scope: builtin
status: skeleton
category: engines
purpose: Reference 는 L1.5 4 형제 중 *정적 JSON 룩업 + 매핑* 담당. 정적 reference dataset (JSON 8 종) + 매핑 엔진 (BaseMapper 등 코드 8 종) 을 분석엔진에 제공. 가공 X — 정적 자원이지만 분석엔진이 직접 보는 표면이라 L1.5 동거. 현 단계는 디렉토리 골격만, 모듈 이동은 P-CORE B. 트리거 — '계정 매핑', '산업 분류', 'reference 룩업'.
whenToUse:
  - reference
  - 계정 매핑
  - accountMapping
  - 산업 분류
  - taxonomy
  - reference JSON
  - 정적 룩업
inputs:
  - mapping key (계정명·산업코드·종목코드 등)
  - mapper 종류 (예: accountMapper · industryMapper)
outputs:
  - 매핑 결과 (snake_id · 표준명 · 산업코드 등)
  - reference DataFrame 또는 dict
capabilityRefs: []
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.mappers
sourceRefs:
  - dartlab://skills/engines.reference
requiredEvidence:
  - mapperVersion
  - mappingKey
  - referenceJsonAsOf
expectedOutputs:
  - 표준 매핑 결과
  - 미매핑 fallback 명시
  - reference 버전 정보
runtimeCompatibility:
  server:
    status: limited
    notes:
      - P-CORE B 이전까지 모듈 비어있음 — 호출 불가. dartlab.reference.data / mappers 가 본 위치로 이동 예정.
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: supported
    notes:
      - 정적 JSON 자원이라 Pyodide 환경에서도 fully 동작 (모듈 이동 완료 후).
failureModes:
  - 모듈 이동 전 호출 시 ImportError
  - mappingKey 미매핑 시 nonstd_ fallback (정상 동작)
  - reference JSON 버전 불일치 시 매핑 결과 회귀
forbidden:
  - L1.5 4 형제 cross import 금지 — scan/frame/synth 직접 import 안 함.
  - raw 생산 (gather/providers 호출) 금지 — 본 엔진은 *정적 자원* 만 제공.
  - 자체 가공·룰 매칭·점수화 금지 — 룩업·매핑만.
  - reference JSON 손수 편집은 운영자 명시 절차 (mapping-refresh skill) 만.
examples:
  - 계정명 → snake_id 매핑 (accountMapper)
  - 산업코드 → taxonomy phase 매핑
  - 종목코드 → corpProfile 룩업
procedure:
  - 본 엔진은 P-CORE A 단계에서 *디렉토리 골격* 만 존재. 진입 조건 — 정적 자원이 분석엔진 표면.
  - 현재 위치한 candidate 모듈 — `src/dartlab/reference/data/` (JSON 8 종), `src/dartlab/reference/mappers/` (코드 8 종) — 모듈 이동 완료 후 본 SKILL 갱신.
  - mapping 갱신 절차는 별도 skill — `.claude/skills/mapping-refresh/SKILL.md` (운영자 트리거).
  - 룩업 조회는 분석엔진 (L2) 이 직접 호출. AI 도구는 본 엔진을 통과 X (mappers 결과는 L2 에서 인용).
linkedSkills:
  - engines.mappers
  - engines.frame
  - engines.scan
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-18'
---

## 엔진 역할

`reference` 는 L1.5 4 형제 중 *정적 JSON 룩업 + 매핑* 담당. 다른 L1.5 형제와의 책임 분리:

- **scan**: 횡단면 (universe 전수 필터)
- **frame**: raw 결합 → 분석 ready
- **synth**: 분석 후처리 · 매칭 · 시나리오
- **reference**: *정적 JSON 룩업 + 매핑* (본 엔진)

가공 안 함 — 룩업·매핑만. 분석엔진이 직접 보는 *정적 자원 표면*.

## 현 단계 상태 — skeleton (P-CORE A)

`src/dartlab/reference/__init__.py` 만 존재. P-CORE B 단계에서:

- `src/dartlab/reference/data/` (JSON 8 종 — accountMapping · industryTaxonomy · corpProfile 등) 이동 예정
- `src/dartlab/reference/mappers/` (코드 8 종 — BaseMapper / AccountMapper / IndustryMapper / SectorMapper 등) 이동 예정

본 SKILL 은 P-CORE B 이전 *진입 조건 명시* + *L1.5 cross 금지 룰* + *mapping-refresh 절차 연결* 만 박는다.

## 공개 호출 방식

본 단계 (P-CORE A) 는 디렉토리 골격만. 모듈 비어 있어 호출 불가:

```python
# P-CORE B 이전 호출 시 ImportError
# from dartlab.reference import accountMapper  # → ImportError
```

P-CORE B 이전 완료 후 추가 — `accountMapper`, `industryMapper`, `sectorMapper` 등. 현재는 `dartlab.reference.data` (JSON) + `dartlab.reference.mappers` (BaseMapper 등) 가 *임시 거주*.

## 호출 동작

현재 모듈 미존재 — 모든 호출 ImportError. 임시 거주 위치는 직접 import 가능하나 본 SKILL 의 capability 아님.

## 대표 반환 형태

P-CORE B 이전 완료 후 갱신. 예정 형태:

```text
reference.{mapper}.lookup(key) → dict
   snakeId         : str
   label           : str             # 표준명
   alias           : list[str]       # 별칭
   version         : str             # reference JSON 버전
```

## mapping-refresh 절차 연결

reference JSON 갱신은 운영자가 명시 트리거 발동. AI 도구·자동 cron 없음.

- 절차 SSOT: `.claude/skills/mapping-refresh/SKILL.md`
- accountMapping 보강 4 단계: 후보 발굴 → 분류 → 표준 매핑 결정 → JSON 패치
- 본 SKILL 은 *연결만* — 절차 본문은 mapping-refresh SKILL 안.

## 강행 호출 룰 (architecture lint 가드)

1. **L1.5 4 형제 cross import 금지** — reference 가 scan/frame/synth 직접 import 안 함.
2. **raw 생산 금지** — gather/providers 호출 안 함. *정적 자원* 만.
3. **자체 가공·룰 매칭·점수화 금지** — 룩업·매핑만. 분류 룰은 L2/synth 책임.
4. **JSON 직접 편집 금지** — 운영자 명시 mapping-refresh 절차만.

## 후속 작업

P-CORE B 모듈 이동 + 본 SKILL 갱신 1 commit 동행. 현재 단계는 *엔진 격리 선언* + *mapping-refresh 절차 연결* 만.
