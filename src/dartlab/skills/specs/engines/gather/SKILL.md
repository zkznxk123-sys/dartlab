---
id: engines.gather
title: Gather
kind: curated
scope: builtin
status: observed
category: engines
purpose: Gather 엔진은 가격, 컨센서스, 수급, 뉴스, 배당, 소유구조, 섹터, 매크로, catalyst 일정 등 외부/보조 데이터를 수집하는 실행 스킬이다. 트리거 — '가격', '뉴스', '소유구조', '컨센서스', '외부 데이터 수집', '다가오는 일정'.
whenToUse:
  - Gather
  - gather
  - 가격 수집
  - 컨센서스
  - 수급
  - 뉴스
  - 배당
  - 소유구조
  - 섹터
  - 매크로 원자료
  - 다가오는 일정
  - catalyst calendar
  - 정기공시 due
inputs:
  - axis 또는 method
  - stockCode/ticker
  - market
  - period/date
  - provider 설정
outputs:
  - provider result
  - DataFrame
  - snapshot object
  - freshness metadata
capabilityRefs:
  - gather
  - Company.gather
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.data.foundation
  - engines.macro
sourceRefs:
  - dartlab://skills/engines.gather
requiredEvidence:
  - target
  - provider
  - latestAsOf
  - source
  - executionRef
expectedOutputs:
  - 선택한 gather method
  - 공개 호출
  - provider/source
  - freshness/제한
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
  - API 키 누락을 데이터 없음으로 오해함
  - 최신성 기준 없이 외부 데이터를 분석에 사용함
  - gather 원자료를 analysis 결론으로 바로 포장함
forbidden:
  - API 키나 인증정보를 답변에 노출하지 않는다.
  - provider/source/latestAsOf 없이 최신 데이터라고 말하지 않는다.
  - 공개 API 호출법, 메서드 목록, 반환 형태가 바뀌었는데 이 skill을 갱신하지 않은 상태로 완료 처리하지 않는다.
examples:
  - 현재 가격 snapshot 수집
  - 컨센서스와 뉴스 확인
  - 주요주주와 기관 보유 확인
  - 배당 분할 이력
  - peer 그룹 자동 추출
  - 매크로 원자료 (FRED · ECOS) 가져오기
procedure:
  - dartlab.gather() 또는 c.gather() 로 사용 가능한 method 가이드 확인.
  - method 선택 (price · consensus · news · supplyDemand · dividend · ownership · sector · insider · macro).
  - dartlab.gather(method, stockCode, period?, market?) 호출.
  - 결과의 provider · source · latestAsOf · executionRef 검증.
  - 분석 결합은 engines.analysis · engines.macro 가 담당. gather 결과를 결론으로 직접 포장 금지.
linkedSkills:
  - engines.company
  - engines.macro
  - engines.analysis
  - engines.scan
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

`gather`는 분석 엔진이 쓰는 외부/보조 데이터를 가져오는 L1 성격의 실행 엔진이다. 가격, 컨센서스, 수급, 뉴스, 배당/분할, 섹터, 내부자거래, 주요주주, 기관 보유, peer, 매크로 원자료를 다룬다.

`gather`는 원자료 수집과 snapshot 생성이 목적이다. 재무 해석은 `analysis`, 시장 매크로 해석은 `macro`, 후보 발굴은 `scan`이 담당한다.

## 공개 호출 방식

```python
import dartlab

g = dartlab.gather()

price = g.price("005930", market="KR")
consensus = g.consensus("005930", market="KR")
flow = g.flow("005930", market="KR")
history = g.history("005930", market="KR")
news = g.news("삼성전자", market="KR", days=30)
dividends = g.dividends("005930", market="KR")
holders = g.majorShareholders("005930", market="KR")
snapshot = g.collect("005930", market="KR")

c = dartlab.Company("005930")
company_price = c.gather("price")
```

## 호출 동작

`dartlab.gather()`는 기본 Gather 객체를 반환한다. 메서드 호출은 provider, cache, snapshot을 통해 데이터를 가져오며, API 키가 필요한 provider는 키 누락 시 안내 가능한 예외 또는 제한 상태를 반환한다.

Company-bound `c.gather(axis)`는 회사의 종목코드와 market을 자동으로 넣어 gather method를 실행한다.

## 전체 축/메서드 목록

| method | 담당 데이터 | 대표 호출 |
| --- | --- | --- |
| price | 현재 가격 snapshot | `g.price("005930", market="KR")` |
| consensus | 실적/목표가 컨센서스 | `g.consensus("005930", market="KR")` |
| flow | 투자자별 수급 | `g.flow("005930", market="KR")` |
| revenue_consensus | 매출 컨센서스 | `g.revenue_consensus("005930", market="KR")` |
| history | 가격/거래량 시계열 | `g.history("005930", market="KR")` |
| news | 뉴스 검색/수집 | `g.news("삼성전자", market="KR", days=30)` |
| dividends | 배당 이력 | `g.dividends("005930", market="KR")` |
| splits | 액면분할/주식분할 | `g.splits("005930", market="KR")` |
| sector | 섹터/업종 정보 | `g.sector("005930", market="KR")` |
| insiderTrading | 내부자 거래 | `g.insiderTrading("005930", market="KR")` |
| majorShareholders | 주요주주 | `g.majorShareholders("005930", market="KR")` |
| ownership | 기관/소유 구조 | `g.ownership("005930", market="KR")` |
| industryPeers | 업종 peer | `g.industryPeers("005930", market="KR")` |
| macro | 매크로 원자료 | `g.macro("GDP", market="KR")` |
| collect | 종목 snapshot 일괄 수집 | `g.collect("005930", market="KR")` |
| invalidate | cache 무효화 | `g.invalidate("005930")` |
| close | client/session 종료 | `g.close()` |

## 대표 반환 형태

메서드에 따라 DataFrame, list/dict, Pydantic-like snapshot object, 또는 `None`을 반환한다.

```text
provider, source, target, market, latestAsOf/date,
metric, value, unit, raw, flags
```

`price`는 가격, 통화, 기준시각을 포함하고, `history`/`flow`는 DataFrame 성격의 시계열을 반환한다. `collect`는 여러 domain 결과를 묶은 snapshot을 반환한다. provider가 데이터를 주지 않으면 `None`, 빈 DataFrame, 제한 flag로 표현한다.

## evidence 기준

외부 데이터는 provider, source, latestAsOf, target, executionRef를 남긴다. 최신성이 중요한 질문이면 snapshot 기준시각을 답변에 포함한다.

## 기본 실행 순서

1. 필요한 데이터 domain을 정한다.
2. `dartlab.gather()` 또는 `c.gather(axis)`를 선택한다.
3. provider/API 키 제한을 확인한다.
4. 반환값의 기준일, source, 결손 여부를 확인한다.
5. 해석은 analysis/macro/scan/story로 넘긴다.

## 기본 검증

스킬은 공개 실행 문서다. Gather 공개 메서드, Company-bound 호출, 대표 반환 형태가 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신한다.
