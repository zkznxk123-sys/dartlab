---
id: start.installUv
title: uv로 DartLab 설치와 첫 실행
kind: curated
scope: builtin
status: unverified
category: start
purpose: DartLab을 처음 설치하거나 새 환경에서 실행할 때 필요한 최소 절차를 안내한다.
whenToUse:
  - uv로 dartlab 시작하는 법
  - 새 가상환경에서 DartLab 설치
  - 첫 실행 전 환경 점검
inputs:
  - Python 3.12 이상
outputs:
  - 설치 명령
  - import smoke 절차
  - 다음에 실행할 분석 skill 후보
toolRefs:
  - search_reference
  - run_python
requiredEvidence:
  - execution
expectedOutputs:
  - install guide
  - smoke check
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
      - 웹에서는 설치 대신 Pyodide 또는 hosted runtime skill을 연결한다.
  pyodide:
    status: unsupported
    limitations:
      - uv 설치는 로컬 Python 환경 절차다.
failureModes:
  - 설치와 런타임 데이터 준비를 혼동
forbidden:
  - 검증 없이 설치 성공 단정
examples:
  - uv로 dartlab 시작하는 법 알려줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- `uv venv` 또는 기존 프로젝트 가상환경을 준비한다.
- `uv pip install -U dartlab` 또는 repo 개발 환경에서는 `uv sync`를 실행한다.
- `uv run python -X utf8 -c "import dartlab; print(dartlab.__version__)"`로 import를 확인한다.
- 데이터가 필요한 skill은 설치와 별개로 RuntimeDatasetCatalog 또는 prefetch 절차를 확인한다.
- 첫 분석은 `search_reference`로 목적 skill을 찾은 뒤 capability와 runtime 제한을 함께 확인한다.

