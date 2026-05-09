---
id: operation.architecture
title: dartlab 아키텍처 — 전체 청사진
kind: curated
scope: builtin
status: observed
category: operation
purpose: dartlab 아키텍처 — 전체 청사진 운영 규칙을 Skill OS에서 확인하고 변경 전후 검증 게이트로 사용한다.
whenToUse:
  - dartlab 아키텍처 — 전체 청사진
  - architecture
  - 1. 레이어 — L0→L4 (L1.5 포함 6 단) 구조로 간다
  - 2. 5 L2 분석엔진 — 두 소비자를 최고로 지원한다
  - 소비자별 차이
  - 3. 모듈 제공 패턴 — analysis 기준 (5 L2 엔진 동일)
  - 4. import 방향 — L0 ← L1 ← L1.5 ← L2 ← L3 하향만 허용한다
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs: []
toolRefs:
  - search_reference
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/operation.architecture
procedure:
  - 1. 레이어 — L0→L4 (L1.5 포함 6 단) 구조로 간다 기준을 확인한다.
  - 2. 5 L2 분석엔진 — 두 소비자를 최고로 지원한다 기준을 확인한다.
  - 소비자별 차이 기준을 확인한다.
  - 3. 모듈 제공 패턴 — analysis 기준 (5 L2 엔진 동일) 기준을 확인한다.
  - 4. import 방향 — L0 ← L1 ← L1.5 ← L2 ← L3 하향만 허용한다 기준을 확인한다.
  - '**story 가 쓸 때** — L3 조합기로서 5 L2 분석엔진 + L1.5 scan 의 calc 결과를 블록으로 변환하여 보고서에 배치. 자체 해석·계산 0 — 모든 숫자는 하위 엔진 ref. story 가 단독으로 다중 결합 책임을 짊어져 L2 끼리 직접 import 가 만드는 순환참조를 차단.'
  - '**AI 가 쓸 때** — AI 가 주체. 엔진 결과를 의심하고, 원본 (`c.show`) 으로 검증하고, override 로 재계산.'
  - 엔진은 양쪽 모두에게 최고의 재료를 제공한다. 숫자와 근거를 투명하게 반환하여 story 는 배치하고 AI 는 검증할 수 있게.
  - calc 함수는 **독립 모듈** — 다른 calc 호출 가능하지만 순환 없음.
requiredEvidence:
  - skillRef
expectedOutputs:
  - 작업 경로
  - 확인한 근거
  - 검증 결과
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
    status: supported
    notes: []
failureModes:
  - Skill OS 검색 없이 과거 문서 경로를 직접 찾음
  - API schema를 skill 본문에 중복해 docstring/capability와 어긋남
  - 검증 게이트 없이 변경 또는 답변을 완료 처리함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - 공개 호출 방식, 대표 반환 형태, 오류/제한 동작을 skill과 불일치한 채 방치하지 않는다.
examples:
  - dartlab 아키텍처 — 전체 청사진 규칙 확인
  - architecture 작업을 Skill OS에서 시작
source:
  type: absorbed_skills
  absorbedKey: architecture
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- 공개 호출 방식과 대표 반환 형태는 skill에서 확인하고, 세부 필드는 capability/docstring으로 검산한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- 1. 레이어 — L0→L4 (L1.5 포함 6 단) 구조로 간다 기준을 확인한다.
- 2. 5 L2 분석엔진 — 두 소비자를 최고로 지원한다 기준을 확인한다.
- 소비자별 차이 기준을 확인한다.
- 3. 모듈 제공 패턴 — analysis 기준 (5 L2 엔진 동일) 기준을 확인한다.
- 4. import 방향 — L0 ← L1 ← L1.5 ← L2 ← L3 하향만 허용한다 기준을 확인한다.
- **story 가 쓸 때** — L3 조합기로서 5 L2 분석엔진 + L1.5 scan 의 calc 결과를 블록으로 변환하여 보고서에 배치. 자체 해석·계산 0 — 모든 숫자는 하위 엔진 ref. story 가 단독으로 다중 결합 책임을 짊어져 L2 끼리 직접 import 가 만드는 순환참조를 차단.
- **AI 가 쓸 때** — AI 가 주체. 엔진 결과를 의심하고, 원본 (`c.show`) 으로 검증하고, override 로 재계산.
- 엔진은 양쪽 모두에게 최고의 재료를 제공한다. 숫자와 근거를 투명하게 반환하여 story 는 배치하고 AI 는 검증할 수 있게.
- calc 함수는 **독립 모듈** — 다른 calc 호출 가능하지만 순환 없음.

## 6 단 계층 SSOT (L0 → L4)

| Layer | 구성 | 역할 |
|---|---|---|
| L0 | `core` | 타입·유틸·SSOT 데이터 (sector classification, mapper, registry, parser) |
| **L1** | `company` (provider facade), `gather` | 외부 1 차 데이터 진입 — DART · EDGAR · 시장 데이터 통합 |
| **L1.5** | `scan` (종목 횡단), `search` (문서 횡단) | L1 위에서 전체 universe 스캔. 단일 종목 심층은 L2 가 담당. |
| **L2 분석엔진 (5)** | `analysis`, `credit`, `macro`, `quant`, `industry` | 단일 도메인 분석. **다른 L2 직접 import 금지** (도메인 격리 + 순환참조 방지) |
| **L3 조합기** | `story` | 분석엔진 X. L2 5 엔진 + L1.5 결과를 블록 단위로 결합해 6 막 보고서 직조. 자체 계산 0, 모든 숫자는 하위 엔진 ref. **L2 다중 소비 책임을 단독으로 짊어져 L2 끼리의 import 순환을 차단** |
| L4 | AI (`dartlab.ask`), 사람 (`dartlab.Company`) | 소비자 — 엔진 결과를 의심·검증·재계산 |

import 단방향 강제: `L0 ← L1 ← L1.5 ← L2 ← L3 ← L4`. CI lint 로 L2 → L2 import 0 건 강제. story 만 다중 L2 소비 허용 (조합기 책임).

### 5 L2 분석엔진 도메인 격리

| Engine | 담당 질문 | 범위 |
|---|---|---|
| `analysis` | 이 회사는 무엇으로 돈을 벌고, 어떻게 남기고, 지금 가격이 어느 정도인가 | 단일 기업 재무제표 22 축 |
| `credit` | 이 회사가 부도 날 가능성·재무 건전성은 | 단일 기업 dCR 등급 + 7 축 |
| `macro` | 시장·경제 환경은 어느 국면이고 다음 시나리오는 | 시장 레벨 6 막 인과 |
| `quant` | 가격·팩터·전략의 정량 신호와 백테스트는 | 가격·수급·공시 텍스트·포트폴리오 |
| `industry` | 이 종목이 밸류체인 어느 공정·peer 그룹에 속하는가 | 산업 분류 + 공정 매핑 + lifecycle |

### 명명 alias 금지 (operation.philosophy §5)

- "6 분석 엔진" 표현 금지 — 5 L2 분석엔진 + L3 조합기 (story) 분리 명시.
- "매퍼 엔진" 단독 표현 금지 (industry) — `L2 분석엔진 (산업 매퍼)` 형식.
- scan 을 "L2" 라고 부르지 않는다 — `L1.5` (전체 횡단).
- story 를 "분석 엔진" 또는 "L2" 와 평탄화하지 않는다 — `L3 조합기` 명시.

