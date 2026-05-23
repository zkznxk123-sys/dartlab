---
id: recipes.sentiment.README
title: Sentiment 페르소나 — 토대 1 차 진입 (flow-based)
purpose: 투자심리·플로우·포지셔닝 페르소나의 *evidence-bound* 형태 진입점. 추론 라벨링 (긍정/부정) 대신 정량 신호 (외국인 imbalance · 공매도 잔고 · 내부자 cluster) 만 사용.
category: recipes
kind: curated
status: published
whenToUse:
  - 투자심리 분석 페르소나 진입
  - flow imbalance · short balance · insider cluster 절차 선택
  - 추론 라벨 vs 정량 신호 정책 확인
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
    status: supported
linkedSkills:
  - engines.company
  - engines.gather
---

# Sentiment 페르소나 — evidence-bound 진입

외부 트렌드의 "AI 센티멘트 애널리스트" 는 *뉴스·소셜 본문에서 추론으로* 심리를 만든다. dartlab 은 *본문 추론 라벨* 을 결론으로 쓰지 않는다 — 본 페르소나는 1 차 출처 (KRX·DART) raw 의 *정량 imbalance* 만으로 작성된다.

본 페르소나는 다음 커버 조건을 충족한 상태로 진입한다:

1. L1 raw — [gather/sources/flow.py](src/dartlab/gather/sources/flow.py) (외국인·기관 매매) · [gather/sources/insider.py](src/dartlab/gather/sources/insider.py) (내부자 거래) · [gather/sources/ownership.py](src/dartlab/gather/sources/ownership.py) (외국인 보유율) · [gather/domains/naver.py](src/dartlab/gather/domains/naver.py) `fetchFlow` 4 개 raw 사용 가능.
2. L1.5 합성 — `c.gather("flow")`, `c.gather("insiderTrading")` 결과를 RunPython 안에서 panel 로 정렬.
3. 본 페르소나의 recipe ≥3 개 (아래 1 차 진입 표).

## 1 차 진입 recipe

| recipe | 역할 |
|---|---|
| [recipes.sentiment.flowImbalance](/skills/recipes.sentiment.flowImbalance) | 외국인·기관·개인 순매수 imbalance + 20 거래일 z-score |
| [recipes.sentiment.insiderClusterTiming](/skills/recipes.sentiment.insiderClusterTiming) | 내부자 매수/매도 cluster (180 day window 3+ 명) + 직전 가격 lag |
| [recipes.sentiment.foreignBuyMomentum](/skills/recipes.sentiment.foreignBuyMomentum) | 외국인 누적 순매수 5/20/60d 가속도 |
| [recipes.sentiment.foreignHoldingLevel](/skills/recipes.sentiment.foreignHoldingLevel) | 외인 보유 비율 절대 수준 (5%~50% 범위) |
| [recipes.sentiment.priceMomentumGap](/skills/recipes.sentiment.priceMomentumGap) | 가격 5/20/60d 수익률 갭 — 가속/감속 phase |
| [recipes.sentiment.ownershipShiftSignal](/skills/recipes.sentiment.ownershipShiftSignal) | 5% 보유공시 누적 +/- 변화 |
| [recipes.sentiment.retailFlowReversal](/skills/recipes.sentiment.retailFlowReversal) | 개인 vs 외인+기관 z-divergence 반전 |

**deprecated**: `shortBalanceMomentum` · `consensusRevisionPace` (해당 gather axis 미구현 — 데이터 소스 추가 후 재작성).

## 미커버 영역 (정직 표시)

다음 raw 는 *여전히 dartlab L1 에 없음* — 본 페르소나의 깊이 확장은 이 raw 가 들어온 뒤:
- 옵션 Put/Call ratio · skew · OI (KRX 파생 raw 부재)
- 변동성 surface (KVIX · 옵션 IV)
- 펀드 플로우 panel (EPFR / KOFIA flow report)

## 페르소나 정체성

외부 sentiment analyst 의 *본문 → sentiment label* 추론을 dartlab 은 *raw flow imbalance → 정량 z-score → cluster timing* 으로 재해석한다. 추론 라벨 (긍정/부정/중립) 단계는 본 페르소나의 recipe 어디에도 없다 — 1 차 출처 cluster 와 z-score 만 인용한다.
