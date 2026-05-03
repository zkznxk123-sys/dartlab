---
id: engines.viz
title: Viz
kind: curated
scope: builtin
status: observed
category: engines
purpose: Viz 엔진의 목적, 경계, 조합 기준을 Skill OS에서 확인하고 실행은 capability/docstring으로 내려간다.
whenToUse:
  - Viz
  - viz
  - Appendix. Visual Explanation Engine
  - 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다
  - 2. VizSpec 프로토콜 — 이 구조로 넘긴다
  - 3. AI → 차트 파이프라인 — stdout 마커로 전달한다
  - 4. Company → ChartSpec 자동 생성기 8 종
inputs:
  - 작업 목적
  - 대상 엔진 또는 실행 환경
  - 검증 범위
outputs:
  - selected skill
  - capability/docstring handoff
  - verification gate
capabilityRefs:
  - ChartResult
toolRefs:
  - search_reference
  - run_python
knowledgeRefs:
  - start.dartlabSkillOs
sourceRefs:
  - dartlab://skills/engines.viz
procedure:
  - Appendix. Visual Explanation Engine 기준을 확인한다.
  - 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다 기준을 확인한다.
  - 2. VizSpec 프로토콜 — 이 구조로 넘긴다 기준을 확인한다.
  - 3. AI → 차트 파이프라인 — stdout 마커로 전달한다 기준을 확인한다.
  - 4. Company → ChartSpec 자동 생성기 8 종 기준을 확인한다.
  - '`emit_chart(spec)` — ChartSpec dict 를 stdout 마커로 출력.'
  - '`emit_diagram(type, source)` — 다이어그램 소스를 stdout 마커로 출력.'
  - '`extract_viz_specs(stdout)` — 마커 추출 + 텍스트 정제.'
  - '`AnalysisEvent("chart", {"charts": [spec]})` — SSE 로 전달.'
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
    status: limited
    notes:
      - 실제 실행 가능 여부는 연결된 capability와 데이터 snapshot 범위를 따른다.
failureModes:
  - Skill OS 검색 없이 과거 문서 경로를 직접 찾음
  - API schema를 skill 본문에 중복해 docstring/capability와 어긋남
  - 검증 게이트 없이 변경 또는 답변을 완료 처리함
forbidden:
  - 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다.
  - API parameters/returns를 SkillSpec에 복사하지 않는다.
examples:
  - Viz 규칙 확인
  - viz 작업을 Skill OS에서 시작
source:
  type: absorbed_skill_os
  absorbedKey: viz
  format: markdown
lastUpdated: '2026-05-03'
---

## Skill OS 흡수 규칙

- 이 skill이 공식 진입점이다. 삭제된 운영 문서 경로를 다시 안내하지 않는다.
- API 세부 인자와 반환 구조는 capability/docstring을 확인한다.
- 분석이나 변경 결과는 ref, 실행 로그, 테스트 결과로 검증한다.

## 실행 순서

- Appendix. Visual Explanation Engine 기준을 확인한다.
- 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다 기준을 확인한다.
- 2. VizSpec 프로토콜 — 이 구조로 넘긴다 기준을 확인한다.
- 3. AI → 차트 파이프라인 — stdout 마커로 전달한다 기준을 확인한다.
- 4. Company → ChartSpec 자동 생성기 8 종 기준을 확인한다.
- `emit_chart(spec)` — ChartSpec dict 를 stdout 마커로 출력.
- `emit_diagram(type, source)` — 다이어그램 소스를 stdout 마커로 출력.
- `extract_viz_specs(stdout)` — 마커 추출 + 텍스트 정제.
- `AnalysisEvent("chart", {"charts": [spec]})` — SSE 로 전달.
