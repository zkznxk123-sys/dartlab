---
id: engines.mappers.synonyms
title: Mappers — Synonyms (한글·영문·한자 변형 + EDGAR 비대칭)
category: engines
kind: curated
scope: builtin
status: observed
purpose: 동의어 매핑 SSOT — accountMappings.json 안 learnedSynonyms (31,489 DART) + EDGAR 자체 mapperData/learnedSynonyms.json (11,375 SEC GAAP) 두 provider 비대칭 구조 + 변형 정규화 룰 6 종 (한자/괄호/공백/하이픈/액suffix/jamo 분해) 단일 정의.
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

`mappers` 엔진의 *동의어 데이터* SSOT sub-spec. accountMappings sub-spec 이 *전체 파일 구조* 라면 본 sub-spec 은 그 안 `learnedSynonyms` 섹션 + EDGAR 측 별도 파일 두 곳의 변형 정규화 룰 정의.

핵심 사실: **DART/EDGAR 두 provider 비대칭** — DART 는 `reference/data/accountMappings.json` (통합 승격), EDGAR 는 자체 `providers/edgar/finance/mapperData/learnedSynonyms.json` 유지. 대칭 작업은 후속 트랙.

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

## DART 측 동의어 (learnedSynonyms 31,489)

`src/dartlab/reference/data/accountMappings.json::learnedSynonyms` — flat dict:

```json
{
  "총자산": "total_assets",
  "Total Assets": "total_assets",
  "자산 총계": "total_assets",
  "資産總計": "total_assets",
  ...
}
```

- value 는 `standardAccounts` 의 snakeId 단일 enum.
- 한 snakeId 당 평균 9.3 변형 (3,402 표준 × 9.3 = 31,489).
- 갱신: `mappingPromote.py apply` 진입점만 (engines.mappers.accountMappings SSOT).

## EDGAR 측 동의어 (11,375 SEC GAAP)

`src/dartlab/providers/edgar/finance/mapperData/learnedSynonyms.json` — 별도 파일:

```json
{
  "us-gaap:Assets": "total_assets",
  "us-gaap:OperatingIncomeLoss": "operating_profit",
  "us-gaap:Revenues": "sales",
  ...
}
```

- key 는 SEC GAAP namespace 태그 (us-gaap:* / dei:* / custom).
- value 는 DART 와 같은 snakeId enum — 두 provider SSOT 동등.
- 11,375 태그 = SEC GAAP 2024 분류 (운영자 수동 갱신).

## 두 provider 비대칭 (정정 trace)

| 항목 | DART | EDGAR |
|---|---|---|
| 파일 위치 | `reference/data/accountMappings.json` (통합 승격) | `providers/edgar/finance/mapperData/` (provider 격리) |
| 진입점 | `mappingPromote.py apply` (atomic) | 직접 JSON 편집 (atomic write X) |
| 갱신 빈도 | cycle 30~80 매핑 / 주 | SEC GAAP 분기 갱신 시 batch |
| AccountMapper | `reference/mappers/accountMapper.py` | `providers/edgar/finance/mapper.py` 별도 |

**대칭 작업 후속 트랙**: EDGAR mapperData 도 `reference/data/edgarMappings.json` 으로 통합 승격 + `mappingPromote.py edgar` 서브커맨드 추가. 본 sub-spec 갱신 시점 미정.

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
