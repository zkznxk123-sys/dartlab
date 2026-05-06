---
id: engines.recipe.dataAvailabilityFirst
title: 데이터 가용성 우선 점검 (수집 전 확인 → 누락 시 gather/update)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 분석 시작 전 필요한 데이터 (finance/docs/report/price) 가 local 에 있는지 확인하고 누락 시 수집을 트리거하는 절차. emit_result 실패 사이클 예방.
whenToUse:
  - 데이터 가용성
  - 데이터 있는지
  - 분석 전 확인
  - 데이터 수집
  - 누락 데이터
  - inspect dataset
  - schema 확인
linkedSkills:
  - engines.company.researchStarter
  - engines.gather
  - engines.data.foundation
toolRefs:
  - inspect_dataset
  - engine_call
requiredEvidence:
  - skillRef
  - datasetRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 update() 호출 제약
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

topics = c.topics  # 가용 토픽 목록
# inspect_dataset 으로 schema 확인
# 누락 시 c.update() 또는 c.gather('price') 호출
```

## 호출 동작

분석 의도 → 필요한 dataset 식별 → inspect_dataset 으로 schema/최신 시점 확인 → 누락 시 update/gather 트리거.

1. 회사 진입
2. c.topics — 가용 토픽 목록
3. inspect_dataset — 핵심 dataset 확인 (Company.show:code:BS 등)
4. (누락 시) c.update() — finance/docs/report 증분 수집
5. (가격 필요 시) c.gather("price") — KR/US 주가

## 대표 반환 형태

- `skillRef` 1 (data foundation)
- `datasetRef` 3+ (BS / IS / CF 또는 price / macro)
- 답변 본문: 가용 vs 누락 dataset 표

## 연계 절차

1. engines.company.researchStarter — 회사 진입 + topics 조회
2. engines.data.foundation — 데이터 기본기 확인
3. engines.gather — 누락 데이터 수집

## 기본 검증

- 가용 dataset / 누락 dataset 명시.
- schema (컬럼 + dtype + 최신 시점) 표시.
- update 호출은 비용 (네트워크) — 누락 명확할 때만.
