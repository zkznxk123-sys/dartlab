---
id: engines.industry
title: Industry
kind: curated
scope: builtin
status: observed
category: engines
purpose: Industry 엔진은 단일 종목을 산업 분류 (taxonomy.json) 의 공정 단계와 peer 그룹에 연결해 밸류체인 위치·동종 비교 맥락을 제공한다. 트리거 — '산업', '섹터', '업종', '밸류체인', 'industry'.
whenToUse:
  - Industry
  - industry
  - 산업 분석
  - 섹터 분석
  - 밸류체인
  - 공정 단계
  - peer 그룹
  - 동종업종
  - 산업 지도
  - 산업 라이프사이클
  - lifecycle
  - Vernon phase
  - 도입·성장·성숙·쇠퇴
inputs:
  - industryId 또는 종목코드 (Company-bound)
  - stage 필터 (선택)
  - summary / timeline / lifecycle 모드
outputs:
  - 산업 가이드 DataFrame
  - 공정·종목 DataFrame
  - 산업 위치 dict (Company-bound)
  - peer 종목 list
capabilityRefs:
  - industry
  - Company.industry
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
  - engines.scan
sourceRefs:
  - dartlab://skills/engines.industry
requiredEvidence:
  - target
  - industryId
  - stage
  - tableRef
  - executionRef
expectedOutputs:
  - 산업 ID / 산업명
  - 공정 단계 + 종목 list
  - 매출/영업이익 집계 (summary)
  - 연도별 공정 매출 추이 (timeline)
  - 라이프사이클 phase 시계열 (lifecycle — 도입·성장·성숙·쇠퇴)
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
  - 산업 ID 를 추측해 호출 — `dartlab.industry()` 가이드 미확인
  - 공정 단계명을 추측 — `dartlab.industry(industryId)` 결과의 공정 컬럼 미확인
  - summary 와 timeline 동시 호출 (둘 중 하나만)
  - peer 의 산업 분류 신선도 미확인 (taxonomy 운영자 수동 갱신)
forbidden:
  - 결손값을 0 으로 채우지 않는다.
  - peer 그룹을 추측해 답변하지 않는다 (반드시 industry() 결과 또는 Company.industry().peers 인용).
  - 공개 호출·반환 형태가 바뀌었는데 본 skill 갱신 없이 완료 처리하지 않는다.
examples:
  - 반도체 산업 공정 단계 확인
  - 삼성전자 밸류체인 위치 (전공정/후공정/장비)
  - 자동차 산업 peer 그룹 추출
  - 공정별 매출 집계 (summary)
  - 연도별 공정 매출 추이 (timeline)
  - 산업 라이프사이클 phase 분류 (lifecycle — Vernon 3-phase + 쇠퇴)
procedure:
  - 산업 목록 확인은 `dartlab.industry()` (가이드 DataFrame).
  - 산업 ID 정한 뒤 `dartlab.industry("semiconductor")` 로 공정·종목 확인.
  - 단일 기업 위치는 `dartlab.Company(code).industry()` — chainId·stage·confidence·peers dict.
  - 공정 매출 집계는 `dartlab.industry(industryId, summary=True, year="2024")`.
  - peer 그룹을 다른 엔진에 전달할 때는 종목코드 list 만 추출 (전체 dict 통째 전달 금지).
linkedSkills:
  - engines.company
  - engines.analysis
  - engines.scan
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-08'
---

## 엔진 역할

`industry` 는 단일 종목을 *밸류체인 공정 단계* 와 peer 그룹에 연결하는 **L2 분석엔진** (산업 매퍼) 이다. 산업 분류 (`taxonomy.json`) 와 종목→공정 매핑 (`nodes.json`) 을 데이터로 들고 있고, 매칭/집계/lifecycle 파이프라인이 분석 표면을 만든다. 분류체계는 운영자가 JSON 직접 편집해 갱신.

회사 재무 인과는 `analysis`, 부도 위험은 `credit`, 시장 매크로는 `macro`, 정량 가격 신호는 `quant`, 횡단 후보 발굴은 `scan` (L1.5) 이 담당. industry 는 *산업 컨텍스트 분석* 을 다른 L2 엔진과 **동등한 도메인 격리** 로 제공한다 — 다른 L2 를 직접 import 하지 않고 결합은 L3 조합기 `story` 가 한다.

## 공개 호출 방식

```python
import dartlab

# 1. 산업 목록 가이드
guide = dartlab.industry()
# → DataFrame: 산업ID · 산업명 · 공정수

# 2. 특정 산업의 공정·종목
nodes = dartlab.industry("semiconductor")
# → DataFrame: 공정 · 공정명 · 종목코드 · 종목명 · 역할 · 위치

# 3. 공정 단계 필터
fab_only = dartlab.industry("semiconductor", stage="fab")

# 4. 공정별 매출/영업이익 집계 (year 기준)
summary = dartlab.industry("semiconductor", summary=True, year="2024")
# → DataFrame: 공정 · 매출합계 · 영업이익합계

# 5. 연도별 공정 매출 추이
timeline = dartlab.industry("semiconductor", timeline=True)

# 6. 단일 기업의 산업 위치 (Company-bound)
c = dartlab.Company("005930")
position = c.industry()
# → dict: chainId · chainName · stage · stageLabel · confidence · matches · products · peers
```

## 호출 동작

`dartlab.industry()` (인자 없음) → 등록된 산업 목록 가이드 DataFrame.

`dartlab.industry(industryId)` → 해당 산업의 공정·종목 DataFrame. `stage` 로 특정 공정만 필터.

`summary=True` → year 기준 공정별 매출/영업이익 집계. `timeline=True` → 연도별 공정 매출 시계열. `lifecycle=True` → 산업 라이프사이클 phase 시계열 (Vernon 3-phase + 쇠퇴 — 도입 ≥30% / 성장 10~30% / 성숙 0~10% / 쇠퇴 0% 미만 YoY). 셋 동시 사용 X — 우선순위 summary > timeline > lifecycle.

`Company.industry()` → 단일 종목의 밸류체인 위치 dict — `chainId` (산업 ID), `stage` (공정), `confidence` (0~1 매칭 신뢰도), `peers` (같은 stage 종목코드 list). 매칭 실패 시 `None`.

분류체계 신선도는 `taxonomy.json` 의 운영자 수동 갱신 시점 — 신생 산업·신규 상장 직후엔 매칭 누락 가능.

## 대표 반환 형태

```text
dartlab.industry()
→ DataFrame
   산업ID : str         # 식별자 (semiconductor, automobile, ...)
   산업명 : str         # 한글
   공정수 : int         # 해당 산업의 공정 단계 수
```

```text
dartlab.industry("semiconductor")
→ DataFrame
   공정 : str           # 공정 단계 ID (fab, oSat, equipment, ...)
   공정명 : str         # 한글 공정명 (전공정 / 후공정 / 장비 / ...)
   종목코드 : str       # 6자리
   종목명 : str
   역할 : str           # 해당 공정에서의 역할
   위치 : str           # 밸류체인 상 위치
```

```text
Company("005930").industry()
→ dict
   chainId : str             # "semiconductor"
   chainName : str           # "반도체"
   stage : str               # "fab" / "oSat" / "equipment" / "design" / ...
   stageLabel : str          # 한글 공정명
   confidence : float        # 0.0 ~ 1.0 매칭 신뢰도
   matches : list[str]       # 매칭 키워드
   products : list[str]      # 주요 제품
   peers : list[str]         # 같은 stage 종목코드
```

## evidence 기준

산업 답변은 `target` (종목코드) · `industryId` · `stage` · taxonomy `dataAsOf` (운영자 갱신 시점) 를 남긴다. `confidence < 0.5` 면 매칭 신뢰도 낮음을 답변에 명시.

## 기본 실행 순서

1. 산업 ID 모르면 `dartlab.industry()` 로 목록 확인.
2. 단일 기업 위치는 `Company(code).industry()` — chainId·stage·peers 1 회로.
3. 공정 매출 집계가 필요하면 `dartlab.industry(industryId, summary=True, year=...)`.
4. peer 그룹은 `peers` list 만 추출해 `analysis` / `scan` / `quant` 에 전달.
5. 매칭 실패 (None 반환) 시 추측하지 않고 산업 분류 미등록임을 답변에 명시.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.industry()` 시그니처·반환 컬럼·`Company.industry()` 반환 키가 바뀌면 본 파일을 같은 변경에서 갱신한다.
