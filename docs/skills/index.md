---
title: DartLab Skills
description: DartLab의 모든 분석 절차와 AI/MCP/Web 실행 흐름은 SkillSpec에서 생성되는 Skill Docs를 기준으로 한다.
---

# DartLab Skills

이 문서는 `src/dartlab/skills` SkillSpec에서 생성된다. 직접 수정하지 않는다. 사람, 자체 AI, 외부 AI, MCP, Web UI는 같은 skill resolver와 같은 capability ref를 본다.

## 사용 원칙

- 분석 절차는 먼저 skill을 검색한다.
- 선택한 skill의 `capabilityRefs`로 공개 API docstring/capability를 확인한다.
- 실행 가능 범위는 `runtimeCompatibility`로 확인한다.
- 결과는 table/value/date/visual 같은 근거 ref로 남긴 뒤 최종 답변 전에 검산한다.

## 카테고리

- [Start](start) — 2개: 설치, 첫 실행, skill catalog 사용법처럼 처음 진입할 때 필요한 절차.
- [Runtime](runtime) — 5개: Local Python, Pyodide, Web AI, MCP, VSCode 같은 실행 환경별 제약과 근거 흐름.
- [Engines](engines) — 10개: DartLab 엔진을 어떤 목적에 연결할지 알려주는 사용 지도.
- [Screens](screens) — 3개: scan/gather 기반 후보 발굴, 횡단 비교, 시장 필터링 절차.
- [Finance](finance) — 14개: 기업 분석, 공시 이벤트, 신용, 밸류에이션, 현금흐름 등 금융 리서치 절차.
- [Visuals](visuals) — 1개: 표 근거가 있는 차트와 시각 산출물을 만들고 검증하는 절차.
- [Basic Engine Maps](basic) — 10개: 공개 docstring/capability에서 자동 생성한 엔진별 능력 지도.
- [Capability Reference](capability) — 137개: 공개 API docstring에서 자동 생성한 capability 검색 진입점.

## Runtime 특화 목록

- [Pyodide 가능 skill 목록](pyodide)
