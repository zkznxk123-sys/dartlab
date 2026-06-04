---
id: engines.company.sections
title: Company Sections (사업보고서 II 항)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Company.sections — DART 사업보고서 II 항 "사업의 내용" segment narrative grid. period × topic × content 의 sectionsStorage artifact. 005930 기준 40 분기 · 60 topics · 3,100 page-equiv. Bloomberg/AlphaSense 가 구조적으로 손대지 못한 한국 고유 segment 깊이.
whenToUse:
  - 사업의 내용
  - segment
  - 부문별 매출
  - 제품별 ASP
  - 메모리 ASP
  - 지역별 매출
  - 주요 제품
  - 사업보고서 II
  - business content
  - 사업 부문
  - 원재료 가격
  - 시장점유율
inputs:
  - 종목코드
  - period (예 2025Q4 또는 2024Q1) 또는 전체
  - 선택 section query (예 사업의 내용 또는 원재료 및 생산설비)
outputs:
  - LazyFrame (period · topic · content · sourceRef)
  - 또는 wide DataFrame (period × topic pivot)
capabilityRefs:
  - Company.sections
  - Company.readFiling
  - Company.disclosure
knowledgeRefs:
  - engines.company
  - engines.company.koreanDisclosure
  - engines.company.disclosureEvent
sourceRefs:
  - dartlab://skills/engines.company.sections
requiredEvidence:
  - target
  - period
  - rceptNo
  - section
  - sourceRef
expectedOutputs:
  - period × topic narrative grid
  - 분기별 segment narrative 추세
  - 사업보고서 본문 원문 인용
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
failureModes:
  - section query 가 한국 양식 ("II. 사업의 내용") 인데 영어 "Item 1. Business" 로 매칭 시도
  - period 인자 미지정 시 sectionsStorage 전체 load (대용량 메모리 위험 — BoundedCache critical_prefix 박힘)
  - narrative diff 비교 시 분기별 양식 변경 (XBRL tag rename) 회귀
forbidden:
  - rceptNo 또는 section paragraph 의 sourceRef 없이 segment narrative 의 ASP/volume 수치를 인용하지 않는다
  - 사업보고서 본문 원문은 wrapExternalInResult 의 untrusted marker 강제 (외부 본문 untrusted tier)
examples:
  - 삼성전자 메모리 부문 분기별 ASP 5 년 추세 - Company.sections + section 사업의 내용 + period filter
  - LG화학 배터리 사업 지역별 매출 비중 - Company.sections + topic filter
  - 현대차 ICE vs EV 전환 narrative drift Q1 Q4 2024 - Company.sections + period pair diff
  - POSCO 철광석 원재료 가격 변동 - Company.sections + section 원재료 및 생산설비
  - 005930 wide pivot period x topic - Company.sectionsAs(wide)
  - SK하이닉스 시장점유율 narrative 분기별 - Company.sections + topic filter 시장점유율
procedure:
  - 종목코드 → Company 객체 생성
  - sectionsStorage 사용 여부 확인 (`hasSectionsArtifact`) — 박혀있으면 빠른 load
  - period 명시 — 단일 period 또는 list (메모리 절약)
  - LazyFrame 으로 filter (period · topic · section)
  - .collect() 호출 직전 gc.collect() (Polars OOM 가드)
  - rceptNo + section paragraph sourceRef 답변 본문 인용
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 최신 분기 sections artifact
sec = c.sections                         # LazyFrame (period × topic × content)
print(sec.collect().shape)               # (~63, 4) per quarter

# 특정 분기
q4 = c.sections.filter(period="2025Q4")

# 사업의 내용 narrative
narrative = c.sections.filter(section="사업의 내용").collect()

# wide pivot (period × topic)
wide = c.sectionsAs("wide")

# 분기별 narrative diff (drift)
q1 = c.sections.filter(period="2024Q1", section="사업의 내용").collect()
q4 = c.sections.filter(period="2024Q4", section="사업의 내용").collect()
```

## 호출 동작

- target = DART 종목코드 (KOSPI/KOSDAQ). KOSDAQ/KOSPI 외 종목은 sections artifact 미박힘 가능 → None 또는 빈 LazyFrame 반환.
- period 미명시 = 전체 sectionsStorage load (LazyFrame · collect() 전까지 메모리 안전).
- section query = 한국 양식 ("사업의 내용" · "원재료 및 생산설비" · "주요계약·연구개발" 등) — XBRL tag 기준 매핑.
- sectionsStorage artifact 박힘 (`hasSectionsArtifact`) 시 빠른 load (period-sharded parquet · ~1 sec).
- artifact 미박힘 시 runtime build (~수 sec/분기) — Company.sectionsAs("build") 로 강제 가능.
- 결과 content 컬럼은 한국어 원문 + XML 태그 보존 (Polars Utf8). content_plain 사전 계산 X (`feedback_no_content_plain_precompute.md`).

## 대표 반환 형태

| 컬럼 | 타입 | 의미 |
|---|---|---|
| period | Utf8 | 분기 ("2025Q4") |
| topic | Utf8 | 사업보고서 항목 ("사업의 내용" · "원재료 및 생산설비" 등) |
| section | Utf8 | sub-section (예: "II. 사업의 내용 > 1. 주요 제품") |
| content | Utf8 | 한국어 원문 (XML 태그 보존) |
| rceptNo | Utf8 | DART 공시 접수번호 |
| sourceRef | dict | {url, page, paragraph} |

005930 sectionsStorage 실측: 40 분기 · 60 distinct topics · 7.76M chars · ≈ 3,100 page-equiv. artifact size 16.8MB (commit `f029d2298`).

## 기본 검증

- segment narrative 의 ASP/volume 수치 claim 은 모두 rceptNo + section paragraph 의 sourceRef 에 묶는다.
- period 미지정 호출 시 LazyFrame 의 .collect() 호출 직전 gc.collect() 강제 (Polars OOM 가드 · BoundedCache critical_prefix `_sections` 보존).
- section query 의 한국 양식 → 영어 자동 번역 금지 (DART XML 양식 SSOT 유지).
- 분기별 narrative drift 비교 시 양식 변경 (XBRL tag rename · 항목 통합) 회귀 가드 — c.sections 의 schema 변경 시 본 skill 의 반환 형태 동기화.
- 사업보고서 본문 원문 = `Ref.sourceType="external"` · wrapExternalInResult 의 [EXTERNAL CONTENT START] 마커 자동 박힘.
