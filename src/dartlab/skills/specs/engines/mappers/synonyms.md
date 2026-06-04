---
id: engines.mappers.synonyms
title: Mappers — Synonyms (한글·영문·한자 변형 + EDGAR 비대칭)
category: engines
kind: curated
scope: builtin
status: observed
purpose: 동의어 매핑 SSOT — accountMappings.json 단일 파일에 DART(mappings + layers) + EDGAR(edgar.learnedTags ~11,708) 통합 (2026-06 단일 소유, 옛 EDGAR 별도 파일 흡수) + 변형 정규화 룰 6 종 (한자/괄호/공백/하이픈/액suffix/jamo 분해). 구조·관리는 operation.mappingRefresh §0 정본.
whenToUse:
  - synonyms
  - 동의어
  - 한글 변형
  - 한자 정규화
  - 영문 alias
  - learnedSynonyms
  - EDGAR mapperData
  - SEC GAAP 태그
  - 변형 정규화
sourceRefs:
  - dartlab://skills/engines.mappers.synonyms
capabilityRefs: []
knowledgeRefs:
  - engines.mappers
  - engines.mappers.accountMappings
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
  - engines.mappers.accountMappings
---

## 엔진 역할

`mappers` 엔진의 *동의어 데이터* SSOT sub-spec. accountMappings sub-spec 이 *전체 파일 구조* 라면 본 sub-spec 은 변형 정규화 룰 6 종 + DART/EDGAR 동의어 데이터 정의.

핵심 사실 (2026-06 통합): **DART/EDGAR 동의어가 단일 파일 `reference/data/accountMappings.json` 로 통합**. DART 변형은 `mappings` + `layers.{idSynonym,nameSynonym}`, EDGAR tag 는 `edgar.learnedTags` + `edgar.accounts.commonTags`. 옛 EDGAR 별도 파일(`providers/edgar/finance/mapperData/`)은 흡수 후 제거됨. 단일 소유 엔진 = `core/accounts/`. 상세는 [operation.mappingRefresh](/skills/operation.mappingRefresh) §0.

## 공개 호출 방식

```python
# RunPython prelude (mappers 와 동일 진입)
col = normalizeColumn("IS", "Operating Profit")   # → "operating_profit" (영문 alias)
col = normalizeColumn("IS", "영업 이익")          # → "operating_profit" (공백 변형)
col = normalizeColumn("IS", "營業利益")           # → "operating_profit" (한자)

# 직접 동의어 인덱스
from dartlab.reference.mappers.accountMapper import AccountMapper
mapper = AccountMapper()
mapper.synonyms("operating_profit")
# → ["영업이익", "영업 이익", "Operating Profit", "營業利益", "영업이익(손실)", ...]
```

## 호출 동작

`normalizeColumn` 의 12 단계 fallback 중 2~9 단계가 본 sub-spec 의 변형 정규화 룰. 1 단계 (`mappings` 직 hit) 미달 시 본 sub-spec 의 6 종 정규화 + 1 자모 차이 fallback 순차 시도.

## 6 종 정규화 룰

| 룰 | 패턴 | 예시 변환 |
|---|---|---|
| **한자 → 한글** | `營業 → 영업`, `利益 → 이익` | 營業利益 → 영업이익 |
| **괄호 제거** | `(연결)`, `(주)`, `(손실)` | 영업이익(손실) → 영업이익 |
| **공백 정규화** | multiple space → single, trim | "영업  이익" → "영업 이익" → "영업이익" |
| **하이픈 정규화** | `-` 종류 통일 + 제거 | 영업-이익 → 영업이익 |
| **suffix 제거** | `액`, `등`, `순액`, `조정` | 매출액 → 매출, 순매출액 → 매출 |
| **jamo 1 자모 차이** | 한글 자모 분해 후 Levenshtein ≤ 1 | 지배지업 → 지배기업 (오타 흡수) |

각 룰 hit 시 confidence 감점:
- 한자/괄호/공백/하이픈: 0.95
- suffix: 0.85
- jamo 1 자모: 0.70 (오타 의심 — 답변 시 명시)

## DART 측 동의어 (mappings + layers)

`src/dartlab/reference/data/accountMappings.json` 단일 파일:

- `mappings` — 한글/영문 → snakeId 평면 사전 (~34,622). value 는 `standardAccounts` snakeId enum.
- `layers.idSynonym` — 영문 XBRL id → canonical id (옛 in-code `ID_SYNONYMS`).
- `layers.nameSynonym` — 한글 → canonical 한글 (옛 in-code `ACCOUNT_NAME_SYNONYMS`).
- `layers.snakeAlias` — snakeId → snakeId (옛 `SNAKEID_ALIASES`, DART↔EDGAR 통합).

갱신: `mappingPromote.py --layer <name> apply` 단일 진입점.

## EDGAR 측 동의어 (edgar 구획 — 같은 SSOT)

같은 `accountMappings.json` 의 `edgar` 구획 (2026-06 통합, 옛 별도 파일 흡수):

```json
"edgar": {
  "accounts": [{"snakeId": "total_assets", "stmt": "BS", "commonTags": ["Assets", ...]}, ...],
  "learnedTags": {"revenues": "sales", "operatingincomeloss": "operating_profit", ...},
  "stmtOverrides": {"NetIncomeLoss|IS": "net_profit", "NetIncomeLoss|CF": "net_income_cf"}
}
```

- `edgar.learnedTags` — SEC GAAP tag(lower) → snakeId (~11,708). value 는 DART 와 같은 snakeId enum.
- `edgar.accounts.commonTags` — 211 표준 계정의 대표 tag (commonTags 가 learnedTags 우선).
- `edgar.stmtOverrides` — 같은 tag 가 stmt 따라 다른 snakeId (`"tag\|stmt"` 인코딩).
- 소스만 저장, tagMap/stmtTagMap 인덱스는 `core/accounts/edgar.py` 가 로드 시 파생.

## DART/EDGAR 통합 완료 (옛 비대칭 해소)

| 항목 | 통합 후 (2026-06) |
|---|---|
| 파일 위치 | DART·EDGAR 모두 `reference/data/accountMappings.json` 단일 |
| 진입점 | `mappingPromote.py --layer` (atomic write + single-line 보존) |
| 매퍼 본체 | `core/accounts/` (DART `normalize` · EDGAR `edgar` · 라벨 `labels`) |
| facade | `providers/{dart,edgar}/finance/mapper.py` (위임, 하위 호환 re-export) |

옛 "EDGAR 별도 파일·대칭 작업 후속 트랙" 은 완료 — `providers/edgar/finance/mapperData/`
2 파일 제거, `edgar` 구획으로 흡수. EDGAR learnedTags 추가는 직접 편집 + `release()`
(현재 `mappingPromote --layer` 는 DART layers 6 종 대상; EDGAR 는 후속 layer 확장 후보).

## 대표 반환 형태

```text
AccountMapper.synonyms("operating_profit")
→ list[str]               # 모든 동의어 (한글 + 영문 + 한자 + 변형)

normalizeColumn("IS", "Operating Profit")
→ "operating_profit"      # 동의어 hit, confidence=1.0 또는 0.95
```

## 기본 검증

- `learnedSynonyms` 의 모든 value 가 `standardAccounts.snakeId` enum 안.
- EDGAR `learnedSynonyms` 의 모든 value 도 같은 enum (두 provider SSOT 동등).
- 6 종 정규화 룰 idempotent — 두 번 적용해도 결과 동일.
- jamo 1 자모 fallback 은 confidence ≤ 0.70 표기 강행.

## 관련

- [engines.mappers](/skills/engines.mappers) — base SKILL
- [engines.mappers.accountMappings](/skills/engines.mappers.accountMappings) — 전체 파일 구조 + 12 단계 fallback
- [operation.mappingRefresh](/skills/operation.mappingRefresh) — 동의어 추가 운영 절차
