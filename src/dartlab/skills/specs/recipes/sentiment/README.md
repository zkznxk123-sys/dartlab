---
id: recipes.sentiment.README
title: Sentiment 페르소나 — 미커버 (의도적)
purpose: 투자심리·플로우·포지셔닝 페르소나는 현재 dartlab 에서 미커버. 외부 AI 페르소나 트렌드와 비교 메시지 자리.
category: recipes
kind: index
status: published
whenToUse:
  - 투자심리 분석 페르소나 커버리지 확인
  - dartlab 의 정직 표시 방침 확인
---

# Sentiment 페르소나 — 미커버

dartlab 의 모든 recipe 는 L1.5 이하 (core · gather/providers · scan/frame/synth/reference) 의 *추적 가능한 raw 조합* 으로 작성된다. 투자심리·플로우·포지셔닝 영역은 **현재 미커버** — 다음 1차 데이터 소스가 dartlab raw 층에 없기 때문:

- 펀드 플로우 (EPFR · ICI · KOFIA flow report)
- 옵션 포지셔닝 (Put/Call ratio · skew · OI)
- 공매도 잔고 (KRX 단기 종가 + 일별 변동)
- 외국인·기관 일별 매매 (KRX investor flow)
- 변동성 surface (VIX · KVIX · 옵션 IV)

## 정직 표시

외부 트렌드는 "AI 센티먼트 애널리스트" 가 *뉴스·소셜 본문에서 추론으로* 심리를 만든다. dartlab 은 raw 데이터가 없으면 *없다고 말한다* — placeholder recipe 로 빈 칸을 채우지 않는다.

## 커버 조건

본 페르소나가 채워지려면:
1. L1 gather/providers 에 위 소스 중 ≥3 개의 raw 적재 (예: `providers.krx.shortBalance`, `providers.krx.investorFlow`).
2. L1.5 scan/frame 에 시점·종목 정렬된 panel 가공 (예: `scan.flow`, `frame.positioning`).
3. L1.5 이하 조합으로만 작성된 recipe ≥3 개 (예: `recipes.sentiment.shortBalanceMomentum`, `recipes.sentiment.foreignBuySignal`).

이 3 조건을 *순서대로* 채운 뒤 본 README 를 갱신하면서 recipes 추가.
