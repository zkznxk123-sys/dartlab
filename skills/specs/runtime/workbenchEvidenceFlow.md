---
id: runtime.workbenchEvidenceFlow
title: Workbench 근거 생성과 검산 흐름
kind: curated
scope: builtin
status: unverified
category: runtime
purpose: skill 절차를 실행 결과 ref와 최종 검산으로 연결하는 공통 작업 흐름이다.
whenToUse:
  - 실행하고 근거 남기기
  - 검산하고 답변 마무리
  - evidence ref 만들기
  - run_python 결과를 답변 근거로 쓰기
inputs:
  - selectedSkill
  - capabilityRefs
outputs:
  - executionRef
  - tableRef
  - valueRef
  - dateRef
  - verifyRef
toolRefs:
  - search_reference
  - inspect_dataset
  - run_python
  - compile_visual
  - finalize_answer
requiredEvidence:
  - skillRef
  - execution
  - table
expectedOutputs:
  - 검산 가능한 답변 초안
  - refs
  - limits
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
    limitations:
      - 브라우저에서는 선택한 skill과 dataset snapshot 범위 안에서만 실행한다.
failureModes:
  - 실행 결과 없이 계산 답변 작성
  - 실패한 실행을 숨김
  - date ref 없이 최신성 주장
  - table ref 없이 ranking 또는 chart 주장
  - ranking/candidate 최종 답변에 table ref만 제출하고 사람이 읽을 evidence table을 쓰지 않음
  - 입력/유니버스, 필터, 계산식/지표, 결과를 답변에 명시하지 않아 재현 불가능함
  - 문자열 날짜/라벨 컬럼을 table metric으로 지정해 검증 실패
  - 사용법 답변의 코드 예시 숫자를 근거 없는 재무 claim처럼 제출
  - evidence refs는 제출했지만 material claim별 refs가 비어 있어 숫자 검산 실패
  - 여러 실행 중 실패한 초안의 숫자 claim을 최종 답변에 남김
forbidden:
  - tool call transcript를 최종 답변으로 노출
  - 근거 없는 숫자 claim
  - 단일값 chart
  - run_python 코드 안에서 emit_result를 재정의
  - 후보·상위·랭킹 답변을 bullet 나열로만 마무리
examples:
  - 실행하고 근거 남기는 순서 알려줘
  - 검산하고 답변을 마무리하려면?
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- Workbench 공식 순서는 `routeIntent → selectSkill → searchCapability → planEvidence → executeTool → observeResult → verifyClaims → composeAnswer → repairOrFail`이다.
- `routeIntent`는 profile 생성만 담당한다. 실행 계획은 질문 문자열 하드코딩이 아니라 선택된 skill의 `requiredEvidence`/`toolRefs`/`knowledgeRefs`와 generated capability/docstring 결과로 만든다.
- root `skills/`가 실행 절차 SSOT이고, `CAPABILITIES`/docstring이 호출 가능 API SSOT다. AI 내부에 별도 skill resolver나 capability index를 중복 생성하지 않는다.
- 선택한 skill의 requiredEvidence를 실행 전 체크리스트로 둔다.
- dataset이 필요한 질문은 먼저 inspect 단계로 schema, latest, metric 후보를 확인한다.
- 계산은 실행 결과가 table/value/date ref를 만들 수 있게 수행한다. 표를 만들 때 `metric`은 숫자 컬럼으로 두고, 날짜·라벨·식별자는 `meta`, `asOf`, `period`, `target` 또는 별도 문자열 컬럼으로 둔다.
- `emit_result`는 run_python prelude가 제공하는 예약 helper다. 직접 `def emit_result`로 만들거나 다른 값으로 덮어쓰지 않는다.
- 기능 설명이나 API 사용법처럼 계산이 필요 없는 질문은 run_python으로 가짜 evidence table을 만들지 않는다. skill/capability ref를 근거로 좁은 설명을 제출한다.
- 시각화는 table ref가 있고 2개 이상 비교 가능한 값이 있을 때만 만든다.
- 최종 답변은 evidence refs와 limits만 제출해서 끝내지 않는다. 숫자·날짜·ranking 같은 material claim은 각 claim 안에서 supporting table/value/date ref를 직접 가리켜야 한다.
- 후보·상위·랭킹 최종 답변은 `입력/유니버스`, `필터`, `계산식/지표`, `결과`를 포함하고, 회사/식별자, 기준 기간, 원값, metric, rank가 들어간 markdown evidence table을 본문에 렌더링한다.
- 검산 실패 후 재시도할 때는 실패한 초안의 숫자 문장을 그대로 유지하지 말고, ref로 뒷받침되는 claim만 남긴다.
- 서버 audit runner는 원문 답변과 refs/events/meta를 캡처만 한다. 품질 pass/fail은 저장된 답변 원문을 사람이 직접 읽고 별도 review 기록으로 판정한다.

