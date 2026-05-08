---
id: operation.aiProductReplatform
title: DartLab AI 제품 바탕 교체
kind: curated
scope: builtin
status: observed
category: operation
purpose: 기존 DartLab web chat과 AI 엔진을 백업으로 분리하고, LibreChat UI 바탕과 AG-UI 공개 이벤트, LangGraph/Dexter식 금융 research loop로 제품 경계를 재설계하는 공식 전환 계약이다.
whenToUse:
  - AI 채팅 표면을 구현할 때
  - Agent Gateway 이벤트 계약을 바꿀 때
  - Research Graph 노드와 검증 게이트를 바꿀 때
  - LibreChat-derived UI를 DartLab shell에 연결할 때
inputs:
  - user question
  - thread messages
  - workspace context
  - DartLab Skill OS and data refs
outputs:
  - AG-UI public stream
  - assistant response
  - concise activity
  - evidence refs
  - artifacts
toolRefs:
  - dartlab.skills.search
  - dartlab.skills.get
sourceRefs:
  - dartlab://skills/operation.aiProductReplatform
  - dartlab://skills/operation.ui
requiredEvidence:
  - skillRef
  - sourceRef
  - executionRef
  - verifyRef
expectedOutputs:
  - product path contract
  - UI replacement boundary
  - engine graph contract
  - verification gate
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: limited
  webAi:
    status: supported
  pyodide:
    status: limited
    notes:
      - Product replatform contract is readable in Pyodide; server-side Agent Gateway execution is not available in-browser.
failureModes:
  - backup 디렉터리를 만들지 않고 기존 UI/AI 위에 덕지덕지 덧붙임
  - internal TraceEvent를 UI에 직접 노출함
  - tool 실행 순서와 spinner 상태를 public event에서 재구성하지 못함
  - 검색만 하고 응답을 성공 처리함
  - 숫자·날짜·표 claim이 ref 없이 release됨
forbidden:
  - "`search_reference`, `draft_rejected`, `prose_without_finalize` 같은 내부명을 채팅 본문에 노출하지 않는다."
  - "`Agent Trace`, raw JSON, provider 내부 오류코드를 채팅 본문 카드로 렌더하지 않는다."
  - 구 AI 엔진 백업을 새 production path에서 import하지 않는다.
examples:
  - DartLab web chat을 LibreChat-derived surface로 교체
  - "`/api/ask` stream을 AG-UI public event stream으로 검증"
  - "Workbench 가 `BRIEF → WORK → CRITIQUE → COMPOSE → GATE → HARVEST` 5 패스 순서로 실행되는지 확인"
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-04"
---

## 확정 방향

- DartLab 제품은 유지한다. 교체 대상은 기존 `ui/web` 채팅 표면과 기존 `src/dartlab/ai` 엔진 구현이다.
- 기존 구현은 백업으로 분리한다.
  - UI 백업: `ui/web_legacy_backup_20260504`
  - AI 백업: `src/dartlab/ai_legacy_backup_20260504`
- 새 UI 바탕은 LibreChat repository를 `ui/web`에 vendoring한다. DartLab은 LibreChat 서버/auth/provider stack을 그대로 운영하지 않고, client data model과 ChatGPT-like surface를 DartLab shell에 붙인다.
- 공개 AI 답변 진입점은 `dartlab.ask(...)`와 `/api/ask`다. UI도 `/api/ask` stream을 사용한다.
- 새 production 엔진 경계는 `DartLabResearchGraph`다. `runAsk`는 public export로 유지하지 않는다.

## 외부 기준

- LibreChat은 self-hosted ChatGPT-like 제품 바탕, agents, tools, artifacts 개념을 제공한다.
- AG-UI는 `TEXT_MESSAGE_*`, `TOOL_CALL_*`, `STATE_*`, `ACTIVITY_*`, `RUN_FINISHED`, `RUN_ERROR` 같은 사용자 표면 이벤트를 표준화한다.
- LangGraph는 durable execution, streaming, human-in-the-loop, stateful long-running agent orchestration을 제공한다. DartLab은 LangGraph Platform 종속 없이 OSS graph/checkpoint 사상을 흡수한다.
- Dexter는 금융 research agent의 planning, tool call scratchpad JSONL, self-validation, evaluation loop를 참고한다.

## 제품 경계

```text
DartLab App
  -> LibreChat-derived UI/data model
  -> /api/ask stream
  -> Agent Gateway
  -> DartLabResearchGraph
  -> Skill OS / Data engines / RunPython / verifier
  -> Evidence / Artifact store
```

## UI 계약

- 채팅 본문 허용 표면은 assistant response, concise activity, tool card, source/artifact strip, failure notice다.
- raw tool input/output, source snippets, verification issue, dataset schema, execution table은 Evidence panel로만 간다.
- activity는 시간 순서대로 append한다. 완료 이벤트가 진행 중 이벤트보다 먼저 보이면 UI 계약 위반이다.
- spinner는 `status=running`인 현재 activity/tool call에만 붙인다. 완료된 search/read/verify 항목에는 spinner를 붙이지 않는다.
- 내부 tool id 표시명은 공백 표기로 바꾼다. 예: `search_reference`는 본문에 나오지 않고 `search reference 실행함`만 허용한다.

## Engine 계약

- `WorkbenchLoop.nodes` (= `DartLabResearchGraph.nodes`) 는 5 패스 단일 SSOT 로 고정한다.
  - `brief` — 질문 해석 + skill/capability 후보 + recall + 검증 기준 + lens 분기
  - `work` — RunPython / InspectDataset / EngineCall / WebSearch / SaveArtifact 반복
  - `critique` — 반대가설 / 누락 lens / 데이터 신선도 점검
  - `compose` — 답안 + claim 별 [refId] 묶음
  - `gate` — claim ↔ ref 매칭 검증 (programmatic)
  - `harvest` — propose_skill 후보 + decision remember
- `brief` 는 질문별 답변 분기자가 아니라 target, 비교 여부, 필요한 evidence 같은 profile 만 만들고, 선택 skill 의 `requiredEvidence` 를 그대로 GATE 동적 체크리스트로 주입한다. 옛 `routeIntent / selectSkill / searchCapability / planEvidence` 4 단계는 본 패스 안에 흡수되었다.
- 최종 실행 계획은 반드시 `dartlab.skills` 검색 결과와 generated capability/docstring 검색 결과로 만든다.
- 질문 문구별 if/else 라우팅, 종목/엔진별 임시 helper, 템플릿 답변은 production 경로에 두지 않는다.
- 정체성 prompt 에 6 막 인과 같은 분석 단계를 모든 질문에 강제하는 한 줄을 박지 않는다. 단계가 필요한 skill 은 그 skill 의 `requiredEvidence` 로 표현한다.
- LLM 에게 DartLab API 수십 개를 직접 tool 로 노출하지 않는다. LLM 은 `ReadSkill`, `ReadCapability`, `RunPython`, `EngineCall`, `InspectDataset`, `WebSearch`, `SaveArtifact`, `propose_skill` 수준의 작은 도구만 본다.
- `RunPython` 은 금융 데이터 계산의 중심 작업공간이다. Company, scan, macro, quant, analysis 는 Python 코드에서 조합하는 DartLab library 다.
- 모든 중간 산출물은 ref 로 남긴다. 최소 ref 종류는 `skillRef`, `apiRef`, `executionRef`, `tableRef`, `valueRef`, `dateRef`, `webRef`, `artifactRef`, `verifyRef` 다. ref kind 발급 책임은 `runtime.workbenchEvidenceFlow` 의 표가 SSOT.

## Release Gate

- `너 뭐 할 수 있니`는 실패 카드가 아니라 DartLab capability 답변을 반환해야 한다.
- 검색-only 응답은 성공 처리하지 않는다. 답변에는 검증된 `skillRef` 이상이 있어야 한다.
- 계산/랭킹/비교 질문은 `executionRef` 또는 `tableRef`가 없으면 production 품질로 release하지 않는다.
- 숫자 claim은 `valueRef/tableRef`, 날짜 claim은 `dateRef` 검증 없이는 release하지 않는다.
- provider/tool/finalize 실패를 숨기지 않는다. 단, 채팅 본문에는 사용자용 실패 문구만 노출한다.

## Answer Quality Gate

- 품질 판정은 “정상 종료”가 아니라 실제 답변 원문 기준으로 한다.
- `삼성전자 재무제표 확인`은 `Company.show("BS")`, `Company.show("IS")`, `Company.show("CF")` 실행 결과를 사용하고, 핵심 계정은 조원/억원 포맷으로 보여준다.
- `자산/부채/자본` 질문은 재무상태표 중심으로 답하고, 자산총계·부채총계·자본·부채/자본 비율 해석을 포함한다.
- `A와 B 재무상태표 비교`는 두 회사를 모두 확정하고 같은 기준시점의 표와 핵심 차이를 함께 낸다.
- `성장하는 회사`, `성장주`, `growth` 질문은 Skill OS 설명에서 멈추지 않고 `dartlab.scan("growth")`를 실행해 후보 evidence table을 낸다.
- 성장 후보는 최소 매출CAGR·영업이익CAGR·순이익CAGR이 모두 양호하고, 매출 규모와 기간이 제한 조건을 통과한 행만 상위 후보로 제시한다.
- 서버 경유 `/api/ask` audit에서 한글 본문, 표, 숫자 포맷, ref 분리가 직접 확인되기 전에는 품질 개선 완료를 주장하지 않는다.

## 구현 순서

1. 백업 분리: 기존 `ui/web`, `src/dartlab/ai`를 legacy backup 디렉터리로 이동한다.
2. LibreChat vendoring: `ui/web`에 upstream UI 바탕을 가져오고 nested git metadata를 제거한다.
3. 서버 연결: `_ui_path.py`가 `ui/web/client/dist`를 공식 dev build 산출물로 인식한다.
4. Agent Gateway: `/api/ask` stream은 AG-UI allowlist만 방출한다.
5. Research Graph skeleton: import 가능한 새 AI 패키지, Skill OS reference search, deterministic capability answer, done meta를 닫는다.
6. LangGraph 흡수: graph checkpoint, thread id, durable replay, node-level side-effect task를 추가한다.
7. Dexter 흡수: query scratchpad JSONL, tool call limit, loop detection, result summary, eval runner를 추가한다.
8. UI 흡수: LibreChat message/conversation/tool/artifact components를 DartLab API와 AG-UI event source에 연결한다.
9. Evidence panel: raw refs, execution, verification, artifacts를 채팅 밖 패널로 분리한다.
10. Audit: 기능 안내, 재무상태표, 성장주 scan, 종목 비교, 매크로, 계산, provider 실패, tool 실패, empty final을 서버 경유로 검증한다.
