---
id: engines.recipe.usageAndApi
title: dartlab 사용법·API 설명 (RunPython 우회)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: dartlab 의 기능·사용법·API 를 설명하는 질문에서 ReadSkill + ReadCapability 만 사용하고 RunPython 가짜 evidence 를 만들지 않는 절차. 트리거 — '사용법 안내', 'API 도움말', 'dartlab 호출 예시'.
whenToUse:
  - dartlab 사용법
  - 어떤 기능이 있나
  - 너 뭐 할 수 있니
  - dartlab 으로 뭐 가능
  - 어떻게 쓰나
  - API 설명
  - 함수 사용법
  - capability 설명
linkedSkills:
  - start.dartlabSkillOs
toolRefs:
  - ReadSkill
  - ReadCapability
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: supported
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
# 사용법 질문은 ReadSkill + ReadCapability 만 사용
# RunPython 으로 가짜 숫자 만들지 않는다
from dartlab.ai.tools.readSkill import readSkill
from dartlab.ai.tools.readCapability import readCapability

skills = readSkill("dartlab 사용법", limit=8)
caps = readCapability("Company.show", limit=5)
```

## 호출 동작

사용법·API 설명 질문은 **계산이 필요 없다**. 가짜 숫자 만들지 않고 skill 절차 + capability docstring 으로 좁은 설명을 답한다.

1. `ReadSkill` 로 관련 skill 본문 검색
2. `ReadCapability` 로 호출 가능한 API docstring 검색
3. skill ref + apiRef 를 본문에 인용해 답변
4. **RunPython 으로 emit_result 호출 X** — 사용법은 evidence table 이 필요 없다

## 대표 반환 형태

- `skillRef` 3~5 개 (관련 skill 본문)
- `apiRef` 3~5 개 (호출 가능한 capability docstring)
- 답변 본문 안 capability 사용 예시 (파이썬 코드블록)

## 연계 절차

1. start.dartlabSkillOs — 첫 진입 skill 확인
2. (ReadSkill 로 관련 도메인 skill 직접 검색)
3. (ReadCapability 로 호출 가능한 API 직접 검색)

## 기본 검증

- 사용법 답변에 숫자 (12 조원, 30%) 가 들어가면 GATE 차단 — 실제 데이터가 없는 가짜 숫자다.
- skill ref + apiRef 만 묶고 evidence table 없이 답해도 OK.
- 사용자에게 "이 함수를 직접 호출해 보세요" 같은 행동 유도는 코드블록으로.
