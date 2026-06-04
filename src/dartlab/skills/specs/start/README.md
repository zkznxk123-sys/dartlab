---
id: start.README
title: Start 카테고리 hub
purpose: dartlab skills/specs/start/ 카테고리 진입점.
kind: curated
category: start
status: curated
requiredEvidence: []
expectedOutputs: []
runtimeCompatibility:
  pyodide:
    status: supported
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
whenToUse:
  - start 카테고리 시작점
---

# Skill OS — `start/` 카테고리 hub

> **외부 LLM / 신규 사용자 첫 진입점**. 다른 카테고리 (operation / runtime / engines) 가기 전에 본 hub 부터.
> 본 README 는 카테고리 인덱스 + 추천 진입 순서 + 첫 시나리오. spec 본문은 각 `*.md`.

---

## 추천 진입 순서

| 순서 | spec | 무엇을 |
|------|------|--------|
| 1 | [dartlabSkillOs.md](dartlabSkillOs.md) | Skill OS 전체 그림 — 257 노드 / 4 카테고리 / capability ref |
| 2 | [installUv.md](installUv.md) | uv 설치 + dartlab 환경 셋업 |
| 3 | [quickStart.md](quickStart.md) | 5분 안 첫 결과 — `Company` / `scan` / `dartlab.ask` 3 진입점 |
| 4 | [firstAnalysisRecipe.md](firstAnalysisRecipe.md) | 첫 분석 시나리오 — 외인 매수 모멘텀 1 종목 |

---

## 첫 시나리오 — 5분 진입

```python
import dartlab

# 1) AI workbench 진입 (1분, 자연어)
result = dartlab.ask("삼성전자 최근 외인 매수 흐름 분석")
print(result)

# 2) Python 직접 (3분, 코드)
c = dartlab.Company("005930")
print(c.corpName)        # "삼성전자"
print(c.panel("IS"))      # 손익계산서

# 3) CLI (2분, terminal)
# $ dartlab help 외인
# $ dartlab analyze 005930 --aspect foreign-flow
```

---

## 다음 카테고리

- **operation/** — 운영 설계 SSOT (philosophy / architecture / code / apiContract / testing 등 29 spec)
- **runtime/** — 실행 환경 (mcp / pyodide / workbenchEvidenceFlow 등 11 spec)
- **engines/** — 15 분석 엔진 (analysis / company / credit / industry / macro / quant / scan / story 등)
- **recipes/** — 분석 recipe 6-stage lifecycle

---

## 관련

- [SCHEMA.md](../SCHEMA.md) — Skill OS schema (frontmatter / capabilityRefs / requiredEvidence)
- [TODO.md](../../../../../TODO.md) T10-5 — 본 hub README 생성 트랙
- 외부 LLM 첫 호출: `ReadSkill(query="start.dartlabSkillOs")`
