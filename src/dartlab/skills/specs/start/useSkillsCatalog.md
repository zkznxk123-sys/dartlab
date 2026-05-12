---
id: start.useSkillsCatalog
title: Skill catalog 기반 작업 시작
kind: curated
scope: builtin
status: observed
category: start
purpose: dartlab 코드 전체를 읽기 전에 skills catalog 만 보고 목적 skill · 공개 호출 방식 · 대표 반환 형태 · 근거 요구사항을 찾는 시작 절차다. AI 와 사람이 같은 표면을 보고 같은 속도로 진입한다.
whenToUse:
  - dartlab skills 어떻게 써
  - dartlab 뭐 할 수 있어
  - dartlab 기능과 가능한 분석
  - 스킬만 보고 시작
  - 외부 AI 가 dartlab 기능을 찾기
  - 목적 기반 capability 검색
  - show 함수 사용법
  - skill 검색 패턴
  - whenToUse 키워드 어떻게 매칭
  - dartlab 기능 카탈로그 본다
inputs:
  - 사용자 질문 (자연어)
  - 작업 카테고리 (분석 · 운영 · 확장 중)
outputs:
  - selectedSkill
  - capabilityRefs
  - requiredEvidence
  - runtime limits
capabilityRefs:
  - Company
  - Company.show
  - Company.analysis
  - gather
  - scan
  - macro
  - quant
  - ChartResult
  - ask
toolRefs:
  - dartlab.skills.search
  - dartlab.skills.get
  - search_reference
linkedSkills:
  - start.dartlabSkillOs
  - start.installUv
  - start.quickStart
sourceRefs:
  - dartlab://skills/start.useSkillsCatalog
requiredEvidence:
  - skillRef
expectedOutputs:
  - 목적 skill 후보
  - capability ref 목록
  - 실행 전 확인할 evidence 목록
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
    limitations:
      - 실제 분석 실행 가능 여부는 선택한 skill 의 runtimeCompatibility 를 따른다.
procedure:
  - 사용자 질문을 그대로 skill 검색어로 사용한다 (자연어 그대로, whenToUse[] 가 매칭).
  - 후보가 너무 많으면 카테고리 (start · runtime · operation · engines) 또는 sub-group 으로 좁힌다.
  - 후보 skill 의 frontmatter (purpose · inputs · outputs · runtimeCompatibility) 와 본문 (## 공개 호출 방식 · ## 호출 동작) 을 읽는다.
  - capabilityRefs · requiredEvidence · forbidden 을 확인하고 답변에 묶을 ref 종류를 고정한다.
  - skill 의 procedure 또는 코드 예시를 따라 실행하고, 반환 source 와 결손을 검증한다.
failureModes:
  - 엔진 기본 skill 을 보지 않고 capability 이름만 보고 분석 시작
  - dartlab 기능 설명 질문을 RuntimeDatasetCatalog 만으로 답함
  - skill 의 ## 공개 호출 방식 과 ## 대표 반환 형태 를 확인하지 않음
  - requiredEvidence 확인 없이 답변 작성
  - whenToUse 매칭 후보를 1 개로만 보고 끝냄
forbidden:
  - skill 과 실제 공개 API 의 불일치를 방치하지 않는다.
  - capabilityRefs 확인 없이 실행 코드 작성하지 않는다.
  - sourceRefs 없는 답변을 공식 절차로 취급하지 않는다.
examples:
  - dartlab skills 어떻게 써?
  - 스킬만 보고 삼성전자 분석을 시작하려면?
  - 가치평가 skill 어디 있나?
  - dartlab 으로 시장 횡단 스캔 어떻게?
  - AI workflow skill 찾기
  - 검증 방법 skill 어디?
  - dartlab 기능 모르겠을 때 어디 봐
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-06"
---

dartlab 의 모든 기능은 **`/skills` 카탈로그** 에 진입한다. 사람과 AI 가 같은 표면을 본다. 외부 API 문서나 코드 트리 직접 탐색 대신 skill frontmatter 와 본문으로 시작한다.

## 검색 → 선택 → 검증 → 실행

### 1. 검색

자연어 질문을 그대로 검색어로. dartlab skill 의 `whenToUse[]` 에 한국어 + 영문 키워드가 풍부하게 들어있어 매칭이 직접 일어난다.

```
"삼성전자 재무 분석"  →  engines.company / engines.analysis
"시장 ROE 횡단"      →  engines.scan / engines.scan.ratio
"신용 등급 분석"      →  engines.credit.creditRisk
"공시 변경 추적"      →  engines.company.disclosureEvent
"매크로 분석"        →  engines.macro 군 (12 개)
"AI workflow"       →  runtime.workbenchEvidenceFlow
```

### 2. 선택

후보 1~3 개를 frontmatter 만 보고 좁힌다.

- **`purpose`** — 1~2 줄. 이게 내 질문에 맞나?
- **`inputs` · `outputs`** — 어떤 인자를 받고 어떤 결과를 내나?
- **`runtimeCompatibility`** — 내 실행 환경 (`localPython` · `mcp` · `pyodide` 등) 에서 동작?
- **`whenToUse`** — 내 질문과 실제로 매칭되는지 재확인.

후보가 1 개로 좁혀지지 않으면 **엔진 기본 skill (`engines.{group}`)** 부터 본다 — 거기서 응용 skill 로 좁힌다.

### 3. 검증

본문 진입 — 답변 전 다음 5 가지 확인:

| 확인 | 위치 |
|---|---|
| 호출 방법 | 본문 `## 공개 호출 방식` |
| 입출력 형태 | 본문 `## 호출 동작` + `## 대표 반환 형태` |
| 답변에 묶을 evidence | frontmatter `requiredEvidence[]` |
| 어겨선 안 되는 항목 | frontmatter `forbidden[]` |
| 흔한 실패 회피 | frontmatter `failureModes[]` |

### 4. 실행

skill 의 코드 예시를 그대로 실행한다 (또는 MCP tool 로 호출). 결과의 `source`, 결손값, ref 를 검증하고 답변에 묶는다.

## 자주 쓰는 검색 패턴

| 질문 패턴 | 추천 skill |
|---|---|
| 회사 분석 진입 | `engines.company`, `engines.company.sections` |
| 재무비율 / ROE / OPM | `engines.analysis.profitability`, `engines.scan.ratio` |
| 시장 횡단 (전 종목) | `engines.scan` 군 (19 축) |
| 매크로 / 거시 / 경기 | `engines.macro` 군 (12 축) |
| 가치평가 | `engines.analysis.valuation`, `engines.quant.damodaranValuation` |
| 신용 / 부실 위험 | `engines.credit.creditRisk` |
| 공시 검색 / 본문 | `engines.search`, `engines.company.disclosureEvent` |
| 보고서 / story | `engines.story` 군 |
| AI / 자연어 분석 | `runtime.workbenchEvidenceFlow`, `runtime.mcpWorkbench` |
| 노트북 (Colab · marimo) | `runtime.notebooks` |
| 운영 규칙 (테스트 · 안정성) | `operation.testing`, `operation.stability`, `operation.methodology` |

## capability vs skill — 다른 결

- **capability** = `Company.show` 같은 공개 함수 식별자 (코드 원천).
- **skill** = 그 capability 를 어떤 절차로 쓰는지 + 입출력 + 검증 (사용 절차 SSOT).

skill 본문은 capability 의 사용 설명. 세부 인자와 전체 반환 필드는 capability docstring 으로 검산한다 (skill 본문에 docstring 통째로 복사 금지 — SSOT 분리).

## 다음 단계

- [start.dartlabSkillOs](/skills/start.dartlabSkillOs) — Skill OS 5 카테고리 + 검증 게이트.
- [start.installUv](/skills/start.installUv) — uv 설치와 첫 실행.
- [start.quickStart](/skills/start.quickStart) — 8 단계 walkthrough.
- [start.firstAnalysisRecipe](/skills/start.firstAnalysisRecipe) — 첫 회사 분석 recipe.
- [Skills 카탈로그](/skills) — 179 개 skill 검색.
