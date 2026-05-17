---
id: engines.scan
title: Scan
kind: curated
scope: builtin
status: observed
category: engines
purpose: Scan 엔진은 시장/유니버스 횡단면에서 후보를 발굴하고 순위를 계산하는 실행 스킬이다. 트리거 — '스캔', '종목 발굴', '후보 추출', '랭킹'.
whenToUse:
  - Scan
  - scan
  - 스크리닝
  - 저평가 종목
  - 전종목 비교
  - 재무비율 횡단면
  - 공시리스크
  - 배당추이
  - 퀄리티 스캔
  - 조건형 screen
inputs:
  - axis
  - target 또는 preset
  - universe
  - spec
  - metric/account/ratio
outputs:
  - guide DataFrame
  - ranking/filter DataFrame
  - candidate evidence table
capabilityRefs:
  - scan
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.data.foundation
  - engines.analysis
sourceRefs:
  - dartlab://skills/engines.scan
requiredEvidence:
  - universe
  - datasetAsOf
  - filter
  - formula
  - table
  - executionRef
expectedOutputs:
  - 선택한 scan axis
  - 공개 호출
  - 필터/계산식
  - 후보 evidence table
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
    notes:
      - prebuilt snapshot과 Pyodide 포함 데이터 범위에 따라 일부 axis가 제한될 수 있다.
failureModes:
  - universe와 기준일 없이 후보를 나열함
  - ranking table 없이 회사명 bullet만 제시함
  - account/ratio primitive와 screen preset을 혼동함
  - scan 후보를 심층 analysis 검증 없이 투자 결론으로 확정함
forbidden:
  - universe, 필터, 계산식, 기준일, table ref 없이 후보 발굴을 완료했다고 말하지 않는다.
  - 결손값을 0으로 대체하지 않는다.
  - 단일 기업 심층 해석을 scan에서 끝내지 않는다. 후보 발굴 뒤 analysis/credit/quant로 검증한다.
  - 공개 API 호출법, guide 축, 반환 형태가 바뀌었는데 이 skill을 갱신하지 않은 상태로 완료 처리하지 않는다.
examples:
  - 저평가 퀄리티 종목 찾기
  - 배당 증가 종목 스크리닝
  - 공시리스크 상위 종목 확인
  - ROE 전 종목 횡단 비교
  - 매출 상위 100 개 회사 발굴
  - 신용 위험 상위 100 개 스크리닝
procedure:
  - dartlab.scan() 으로 21 축 가이드 DataFrame 확인.
  - axis 선택 (account · ratio · screen · valuation · quality · governance 등).
  - dartlab.scan(axis, target?, universe=..., spec=...) 호출.
  - 결과의 ranking · universe · datasetAsOf · filter · formula · executionRef 묶음.
  - 후보 발굴 후 단일 종목 심층 검증은 engines.analysis · engines.credit · engines.quant.
linkedSkills:
  - engines.scan.ratio
  - engines.scan.screen
  - engines.analysis
  - engines.credit
  - engines.quant
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

`scan`은 여러 기업을 한 번에 훑어 후보를 찾는 **L1.5 횡단 엔진**이다. L1 (company · gather) 위에서 전체 종목 universe 를 스캔해 ranking · filter · candidate evidence table 을 만든다. 단일 종목 심층 분석은 L2 (analysis · credit · macro · quant · industry) 의 책임. 질문의 단위가 "삼성전자를 분석해줘"이면 `Company`/`analysis`가 우선이고, "조건에 맞는 종목을 찾아줘", "전종목에서 상위 기업을 골라줘"이면 `scan`이 우선이다.

`account`와 `ratio`는 primitive다. 복합 투자 질문은 `screen` preset/spec 또는 `quality`, `valuation`, `growth`, `profitability` 같은 축으로 시작하고, 최종 판단은 후보별 `analysis`, `credit`, `quant`로 검증한다.

## 공개 호출 방식

```python
import dartlab

# 전체 스캔 축 가이드
guide = dartlab.scan()

# 축 실행
quality = dartlab.scan("quality")
valuation = dartlab.scan("valuation")
cashflow = dartlab.scan("cashflow")

# primitive
revenue = dartlab.scan("account", "매출액")
roe = dartlab.scan("ratio", "roe")

# 조건형 스크리닝
fields = dartlab.scan("fields", "roe")
value = dartlab.scan("screen", "value")
custom = dartlab.scan("screen", spec={"filters": []})
```

## 호출 동작

무인자 `dartlab.scan()`은 실행 가능한 스캔 축 가이드 DataFrame을 반환한다. 특정 axis를 주면 해당 유니버스의 prebuilt parquet 또는 provider scan 함수를 읽어 DataFrame을 반환한다.

`account`와 `ratio`는 전종목 단일 계정/비율 시계열을 조회하는 원자 축이다. `fields`는 조건형 screen에 넣을 필드를 찾는 축이고, `screen`은 preset 또는 spec 기반 조건식을 실행한다.

데이터가 없거나 snapshot이 제한되면 값을 추정하지 않는다. 빈 DataFrame, 결손 컬럼, 제한 메시지, 기준일 누락을 그대로 드러내고 필요한 수집/필드 확인 경로를 말한다.

## 전체 축/메서드 목록

| axis | label | group | 대표 호출 |
| --- | --- | --- | --- |
| governance | 거버넌스 | DART | `dartlab.scan("governance")` |
| workforce | 인력/급여 | DART | `dartlab.scan("workforce")` |
| capital | 주주환원 | DART+EDGAR | `dartlab.scan("capital")` |
| debt | 부채구조 | DART+EDGAR | `dartlab.scan("debt")` |
| account | 계정 | DART+EDGAR | `dartlab.scan("account", "매출액")` |
| ratio | 비율 | DART+EDGAR | `dartlab.scan("ratio", "roe")` |
| network | 네트워크 | DART | `dartlab.scan("network")` |
| cashflow | 현금흐름 | financial | `dartlab.scan("cashflow")` |
| audit | 감사리스크 | DART | `dartlab.scan("audit")` |
| insider | 내부자지분 | DART | `dartlab.scan("insider")` |
| quality | 이익의 질 | financial | `dartlab.scan("quality")` |
| liquidity | 유동성 | financial | `dartlab.scan("liquidity")` |
| growth | 성장성 | financial | `dartlab.scan("growth")` |
| profitability | 수익성 | financial | `dartlab.scan("profitability")` |
| efficiency | 효율성 | financial | `dartlab.scan("efficiency")` |
| valuation | 밸류에이션 | financial | `dartlab.scan("valuation")` |
| dividendTrend | 배당추이 | financial | `dartlab.scan("dividendTrend")` |
| macroBeta | 거시베타 | DART | `dartlab.scan("macroBeta")` |
| fields | 필드카탈로그 | DART | `dartlab.scan("fields", "roe")` |
| screen | 스크리닝 | DART | `dartlab.scan("screen", "value")` |
| disclosureRisk | 공시리스크 | DART | `dartlab.scan("disclosureRisk")` |

## 대표 반환 형태

가이드 호출은 DataFrame을 반환한다.

```text
dartlab.scan()
-> DataFrame
   axis, label, group, description, example, apiKey
```

축 실행도 대부분 DataFrame을 반환한다. 축마다 세부 컬럼은 다르지만 후보 발굴 답변에는 최소 다음 성격의 필드가 있어야 한다.

```text
stockCode/ticker, corpName/name, market/universe, latestAsOf/asOf,
metric/value/score, rank, basis/source, flags
```

`screen`은 조건식과 통과 여부, `account`/`ratio`는 계정명 또는 ratio id, 기간별 값, 기준일을 포함해야 한다. ranking/filter 결과를 말할 때는 원값과 rank를 함께 제시한다.

## evidence 기준

후보 발굴 결과에는 `universe`, `datasetAsOf`, `filter`, `formula`, `table`, `executionRef`가 필요하다. 최종 답변은 회사명만 나열하지 말고 evidence table을 포함한다.

## EngineCall (agent 경로) args 매핑

agent (ai/mcp/server) 가 본 엔진을 호출할 때는 `EngineCall(apiRef="scan", args={...})` 양식. dartlab.scan() 의 positional 인자를 args dict 의 key 로 변환:

| `dartlab.scan(...)` | `EngineCall(apiRef="scan", args=...)` |
| --- | --- |
| `dartlab.scan("growth")` | `{"axis": "growth"}` |
| `dartlab.scan("account", "매출액")` | `{"axis": "account", "target": "매출액"}` |
| `dartlab.scan("ratio", "roe")` | `{"axis": "ratio", "target": "roe"}` |
| `dartlab.scan("screen", "value")` | `{"axis": "screen", "target": "value"}` |
| `dartlab.scan("screen", spec={"filters": [...]})` | `{"axis": "screen", "spec": {"filters": [...]}}` |

**guard** — axis 와 target 을 점 표기로 합쳐 `apiRef="scan.ratio.roe"` 호출 금지 (`unknown_api_ref` 차단). args 안에 분리.

## 산업/섹터 질문 ("반도체 어때?" 류) 처리

"반도체", "2 차전지", "자동차" 같은 산업 keyword 가 질문에 있으면:

1. **industry 엔진 우선** — `dartlab.industry("반도체")` 또는 `c.industry()` 가 산업 라이프사이클 단계 (도입·성장·성숙·재도약·쇠퇴) + 밸류체인 노드 + 동종 종목 list 반환.
2. **scan 으로 횡단면 비교** — 같은 industryHint 안에서 `dartlab.scan(axis, universe={"industryHint": "반도체"})` 또는 결과 DataFrame 의 `industryName` 컬럼 필터.
3. 답변에는 산업 라이프사이클 단계 + 공정/세부 분류 (전공정 FAB · 후공정 패키징 · 테스트 · 설계 · 소재 · 장비) 별 ranking 둘 다.

단일 종목 답변에 부착되는 `industryBadge` (Company.show 응답) 는 같은 산업 종목 peers list 를 자동 포함 — 별도 industry 호출 없이 peer 후보 즉시 사용 가능.

## universe default

- `universe` 미지정 → KR 전종목 (KOSPI + KOSDAQ + KONEX 등 dartlab 수집 범위).
- 미국 시장 한정 질문이면 `universe="US"` 또는 `market="US"`.
- 산업 한정 → `universe={"industryHint": "반도체"}`.
- 사용자 지정 종목 list → `universe={"stockCodes": ["005930", "000660"]}`.

기준일 (`datasetAsOf`) 은 결과 DataFrame 의 컬럼으로 반환. 답변에 그대로 인용 — 데이터 freshness 명시.

## 기본 실행 순서

1. 질문이 후보 발굴인지 단일 기업 분석인지 산업 횡단인지 구분.
2. 후보 발굴이면 `dartlab.scan()`으로 axis 확인.
3. primitive (`account`/`ratio`) vs preset (`screen`) vs financial axis (`growth`/`profitability`/`quality`/...) 선택.
4. `dartlab.scan(axis, target/spec)` 또는 `EngineCall(apiRef="scan", args={"axis": ..., "target": ...})` 호출.
5. 기준일, 유니버스, 필터, 계산식, rank 검산.
6. 상위 후보는 `Company(...).analysis()`, `credit`, `quant` 로 심층 검증.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.scan()`의 guide 축, 공개 호출, 대표 반환 컬럼이 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신한다.
