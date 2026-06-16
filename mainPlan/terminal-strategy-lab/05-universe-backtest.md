# 05. Universe Backtester — 전종목 크로스섹셔널 랭킹 백테스트

상태: v0.1 (2026-06-16, 전문에이전트 4렌즈 토론 + 적대검증). 거처 = `ui/packages/surfaces/src/scan/universe/`(신규).

> ① 단일종목 다전략 캔버스(00~04)와 **별도 객체**다. "이 규칙으로 매 분기 상위 종목을 사면?"을 17년 survivorship-clean 유니버스 위에서 정직하게 회계한다. ①의 단일종목 가드는 *비상속* — 유니버스 특유 거짓말(생존 청산가·자유도 폭발·턴오버·벤치 조작)을 겨냥한 신규 가드가 필요.

---

## 0. 왜 별도 객체인가 (토론 합의)

`①`은 한 종목 candles 위 N전략 equity 곡선이다. `runPortfolioBacktest`의 `equity:(number|null)[]`는 candles 길이에 묶이고(`portfolio.ts:73`), combo는 *손으로 고른 N≤3 전략의 equity 가중합*이다. 유니버스는 **전종목(~2000+)을 매 리밸런싱마다 팩터로 랭킹 → 상위 K 보유 → 재랭킹**하는 *크로스섹셔널 포트폴리오 회계*다. 멤버십 교체·체결·턴오버 회계가 필요해 `runPass`(long/flat 단일종목 캐시 회계)를 **버린다**. 공유는 순수 equity 헬퍼 6종(`mdd`·`mddWindowOf`·`riskRatios`·`benchmarkStats`·`endRet`·`cagr`)뿐.

→ **04 §2 가드를 그대로 상속하면 "단일종목 가드로 유니버스를 검사했다"는 거짓 안전감**이 생긴다. 04 §2.8·2.9 신설로 막는다.

## 1. 거처 · 재사용 (실측 근거)

- **거처 = `ui/packages/surfaces/src/scan/universe/`** (terminal charts 아님). 근거: scan이 이미 `gov/prices/date/{year}.parquet`(67만행 long-form, 17년 survivorship-clean)를 DuckDB-wasm 뷰 `krxPricesAll`로 등록(`scan/tableSources.ts`) + ScreenBuilder(유니버스 정의) 보유. 백테스터 = scan의 자연 종착("스크린→랭킹→walk").
- **reject**: terminal `btLayer.ts`/`portfolio.ts` 확장 = candles-aligned 단일종목 계약(`portfolio.ts:73`)이라 N종목 holdings 못 받음. DataExplorer 탭 = 테이블 뷰어라 시계열 루프 부적합.
```
scan/universe/
  UniverseBacktester.svelte   풀스크린 모달 (DataExplorer 형제, scan LeftRail [유니버스 백테스트▸])
  engine.ts                   N종목 holdings 회계 루프 (신규 — 순수 헬퍼 6종만 재사용)
  ranking.ts                  랭킹 신호 (모멘텀·저변동성·52주신고가·유동성·단기반전)
  types.ts                    UniverseSpec·RebalanceSnapshot·UniverseBtResult
  viz/{NavCurves,QuantileSpread,RebalanceWalk,HoldingsTurnover}.svelte
```
- **재사용**: `terminal/lib/backtest/engine.ts`(헬퍼 6종)·`charts/btLayer.ts` 공유 절대축 draw 패턴(공통 lo/hi 픽셀 매핑)·OOS 분할선 draw·`scan/duckSql.ts`(`DartDb`·`krxPricesAll`)·`scan/ScreenBuilder`·`origin.ts`(HF SSOT)·`quant/alphas`(local 재무, P1 미사용).
- **동선**: 유니버스 walk → Q5 보유 행 클릭 → `/terminal?symbol=` 단일종목 차트(단방향 drill-down). **역방향 금지**(단일종목→유니버스 = cherry-pick 유인).

## 2. 엔진 계약 (신규 `universe.ts`)

```ts
interface UniverseSpec {
  rebalance: 'M' | 'Q' | 'W';                 // 거래일 캘린더 위 첫 거래일
  rankSignal: RankSignalKey;                   // 'mom12_1'|'lowVol60'|'high52w'|'turnover'|'reversal1m' (가격/기술만 P1)
  selection: { kind:'topN'; n:number } | { kind:'quantile'; buckets:number; pick:number };
  weight: 'equal';                             // P1 동일가중만 (cap/inv-vol = 후속)
  longShort: false;                            // P1 long-only (공매도·차입비용 folk)
  universe: 'all' | { market:'KOSPI'|'KOSDAQ' };
  minLiquidity?: number;                       // ADV 컷 (그 리밸 시점 데이터로만 — PIT)
  costBp: BtCostsBp;                           // 기존 타입 재사용 (턴오버 기반 적용)
  windowFrom: string; windowTo: string;
}
interface RebalanceSnapshot {
  t: string; decisionT: string; fillT: string; // decisionT < fillT 불변 (look-ahead 차단)
  selected: { code; rankValue; weight }[];
  turnover: number; nHeld: number; nEligible: number;
  delistedExits: number; advBreaches: number;   // 정직 카운터
}
interface UniverseBtResult {
  navByBucket: Record<number, number[]>;        // 분위별 NAV (시작 100)
  ewBench: number[]; indexBench: number[];      // 동일가중 전체 + 지수 (둘 다)
  rebalances: RebalanceSnapshot[];
  metrics: UniverseMetrics;                     // equity 헬퍼 재사용 + 턴오버·집중도
  cashDragPct: number; status: 'ok'|'invalid';
}
```
- **회계 루프**(일별 마킹 + 리밸일 execute): `nav = cash + Σ shares·close(code,t)`. 리밸일 = 신호는 `decisionT`(직전 거래일) 종가까지로 랭킹 → `fillT`(t+1) 시가 청산·매수, 비용 = `turnover × costBp`. 정지(v=0)·결측 = 체결 이연 + cashDrag(forward-fill 금지).
- **재사용 vs 신규**: 헬퍼 6종 그대로 / 랭킹·eligibility·분위 버킷·holdings 루프·턴오버·이중 벤치 전부 신규.

## 3. 데이터 경로 — floor vs local (실측 성능)

- **date 샤드 실측**: 연도당 12.5~16.6MB, 17파일 ≈ 230MB, 일별 전체 ≈ 1,200만행. **라이브 일별 17파일 쿼리 = floor 불가**(iOS WASM 힙 200~512MB 즉사, scan이 2년 윈도에도 30/60초 타임아웃 — `duckSql.ts`).
- **floor(퍼블릭 서버0) = prebuilt 월말 리샘플 패널**. 신규 `.github/scripts/prebuild/buildUniversePanel.py`(offline only, `buildPricesSnapshot.py` 템플릿·`enforceOffline()`):
  - 산출물 `gov/prices/universe-monthly.parquet` (long-form, 월말 1행/종목/월). 스키마: `ym·stockCode·close·mktcap·ret_fwd_1m·ret_fwd_3m·mom_12_1·vol_60d·high52w_prox·turnover·delisted`. ~58만행 = **5~15MB 단일 파일**(가격/기술 팩터만, 재무 EXCLUDE).
  - 브라우저는 1파일 로드 → DuckDB-wasm `NTILE` 크로스섹셔널 랭킹 + forward port return 루프.
  - **월말 = `MAX(BAS_DD) per (ym,stockCode)`**(캘린더 월말 아닌 그 월 마지막 거래봉).
- **local(:8400 bonus) = Python 일별 full-resolution**(date 샤드 17파일 직독, t+1 시가 체결·정지 이연 정밀). floor 월말 근사를 일별 정밀로 격상.
- **선결 의존**: ① `buildUniversePanel.py` 산출물(없으면 floor가 67만행 클라 로드 = 죽음) ② OPFS 캐시 재활성(`duckdb.ts:142` 현재 비활성 — 재방문 0다운로드).

## 4. 팩터 — 가격 P1 / 재무 랭킹 금지

- **✅ P1 (가격/기술, 17년 clean)**: 모멘텀(12-1·6-1)·저변동성(60/120봉)·52주 신고가 근접·유동성(거래대금)·단기반전(1개월). OHLCV만 쓰고 상폐사도 폐지일까지 후보 → survivorship-clean.
- **❌ 재무 팩터 *랭킹* = P1 금지(배너로도 불가)**: panel은 사라진 코드의 **13.9%(86/618)만** 재무 보유 → 망한 회사 86% 후보 누락 = 분모 자체가 생존자 편향(저PBR·고배당 등이 실제보다 좋아 보임). **배너는 *해석*을 가릴 뿐 *생성된 수치의 상향 편향*은 못 가림.** G6(held-out·zero-train 게이트) = 상폐사 재무 미수집이라 통과 *불가능* → 금지가 정공법. 정밀 재무 유니버스 = 상폐사 재무 재수집(별도 트랙) 선결.
- **✅ 단일종목 재무 *게이트*(04 §4.10)는 허용** — 한 종목 진입 조건이라 분모 문제 없음(생존편향 무관). **칼 = 랭킹 금지 / 게이트 허용.**

## 5. 벤치마크 — 이중 강제

- **(a) 동일가중 전체 유니버스(primary)** + **(b) 시총가중 지수(KOSPI/KOSDAQ, gov indices 샤드)** — **둘 다 동시 표시 의무(택일 금지)**.
- 동일가중 = 그 자체가 소형주 size 틸트 → "초과수익은 size 프리미엄 포함" 라벨. 지수만 쓰면 size·비용 차이가 알파로 오인. **둘 다 + 라벨 = 정직 필요조건(충분조건 아님 — size·유동성·생존 잔차 미통제 명시).**

## 6. 킬러뷰 + UX

킬러뷰 = **"N분위 NAV 곡선 + 분위 스프레드(Q5−Q1)"**. "분위가 단조롭게 벌어지는가"가 한 자에 읽히는 게 전부. 보유 회전 테이블은 *증거*(walk 다이얼로그 격리).
```
┌─ 유니버스 백테스터 ─────────────────────[월말 근사 ⓘ]──[✕]─┐
│ KOSPI+KOSDAQ 전종목(상폐포함) · 리밸 분기 · 12-1 모멘텀 · 5분위 · 동일가중 │
│ ┌─ NAV (공유 절대축, 시작 100) ──────────────────────────┐  │
│ │ Q5(상위) ━━━━━━ +148   Q4 ─── +121                      │  │ ★분위 끝만 라벨
│ │ EW전체 ▒▒▒▒ +110 (primary 벤치)  KOSPI - - +88 (보조)   │  │
│ │ Q1(하위) ─ ─ +71   ░EW MDD -34%(월말표본)░  ⚖⚖⚖ 리밸    │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌ 분위 스프레드 Q5−Q1 +77%p ┐ ┌ 턴오버 38%/분기 ┐            │
│ │ ⚠ 단조성=눈으로(t-stat 아님)│ │ ⚠ ADV초과 4% 빨강│            │
│ └────────────────────────────┘ └─────────────────┘            │
│ Q5 +148·EW +110·α +38%p │ ⚠ 사후선택 1신호·표본=리밸24회 [walk▸]│
└────────────────────────────────────────────────────────────────┘
```
- NAV = klinecharts 아닌 경량 SVG(NavCurves), `btLayer` 공유 절대축 draw 이식. floor 곡선은 **계단**(직선 보간 금지 — 월말만 평가 시각화). 분위 끝만 라벨, 중간 dim.
- **리밸 walk = 읽기전용 점프 스크럽**(이산 리밸 시점, ①의 연속 재생 아님). 편입▲/편출▼/유지● + "→다음분기 수익"(사후 라벨). 행 클릭 → 단일종목 drill-down("구성원이지 추천 아님" 툴팁).

## 7. 정직 가드 (04 §2.8·2.9 신설 — 떼어낼 수 없음)

| 가드 | 내용 |
|---|---|
| **U-G1 생존 보수 청산** | 멤버 소멸 시 마지막 종가 청산 = **금지**(휴지조각 과대평가). 사유 미구분 → **마지막 유효가 −30%(또는 0) 강제 손실 청산**(기본 보수). 합병 프리미엄 상향 보정 금지. 0손실 옵션 코드에서 *제거*. |
| **U-G2 PIT 멤버십** | 유니버스·필터(시총/거래대금 컷)는 *그 리밸 시점 그날 date 샤드*로만(코드 assert: 필터 입력 ts ≤ rebalanceT). IPO = 상장+룩백 충족 후만. forward-fill 금지. |
| **U-G3 턴오버·ADV P1 승격** | 단일종목 P4 아님 — **턴오버율·추정비용·ADV 초과 주문비율 KPI 동급 상시 노출**. 주문>ADV X% = "실거래 불가능" 빨강. bp 고정=소형주 비용 과소 경고. |
| **U-G4 이중 벤치** | EW 유니버스 + 지수 둘 다 표시 의무. size 틸트 라벨. 필요조건이지 충분조건 아님 명시. |
| **U-G5 리밸 타이밍 운** | "리밸일 ±N일 흔들면 결과 달라짐 — 한 타이밍 운 포함" 라벨. (지터 밴드 = local bonus.) |
| **U-G6 floor/local 근사(§2.9)** | floor NAV에 *(근사·월말)* 접미. "월중 손절·갭·정지 미반영, MDD 과소평가" 라벨. env.kind 분기로 라벨 증발 금지. local에서 괴리 오버레이 비교. |
| **U-G7 selection 차단** | argmax 금지만으론 부족 → **시도 조합 카운터**(팩터×분위×K×주기×필터 누적, "N조합 탐색=자유도 N") + **OOS 강제(끌 수 없음, 2010~19 train/2020~26 test)** + 사전규칙 1종 P1 + 중립 렌더(수익순 정렬 금지). |
| **U-G8 어휘 봉인** | "이 팩터가 시장/KOSPI를 이긴다"·"검증된 팩터"·"유효한 전략" = 투자자문(CLAUDE) grep 0. IC·팩터 t-stat·분위 단조성 **수치** 금지(표본=리밸 ~72회). 표면 = "과거 [기간] 이 유니버스·규칙 회계 결과, 추천 아님". |

## 8. 단계

- **U1 (최소·정직)**: 단일 가격 팩터(모멘텀 12-1) · 5분위 · 분기 리밸 · 동일가중 · long-only · 이중 벤치 · 보수 청산 · 시도 카운터 · OOS 강제. floor 월말 패널(prebuild) + DuckDB-wasm 루프. 킬러뷰(NAV 분위 + 스프레드 + 턴오버).
- **U2**: 가격/기술 팩터 다양화(저변동성·52주·유동성·반전) · 리밸 walk · 보유 회전 테이블 · ① drill-down.
- **U3 (local bonus)**: Python 일별 정밀 · ADV 비선형 충격 · 리밸일 지터 밴드 · floor/local 오버레이 비교.
- **U4 (별도 트랙·미착수)**: 재무 팩터 유니버스 = 상폐사 재무 재수집 선결(G6 게이트). 그 전 영구 금지.

## 9. 위험 · 선결 의존

1. **floor 라이브 일별 유혹 = iOS 즉사** → prebuilt 월말 패널이 **P1 진짜 선결**(아직 HF/prebuild에 없음). `buildUniversePanel.py` 신설이 코딩 착수 전 1순위.
2. **생존 청산가 과대평가**(U2 적대 발견 — 00 §4.11 "사유 미구분=무관"은 크로스섹셔널에서 거짓) → U-G1 보수 청산 필수.
3. **자유도 폭발**(팩터×분위×K×주기×필터 = 수천 조합) → U-G7 카운터+OOS+사전규칙.
4. **OPFS 비활성** → 재방문 재다운로드. 월말 패널 작아 견디나 재활성이 헤드룸.
5. **floor 월말 vs local 일별 괴리** → U-G6 근사 라벨·계단 곡선·오버레이.

## 10. 경계 (claim 금지)

- JUDGE(reverseDCF·compare) = financial-statement-lab. 시뮬/지수/이벤트레일 = scenario-simulator. egress = table-export. 본 랩 = *전종목 규칙 회계*만.
- 종목 추천·목표주가·"검증된 팩터"·"시장 초과" 일반화 = 금지(CLAUDE 투자자문 규약).
