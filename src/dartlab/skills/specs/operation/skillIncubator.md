---
id: operation.skillIncubator
title: Skill Incubator — AI 자율 분석 skill 개발 사이클
kind: curated
scope: builtin
status: unverified
category: operation
purpose: AI 가 분석 빈칸을 발굴해 skill 초안을 만들고, 같은 세션에서 자가 실행으로 품질을 검증한 뒤 정식 skill 로 굳히는 5 단계 사이클을 정의한다. 트리거 — '신규 분석 skill 만들자', '분석 빈칸 메우기', '효과적인 skill 굳히기'.
whenToUse:
  - 신규 분석 skill 후보 발굴
  - Company/gather/scan 원천 데이터로 빈칸 메우기
  - skill 초안을 직접 써보고 품질 검증
  - 인큐베이팅 skill 을 정식 specs/ 로 승격
  - 분석 skill 의 ground-truth 비교
  - skillIncubator
  - skill incubation
  - skill 자가 검증 파이프라인
inputs:
  - 분석 빈칸 후보 (자유형 슬러그 또는 자동 발굴)
  - ground-truth 종목 3 개 (성공 / 실패 / 위기 또는 등가 케이스)
outputs:
  - incubating skill markdown (.dartlab/skills/incubating/{id}.md)
  - selfRun 결과 표 (3 케이스 × evidence)
  - graduate 결정 (정식 specs/ 등재 또는 회귀)
capabilityRefs: []
toolRefs:
  - ReadSkill
  - GetSkillBody
  - ReadCapability
  - EngineCall
  - RunPython
  - SaveArtifact
  - RunWorkbench
knowledgeRefs:
  - operation.extendSkills
  - operation.coreloop
  - operation.opsAsSkills
  - runtime.workbenchEvidenceFlow
sourceRefs:
  - dartlab://skills/operation.skillIncubator
procedure:
  - gapSpot — ReadCapability + ReadSkill 로 *현재 노출되지만 분석 skill 없는* axis 식별 후 후보 5~8 개 nominate (axis 명 / 사용 데이터 / 가설).
  - protoSkill — 후보 1 개 선택. SCHEMA.md 준수 markdown 초안을 `.dartlab/skills/incubating/{category}.{slug}.md` 에 SaveArtifact 로 저장. requiredEvidence[] 에 ground-truth 3 케이스 명시.
  - selfRun — 같은 세션에서 ReadSkill 로 재로드 후 capabilityRefs 를 EngineCall/RunPython 으로 3 케이스 전부 실행. 출력 ref + 정량 결과 누적.
  - redTeam — RunWorkbench 의 CRITIQUE 패스로 (a) 반대 가설 (b) 누락 데이터/edge case (c) 다른 axis 와 중복성 점검. 통과 못하면 protoSkill 재집필 1 회 회귀.
  - graduate — 통과 시 specs/{category}/{slug}.md 로 이동 + generateSkills.py 로 index.json 갱신 + 운영자 ack 1 줄 (ok 또는 reject 와 사유). 미통과 시 incubating 에 회귀 카운트 누적, 3 회 초과 폐기.
requiredEvidence:
  - groundTruthCases (3 종목)
  - selfRunResultTable
  - redTeamCheck
  - skillRef (incubating + 승격 후 정식 id)
expectedOutputs:
  - 빈칸 후보 표 (gapSpot 결과)
  - incubating skill 본문
  - selfRun 결과 표 (3 케이스 × evidence ref)
  - redTeam 통과 여부 + 사유
  - graduate 최종 위치
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
    notes:
      - selfRun 단계의 EngineCall/RunPython 은 server/localPython 환경 필요. webAi 단독으로는 protoSkill 작성까지만 가능.
  pyodide:
    status: limited
    notes:
      - 일부 capability (대량 parquet, MCP) 미지원으로 selfRun 부분 실행만 가능.
failureModes:
  - ground-truth 케이스 없이 selfRun 통과시킴 (정성 평가 회귀)
  - incubating skill 을 selfRun 없이 바로 specs/ 로 등재
  - 1 종목으로만 검증 (3 케이스 강행규칙 위반)
  - redTeam 회귀 횟수 누적 없이 무한 재집필
  - 동일 axis 가 이미 analysis/scan/quant 에 존재함을 점검 안 함
forbidden:
  - 운영자 ack 없이 graduate 실행
  - specs/ 디렉터리에 검증 미통과 skill 직접 쓰기
  - selfRun 결과를 외부 본문으로 인용 (sourceType=external 마커 누락)
  - 종목 3 개 동시 메모리 로드 (CLAUDE.md 메모리 안전 위반)
examples:
  - 분석 axis 빈칸 메우자 — gapSpot 후보 표 → protoSkill 1 개 선정
  - flowAnomaly skill 만들어보자 — protoSkill → selfRun (005930/047810/138930) → redTeam → graduate ack 대기
  - 이번에 만든 incubating skill 정식으로 등재 — graduate 단계만 실행
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-08"
---

## 무엇을 하나

DartLab 의 analysis 엔진은 25 axis 로 *재무 인과* 영역을 두텁게 덮고 있지만, Company/gather/scan 이 노출하는 원천 데이터 (가격·수급·뉴스·컨센서스·내부자거래·배당이벤트·공시텍스트·거시지표) 의 *시장신호·이벤트추적·시계열 누적* 관점은 빈칸이 많다.

이 skill 은 그 빈칸을 AI 가 자율로 메우는 5 단계 사이클을 정의한다. 책임 경계:

- **operation.extendSkills** — *승격 규칙* SSOT. user → curated 승격 기준, official 조건.
- **operation.coreloop** — 자가개선 루프 *전체* SSOT. AuditPacket/ImprovementCandidate 같은 메타 흐름.
- **operation.skillIncubator** (본문) — 신규 분석 skill *인큐베이션 사이클* SSOT. gapSpot → graduate 5 단계만.

세 skill 은 중복 규칙 금지 — 인큐베이션은 사이클만, 승격은 규칙만, coreloop 은 메타만.

## 5 단계 사이클

```
gapSpot → protoSkill → selfRun → redTeam → graduate
            (.dartlab/skills/incubating/)         (specs/{category}/)
```

### 1. gapSpot

- `dartlab.skills.search(축_명사구)` 로 *없음* 확인.
- ReadCapability 로 Company/gather/scan 의 노출 데이터 인벤토리 확인.
- 후보 5~8 개를 표로 nominate. 각 후보는 `(axis 명 / 사용 데이터 / 가설 한 줄)`.
- 후보 1 개 선택은 운영자 발화 또는 AI 자체 판단 (위험 낮은 것부터).

### 2. protoSkill

- SCHEMA.md `## 1. 4 카테고리` 표에 따라 카테고리 결정. 신규 axis 가 *signal/event* 영역이면 `engines.scan.{slug}` 또는 `engines.analysis.eventBased.{slug}`. *재무 인과* 면 `engines.analysis.{slug}`.
- 초안 markdown 을 `.dartlab/skills/incubating/{category}.{slug}.md` 경로에 SaveArtifact 로 저장.
- frontmatter 필수 5 개 (id·title·category·purpose·whenToUse) 채우고 `requiredEvidence[]` 에 ground-truth 3 케이스 명시 — 예: 005930 (성공), 047810 (위기), 138930 (저평가).
- 본문 강제 섹션 (engine skill 인 경우): `## 공개 호출 방식`, `## 호출 동작`, `## 대표 반환 형태`.

### 3. selfRun

- 새로 저장한 incubating skill 을 ReadSkill 로 다시 로드 (검증 — 같은 세션에서 검색 매칭되는지).
- capabilityRefs 의 각 API 를 EngineCall 로 호출, 보조 계산은 RunPython.
- 3 케이스를 *순차* 실행 (CLAUDE.md 메모리 안전: 동시 로드 ≤ 2).
- 결과 표: `(케이스 / 입력 / 출력 / evidence ref)` 4 열. 각 행은 1~2 줄.

### 4. redTeam

- RunWorkbench 의 CRITIQUE 모드 또는 명시 검토 프롬프트로:
  1. **반대 가설** — 같은 데이터로 정반대 결론이 나오는 시나리오 가능한가?
  2. **누락 데이터 / edge case** — 분기 결손, IPO 1 년 미만, 해외 dual listing 등에서 동작 보장되는가?
  3. **중복성** — 이미 analysis/scan/quant 의 어느 axis 와 90% 이상 겹치는가?
- 셋 다 통과해야 4 단계 완료. 하나라도 실패면 protoSkill 재집필 1 회 회귀.
- 회귀 카운트는 incubating skill frontmatter 의 `lastUpdated` + 본문 끝 `<!-- redTeamRetry: N -->` 주석으로 추적. 3 회 초과 시 폐기.

### 5. graduate

- 운영자에게 다음 4 가지를 한 응답에 보여준다:
  1. selfRun 결과 표 (3 케이스 × evidence)
  2. redTeam 통과 사유
  3. incubating skill 본문 요약 (frontmatter + 본문 핵심 3 줄)
  4. 정식 등재 위치 제안 (`specs/{category}/{slug}.md`)
- 운영자 ack 1 줄: `ok` 또는 `reject: 사유`.
- `ok` 시:
  - `mv .dartlab/skills/incubating/{category}.{slug}.md src/dartlab/skills/specs/{category}/{slug}.md`
  - `uv run python -X utf8 scripts/build/validateSkills.py src/dartlab/skills/specs/{category}/{slug}.md`
  - `uv run python -X utf8 scripts/build/generateSkills.py` — index.json 갱신
- `reject: 사유` 시: incubating 에 머무르며 회귀 카운트 +1.

## ground-truth 케이스 정책

- 3 케이스는 가능하면 *알려진 대표 사례* — DartLab 기존 분석/뉴스에서 진단이 명확한 종목.
  - 성공: 005930 (삼성전자) — 대형 안정형
  - 위기: 047810 (한국항공우주) 또는 동등 위기 사례
  - 저평가/턴어라운드: 138930 (BNK금융지주) 또는 동등
- 케이스 set 은 incubating skill frontmatter 에 명시 + 향후 동일 skill 의 backtest 시 재사용.
- 3 케이스 모두 *방향성 일치* 면 통과. 1 개라도 반대 진단이면 redTeam 재진입.

## 책임 분리 — extendSkills / coreloop 와 차이

| skill | 다루는 것 |
|---|---|
| operation.skillIncubator (본 skill) | 인큐베이션 사이클 5 단계 — gapSpot → protoSkill → selfRun → redTeam → graduate |
| [operation.extendSkills](/skills/operation.extendSkills) | user → curated 승격 *규칙* (lint, audit P, 운영자 확인). graduate 단계가 호출. |
| [operation.coreloop](/skills/operation.coreloop) | 자가개선 루프 *전체* SSOT (AuditPacket/ImprovementCandidate 메타). 인큐베이션은 그 하위 한 사이클. |

## 트리거

- 자유형 발화: "신규 분석 skill 만들자", "분석 빈칸 메우기", "효과적인 skill 굳히기", "consensusRevision skill 만들어보자".
- slash command: `/skill-incubate {gap_slug?}` — 인자 있으면 gapSpot 생략하고 protoSkill 부터 시작.

## 다음 단계

- [operation.extendSkills](/skills/operation.extendSkills) — graduate 단계의 승격 규칙
- [runtime.workbenchEvidenceFlow](/skills/runtime.workbenchEvidenceFlow) — selfRun/redTeam 의 GATE 검증 메커니즘
- [operation.opsAsSkills](/skills/operation.opsAsSkills) — skill 동기화 강제규칙 (graduate 후 docstring/SkillSpec 정합성)
