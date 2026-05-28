---
id: operation.dataLineage
title: Data Lineage — raw → parquet → axis 매핑 SSOT
kind: curated
scope: builtin
status: drafted
category: operation
purpose: dartlab 데이터 lineage SSOT — raw source (DART/EDGAR/KRX) → parquet (`data/{provider}/`) → engine axis 매핑 표. 데이터 변경 시 영향 범위 추적 + schema migration 사전 검토.
whenToUse:
  - data lineage
  - 데이터 흐름
  - raw to parquet
  - schema migration
  - 영향 범위
inputs:
  - source 또는 parquet 또는 axis 식별자
outputs:
  - upstream / downstream 매핑
  - 영향 범위 list
toolRefs: []
knowledgeRefs:
  - operation.architecture
  - operation.docsBuilderRefactor
sourceRefs:
  - dartlab://skills/operation.dataLineage
requiredEvidence:
  - skillRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
linkedSkills:
  - operation.architecture
  - operation.docsBuilderRefactor
---

## 4 layer

```
L0: raw source
   DART zip (data/dart/original/, 로컬 임시, .gitignore)
   EDGAR XBRL (HF dataset eddmpython/dartlab-data/edgar/)
   KRX OpenAPI (HF dataset eddmpython/dartlab-data/krx/)
   ↓
L1: parquet (정규화)
   data/dart/finance/*.parquet  (BS/IS/CF/CIS/SCE × snake_id)
   data/dart/sections/*.parquet (section_content 본문)
   data/edgar/finance/*.parquet
   data/krx/prices/*.parquet
   ↓
L2: in-memory
   Company.show(...) — BoundedCache
   Company.scan(...) — heap 가드 maxTargets=5
   ↓
L3: axis / recipe
   engines.* (15 카테고리 × N axis)
   recipes.* (220+ recipe)
```

## 매핑 표

| source | provider | parquet | axis 영향 |
|---|---|---|---|
| DART finance | dart/ | bs/is/cf/cis/sce | analysis 22 + credit + quant 일부 |
| DART sections | dart/ | section_content | search + sections deep dive |
| EDGAR XBRL | edgar/ | finance/* | edgar SKILL |
| KRX OHLCV | krx/ | prices/raw-YYYY | quant 30+ + scan |
| KRX events | krx/ | events/* | _adjustPrice (split/dividend) |
| 한은 macro | macro/ | (외부 API) | macro 12 axis |

## 갱신 절차

1. source 변경 → L1 parquet rebuild (sync workflow).
2. parquet schema 변경 → migration 절차 (별 spec).
3. L2 cache invalidation (`BoundedCache.clear`).
4. L3 axis 영향 확인 → 본 매핑 표 갱신.

## 강행 룰

1. lineage 표 source ↔ parquet ↔ axis 1:N 매핑 명시.
2. 새 source 추가 → 본 spec 동시 갱신.
3. schema migration → backward compat 또는 명시 break.

## 기본 검증

- 모든 parquet 의 source / provider 추적 가능.
- 모든 axis 의 input parquet 추적 가능.
- migration 시 영향 범위 사전 명시.
