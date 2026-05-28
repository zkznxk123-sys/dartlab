---
id: engines.mappers.accountMappings
title: Mappers — accountMappings.json (DART SSOT)
category: engines
kind: curated
scope: builtin
status: observed
purpose: DART 측 계정 매핑 SSOT — `src/dartlab/reference/data/accountMappings.json` 의 standardAccounts (3,402) + learnedSynonyms (31,489) + merged (34,171) 구조 정의 + 12 단계 fallback 룰 + atomic write 진입점 단일화 (mappingPromote.py).
whenToUse:
  - accountMappings
  - DART 계정 매핑
  - standardAccounts
  - learnedSynonyms
  - 12 단계 fallback
  - AccountMapper
  - snake_id 정규화 SSOT
  - 매핑 파일 구조
sourceRefs:
  - dartlab://skills/engines.mappers.accountMappings
capabilityRefs: []
knowledgeRefs:
  - engines.mappers
  - operation.mappingRefresh
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
linkedSkills:
  - engines.mappers
  - operation.mappingRefresh
---

## 엔진 역할

`mappers` 엔진의 *DART 매핑 데이터* SSOT sub-spec. base SKILL `engines.mappers` 의 학습 파이프라인 4 단계와 5 신호 게이트가 *생성하는* 결과물 SSOT — `src/dartlab/reference/data/accountMappings.json` 단일 파일. EDGAR 측 (`synonyms` sub-spec) 과 직교 — 두 provider 비대칭 (EDGAR 는 자체 `mapperData/` 보유).

## 공개 호출 방식

```python
# RunPython prelude (engines.mappers 와 동일)
col = normalizeColumn("BS", "총자산")        # → "total_assets"

# 직접 로더 (운영자/디버그)
from dartlab.reference.mappers.accountMapper import AccountMapper
mapper = AccountMapper()
print(mapper.stats())
# MapperStats(name='account', totalEntries=34249, coverage=1.0, lastUpdated='2026-03-09')
mapper.lookup("매출액")
# {'snakeId': 'sales', 'category': 'is', ...}
```

## 호출 동작

`normalizeColumn` / `AccountMapper.lookup` 모두 본 sub-spec 의 SSOT 파일을 메모리 로드 (lru_cache) 후 12 단계 fallback 매칭 — 사전 hit → synonym 정규화 → 공백/괄호/하이픈 역인덱스 → 액 suffix.

JSON 직접 편집 후 `AccountMapper.release()` 호출해야 cache 무효화 (lru_cache.cache_clear).

## 파일 구조

```json
{
  "_metadata": {
    "lastUpdate": "2026-03-09",
    "addedCount": 34171,
    "promoteCommit": "abc1234"
  },
  "standardAccounts": {
    "total_assets": {
      "snakeId": "total_assets",
      "korName": "자산총계",
      "category": "asset",
      "type": "total",
      "topic": "BS"
    },
    ...
  },
  "learnedSynonyms": {
    "총자산": "total_assets",
    "Total Assets": "total_assets",
    "자산 총계": "total_assets",
    ...
  },
  "mappings": {
    "<accountId>": "<snakeId>",
    ...
  }
}
```

- `standardAccounts` — 3,402 표준 계정 (snakeId 단일 SSOT, IFRS 분류).
- `learnedSynonyms` — 31,489 한글/영문/한자 변형 (synonyms sub-spec SSOT).
- `mappings` — accountId → snakeId 직접 lookup (12 단계 fallback 의 1 단계 hit).
- `_metadata` — 갱신 추적 + promote commit 해시.

## 12 단계 fallback 룰

1. `mappings[accountId]` 직 hit
2. `learnedSynonyms[accountNm]` 직 hit
3. `accountNm` 한자 → 한글 정규화 후 retry
4. `accountNm` (주)/(연결) suffix 제거 후 retry
5. 공백 정규화 후 retry
6. 괄호 제거 후 retry
7. 하이픈 정규화 후 retry
8. `accountId` prefix (-표준계정코드 미사용-) 제거 후 retry
9. 액 suffix (영업이익액 → 영업이익) 제거 후 retry
10. `accountNm` jamo 분해 → 1 자모 차이 standardAccounts.korName 매칭
11. accountNm substring (≥ 0.70 score) standardAccounts.korName 매칭
12. None 반환 (진짜 미커버)

각 단계 hit 시 `confidence` 1.0 (1 단계) → 0.6 (10~11 단계) 감점. 답변 시 confidence < 0.8 명시.

## atomic write 진입점

**prod JSON 직접 편집 금지** — `src/dartlab/reference/mapping/mappingPromote.py` 만 진입점:

```bash
# 운영자 절차 (operation.mappingRefresh 4 단계 마지막)
uv run python -X utf8 src/dartlab/reference/mapping/mappingPromote.py apply --batch=<staged_file>
```

`mappingPromote.py` 가:
1. atomic write (`accountMappings.json.tmp` → rename)
2. `_metadata.lastUpdate` / `addedCount` / `promoteCommit` 갱신
3. `AccountMapper.release()` 자동 호출 (cache 무효화)
4. single-line JSON 보존 (`separators=(',', ':')` — diff noise 최소)

## 대표 반환 형태

```text
AccountMapper.lookup("매출액")
→ dict
   snakeId : str           # "sales"
   korName : str           # "매출액"
   category : str          # "revenue"
   type : str              # "operating"
   topic : str             # "IS"
   confidence : float      # 1.0 (1 단계 hit)
   matchStage : int        # 1 ~ 11
```

## 기본 검증

- `_metadata.lastUpdate` 날짜 ≤ 오늘 (역날짜 X).
- `mappings` 의 모든 value 가 `standardAccounts` 의 snakeId.
- `learnedSynonyms` 의 모든 value 가 `standardAccounts` 의 snakeId.
- `AccountMapper.stats().totalEntries` ≥ 34,000.
- coverage ≥ 0.99.

## 관련

- [engines.mappers](/skills/engines.mappers) — base SKILL (학습 파이프라인 4 단계 + 5 신호 게이트)
- [engines.mappers.synonyms](/skills/engines.mappers.synonyms) — learnedSynonyms 측 SSOT + EDGAR 비대칭
- [operation.mappingRefresh](/skills/operation.mappingRefresh) — 운영자 트리거 절차 4 단계
