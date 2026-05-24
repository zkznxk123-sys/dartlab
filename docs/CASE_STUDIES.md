# Case Studies — 실무 사용 시나리오 3 종

> dartlab 의 *실제 의사결정 흐름* 3 종. 각 사례는 문제 → API 호출 → 결과 → 의사결정 → 학습 5 단계로 따라할 수 있다.
> [TODO.md](../TODO.md) T12-4 트랙. 외부 기여자가 본 사례를 *템플릿* 으로 새 시나리오 추가 가능.

---

## 사례 1 — 외인 매수 모멘텀 스크리닝 (퀀트 트레이더)

### 문제

KOSPI 시가총액 상위 200 종목 중 *외국인이 최근 20영업일 누적 순매수* 가 90 percentile 이상이고 *주가 모멘텀* 도 동행하는 종목을 매주 발굴하고 싶다.

### API 호출

```python
import dartlab

# 1) 전종목 외인 보유 비중 변화 스크린
result = dartlab.scan(
    "foreignBuyMomentum",
    universe="kospi200",
    window="20d",
    minPercentile=90,
)

# 2) 결과 표 — 종목코드 / corpName / 외인 누적 순매수 / 20일 수익률 / percentile
print(result.table.head(20))

# 3) 각 종목의 ref 검증 (스크린 결과 → 원본 데이터)
for ref in result.refs[:3]:
    print(ref.toDict())   # source / period / values
```

### 결과 예시

```
| code   | corpName  | foreignBuyKrwBn | ret20d | percentile |
|--------|-----------|-----------------|--------|------------|
| 005930 | 삼성전자  | 1240            | 8.4%   | 99         |
| 000660 | SK하이닉스 | 380            | 12.1%  | 97         |
| 035420 | NAVER     | 95              | 5.8%   | 92         |
| ...    | ...       | ...             | ...    | ...        |
```

### 의사결정

- **진입 후보**: percentile 95+ 종목 6 개 선정
- **검증 단계**: 각 종목 `Company("...").show("ratios")` 로 PER/PBR 정상 범위 확인
- **백테스트**: `dartlab.scan("foreignBuyMomentum", ..., asOf="2024-01-01")` 로 과거 동일 신호 → 30일 후 수익 분포

### 학습

- 외인 매수 자체보다 *percentile 분포* + *동행 모멘텀* 결합이 신호 명확
- ref 발급으로 *답변 숫자 → 원본 데이터* 추적 가능 — AI 환각 차단
- 같은 recipe 가 universe 만 바꿔 (kosdaq150, sp500) 다른 시장에도 적용

---

## 사례 2 — 회사 신용 점수 모니터링 (재무 분석가)

### 문제

포트폴리오 30 종목의 *신용 위험 변화* 를 분기마다 자동 추적하고, Z-score 가 *위험 영역 (1.8 이하)* 진입 시 알람 받고 싶다.

### API 호출

```python
import dartlab

watchlist = ["005380", "000660", "005930", "035720", "207940"]  # 5 종목 예시

for code in watchlist:
    c = dartlab.Company(code)

    # 1) Altman Z-score (한국 K-IFRS 정합 버전)
    credit = c.credit.altmanZScore()
    print(f"{c.corpName}: Z={credit.score:.2f} ({credit.zone})")

    # 2) 3년 추이
    trend = c.credit.trend(years=3)
    print(trend.df.tail())

    # 3) 위험 영역 진입 시 알람 (사용자가 별도 webhook 또는 INCIDENTS)
    if credit.score < 1.8:
        print(f"  [경고] {c.corpName} 위험 영역 — 원본 ref: {credit.ref}")
```

### 결과 예시

```
삼성전자: Z=4.85 (safe)
SK하이닉스: Z=2.34 (gray)
LG에너지솔루션: Z=1.65 (distress)  <- 위험
  [경고] LG에너지솔루션 위험 영역 — 원본 ref: <Ref source=dart period=2025FY ...>
```

### 의사결정

- **distress 종목**: 분기 재무 변화 + 차입금 추이 + 이자보상배율 추가 점검
- **gray 종목**: 다음 분기 결과 우선 체크 (자동 cron 으로 분기마다 재실행)
- **safe 종목**: 정기 모니터링만 (월 1회)

### 학습

- Z-score 는 *단일 숫자* 가 아닌 *zone* (safe / gray / distress) 으로 보면 의사결정 빠름
- `credit.altmanZScore()` 의 ref 가 *어떤 재무항목 4 개* 가 점수에 기여했는지 표시 — 사용자 검산 가능
- 한국 K-IFRS 의 자산총계 / 유동비율 등 매핑은 dartlab `mappers` 엔진이 자동 흡수

---

## 사례 3 — Macro 사이클 + 섹터 로테이션 (자산 배분)

### 문제

미국 ISM 제조업 PMI 가 *수축 → 확장* 전환할 때 한국 반도체 / 자동차 / 화학 섹터 중 어디에 비중을 늘릴지 매크로 신호로 결정하고 싶다.

### API 호출

```python
import dartlab

# 1) US ISM PMI 사이클 + 한국 KOSPI 섹터 returns
cycle = dartlab.macro.cycle("us-pmi")
print(cycle.currentRegime)      # 'contraction' / 'expansion' / 'peak' / 'trough'

# 2) 과거 동일 regime 전환 시점에서 섹터별 평균 수익률
rotation = dartlab.macro.sectorRotation(
    cycle="us-pmi",
    transitionFrom="contraction",
    transitionTo="expansion",
    market="kospi",
    horizonDays=60,
)
print(rotation.table)

# 3) 현재 시점 추천
recommendation = rotation.recommend(asOf="latest")
print(recommendation)
```

### 결과 예시

```
현재 regime: trough  (확장 전환 임박)

과거 contraction → expansion 전환 60일 후 평균 수익률:
| sector       | meanRet | hitRatio | sampleN |
|--------------|---------|----------|---------|
| semiconductor | 12.4%  | 0.78     | 9       |
| automobile    | 8.1%   | 0.67     | 9       |
| chemical      | 5.3%   | 0.56     | 9       |

추천: 반도체 비중 +5p (hitRatio 0.78, sampleN 9)
```

### 의사결정

- **반도체 비중 +5p** — 과거 9회 전환 중 7회 hit, 평균 12.4%
- **자동차 +2p** — 보조 (hit 6/9)
- **화학 0** — 변동 큼, 추가 신호 확인 후
- **백테스트**: 1990 ~ 2024 전 사이클 동일 룰 적용 시 누적 수익 + drawdown

### 학습

- 매크로 신호는 *단일 시점* 이 아닌 *regime 전환* 으로 보면 timing 명확
- 섹터 로테이션은 *과거 sampleN* 이 작아도 (n=9) hitRatio 0.7+ 면 통계적 가치
- `macro.sectorRotation` 의 ref 가 *각 전환 시점 reference* 모두 발급 — 사용자 검산 가능

---

## 사례 추가 절차 (외부 기여자)

본 문서는 *템플릿* 으로 새 시나리오 추가 가능. 절차:

1. issue 생성 — "Case Study: <시나리오 한 줄>"
2. fork → master 에서 본 문서에 사례 4 부터 5 단계 형식으로 추가
3. API 호출 코드는 *실제 실행 가능* 해야 (REPL 검증)
4. 결과 예시는 *anonymize 가능한 경우* 실제 결과 사용 (그렇지 않으면 가공)
5. PR — `docs:` prefix + 본 문서 변경만

권장 시나리오 후보:
- ESG 점수 변화 모니터링 (Story / governance 엔진)
- 공시 본문 변화 추적 (sections.diff)
- 한미 비교 분석 (`Company("005930")` + `Company("AAPL")`)
- 산업 맵 + peer 비교 (`industry.sectorMomentumLeadership`)
- 시나리오 매칭 (`synth.scenarioMatch`)

---

## 관련

- [DEVELOPMENT.md](DEVELOPMENT.md) — 첫 수정 10분 가이드
- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR 흐름 + 5 PR 시나리오
- [TODO.md](../TODO.md) — T12-4 트랙
- [src/dartlab/skills/specs/start/firstAnalysisRecipe.md](../src/dartlab/skills/specs/start/firstAnalysisRecipe.md) — Skill OS 의 첫 분석 recipe
