# 01. Mechanism Architecture — 메커니즘을 차트에 박는 법

상태: v0.1 (2026-06-16). 거처 = `ui/packages/surfaces/src/terminal/`.

> "어떻게 주가그래프에 메커니즘을 넣나"의 답. 3겹: ① 시각화 = klinecharts 커스텀 draw + extendData ② 시간 척추 = 리플레이 절단 ③ 미래 = mode 토글. 엔진은 순수함수 재사용.

---

## 0. 실측 기반 (코드 확인됨 — 추측 0)

- **전략 시각화 기반** `charts/btLayer.ts`: klinecharts 커스텀 지표 2종. `BT_TRADES`(candle_pane, `figures:[]`, custom `draw`로 마커·음영 직접) + `BT_EQUITY`(`pane_BT` 서브페인, `figures:[{eq},{bh}]` → **klinecharts가 공유 절대축 자동 스케일**). 결과는 **모듈 전역 Map 1슬롯**(`tradeMap`/`eqMap`). `applyBt(chart,rev)` = createIndicator + `overrideIndicator(calcParams:[rev])` 재계산.
- **N-라인 가변 선례** `charts/compareOverlay.ts`(CMP): `figures:[]` + `extendData.peers[]`(가변 N) + 단일 draw `forEach` 폴리라인. **단 캔들축에 `base*(v/v0)` % 리베이스**(공유 절대축 아님). `econOverlay.ts`(ECON): 서브페인 시리즈별 *독립* min-max 정규화(모양만).
- **리플레이 척추** `PriceChart.svelte` `displaySeries()`: `replayCutT`까지 절단 → `runBacktest(displaySeries(),...)`(`:800`)가 *그 시점 데이터만으로* 재계산. BT effect는 `dataRev` 의존이라 절단 시 자동 재실행. **별도 replay↔BT 바인딩 코드 없음 — "잘린 배열을 엔진에 먹임"이 전부.**
- **미래 Play 설계** `scenario-simulator/05`: `sim.play{on,t,len,ms}` + `play*` 4메서드를 replay와 **동형 신설**, 재생엔진 공유, `mode:live|simulate` 상호배타. 미래 fan band = 새 multi-point figure(valBand priceLine 재사용 불가). **시뮬 코어 DAG 미완**(`mc.distribution`/`pricePath` 부재) → fan 렌더 계약까지만 지금.
- **엔진** `lib/backtest/engine.ts`: `runBacktest(candles,preset,params,opts)` → `BtResult`, 순수함수 동기 <1ms/4000봉. `runPass`(target:Int8Array 1봉 shift 체결). 순수헬퍼 `mdd`/`riskRatios`/`mddWindowOf`/`endRet`/`benchmarkStats` = equity 배열만 받음.

## 1. ⚠ 적대검증이 정정한 2대 설계 함정 (반드시 반영)

### 1.1 공유 절대축 함정 (치명)
CMP는 캔들축 % 리베이스, ECON은 시리즈별 독립 정규화 — **둘 다 공유 절대축이 아니다.** 현 `BT_EQUITY`는 `figures:[{eq},{bh}]`로 klinecharts가 두 라인을 *공유 절대축*에 자동 스케일(→ "전략 +30% vs B&H +12%"를 한 자 비교). N전략으로 가며 `figures:[]`+draw로 전환하면 이 자동 공유축을 **잃는다**.
→ **해법(신규 코드)**: draw 안에서 전 라인(N전략 equity + combo + B&H)의 **공통 lo/hi 계산 → 가시구간 시작=100 재기준 → forEach 폴리라인**. CMP/ECON엔 없는 신규. *per-series 정규화 절대 금지*(절대수익 비교 = 본질).

### 1.2 combo 거래 부재 (치명)
combo = equity 가중 산술합 → 체결 개념 0 → 승률·손익비·노출·거래표·CSV **전부 N.A.**(억지 합산=거짓). equity 메트릭(수익·MDD·Sharpe·Calmar·vs B&H)만 순수헬퍼를 combo equity에 재호출. **거래 KPI는 UI에서 명시적 "—"**.

### 1.3 확인된 사실
한 run의 모든 전략은 동일 candles·windowBars → **동일 startIdx·전부 non-null·시작 100**(워밍업 차이는 flat target=0, null 아님). `combo[i]=Σ wₛ·eqₛ[i]`는 "고정가중 보유합성(리밸런싱 없음)"의 정확한 표현. OOS 분할선은 BT_TRADES(캔들페인) draw라 figures 무관 → 회귀 0. "lines deep-merge 함정"은 직접 draw 전환 시 소멸(이득).

## 2. 3겹 메커니즘

### 2.1 시각화 — btLayer 1슬롯 → extendData N슬롯
```
extendData 페이로드 (BtLayerExtend):
{
  strategies: { id; color; label; trades: {ts→{side,px,exitReason}}; equity: (number|null)[] }[],  // N≤3
  combo:      { equity: (number|null)[]; color } | null,   // 동일가중 가중합
  bh:         (number|null)[],                              // 공통 B&H (동일비용)
  rebalances: { ts; weights }[] (P3),                       // ⚖ 마커
  mdd:        { peak; recover } | null                      // combo 기준 음영
}
```
- `publishBt`→`publishPortfolio(pf, candles)`: 모듈 Map 대신 extendData 구성. `applyBt`/`clearBt` 시그니처 변경(`calcParams:[rev]`→`overrideIndicator({extendData})` CMP식 신참조 재계산).
- `BT_EQUITY`: `figures:[]` + **신규 공유축 draw**(§1.1). N전략(1.2px)·combo(2px 굵게)·B&H(회색 점선). MDD 음영=combo 1개. tooltip/legend 자동소멸 → draw 직접 라벨 또는 `createTooltipDataSource` 신규.
- `BT_TRADES`: `extendData.strategies[].trades` forEach 색마커. **클러터 LOD**: N≥2 → 캔들페인 마커=포커스 1전략만(라벨 off, barSpace≥12만), 줌아웃(barSpace<2) 전체 off. `STRAT_COLORS`(≤3) 신규 팔레트. exitReason='stop' 색 구분(P2).
- 성능: draw O(가시봉 ~200)×N(≤3) ≈ 600 iter/frame 무시 가능. 엔진 N≤3회 ×<1ms.

### 2.2 시간 척추 — 리플레이 절단 상속
BT effect를 N-aware로: `runPortfolioBacktest(displaySeries(), btStrategies, opts)`. `displaySeries()`가 이미 `replayCutT`까지 절단 → **N전략 전부 그 시점 데이터만으로 재계산**(look-ahead 차단이 무료 상속). 리밸런싱(P3)도 절단 위에 올라타 t≤cut인 가중치만 적용.

### 2.3 미래 — mode 토글
`mode:'live'|'simulate'` 신설(replay·sim.play 상호배타). live=현 동작. simulate=xAxis 미래 패딩 + fan band(CMP draw 변형). asOf 포트 상태(전략별 포지션·자본·가중치) → sim 초기조건. **실제 미래 path는 시뮬 코어 졸업 후**(P5는 계약·토글·anchor까지).

### 2.4 ★조건 빌더 + 펀더 게이트 — 규칙을 시간 레인으로 (02 §1.5 시각화의 데이터 측)
조작 패널 조건 빌더 = `quant/strategy/rule.py` Rule DSL(`entry/exit` boolean·AND/OR)의 브라우저 이식. 각 조건이 시간축 boolean 배열 → 조건 레인 + AND/OR 합성 → 진입 시그널.
```ts
interface Condition {
  kind: 'indicator' | 'fundamentalGate';
  // indicator: RSI<30, 가격>MA200 등 — closes/지표 배열에 비교 (브라우저 계산)
  // fundamentalGate: Piotroski≥6, AltmanZ>안전, Beneish<의심 — panel PIT 조인
  series: (number|null)[];   // 봉별 값(지표) 또는 분기 계단(펀더, 공시일 rcept_dt 이후만 채움)
  op: '<'|'>'|'>='|'<='|'crosses'; threshold: number;
  satisfied: Uint8Array;     // 봉별 0/1 → 조건 레인 렌더
}
interface StrategyRule { entry: Condition[]; exit: Condition[]; combine: 'AND'|'OR' }
// signal[i] = combine(entry conditions satisfied at i)  — 기존 BtPresetDef.signal 일반화
```
- **펀더 게이트 데이터**: `quant/alphas`(Piotroski 등 9개)·panel account 필드를 *과거 시점별로* 산출 → `rcept_dt` 이후 봉부터 그 분기 값 적용(PIT 근사·계단). 생존편향 무관(단일종목). 브라우저 floor면 prebuilt 시계열, 로컬이면 라이브 계산.
- **렌더(02 §1.5)**: 조건별 `satisfied` → 조건 레인 서브페인(`figures:[]` draw, on/off 스트립). 펀더 게이트 = 가격 페인 **배경 음영**(분기 계단). AND 합성 레인이 진입 마커와 수직 정렬. 레인 LOD: 줌아웃=합성만, 줌인=개별 펼침.
- **라벨**: 펀더 게이트는 PIT 근사(공시일 기준)·계단·생존편향 무관 라벨. 유니버스 랭킹 아님(단일종목 게이트).

## 3. 엔진 계약 (P1, `runPass` 무수정)

```ts
// lib/backtest/portfolio.ts (신규)
interface StrategySlot { id:string; preset:BtPresetKey; params:Record<string,number>; color:string; label:string }
interface ComboMetrics { retPct; cagrPct; mddPct; mddDays; sharpe; sortino; calmar; beta; alphaPct; infoRatio }  // equity계만
interface ComboResult { equity:(number|null)[]; bhEquity:(number|null)[]; metrics:ComboMetrics; mddWindow; weightsLabel:'equal' }
interface PortfolioBtResult { slots:{id;result:BtResult}[]; combo:ComboResult|null; startIdx:number }

function runPortfolioBacktest(candles, slots, opts): PortfolioBtResult
  // 1. slots.map(s => runBacktest(candles, s.preset, s.params, opts))   ← 기존 순수함수 재사용
  // 2. combo.equity[i] = Σ (1/N)·slot[s].equity[i]   (동일가중)
  // 3. combo.metrics = { mdd(combo.equity), riskRatios(combo.equity), endRet(...), benchmarkStats(combo,bh) }  ← 순수헬퍼 재호출
  //    거래 KPI 없음 (combo엔 trades 0)
```
- `engine.ts`·`presets.ts` 변경 0. P2(stop·sizing)는 `runPass` 확장(별도 §03). P3(리밸런싱)은 `runComboBacktest` 별도 패스로 격리(부분노출 일반화, 단일전략 경로 무손상).

## 3.5 ★`decisionT < fillT` PIT 불변식 — 세 엔진 통합 SSOT

세 백테스트(단일종목 N전략·유니버스 횡단면·펀더게이트)를 묶는 축은 `runPass`가 아니라 **인과율 불변식**이다. 현 코드에 *이미* 표현돼 있다(단일=`target[i-1]` shift, 유니버스=`decisionT/fillT` 05 §2) → 통합 = 신규 추상이 아니라 *공통 불변식의 명시화*.
```ts
// 모든 백테스트가 공유하는 인과율 불변식 (엔진 계약 진짜 SSOT)
interface PitDecision<T> {
  decisionT: string;   // 결정에 쓰인 마지막 거래봉 (t)
  fillT: string;       // 체결봉 (t+1) — decisionT < fillT 코드 assert (테스트 강제)
  payload: T;          // 단일: target 0/1 | 유니버스: Holding[] | 게이트: gateOpen
}
// 단일종목  = runPass(target[i-1])              의 special case
// 유니버스  = rebalances[].{decisionT,fillT,selected}  (05 §2)
// 펀더게이트 = gate.series[i] = (candle[i].t >= rcept_dt) ? quarterValue : null  (공시 전 봉 null=진입차단)
```
세 엔진은 fill/accounting 루프는 다르나 **`decisionT < fillT` + 비용 적용 지점을 공유**. floor는 vectorized 유지(불변식 충족하므로 event-driven 재작성 불필요). **단 P2 stop은 봉내 이벤트 순서가 필요** → `runPass` 내부에 *봉당 미니 우선순위*(전체 재작성 아님):
```
봉 i 처리(P2): 1.갭 체결(시가가 전일 손절선 갭통과)→시가, "갭손절"  2.인트라바 손절(low≤stopPx)→stopPx(보수: 같은봉 high 무시)  3.신호 청산→시가
// 우선순위 고정 = look-ahead 0. low/high 동시성은 "최악 가정"으로 봉인("당일 인트라바 가정" 라벨)
```

## 3.6 ★한국 비용·체결 모델 — 비용은 *점추정이 아니라 밴드*

현 `BT_COSTS` 고정의 toy 신호 #1 = **슬리피지가 유동성/주문규모와 직교**(삼성전자와 소형주가 같은 10bp). 단 적대검증 정정: √-impact 함수의 계수 `k`도 *EOD에 없는 정보를 지어낸 folk-stat*(U-G1이 금지한 "임의 숫자"와 동죄). → **점추정 함수 금지, 두 길만**:
```ts
interface KrFillModel {
  tickRound: (px) => number;          // 호가단위 스냅 (소형주 0.5% 비용 — 가격대별)
  priceLimit: (fillPx, prevClose) => number | null;  // 상하한가 ±30% 클램프, 갇힘=null=이연(deferredBars 재사용)
  // 슬리피지: 두 경로 중 택1 (점추정 금지)
  //  (A) "슬리피지=사용자 입력 가정, 우리가 추정 안 함" (현 bp 고정 + "가정값" 라벨) — 가장 명확
  //  (B) 유동성 비례를 *밴드*로: slip ∈ [k_lo·√(orderValue/ADV), k_hi·√(...)] 이중실행(U-G1식) — 불확실성 노출
}
```
- ADV = `volSma(v,20)·close`(이미 indicators에 있음, 신규 데이터 0). **세금**: 매도만(이미 정확), 2025 거래세 인하 스케줄 반영. **VI/단일가**: EOD로 복원 불가 → "체결 ±15% 봉=VI 가능성" 라벨(가짜 정밀 금지). **비용 4성분 워터폴**: `costDragPct` 한 줄 → 세금/수수료/슬리피지/충격 분해(기관급 표식이 아니라 *투명성*).
- 세계급 floor의 진짜 상한 = "더 정교한 비용 함수"가 아니라 **"비용 불확실성을 밴드/가정으로 명시"**. local(Python)만 일중 VWAP·비선형 충격(`vectorBacktest` 갭 슬리피지 이미 보유).

## 4. 상태 계약 (`chartState.svelte.ts`)
- 단수→배열: `btKey/btParams/activeBt/setPreset/stepBtParam` → `btStrategies:StrategySlot[]` + `addStrategy/removeStrategy/setSlotPreset(i)/stepSlotParam(i)`. 공유 단수 유지: `btCosts/btCostsBp/btOosSplit`. 포커스 `btFocus:number`.
- P2: `btStop:{lossPct;gainPct;trailPct;timeBars}` (슬롯별 또는 공유). P3: `rebalances:{t;weights}[]` + append-only `replaySession{tuningPasses}`. P5: `mode:'live'|'simulate'` + `sim.play`.

## 5. 회귀 격리 원칙
- **엔진**: `runPass`/`runBacktest`/`presets` P1 무수정 → N=1 경로가 현 결과와 byte 동일(회귀 테스트). P2 stop은 `btStop=null`이면 현 동작. P3 부분노출은 `runComboBacktest` 별도.
- **btLayer**: extendData 전환이 최대 단일 변경점 → 커밋 분리. 공유축 draw 신규.
- **dialog**: 357줄 단일전략 골수 → **N-aware 금지, 포커스 1전략 단수 유지** + 얇은 전략 탭.
