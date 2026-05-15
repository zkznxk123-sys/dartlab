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
  - 매핑 정의는 `src/dartlab/reference/data/accountMappings.json` (DART SSOT) 또는 `src/dartlab/providers/edgar/finance/mapperData/learnedSynonyms.json` (EDGAR).
  - 신규 매핑 추가는 운영자 트리거 발화 ("매퍼 정리"/"mapping refresh") → `.claude/skills/mapping-refresh/SKILL.md` 4 단계 — 관측 ledger → `scripts/audit/mappingLedgerCompact.py` → `scripts/dev/mappingReview.py` confirm/reject/alias/defer → `scripts/dev/mappingPromote.py` apply.
  - prod JSON 단독 권한 진입점은 `scripts/dev/mappingPromote.py` 만. atomic write + `_metadata.{lastUpdate,addedCount,promoteCommit}` 갱신 + `AccountMapper.release()` 자동 호출.
linkedSkills:
  - engines.company
  - engines.data.foundation
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-15'
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

매핑 정의 변경은 본 skill 의 6 매퍼 표 동시 갱신. 신규 매핑 추가 시 `category` · `type` 메타 함께 — AI 가 새 항목을 자동 분류하는 학습 데이터로 작동.

## 학습 파이프라인 (반자동 사이클)

### 저장 위치 (SSOT 인덱스)

| 자산 | 경로 | 내용 | 갱신 방식 |
|---|---|---|---|
| DART 학습 매핑 | `src/dartlab/reference/data/accountMappings.json` | `standardAccounts: 3,402` / `learnedSynonyms: 31,489` / `merged: 34,171` / `_metadata.lastUpdate` | 사람 수동 편집 |
| EDGAR 학습 동의어 | `src/dartlab/providers/edgar/finance/mapperData/learnedSynonyms.json` | 11,375 SEC GAAP 태그 | 사람 수동 편집 |
| Notes 구조 학습 | `src/dartlab/reference/data/notesStructure.json` | 2,700 종목 notes 항목 `{type, category, frequency}` | `scanAll()` 자동 갱신 |
| 라벨 SSOT | `src/dartlab/core/utils/labels.py::_loadAccountMappings` | DART 학습 매핑 로더 | — |
| 캐시 무효화 | `src/dartlab/providers/dart/finance/mapper.py::AccountMapper.release` | JSON 직접 편집 후 호출 | — |

DART 측 mapper 데이터는 `reference/data/` 로 통합 승격 (`providers/dart/finance/mapperData/` 디렉토리 폐기). EDGAR 는 자체 `mapperData/` 보유 — 두 provider 패턴 비대칭 (대칭 작업은 후속 트랙).

### 사이클 4 단계 — 운영자 트리거 발동 (cron 없음)

```
1. 관측 ledger (옵트인, ENV 켤 때만)
   DARTLAB_MAPPING_LEDGER=1 환경에서 Company.show / scan / pivot 호출 시
   pivot._pivotToSeries 가 미커버 (accountId, accountNm, sjDiv) 그룹을
   data/mapping_candidates_raw.ndjson 에 append. ENV OFF 면 사용자 영향 0.
   본체: src/dartlab/core/observability/mapping_ledger.py.

2. 재구성 + 5 신호 평가 (수동)
   uv run python -X utf8 scripts/audit/mappingLedgerCompact.py
   → 그룹화 + S1 빈도 / S2 회사 분산 / S3 한글 정규화 / S4 IFRS 동의어 1 hop /
     S5 오타 거부 적용
   → data/mapping_candidates.parquet (15 컬럼) 산출
   본체: src/dartlab/core/observability/mapping_signals.py.

3. 운영자 review (수동)
   uv run python -X utf8 scripts/dev/mappingReview.py list/inspect/confirm/
     reject/alias/defer/export-pr
   → staging parquet 의 status / suggestedSnakeId / operatorNote / decidedAt
     컬럼만 갱신. accountMappings.json 미수정.

4. Prod patch (수동, 단독 권한)
   uv run python -X utf8 scripts/dev/mappingPromote.py dryrun → apply
   → confirmed 행을 accountMappings.json::mappings 에 atomic write 로 추가.
     _metadata.{lastUpdate,addedCount,promoteCommit} 갱신.
     AccountMapper.release() + labels._loadAccountMappings.cache_clear() 호출.
```

운영자 트리거 발화 ("매퍼 정리해줘"/"분기 매퍼 업데이트"/"mapping refresh") 시
`.claude/skills/mapping-refresh/SKILL.md` 절차서가 4 단계를 안내. 각 단계
사이에 운영자 결정 필수 — 어떤 자동화도 prod JSON 을 직접 수정하지 않는다.

### 안전 자동학습의 정의 (5 신호)

"자동 적용 가능" 의 객관 기준은 `mapping_signals.evaluate` 의 5 신호 모두
통과 (`autoEligible: true`):

| 신호 | 기준 | 거부 시그널 |
|---|---|---|
| S1 빈도 | occurrenceCount ≥ 5 | < 5 = singleton 노이즈 |
| S2 회사 분산 | 고유 stockCode ≥ 3 | 1 사 전용 = 사내 계정 |
| S3 한글 정규화 매칭 | standardAccounts.korName Levenshtein 유사도 ≥ 0.85 | < 0.85 = 의미 모호 |
| S4 IFRS 동의어 1 hop | accountId/accountNm 정규화 후 mappings 직 hit | 1 hop 안에 없음 |
| S5 오타 거부 | jamo 분해 → 1 자모 차이 IFRS korName 존재 시 거부 | 오타 의심 = false + suggestedFix 노출 |

`autoEligible=True` 도 *자동 반영* 이 아니다 — 운영자 `mappingReview.py
confirm` 후 `mappingPromote.py apply` 까지 사람 결정 2 번 필요.

### 사용자 호출 (학습은 내부, 호출은 prelude)

학습 결과 활용은 위 "공개 호출 방식" 의 `normalizeColumn(topic, hint)` / `columnsFor(topic)` — RunPython prelude 자동 노출. 직접 JSON 편집은 운영자 절차.

### 검증

```python
from dartlab.reference.mappers.accountMapper import AccountMapper
mapper = AccountMapper()
print(mapper.stats())  # MapperStats(name='account', totalEntries=34249, coverage=1.0, lastUpdated='2026-03-09')
print(mapper.lookup("매출액"))  # {'snakeId': 'sales', ...}
```
