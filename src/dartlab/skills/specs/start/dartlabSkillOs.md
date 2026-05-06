---
id: start.dartlabSkillOs
title: DartLab Skill OS 최초 진입
kind: curated
scope: builtin
status: observed
category: start
purpose: 사람과 LLM 이 DartLab 을 처음 볼 때 Skills 카탈로그 하나에서 분석 · 엔진 능력 · 운영 규칙 · 확장 절차를 찾는 공식 시작점이다. 외부 API 문서나 흩어진 ops 폴더 대신 skill 검색 → frontmatter 확인 → 본문 절차 → 검증 게이트 순서를 따른다.
whenToUse:
  - DartLab 처음 마주친 LLM
  - DartLab 처음 보는 사람
  - 어떤 문서부터 봐야 할지 모를 때
  - 외부 LLM 이 dartlab 작업을 시작할 때
  - 문서 · API 사용법 · 분석 절차가 흩어져 보일 때
  - 전체 체계와 확장 규칙을 한 번에 확인할 때
  - 4 카테고리 (start · runtime · operation · engines) 의 의미 파악
  - skill 검색 패턴 익히기
inputs:
  - 사용자 목적 (분석 · 운영 · 확장 중 어디)
  - 작업 대상 (회사 · 시장 · 절차 · 코드)
  - 실행 환경 (local · MCP · pyodide · web AI)
outputs:
  - 선택한 skill 후보
  - 다음 실행 절차
  - 필요한 evidence ref 목록
  - 검증 게이트
toolRefs:
  - dartlab.skills.search
  - dartlab.skills.get
linkedSkills:
  - start.installUv
  - start.quickStart
  - start.useSkillsCatalog
recipeSteps:
  - skillId: start.installUv
    note: uv 로 dartlab 환경 준비.
  - skillId: start.quickStart
    note: Company · Scan · Ask 8 단계 walkthrough.
  - skillId: start.useSkillsCatalog
    note: 목적 기반 skill 검색 패턴.
sourceRefs:
  - dartlab://skills/start.dartlabSkillOs
  - dartlab://skills/operation.opsAsSkills
  - dartlab://skills/operation.philosophy
  - dartlab://skills/operation.code
  - dartlab://skills/operation.apiContract
requiredEvidence:
  - skillRef
  - sourceRef
expectedOutputs:
  - 시작 skill
  - 필요한 원문 위치
  - 다음 실행 절차
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
procedure:
  - 작업 목적을 4 카테고리 (start · runtime · operation · engines) 중 하나로 분류한다.
  - whenToUse 키워드로 skill 을 검색하고 후보 1~3 개로 좁힌다.
  - 후보 skill 의 frontmatter (purpose · inputs · outputs · runtimeCompatibility) 와 본문 (공개 호출 방식 · 호출 동작) 을 읽는다.
  - 답변에 묶을 evidence (target · period · tableRef · valueRef · dateRef · executionRef) 를 미리 고정한다.
  - skill 의 procedure 또는 코드 예시를 따라 실행하고, 반환값의 source 와 결손을 검증한다.
failureModes:
  - 삭제된 ops 폴더 경로를 직접 순회하다가 적용 규칙 누락
  - 엔진 실행 skill (engines.*) 과 운영 skill (operation.*) 을 구분 못 함
  - sourceRef 없이 규칙 요약
  - 공개 API 변경 후 관련 skill 동기화 누락
  - 후보 / 상위 / 랭킹 답변을 bullet 로만 내고 입력 / 필터 / 계산식 / 표 근거 누락
forbidden:
  - skills 검색 없이 임의 문서를 시작점으로 삼지 않는다.
  - skill 의 공개 API 호출 방식과 실제 코드 동작 불일치를 방치하지 않는다.
  - sourceRef 없는 규칙 설명을 공식 절차로 취급하지 않는다.
  - 결손값을 0 으로 채우지 않는다.
examples:
  - DartLab 어떻게 써?
  - 처음 온 LLM 은 무엇부터 봐야 하나?
  - dartlab 으로 삼성전자 분석하려면?
  - skill 카탈로그에서 가치평가 어떻게 찾나?
  - dartlab 운영 규칙은 어디서 찾나?
  - 매크로 분석 skill 이 어떤 게 있나?
  - dartlab 공시 검색 사용법
  - 외부 모델이 dartlab 기능을 처음 매핑할 때
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-06"
---

DartLab 은 한국 DART 와 미국 EDGAR 공시를 구조화해 코드와 AI 가 직접 다루는 데이터로 만든다. 외부에서 처음 만나는 LLM·사람·기여자는 흩어진 API 문서나 ops 폴더가 아니라 **Skills 카탈로그** 하나에서 시작한다.

각 skill 은 `id` · `purpose` · `whenToUse` · `inputs` · `outputs` · `procedure` · `examples` · `runtimeCompatibility` · `requiredEvidence` 를 frontmatter 에 갖고, 본문에 `## 공개 호출 방식` · `## 호출 동작` · `## 대표 반환 형태` 를 둔다. 사람이 그대로 실행할 수 있고, AI 가 도구로 호출할 수 있다.

## 4 카테고리

| 카테고리 | 의미 | 대표 skill |
|---|---|---|
| `start` | 첫 진입 — 설치 · walkthrough · 카탈로그 사용법 | `start.installUv`, `start.quickStart`, `start.useSkillsCatalog` |
| `runtime` | 실행 환경 — Pyodide · MCP · Web AI · Local Python · VSCode · 노트북 | `runtime.mcp`, `runtime.notebooks`, `runtime.pyodideBrowser` |
| `operation` | 운영 규칙 — 사상 · 코드 품질 · API 계약 · 테스트 · 안정성 · 검증 방법론 | `operation.philosophy`, `operation.apiContract`, `operation.stability` |
| `engines` | 엔진별 기본 사용법 + 응용 실행 — 회사 · 분석 · 시장 스캔 · 매크로 · 퀀트 · 스토리 | `engines.company`, `engines.analysis`, `engines.scan` |

엔진 응용 skill 의 `id` 는 `engines.{group}.{axis}` 형식 (`engines.analysis.cashflow`). 기본 skill 은 `engines.{group}` (`engines.company`).

## 검색 패턴

자연어 질문을 그대로 검색어로 넣는다. dartlab 의 skill `whenToUse[]` 에 한국어 · 영문 키워드가 들어있어 매칭이 직접 일어난다.

| 질문 패턴 | 매칭되는 skill |
|---|---|
| "dartlab 어떻게 써" / "기능" / "사용법" | `start.useSkillsCatalog`, `start.quickStart` |
| "삼성전자 재무 분석" / "Company" / "show" | `engines.company`, `engines.analysis` |
| "ROE / 매출 시장 횡단 스캔" | `engines.scan`, `engines.scan.ratio` |
| "신용 등급 분석" | `engines.credit.creditRisk` |
| "매크로 / 거시 / 경기" | `engines.macro` 군 |
| "공시 검색 / 본문 찾기" | `engines.search`, `engines.company.disclosureEvent` |
| "AI / 자연어 분석" | `runtime.workbenchEvidenceFlow`, `runtime.mcpWorkbench` |
| "테스트 / 검증 방법" | `operation.testing`, `operation.methodology` |

검색에서 후보가 너무 많으면 (`engines.*` 만 148 개) 카테고리 트리에서 sub-group (`analysis`, `scan`, `macro`, `quant` 등) 을 좁힌다. 후보가 너무 적으면 (`engines.{group}` 기본만) whenToUse 키워드를 변형해 응용 skill 을 다시 검색한다.

## 검증 게이트

답변 하기 전 다음을 확인한다:

1. **`sourceRefs`** — 인용 근거 (`dartlab://skills/{id}`).
2. **`requiredEvidence`** — 답변에 묶어야 할 ref 종류 (target · period · tableRef · valueRef · dateRef · executionRef).
3. **`runtimeCompatibility`** — 실행 환경에서 동작 가능한지 (`unsupported` 면 다른 skill 로).
4. **`forbidden`** — 답변에서 어겨선 안 되는 항목.
5. **본문 `## 공개 호출 방식`** — 코드 답변은 이 호출 패턴을 그대로.

위 5 가지가 빠진 답변은 미완성이다.

## AI 환류 흐름

사람이 엔진 코드와 블로그로 자산을 만든다. 엔진의 공개 함수 docstring 이 그대로 AI 의 tool schema 가 되고, skill 본문이 사용 절차다. AI 가 실행 중 발견한 반복 패턴 · 반례 · 새 조합은 엔진 docstring 또는 블로그 frontmatter 로 사람 자산에 환류한다. **엔진이 다리** — 한 파일이 사람의 분석엔진이자 AI 의 skill 본문.

## 다음 단계

- [start.installUv](/skills/start.installUv) — uv 설치와 첫 실행.
- [start.quickStart](/skills/start.quickStart) — 8 단계 walkthrough.
- [start.useSkillsCatalog](/skills/start.useSkillsCatalog) — 검색 → 선택 → 검증 → 실행 패턴.
- [start.firstAnalysisRecipe](/skills/start.firstAnalysisRecipe) — 첫 회사 분석을 위한 4 단계 recipe.
- [operation.opsAsSkills](/skills/operation.opsAsSkills) — 운영 문서가 어떻게 skills 로 흡수됐는지.
- [Skills 카탈로그](/skills) — 179 개 skill 검색.
