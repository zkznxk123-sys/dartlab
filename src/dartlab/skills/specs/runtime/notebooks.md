---
id: runtime.notebooks
title: Colab · Molab · 로컬 marimo 노트북
kind: curated
scope: builtin
status: observed
category: runtime
purpose: 같은 dartlab 코드를 Colab (Google) · Molab (marimo cloud) · 로컬 marimo 세 경로로 실행하는 노트북 카탈로그와 작성·운영 규칙이다.
whenToUse:
  - dartlab 을 설치 없이 브라우저에서 시도
  - Molab 무료 클라우드에서 실행
  - 로컬 marimo 로 영구 노트북 작성
  - colab/marimo 1:1 대응 코드 위치 찾기
  - 노트북 새로 만들거나 기존 노트북 수정
inputs:
  - 노트북 환경 선택 (Colab · Molab · 로컬)
  - 분석 대상 (Company · Scan · Story · Gather · Analysis · Ask)
outputs:
  - 실행 가능한 노트북 링크
  - 로컬 실행 명령
  - 노트북 작성 규칙
capabilityRefs: []
toolRefs:
  - colab
  - marimo
knowledgeRefs:
  - start.dartlabSkillOs
  - start.installUv
  - start.quickStart
sourceRefs:
  - dartlab://skills/runtime.notebooks
  - https://github.com/eddmpython/dartlab/tree/master/notebooks
procedure:
  - 환경을 고른다 (브라우저 즉시 → Colab/Molab, 로컬 영구 → marimo).
  - 노트북 카탈로그에서 분석 대상에 맞는 항목을 연다.
  - 첫 셀에서 의존성 추가 (`!pip install dartlab` 또는 `uv add dartlab`).
  - 코드 실행 — 데이터는 자동 다운로드.
  - 새 노트북 작성 시 작성 규칙 (Colab 마크다운 / marimo 주석) 을 따른다.
requiredEvidence:
  - execution
expectedOutputs:
  - 노트북 진입 링크
  - 실행 환경별 의존성 설치 결과
  - 작성 규칙 충족 여부
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: supported
    notes:
      - "uv run --with marimo marimo edit notebooks/marimo/{name}.py 로 실행."
  mcp:
    status: limited
  webAi:
    status: supported
    notes:
      - Colab / Molab 둘 다 브라우저에서 즉시.
  pyodide:
    status: limited
    notes:
      - marimo wasm 빌드는 별도 — 본 카탈로그 외 항목.
failureModes:
  - Colab 노트북을 로컬 jupyter 와 혼동
  - marimo 의 reactive 모델을 jupyter 의 셀 순서 모델로 오해
  - 노트북에서 큰 데이터 셋을 메모리 폭주시킴
  - 셀 순서에 의존하는 비결정 코드 작성 (marimo reactive 모델 위반)
  - colab (.ipynb) 과 marimo (.py) 의 1:1 대응을 깨고 한쪽만 갱신
forbidden:
  - 셀 순서에 의존하는 비결정 코드 작성
  - colab/marimo 한쪽만 갱신한 채 변경 완료 처리
examples:
  - dartlab Colab 으로 시도
  - 로컬 marimo 에서 Company 분석
  - Molab 으로 무료 실행
  - 새 노트북 작성 규칙 확인
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-06"
---

## 노트북 카탈로그

Colab 은 브라우저에서 바로 실행 (Google 계정). Molab 은 marimo 클라우드 (무료).

| 기능 | 설명 | Colab | Molab |
|---|---|---|---|
| **Company** | `Company("005930")` — sections, show, trace, diff, 재무 | [![Colab](https://img.shields.io/badge/Colab-ea4647?style=flat-square&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb) | [![Molab](https://img.shields.io/badge/Molab-38bdf8?style=flat-square)](https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py) |
| **Scan** | `scan()` — 13 축 전 종목 횡단 스캔 | [![Colab](https://img.shields.io/badge/Colab-ea4647?style=flat-square&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_scan.ipynb) | [![Molab](https://img.shields.io/badge/Molab-38bdf8?style=flat-square)](https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/02_scan.py) |
| **Story** | `c.story()` — 구조화 보고서 (AI 종합 의견은 `dartlab.ask`) | [![Colab](https://img.shields.io/badge/Colab-ea4647?style=flat-square&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_story.ipynb) | [![Molab](https://img.shields.io/badge/Molab-38bdf8?style=flat-square)](https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/08_story.py) |
| **Gather** | `gather()` — 주가 · 수급 · 거시 · 뉴스 | [![Colab](https://img.shields.io/badge/Colab-ea4647?style=flat-square&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_gather.ipynb) | [![Molab](https://img.shields.io/badge/Molab-38bdf8?style=flat-square)](https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/04_gather.py) |
| **Analysis** | `c.analysis()` — 14 축 분석 · 인사이트 · 전망 · 밸류에이션 | [![Colab](https://img.shields.io/badge/Colab-ea4647?style=flat-square&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/05_analysis.ipynb) | [![Molab](https://img.shields.io/badge/Molab-38bdf8?style=flat-square)](https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/05_analysis.py) |
| **Ask (AI)** | `ask("...")` — 자연어 LLM 분석 | [![Colab](https://img.shields.io/badge/Colab-ea4647?style=flat-square&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_ask.ipynb) | [![Molab](https://img.shields.io/badge/Molab-38bdf8?style=flat-square)](https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/06_ask.py) |

## 로컬 marimo 실행

```bash
uv run --with marimo marimo edit notebooks/marimo/01_company.py
```

같은 코드 (`notebooks/marimo/{name}.py`) 가 Molab 클라우드에서도 동작한다.

Colab (`.ipynb`) 과 marimo (`.py`) 는 **1:1 대응** — 같은 분석을 두 노트북 형식으로 유지한다. 한쪽만 갱신 금지.

## 노트북 작성 규칙

### Colab — 마크다운 허용

- 학습·공유용 독자가 맥락을 빠르게 잡게 마크다운 셀로 섹션 설명.
- **3~4 코드 셀마다 1 마크다운**. 너무 잦으면 흐름 끊고, 너무 드물면 맥락 사라진다.
- 노트북 최상단 1 장: 제목 + 한 줄 요약 + "이 노트북에서 다루는 것" 2~3 줄.
- 주요 섹션 전환점에만 1 장씩.

### marimo — 코드 + 짧은 주석

- 실습·실행용. 설명은 코드 옆 짧은 주석으로.
- 첫 줄 한글 주석으로 셀 의도 표시.
- 마크다운 셀 자제 — reactive 모델은 코드 흐름이 본체다.

### 공통 규칙

- 같은 분석은 같은 코드·같은 순서로 두 노트북에 동기화.
- 셀 순서에 의존하는 비결정 코드 금지 (marimo 가 reactive 라 의도와 다른 결과 낳는다).
- 큰 데이터 셋 (Company 3 개 이상 동시 로드) 금지 — OOM 위험.

## 다음 단계

- [start.installUv](/skills/start.installUv) — 로컬 dartlab 설치.
- [start.quickStart](/skills/start.quickStart) — 8 단계 walkthrough.
- [engines.company](/skills/engines.company) — Company 엔진 메서드 카탈로그.
