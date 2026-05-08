---
id: engines.mappers
title: Mappers (계정 정규화)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Mappers 는 DART/EDGAR 원문 계정명을 공통 snake_id 로 정규화하는 *내부 모듈* 이다. 사용자 직접 호출 capability 가 아니라, Company.show / scan 결과 안에서 자동 적용. 본 skill 은 매핑 규칙을 *AI 가 컬럼 정규화에 활용* 할 때 참조한다. 트리거 — '항목 매핑', '컬럼 정규화', 'snake_id 변환'.
whenToUse:
  - mappers
  - 계정 정규화
  - snake_id
  - 컬럼 매핑
  - 한글 → 영문
  - rawName → standardName
inputs:
  - 한국어 계정명 (예 — 총자산)
  - topic (BS · IS · CF · CIS · SCE)
outputs:
  - snake_id (예 — total_assets)
  - 매핑 metadata (category · type · confidence)
capabilityRefs: []
toolRefs:
  - RunPython
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
  - engines.data.foundation
sourceRefs:
  - dartlab://skills/engines.mappers
requiredEvidence:
  - topic
  - rawName
  - snakeId
  - source
expectedOutputs:
  - 정규화된 snake_id
  - 매핑 신뢰도 (정확/부분/실패)
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
failureModes:
  - snake_id 추측 (반드시 `normalizeColumn(topic, hint)` 또는 `columnsFor(topic)` 결과 인용)
  - topic 누락 — 같은 한글 이름이 BS/IS/CF 에 다 있을 수 있음 ("당기순이익" 등)
  - rawName 의 한자/영문 변형 (`(주)` · `(연결)` · ` ` 공백) 미정규화
forbidden:
  - 매핑 결과 없이 한글 계정명을 직접 컬럼명으로 사용 금지.
  - 매핑 신뢰도 낮을 때 (`confidence < 0.8`) 답변에 그대로 쓰지 않는다.
examples:
  - 총자산 → total_assets 정규화
  - 당기순이익 (topic=IS) → net_income
  - normalizeColumn 으로 RunPython 안에서 동적 정규화
  - 새 사업보고서 항목 매핑 추가
procedure:
  - RunPython prelude 의 `normalizeColumn(topic, hint)` 사용 — 한글/snake/alias → 표준 snake_id.
  - 가능 컬럼 목록은 `columnsFor(topic)` — snake_id · label · aliases.
  - topic 자체는 `availableTopics()` (BS/IS/CF/CIS/SCE).
  - 매핑 정의는 `src/dartlab/mappers/{topic}.json` — AI/사람이 JSON 직접 편집해 추가.
  - 신규 매핑은 confidence + category + type 메타 함께 등록.
linkedSkills:
  - engines.company
  - engines.data.foundation
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-08'
---

## 엔진 역할

`mappers` 는 사용자 capability 가 아니라 *내부 모듈* 이다. DART 사업보고서·재무제표·주석의 한글 계정명을 dartlab 공통 snake_id 로 정규화한다. EDGAR 측은 SEC GAAP 태그 → 같은 snake_id (양쪽 SSOT 동등).

AI 가 직접 쓸 자리는 `RunPython` 안의 prelude 헬퍼 — `normalizeColumn(topic, hint)`, `columnsFor(topic)`, `availableTopics()`. 매핑 자체 편집은 운영자 절차 (`src/dartlab/mappers/{topic}.json` 직접 수정).

## 공개 호출 방식

```python
# RunPython 안에서 — prelude 자동 노출
import dartlab
c = dartlab.Company("005930")
bs = c.show("BS", freq="Q")

# 한글 → snake_id 정규화 (추측 금지)
col = normalizeColumn("BS", "총자산")        # → "total_assets"
col2 = normalizeColumn("IS", "영업")          # → "operating_profit"

# 가능 컬럼 목록 (snake_id · label · aliases)
cols = columnsFor("BS")
print(cols)

# 가능 topic
print(availableTopics())   # BS / IS / CF / CIS / SCE
```

## 호출 동작

`normalizeColumn(topic, hint)` — `topic` 안에서 `hint` 와 매칭되는 표준 snake_id 반환. 매칭 실패 시 `None` (또는 ValueError, 구현 따라). 한글 풀네임 · 부분 키워드 · snake_id 자기 자신 모두 받음.

`columnsFor(topic)` — 해당 topic 의 모든 표준 컬럼 list. 각 항목은 `snake_id` · `label` (한글) · `aliases` (한글/영문 변형) · `category` · `type`.

매핑 데이터는 `src/dartlab/mappers/{topic}.json` 의 `_metadata.description` + `key:value` (한글 → 영문 canonical) + `category/type` 분류.

## 6 매퍼 (topic 별)

| topic | 파일 | 책임 |
| --- | --- | --- |
| BS | `bs.json` | 재무상태표 — 자산·부채·자본 계정 |
| IS | `is.json` | 손익계산서 — 매출·비용·이익 계정 |
| CF | `cf.json` | 현금흐름표 — 영업·투자·재무 활동 |
| CIS | `cis.json` | 포괄손익계산서 — OCI 항목 |
| SCE | `sce.json` | 자본변동표 — 자본 구성 변동 |
| ratios | `ratios.json` | 재무비율 — ROE · 부채비율 등 파생 |

공통 유틸 (`mappers/common.py`) 가 모든 파서·매퍼에서 공유. 한자/영문/공백/괄호 변형 정규화.

## 대표 반환 형태

```text
normalizeColumn("BS", "총자산")
→ "total_assets"  (str)

columnsFor("BS")
→ list[dict]
   snake_id : str
   label : str         # 한글 표시명
   aliases : list[str] # 변형 ("총 자산", "자산총계", "Total Assets")
   category : str      # "asset" / "liability" / "equity"
   type : str          # "current" / "non-current" / "total"
```

## evidence 기준

매핑 결과는 `topic` · `rawName` · `snakeId` · `confidence` · `source` (DART/EDGAR) 를 남긴다. confidence 낮으면 답변에 명시.

## 기본 검증

매핑 정의 변경은 `src/dartlab/mappers/{topic}.json` 직접 수정 + 본 skill 의 6 매퍼 표 동시 갱신. 신규 매핑 추가 시 `category` · `type` 메타 함께 — AI 가 새 항목을 자동 분류하는 학습 데이터로 작동.
