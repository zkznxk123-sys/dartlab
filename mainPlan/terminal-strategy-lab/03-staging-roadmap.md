# 03. Staging Roadmap — 단계별 확실한 실행 명세

상태: v0.1 (2026-06-16). 거처 = `ui/packages/surfaces/src/terminal/`.

> 단계는 *기능을 깎은 MVP가 아니라* 회귀위험을 시간축 단방향으로 격리한 진입 경로. 각 단계 = 독립 출시 가능 + 다음 단계가 그 위에 단방향으로 쌓임. 종착 = 목표 종착(00 §3) 전체.

---

## P1 — 다전략 캔버스 (엔진 무수정)

### AC (수용 기준)
1. 콘솔에서 전략 ≤3개 추가/삭제/설정, 각 색칩.
2. 캔들에 포커스 전략 진입/청산 마커(N≥2면 포커스 1개만, 클러터 LOD).
3. 에쿼티 서브페인에 N전략+조합+B&H가 **공유 절대축**(시작 100)에 — "+30% vs +12%"가 한 자 비교(per-series 정규화 함정 회귀 0).
4. 조합 = 동일가중 equity 가중합. 조합 MDD 음영이 개별보다 얕으면 분산효과 시각 노출.
5. 리플레이 재생 시 N전략 동시 절단 재계산(look-ahead 차단 상속).
6. combo 거래 KPI = 명시적 "—"(거짓 0 금지). 곡선마다 OOS 2열·vs B&H·selection 경고·단일종목 분산 라벨.

### 타입 계약 (01 §3)
`StrategySlot` · `ComboMetrics`(equity계만) · `ComboResult` · `PortfolioBtResult` · `BtLayerExtend`.

### 영향 파일/함수
- **신규** `lib/backtest/portfolio.ts`: `runPortfolioBacktest`(runBacktest N회 + combo 가중합 + 순수헬퍼 메트릭). `lib/backtest/types.ts` 타입 추가. `engine.ts`/`presets.ts` 변경 0.
- **`charts/btLayer.ts`**: `publishBt`→`publishPortfolio`, `BT_EQUITY` `figures:[]`+공유축 draw 신규(공통 lo/hi·재기준·forEach·tooltip 직접), `BT_TRADES` extendData forEach·LOD, `STRAT_COLORS`, `applyBt`/`clearBt` 시그니처(extendData 신참조 재계산).
- **`charts/chartState.svelte.ts`**: `btKey/btParams/activeBt/setPreset/stepBtParam`→`btStrategies[]`+`add/remove/setSlotPreset/stepSlotParam`+`btFocus`. 공유 유지 `btCosts/btCostsBp/btOosSplit`.
- **`charts/PriceChart.svelte`**: BT effect(`:784`) `runPortfolioBacktest(displaySeries(),...)`. `tfv!=='D'` 가드(`:547`) `btStrategies=[]`. strip/dialog props N-aware. 마운트(`:1262`).
- **UI**: `StrategyConsole.svelte`(신규 인셋, BtConfig 흡수), `BacktestStrip.svelte`(헤드라인+combo+N미니행+분산라벨), `BacktestDialog.svelte`(포커스1 단수 유지+전략 탭), `ChartMenus.svelte`(`:211`)·`ChartRibbon.svelte`(`:234`) `btStrategies.length`, `btViz/EquityCurve.svelte`(공유축).

### 테스트
- svelte-check 0. 엔진 단위: N=1 경로 = 현 `runBacktest` byte 동일(회귀). combo[startIdx]=100·전부 non-null·equity 메트릭=직접계산 일치·거래 KPI null. 레이어: 공유축 비교(정규화 함정 회귀)·LOD. Playwright(`:5173/terminal`): 전략 2개→2색 마커+에쿼티 2라인+combo 동시·조합 MDD<개별·가독·리플레이 동시 절단·콘솔 0. 005930+거래多 종목.

### 롤백 / 회귀위험
가역(portfolio.ts·btLayer N슬롯·chartState 배열·UI N-aware 제거→단수 복원). 위험: **btLayer 공유축 draw 신규(중)** + chartState 배열 파급 9지점(중). 엔진 무수정(저).

---

## P1.5 — 프리셋 다양화 + 조건 빌더 조작 패널 + 펀더 게이트 (★운영자 강조)

> "6 드롭다운"을 깨는 핵심 단계. 프리셋 다양화 + **전문가급 조작 패널(조건 빌더)** + **단일종목 펀더 게이트(moat)** + 조건 레인 시각화(02 §1.5).

### AC
1. **프리셋 다양화**(close-only 탈피): 거래량 확인 MA(VWMA+OBV)·변동성 필터·Supertrend·Stochastic RSI·ROC + 스타일 8종(`quant/strategy/styles` 재사용). 입력에 high/low/volume 활용.
2. **조건 빌더 조작 패널**: 진입/청산 조건 다중 조합(AND/OR), 각 조건 = 지표 비교 또는 펀더 게이트. `quant/strategy/rule.py` DSL 브라우저 이식(01 §2.4). best/optimal/추천 단어 금지·OOS 강제·거래<10 수치 숨김(과적합 가드).
3. **펀더 게이트(moat)**: `quant/alphas` 9개(Piotroski·Altman Z·Beneish 등)를 진입 게이트로. PIT 근사(`rcept_dt` 이후)·계단·단일종목(생존편향 무관) 라벨.
4. **조건 레인 시각화**(02 §1.5): 조건별 on/off 스트립 서브페인 + 펀더 게이트 배경 음영 + AND 합성↔진입 마커 수직 정렬. 리플레이 동시 절단.

### 영향 파일/함수
- **엔진**: `lib/backtest/conditions.ts`(신규) — `Condition`/`StrategyRule` 평가, `signal` 일반화(01 §2.4). `synth/indicators` 미러(vatr·vobv·vstochastic) 또는 브라우저 지표 재사용. 펀더 게이트 시계열 = prebuilt(floor) 또는 로컬 라이브.
- **데이터**: 펀더 게이트용 PIT 시계열 — panel account/alphas를 `rcept_dt` join으로 분기 계단 생성(`rt` PricePort/FilingPort 경유). 생존편향 무관(단일종목).
- **레이어**: `btLayer` 조건 레인 draw(서브페인 `figures:[]` on/off) + 가격 페인 게이트 배경 음영.
- **UI**: `StrategyConsole` 조건 빌더 섹션(조건 행 추가/삭제·지표/펀더 선택·연산자·임계·AND/OR).

### 테스트 / 롤백 / 위험
조건 평가 단위(AND/OR·PIT 게이트 계단)·조건 레인↔진입 정렬·펀더 게이트 PIT(공시일 이전 미적용). 위험: **조건 빌더 UI+엔진(높)**·펀더 PIT 조인 데이터 배선(중). 가역(conditions.ts·레인 draw·빌더 UI 제거→프리셋 select 복원).

---

## P2 — 포지션·거래 정밀 (`runPass` 확장)

### AC
1. 전략별 손절%·익절%·트레일%·N봉 청산. 손절 청산 마커 색 구분(✖ 적), `exitReason:'stop'`.
2. 포지션 사이징 — fixed-fractional·vol-target(규칙적 리스케일). **Kelly 수치 금지**(개념만).
3. 거래 분석: 거래당 MAE/MFE·expectancy·R-multiple·연속승패·보유분포·수익 히스토그램. 위험지표: Calmar·MAR·Ulcer·tail ratio·롤링 Sharpe·월별 히트맵·underwater.
4. 손절 = 당일 인트라바 가정 라벨 강제(t+1 체결과 시점 충돌 명시).

### 영향 파일/함수
- **`engine.ts` `runPass`**: 보유 중 stop 체크(`low≤손절`·`high≥익절`·트레일 피크·N봉) → 청산, `exitReason:'stop'`. 거래당 `maePct/mfePct` 기록. 사이징 = shares 비례(fixed-frac/vol-target). `btStop=null`이면 현 동작(회귀 0).
- **`types.ts`**: `BtTrade`에 `maePct/mfePct`·`exitReason:'stop'`. `BtStopConfig`·`BtSizingConfig`. 위험지표 `BtMetrics` 확장.
- **`btViz/`**: `MaeMfeScatter`·`ReturnHistogram`·`MonthlyHeatmap`·`RollingSharpe`·`Underwater`. **`BacktestDialog`** 거래분석/낙폭 탭 확장.
- **`StrategyConsole`**: ⚙ 스탑·사이징 섹션.

### 테스트 / 롤백 / 위험
손절 trade 비용 정합·equity↔trades reconcile(`engine.ts:213` NaN 가드)·MAE/MFE∈[worst,best]·N=1 stop=null byte 동일. 위험: **runPass 확장(중~높)** — entry/exit 의미·비용 모델 재적용. 가역(stop/sizing 분기 제거).

---

## P3 — 커서바인딩 리밸런싱 (`runComboBacktest` 별도 패스)

### AC
1. 리플레이 일시정지 시 가중치 슬라이더 활성(전체차트·재생 중 잠금).
2. t시점 변경은 t 이후만 적용(displaySeries 절단 상속). ⚖ 타임라인 마커·구간별 유효가중.
3. **append-only**: 되감아 결정 수정 → 그 이후 폐기·재포크(새 runId). **반복재생 카운터**: 같은 구간 N회→과적합 경고.
4. 부분노출 = `runComboBacktest` 별도 패스(단일전략 `runPass` 무손상).

### 영향 파일/함수
- **`engine.ts`** 신규 `runComboBacktest(candles, slots, rebalances, opts)`: `runPass` 부분노출 일반화(weight 비례 shares, 리밸 시점 재배분, 비용=전환분만). 기존 `runPass`/`runBacktest` 보존.
- **`chartState`**: `rebalances:{t;weights}[]`·`setWeightAt`·`replaySession{tuningPasses}`·append-only fork. **`PriceChart`** BT effect `void ctl.rebalances`. **`btLayer`** ⚖ 마커 draw(OOS분할선 패턴 재사용). **`StrategyConsole`** 가중치 바(일시정지 게이트).

### 테스트 / 롤백 / 위험
커서<cut 가중치만 적용·되감기 재포크·t+1 정직·반복카운터. 위험: **부분노출 일반화(높)** — 별도 패스 격리가 핵심. 가역(combo 패스·rebalances 제거).

---

## P4 — 강건성 진단 (로컬 bonus + 퍼블릭 민감도)

### AC
1. **퍼블릭**: 파라미터 민감도 히트맵(IS/OOS 나란히, **argmax/추천 금지**)·Monte Carlo 거래 재배열(경로의존 스트레스, 곡선 fan).
2. **로컬**: walk-forward(재학습, 폴드별 거래수 동반)·CPCV. DSR/PBO/haircut **수치는 게이트**(parity+nTrials+다전략, 단일종목 영구 DEFER).

### 영향 파일/함수
- **퍼블릭**: `engine.ts` `sweep(...)`(격자 재실행, argmax 미반환)·`bootstrapTrades(...)`(거래 재배열 N회). `btViz/SensitivityHeatmap`·`McFan`.
- **로컬**: `rt` PricePort 경유 Python `walkForward`/`cpcv`(`src/dartlab/quant/strategy/_backtestAdvanced.py` 기존) 배선 + golden parity fixture. DSR/PBO 수치는 04 게이트.

### 테스트 / 위험
sweep 셀=격자·argmax 미반환. MC fan 결정론(seed). parity fixture(TS↔Python ±ε). 위험: parity gate(중). DSR/PBO 노출 회귀(grep 0).

---

## P5 — 미래 연속 (시뮬 코어 졸업 의존)

### AC
1. `mode:'live'|'simulate'` 토글(replay·sim.play 상호배타). live 여백 0 불변.
2. 리플레이 끝봉 → asOf 포트 상태(전략별 포지션·자본·가중치) → `sim.play` 초기조건.
3. 미래 fan band(점선·반투명·워터마크·단일 path 금지). 조합 곡선 asOf 연속.

### 영향 파일/함수
- **`chartState`** `mode`·`sim.play`(05 §1 동형). **`PriceChart`** 바통 터치 캡처·mode xAxis 패딩. **`btViz/FanBand`**(multi-point figure). **실제 path = `scenario-simulator/` 코어 졸업 후**(09 Phase 0 MC seed kill-test 선결).

### 테스트 / 위험
mode 상호배타·asOf 연속·미래 정직 가드. 위험: 코어 미완(P5는 계약·토글·anchor까지, path 주입 후속).

---

## 순서·게이트
P1→P2→P3→P4→P5 단방향. 각 단계 commit 자율·**push 운영자 명시 승인 후**(UI 시각 회귀·공개 무중단). P4 로컬·P5는 별도 선결(parity gate·시뮬 코어). 운영자 go로 P1 착수.
