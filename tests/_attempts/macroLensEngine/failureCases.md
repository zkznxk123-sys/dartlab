# Macro Lens Engine Failure Cases

본진 승격 전 반드시 막아야 하는 과잉 분석 케이스다.

## F1. Look-ahead

- 상황: 가격 기준일보다 늦게 발표된 macro observation을 같은 달 수익률에 붙인다.
- 기대: 해당 driver는 `blocked: lookahead`로 표시하고 beta/correlation 계산에서 제외한다.

## F2. 표본 부족

- 상황: 가격 월수익률과 macro 변환값의 교집합이 24개월 미만이다.
- 기대: 동행상관을 숫자로 단정하지 않고 `co-movement sample 부족` falsifier를 띄운다.

## F3. 섹터 prior만 있는 회사

- 상황: 섹터 edge는 존재하지만 해외매출, 원재료, 차입 만기 등 회사 증거가 없다.
- 기대: `qualitativeOnly`로 남기고 회사별 민감도 beta는 숨긴다.

## F4. 방향이 양쪽으로 갈 수 있는 driver

- 상황: 원/달러, 유가, PPI처럼 매출과 원가에 동시에 닿는 지표다.
- 기대: sign은 `mixed`로 유지하고 required evidence를 만족하기 전까지 positive/negative 결론을 내지 않는다.

## F5. Stale macro

- 상황: driver observation이 registry의 `staleAfterDays`를 넘겼다.
- 기대: 최신 국면 판단으로 쓰지 않고 source/date/value lineage에 stale 경고를 남긴다.

## F6. 상관을 인과로 오독

- 상황: co-movement correlation이 높지만 전파 edge나 회사 증거가 없다.
- 기대: 상관은 falsifier/탐색 신호로만 표시하고 scenario 또는 투자 결론으로 승격하지 않는다.
