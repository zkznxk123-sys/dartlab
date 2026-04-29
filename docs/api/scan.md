---
title: Scan
---

# Scan — 전종목 횡단분석

`scan()` 하나로 시장 전체를 한 번에 비교한다.
종목 발굴은 먼저 필드를 찾고, 조건을 조합하고, 남은 후보를 심층 분석한다.

## 사용법

```python
import dartlab

# 루트 함수
dartlab.scan("governance")              # 전종목 지배구조
dartlab.scan("governance", "all")       # 전체 상장사
dartlab.scan("fields", "roe")           # 스크리닝 필드 검색
dartlab.scan("screen", spec={
    "where": [
        {"field": "finance.ratio.roe", "op": ">", "value": 10},
        {"field": "valuation.pbr", "op": "<", "value": 1},
    ],
    "select": ["krx.marketCap"],
    "sort": {"field": "finance.ratio.roe", "desc": True},
    "limit": 30,
})

# Company-bound
c = dartlab.Company("005930")
c.governance()                          # 이 회사 1행
c.governance("all")                     # 전체 비교
c.debt()                                # 부채 구조
c.workforce()                           # 인력 분석
c.capital()                             # 주주환원
```

## 주요 축

| 축 | 설명 | 핵심 지표 |
|------|------|---------|
| governance | 지배구조 5축 100점 | 대주주 지분, 사외이사, 경영진 보상, 감사의견 |
| workforce | 인력/급여 | 종업원수, 1인당부가가치, 급여매출괴리 |
| capital | 주주환원 | 배당, 자사주, 환원형/중립/희석형 분류 |
| debt | 부채 구조 | 사채잔액, ICR, 위험등급 |
| network | 관계 네트워크 | 계열사, 주요 거래처 |
| signal | 키워드 트렌드 | 공시 키워드 연도별 추세 |
| disclosureRisk | 공시 리스크 | 우발부채, 리스크 키워드, 감사변경 |
| fields | 필드 카탈로그 | finance, report, docs, krx, krxIndex |
| screen | 조건형 스크리닝 | where/select/sort/limit spec |

## 계정/비율 횡단 조회

```python
# 특정 계정 전종목 조회
dartlab.scan("account", "영업이익")     # 전종목 영업이익 비교

# 특정 비율 전종목 조회
dartlab.scan("ratio", "roe")            # 전종목 ROE 비교
```

## 필드 탐색형 스크리닝

`scan("fields")`는 스크리닝에 쓸 수 있는 필드를 먼저 보여준다.

```python
fields = dartlab.scan("fields", "매출")
fields.select(["field", "label", "source", "unit", "operatorSet"])
```

반환 컬럼:

| 컬럼 | 의미 |
|------|------|
| field | `screen` spec 에 넣는 정규 필드 키 |
| label | 표시명 |
| source | `finance` / `report` / `docs` / `krx` / `krxIndex` |
| kind | number / text / boolean / context |
| unit | 원 / % / 배 / 건 / 일 / 점 / 주 / 텍스트 / 없음 |
| operatorSet | 허용 연산자 |
| coverage | 로컬 prebuild 기준 커버리지 |

조건형 screen 은 같은 field 키를 사용한다.

```python
spec = {
    "where": [
        {"field": "finance.ratio.roe", "op": ">", "value": 10},
        {"field": "finance.ratio.debtRatio", "op": "between", "value": [0, 100]},
        {"field": "docs.content", "op": "contains", "value": "HBM", "topK": 500},
    ],
    "select": ["valuation.pbr", "krx.marketCap", "krx.rsi14"],
    "sort": {"field": "valuation.pbr", "desc": False},
    "limit": 50,
}

dartlab.scan("screen", spec=spec)
```

`docs.*` 조건은 검색 인덱스 hit 기반 후보 생성이다. 완전한 원문 boolean scan 이 아니다.
`krxIndex.*` 필드는 종목별 속성이 아니라 시장 컨텍스트이므로 필터 조건이 아니라 `select` 컬럼으로 사용한다.

단일 지표 하나로 “좋은 종목”을 확정하지 않는다. 최소한 재무, 공시, 가격/거래, 밸류에이션 중 3개 관점을 교차한 뒤 후보 종목을 `Company`와 `analysis`로 다시 확인한다.

## 시장 지수

```python
dartlab.gather("krxIndex", "close", market="KOSPI")     # 코스피 지수
dartlab.gather("krxIndex", "close", market="KOSDAQ")    # 코스닥 지수
```
