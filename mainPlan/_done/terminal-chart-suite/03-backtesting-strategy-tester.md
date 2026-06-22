# 03. Backtesting Strategy Tester — /terminal 전체화면 차트 중심 EOD 전략 검증

> ⛔ **SUPERSEDED (2026-06-16)**: 본 문서는 `mainPlan/terminal-strategy-lab/`(주가차트=시간기계 다전략 백테스팅 PRD)로 **폐기·흡수**되었다. 운영자 판정 — "드롭다운 6개뿐(능력 약함) + 안 읽힘(strip/모달 분산)". 새 PRD = 차트를 전략 검증 표면으로 승격(다전략 동시 비교·조합·리플레이 walk·커서바인딩 리밸런싱·미래 시뮬 연속). §0.6 가드 5종은 새 PRD `04-honesty-and-rigor.md`로 승계. **신규 작업은 `terminal-strategy-lab/` 참조.** 본 문서는 이력 보존용.

> **참조 규약(분리 후):** 본 문서는 `mainPlan/terminal-chart-suite/`(현재/과거 차트 suite)에 속한다. suite 내부 = 01(차트)/02(레일)/03(백테스팅). **시뮬 PRD 참조(바 번호 05·07·08·09 등)는 `../scenario-simulator/NN`을 가리킨다**(단방향: suite ⟶ 시뮬, 역참조 없음).

상태: PRD v0.4 (2026-06-16 — "엔진을 SSOT로 퍼블릭+로컬 터미널에 전문가급으로 박기" 4-렌즈 적대 토론 확정. **§0.5.9 + §0.6 이 엔진 SSOT·floor 경계·가드 SSOT**. v0.3 §0.5.1~0.5.8 유효 유지). v0.3 (2026-06-14 공통배선 이후 현재기준 정합 + v1 스코프 확정 — **§0.5 가 경로·모듈구조·원장깊이·v1 스코프·결과계약 SSOT**. v0.2 본문 중 §14 법적가드·§19 타입계약·§20 지표공식·§21 테스트매트릭스·§5 리포트·§18 상태매트릭스는 유효 참조로 유지. 4-렌즈 토론 확정). 옛 v0.2: 메모리 `project_terminal_backtesting_prd`에서 repo 이관.
지위: 차트 suite의 백테스팅 컴포넌트. 통합 시퀀스(시뮬 07 통합로드맵: 지수→이벤트레일→**백테스팅**→시뮬)에서 3번. 백테스팅 엔진은 시뮬레이터와 **RunSpec·ReportDock·look-ahead 가드 DNA 공유**(시뮬 09 §1, 08 §5 — ReportDock backtest mode). "전문가급"=품질 기준(방법 엄밀함). ⚠**UI 경로 전수 stale — 기계적 매핑 강행**: 본문의 *모든* `landing/src/lib/terminal/<rest>`(본문 :135 `data/backtest.ts`·:158 `charts/btLayer.ts`·:797·:810·:825·:1118 등)를 `ui/packages/surfaces/src/terminal/<rest>` 로 1:1 치환해 읽는다(터미널 전체 이동, commit ff9099ba0, 04 §3). 포트=`ui/packages/contracts`, 데이터 소스=`ui/packages/runtime/src/adapters/{public,local,test}/`. 엔진 경로(`src/dartlab/*`)는 불변. `ui/shared/chart/PriceChart.svelte`(별개 SVG)와 혼동 금지.

## 0. 판정과 확정 결론

사용자 요구는 명확하고 타당하다. `/terminal`에는 이미 기본 백테스트 기능이 있으므로, 다음 단계는 단순 MVP 추가가 아니라 **전체화면 차트에서 전략을 탐색하고, 같은 화면 아래에서 성과와 가정을 검산하는 고밀도 Strategy Tester**로 설계한다.

정식 제품 포지션은 "전문가급 수익 검증"이 아니다. 정식 포지션은 **EOD 일별 데이터 기반, 가정 노출형 과거 시뮬레이션**이다. "전문가급"은 UI 문구가 아니라 내부 품질 기준으로만 쓴다: look-ahead 차단, 비용 기본 ON, B&H 동일비용 비교, 체결/현금/포지션 원장, 결과 재현성, 경고와 출처의 상시 노출.

최종 UX 결론:

- 전략 탐색의 주 표면은 차트다.
- 백테스트는 전체화면 차트 안에서 실행한다.
- 실행 결과는 캔들 위 진입/청산 마커, 보유 구간, 에쿼티/B&H 보조 페인, MDD 음영으로 즉시 보인다.
- 상세 보고서는 차트 아래에 붙는 스크롤 리포트로 제공한다.
- 일반 모드와 전체화면은 같은 `ChartCtl` 상태를 공유한다.
- 결과 문구는 "이 전략이 좋다"가 아니라 "이 기간과 이 가정에서는 이렇게 계산됐다"로 고정한다.

## 0.5 현재기준 정합 + v1 스코프 확정 (공통배선 이후 — 본 절이 경로·구조·원장·스코프·계약 SSOT)

> 본 PRD §1~§23 은 *공통배선 이전* 아이디어로 작성돼 경로·모듈구조·스코프가 stale/과설계 하다. **본 절이 경로·파일구조·원장깊이·v1 스코프·결과계약의 SSOT** 다. §14(법적·표현 가드)·§19(타입 계약)·§20(지표 공식 정본)·§21(테스트 매트릭스)·§5(리포트 상세)·§18(상태 매트릭스)는 *수학·법률·UX 규약*으로 경로 무관하게 유효한 참조다. 2026-06-14 전문 4-렌즈 토론(스코프 아키텍트·과설계 비평·ground-truth 2)로 확정.

### 0.5.1 경로 정합 (stale → 실측)
| 옛 PRD 경로 | 실측 현재 경로 |
|---|---|
| `landing/src/lib/terminal/data/backtest.ts` | **`ui/packages/surfaces/src/terminal/lib/backtest.ts`** (`data/` 아님 `lib/`. 440줄 *단일* 순수파일) |
| `landing/src/lib/terminal/charts/btLayer.ts` | `ui/packages/surfaces/src/terminal/charts/btLayer.ts` (순수 렌더) |
| 신설 `landing/src/lib/terminal/backtest/*` | `ui/packages/surfaces/src/terminal/lib/backtest/*` (§0.5.3) |
| `/lab/terminal-dev` | `landing/src/routes/lab/terminal-dev/+page.svelte` → `DevTerminal`(`@dartlab/ui-surfaces/terminal/dev`, `checkDevIsolation.js` 가드) |
| Python `src/dartlab/quant/strategy/{backtest,_backtestAdvanced}.py` | 동일(불변 — 별개 L2 엔진, DEFER P5만) |

### 0.5.2 ★실측: 정확성 척추는 이미 라이브 (Phase 1-2 의 "구축" 대상 아님)
`lib/backtest.ts:runBacktest`(440줄)이 이미 구현:
- **t종가→t+1시가 체결**(`target[i-1]` 1봉 shift, `:239`) → look-ahead *구조적 불가*.
- v=0/o=0 봉 체결 이연(`:240`)·**B&H 동일 `runPass`+동일 비용**(`:392-393`)·비용 기본 ON(commission 1.5/sellTax 15/slippage 10 bp).
- split-suspect(`:357`)·CAGR null `<252`(`:350`)·Sharpe/Sortino null `<60`(`:334`)·**3-pass cost-drag**(`:389-393`)·open position 가상청산 mark(`:269-282`).
- `btLayer.ts` = 순수 렌더(`BT_TRADES` 캔들페인 figures:[] 무왜곡 + `BT_EQUITY` 서브페인 strat/bh + **MDD 음영 peak→recover**, `:74-92`). `BacktestStrip.svelte` = props 표시 + **상시 면책 footer**(`:87-91`). ChartCtl bt state(btKey/btParams/btCosts/btCostsBp, `:92-95`, 세션 전용 비영속)·일봉 전용.
- **⟹ v1 의 일은 "엔진 구축"이 아니라 *계약 경화 + 리포트 도크*.** PRD §16 Phase 1-2(원장화/계약)는 *이미 옳은 엔진을 재유도*하는 부분이 큼.

### 0.5.3 모듈 구조 — 11파일 과설계 → ~4파일 (변경이유별 분할)
440줄(≈130줄이 preset 정의)을 11파일(`types/strategies/engine/ledger/metrics/validation/robustness/cache/runner/worker/chartAdapter`)로 쪼개는 건 미빌드 기능용 빈 seam·import 의식. **유일한 실제 결합 문제 = preset registry 와 실행 커널이 한 파일**(변경 이유 다름: 전략 추가 vs 체결 의미). 정합:
```
ui/packages/surfaces/src/terminal/lib/backtest/
  index.ts    # compat barrel — runBacktest·BT_PRESETS·BT_COSTS·전 타입 re-export. 기존 7 importer 무수정
  types.ts    # BtPresetKey/Def·BtParamDef·BtTrade·BtWarning·BtMetrics·BtResult·BtCostsBp (+ RunSpec/provenance)
  presets.ts  # BT_PRESETS registry + signal fns (~130줄)
  engine.ts   # runPass·runBacktest·mdd·riskRatios·cagr·findSplitSuspect·BT_COSTS·reconcile 가드
```
- 마이그레이션: `lib/backtest.ts` → `lib/backtest/` 디렉터리 + `index.ts` barrel 이 현 export 전량 재노출 → 7 importer(PriceChart·btLayer·BtConfig·BacktestStrip·chartState·SourcesModal·seriesBus) **무수정**. `cd landing && npm run check && npm run build` 검증. 무동작변경.
- **CUT**: `ledger/robustness/cache/runner/worker/chartAdapter/metrics/validation` 독립 파일. `chartAdapter` 로직은 이미 `btLayer.publishBt`(compact→Map)에 옳게 있음. `worker.ts`/`sensitivityRunner.ts` 는 Sensitivity 출시 때만(DEFER).

### 0.5.4 원장 깊이 — 6원장 과모델 → 2구조 + reconcile 가드
6원장(Order/Fill/Position/Cash/Trade/Equity)은 multi-asset·partial-fill·margin·pyramiding 어휘. 본 제품은 **long/flat·단일종목·fractional·전액**(`shares=cash/entryPx`, cash=0) — order book·부분체결·평단·현금/포지션 분리 부기 없음. PRD §20 의 *실제* 품질 목표 = **3 불변**(trade-PnL↔equity-PnL reconcile · B&H 동일경로[이미 참] · open-position convention 명시[이미 구현]). 정합:
- **최소 원장 = `runPass` 가 이미 만드는 2 배열**: `equity:(number|null)[]`(= cash+shares·close, 전 지표가 여기서 계산) + `trades:BtTrade[]`.
- **ADD(소·고가치)**: ① **reconciliation 가드**(Σ trade 기여 ≈ 최종 equity 수익률, rel-tol 1e-8 — 불일치 시 status invalid·UI 지표 미노출) ② `deferredBars`/`deferredReason`(v=0 이연 감사) ③ `exitReason:'signal'|'finalMark'|'finalLiquidation'`(현 `open:true` 암묵 → 명시).
- **REJECT**: 독립 OrderLedger/CashLedger/PositionLedger 배열(long/flat 에선 equity+trades 의 파생 view, §15 short/margin/pyramiding 제외 제품에 multi-asset 부기 = 과모델).

### 0.5.5 결과 계약 — 평행 `BacktestResult`+adapter 대신 `BtResult` 확장
- PRD §8.1-8.2 의 `BacktestRunSpec`/`BacktestResult` 평행 신설 + `BtResult→Result` adapter 는 불필요 indirection. **`BtResult` 를 *확장*** + **flat `RunSpec` 레코드**(symbol·range·strategy·params·costs·dataAsOf·adjusted·dividend) + `provenance`(source/as-of/adjusted — strip footer 이미 보유) ADD. export/Assumptions 탭 재현성 확보.
- `specHash`/`runId` 는 **DEFER**(worker/cache/async 도입 시) — 동기 sub-ms 실행엔 stale-result race·캐시 키 부재. `orders[]`/`fills[]`/`cash[]` series·중첩 RunSpec 의 `partialFillPolicy`/`impactModel`/`targetWeight`(엔진에 없는 상수 필드) = flatten/CUT.

### 0.5.6 ★v1 스코프 — CORE(P1-3) vs DEFER(별도 PRD)
실제 제품 가치 = **차트 마커 + equity/MDD 페인 + 가정·경고가 숫자 옆에 붙은 스크롤 리포트**. 파라미터 *탐색*·통계적 *과최적화 기계*·전략 *저작*·Python parity 는 각자 독립 정확성 부담 → 별도 PRD.

| Phase / 항목 | 판정 | 근거 |
|---|---|---|
| **P1** flat RunSpec + provenance + `BtResult` 확장(reconcile/exit/deferred 필드) | **CORE** | 재현성·export. 평행 Result+adapter 아님(§0.5.5) |
| **P2** ~4파일 분할 + reconciliation 가드 | **CORE** | preset↔커널 seam(§0.5.3) + §20 reconcile(§0.5.4). 6원장 reject |
| **P3** 전체화면 리포트 도크 **4탭(Overview/Trades/Drawdown/Assumptions)** + row→chart sync | **CORE** | 실제 제품 업그레이드. mddWindow→btLayer 음영 재사용. Assumptions=footer(`:87-91`) 승격 |
| P3.5 날짜범위 + replay-cut **입력** | **CORE(소)** | 유일 데이터역량 갭(현 windowBars만). look-ahead 가드라 cut slice 자명 정확 |
| **P4** Calendar(월/연 heatmap) | **DEFER(선택 CORE-lite)** | equity 후처리·엔진변경 0. P3 정착·눈검수 후 |
| **P4** Sensitivity grid + worker + cache | **DEFER(별도 PRD)** | 파라미터 *탐색* = 다른 제품 모드(data-snooping). worker/cache/stability/overfit-언어 일괄 동반. §10.2 "스윕 보이면 Robustness 필요"로 P5 견인 |
| **P5** Robustness(walk-forward/CPCV/DSR/PBO) + TS↔Python parity | **DEFER(별도 PRD)** | Python L2 엔진 영역(`_backtestAdvanced.py`). §2.4 가 그 엔진 원장 미정합 명시 → synthetic golden parity 선결. **★빈 Robustness 탭 금지 — §5.6 "미계산=검증안됨"이 모든 v1 run 에 '검증 안 됨' 낙인 = 가치없는 surface. 탭 자체를 안 만드는 게 맞음** |
| **P6** Strategy Builder(AND/OR·JSON I/O) | **DEFER(별도 PRD)** | 저작 제품 층. 6 preset 이 v1 탐색 표면(교육용, "추천" 아님) |

**컷 라인 한 문장**: CORE=P1-3(타입화 재현 결과 + ~4파일 + reconcile 가드 + 리포트 도크 4탭 + row→chart sync + 날짜/replay 입력). 파라미터탐색(Sensitivity)·통계검증(Robustness/Python parity)·전략저작(Builder)은 각자 독립 PRD. Calendar 만 회색지대(P3 후 CORE-lite 가능).

### 0.5.7 ★로컬/퍼블릭 공동배선 (운영자 우선순위)
TS 엔진은 `Candle[]` 입력·Svelte/DOM/network import 0(`backtest.ts:1-7`)·결정론 순수 → **어댑터 무관**. `displaySeries()`=`rt.price.loaded(code)`(PricePort, public/local/test 공급). 동일 패리티 2 불변:
1. **PricePort 캔들+조정(`ctl.adj`) 패리티**: public(static·브라우저 parquet)과 local(:8400)이 같은 code/range 에 같은 `Candle{t,o,h,l,c,v}`(+동일 조정) 반환하면 결과 byte-동일. **백테스트 코드는 `env.kind` 분기 절대 금지**.
2. **CORE(P1-3) 동기·in-thread·브라우저 전용 유지**(현 `:635-659` 처럼) — public floor 엔 서버 없음. local :8400 은 *bonus*(빠름/장기이력), 요구 아님.
- **Python 의 합법 진입 = DEFER P5(Robustness)만**, **TS↔Python synthetic golden fixture 통과 후에만** 공식 수치(미통과 시 `research/robustness reference` 라벨 + `pythonParityMissing` 경고). Python=parity-gate bonus·floor 아님.

### 0.5.8 실측 변경 집계 (CORE v1)
| 파일 | 변경 |
|---|---|
| `lib/backtest/{index,types,presets,engine}.ts` | 단일 `lib/backtest.ts` → 4파일(barrel 무수정 마이그레이션) + reconcile 가드·RunSpec/provenance·exit/deferred 필드 |
| `charts/BacktestReport.svelte` 외 4탭 컴포넌트 (신설) | Overview/Trades/Drawdown/Assumptions(카드더미 금지·full-width band) |
| `charts/PriceChart.svelte` | 전체화면 도크 마운트·row→chart sync(기존 `$effect:635-659`·mddWindow 재사용) |
| `charts/BacktestStrip.svelte` | summary strip 으로 축소(상시 가정 footer 유지) + 도크와 result 공유 |
| `charts/chartState.svelte.ts` | 날짜범위/replay-cut 입력 state(btKey 류처럼 세션 전용) |
| (DEFER) worker/sensitivity/robustness/builder | 별도 PRD |

### 0.5.9 v0.4 — "엔진을 SSOT로 전문가급으로 박기" 토론 확정 (2026-06-16, 4-렌즈 적대 토론)

> 계기: 운영자 — "백테스트가 약하다(버튼·개념). 엔진을 SSOT로 퍼블릭+로컬 터미널에 전문가급으로 제대로 박고, 부족하면 엔진 개선." rigor 아키텍트·아키텍처/패리티·UI/UX·적대 레드팀 4 렌즈가 코드 실측 후 토론. **본 절 + §0.6 이 엔진 SSOT·floor 경계·가드 SSOT.**

**A. 핵심 판정 — "전문가급"의 floor 경계 (rigor ≠ 통계 수치)**

전문가급 척추 대부분은 *이미 라이브*다(TS `engine.ts`: look-ahead 1봉 shift·t+1 체결·동일비용 B&H를 같은 `runPass`에 `target≡1` 주입·`reconcileOk`·표본 null 게이트 / Python `_backtestAdvanced.py`: walkForward·cpcv·dsr·pbo / `multipleTesting.haircutSharpe·realityCheck`). 갭은 "기능 부재"가 아니라 *배선·정합·노출*이다.

⚠ **floor 경계 = 표본이 지탱하는 것만 floor에**:
- **floor 승격(브라우저, 표본이 받침)**: OOS train/test **분할 + 시각화 + 인샘플/아웃샘플 2열 비교**. p값 주장이 아니라 "실제로 무슨 일이 있었나"라 단일종목 표본이 버틴다.
- **floor 금지(folk-stat)**: DSR/PBO/CPCV/haircut **수치**를 단일종목·6프리셋·2020+(`gov/prices` T+1·5년) 표면에 노출 금지. `nTrials≈6`이면 `dsr` 보정 off, 5년 6분할 PBO=노이즈. 이 통계는 quantGap **횡단면 다전략** 자산이지 단일종목 표면 아님. → Python 정본 + 표본/nTrials 게이트 + parity 통과 시에만, "로컬 정밀 모드" 라벨.

**B. 엔진 SSOT 정의 (통합 금지 · 책임 분리)**

| 표면 | SSOT | 비고 |
|---|---|---|
| 터미널 단일종목 long/flat 실행 | **TS `runBacktest`** (floor·동기·브라우저) | metrics 정의(Sharpe rf=0·ann√252·<60봉 null·CAGR<252봉 null) 정본 |
| robustness/연구(walk-forward·CPCV·DSR·PBO·multi-asset) | **Python `quant/strategy`** | universe-scale·장기 = local bonus |
| *겹치는* 표면(단일 long/flat next-open) | **golden parity fixture** | TS·Python byte 동의(rel 1e-8). 미통과 Python 수치 = `pythonParityMissing` 라벨 |

Python `_backtestAdvanced.py` 폐기 아님 — **parity 레퍼런스(정답지) + universe-scale bonus**.

**C. 진짜 엔진 갭 3개 (신규 엔진 0 — 배선/정합)**

| # | 갭 | 처치 | 분류 |
|---|---|---|---|
| 1 | Python `vectorBacktest` equity↔trade 비용 불일치(`daily_ret`=무비용 close-to-close vs `trade.pnl`=비용반영) — §2.4 "공식 통계 엔진 아님" 실체 | equity를 trade-cash 원장서 재구성 or daily_ret에 진입/청산 비용 반영 + reconcile(TS `reconcileOk` 미러) | P5 선결(DEFER) |
| 2 | 벤치마크 상대 통계(alpha/beta/IR/tracking error) 전무 | 신설 `_metricsBenchmark.py`(`_metricsBasic` 패턴·B&H 페어 이미 존재→데이터 0). 기초(alpha/beta/IR vs B&H 단일창)는 서술적이라 **floor 후보** | CORE-lite 후보 |
| 3 | TS↔Python golden parity fixture 부재 | `tests/.../btParity.fixture.json` 1개, 양쪽 테스트 소비, `BT_ENGINE_VERSION` 박음 | P5 게이트(DEFER) |

**D. floor / bonus 경계 (env.kind 분기로 floor에서 사라지는 기능 = 0)**

| 기능 | 퍼블릭 floor | 로컬 bonus | 라벨 |
|---|---|---|---|
| 단일 백테스트·equity·trades·마커·핵심 metrics·RunSpec | ✅ TS 동기 | (동일) | costsOff·splitSuspect·fewTrades |
| 날짜범위·replay-cut·OOS train/test **분할 음영+2열** | ✅ (캔들 slice·후처리, 엔진변경 0~소) | (동일) | replayCut 이후 미반영 명시 |
| DSR/PBO/CPCV/walk-forward **수치** | ⊘ (folk-stat, A 참조) | parity+nTrials 충족 시 | `로컬 정밀 모드`·`research reference` |
| 멀티종목 포트(`multiAssetBacktest`) | ⚠ N≤~30 in-thread, 초과 worker | 전종목 universe·risk-parity | 표본 제한 표기 |

UI: bonus는 **숨김 아니라 비활성+이유 라벨**(자물쇠 "로컬 정밀 모드"). "열등 아니라 헤드룸" 프레이밍(`project_terminal_improvement` floor/bonus).

**E. UI/UX — 운영자 불만 직격 (CORE 반영)**

- **"버튼 약함" → `BtConfig`를 "전략 콘솔"로 재설계(CORE 승격 — §0.5.8 누락 항목 추가)**: 6프리셋 칩→라벨 드롭다운(+설명), 명시적 `▶ 백테스트 실행` 버튼(첫 선택은 자동 1회=초보 1클릭 보존), ③기간·검증 행(P3.5 날짜+replay-cut+train/test 분할 슬라이더), ⑤벤치마크 읽기전용 라벨(끌 수 없음=공정성 약속 노출). 리본 활성 칩=스펙 요약(`골든크로스·3Y·▲비용`).
- **"개념 약함" → 리포트 도크 4탭 + OOS**: Overview(RunSpec+KPI그리드+equity/underwater+**인샘플/아웃샘플 2열**)·Trades(MAE/MFE/exitReason+필터+CSV)·Drawdown(underwater+top-N표+row→차트)·Assumptions(footer 승격+상시 고지). strip→요약(헤드라인+5지표+`도크 열기`).
- **차트**: 기존 마커/equity/MDD 음영 + **신규 OOS train/test 세로 음영**(검증 구간이 눈으로 나쁘면 그 자체가 경고).
- **빈 Robustness 탭 금지의 대체**: 회색 빈 탭 대신 Overview 하단 **한계 배너** — "단일 구간 in-sample 결과 · 다구간 교차검증(walk-forward·DSR)은 로컬 정밀 모드."

**F. v1 스코프 재분류 (§0.5.6 표 보강)**

| 항목 | v0.3 | v0.4 정정 |
|---|---|---|
| OOS train/test 분할 시각+2열 | (P5 안) | **CORE-lite(floor, TS, 엔진변경 0~소)** — folk-stat 아님 |
| BtConfig "전략 콘솔" 재설계 | (누락) | **CORE(P3 동반)** — 운영자 "버튼 약함" 직격 |
| alpha/beta/IR 기초(vs B&H 단일창) | 없음 | **CORE-lite 후보(floor, TS 소)** — 서술적 |
| DSR/PBO/CPCV/walk-forward **수치** | P5 DEFER | **P5 DEFER 유지** + 표본/nTrials 게이트 + parity 선결(§0.6.1) |
| Python reconcile 정합 + parity fixture | (P5 묶음) | **P5 선결 명문화** |

## 0.6 레드팀 가드 (v0.4 신설 — CORE 동반 강행, DEFER 불가)

- **§0.6.1 통계 노출 천장**: 단일종목·6프리셋·2020+ 표본에 DSR/PBO/CPCV/haircut Sharpe **수치 노출 금지**(folk-stat). `cpcvSplits` n-가드는 실행가능성만 보장하지 통계 유효성 아님(`_metricsOverfitting.py`). DEFER P5 + parity gate + nTrials 충분 동시 충족 시에만.
- **§0.6.2 "전문가급" 문구 봉인**: UI·툴팁·마케팅 노출 금지. 내부 품질 기준어 한정(§0.12·§0 판정). 사용자 표면 = "과거 일별 데이터 기반 가정 노출형 시뮬레이션". 위반 = `horizonMeaning §8` "확신오정렬 > 정렬실패" 재현.
- **§0.6.3 탐색 = 과적합경고 강제**: 파라미터를 바꿔 돌리는 모든 표면은 과최적화 경고 없이 출시 금지(§10.2). v1은 grid 탐색 표면을 *안 만듦*으로 의무 회피. 슬라이더 재실행 = "단일 run 재계산"이지 "grid 탐색" 아님을 코드/문구로 분리. `best`/`optimal` 단어 금지.
- **§0.6.4 벤치마크 편향 상시 고지**: 배당 미반영(`dividend:'excluded'`)·무수정주가 기본(`adjusted ?? false`)은 B&H를 체계적으로 깎아 전략이 *상대적으로* 좋아 보이게 함. `splitSuspect`처럼 일회 경고가 아니라 Assumptions+strip **상시 고지**. `costDrag`는 "동일 신호·비용만 차이" 가정 라벨 동반(부호 음수 보장 아님).
- **§0.6.5 엔진 개선 게이트 (factor-zoo 차단)**: "부족하면 엔진 개선"이 들어올 때 `finance_slm G1/G2` 차용 — **G1 held-out**(미래 구간 + 미학습 회사 split) → **G2 zero-train 강baseline**(동일비용 B&H가 이미 강baseline; 신규 프리셋/지표는 이걸 못 이기면 추가 금지) 통과 전 새 프리셋·지표·통계 추가 금지. `horizonMeaning §8` factor-zoo·동어반복 gold 재발 차단.

---

## 1. 외부 벤치마크 흡수 결론

조사 기준은 TradingView Strategy Tester, MetaTrader 5 Strategy Tester, QuantConnect/LEAN, Backtrader, vectorbt, NautilusTrader, DSR/PBO 논문 계열이다. 복제 대상은 화면 자체가 아니라 **검증 계약과 작업 흐름**이다.

### 1.1 TradingView에서 흡수할 것

출처:

- https://www.tradingview.com/pine-script-docs/concepts/strategies/
- https://www.tradingview.com/support/solutions/43000764138-tradingview-strategy-report-how-to-start/
- https://www.tradingview.com/support/solutions/43000628599-strategy-properties/
- https://www.tradingview.com/support/solutions/43000666265-how-deep-backtesting-works/

흡수:

- 차트가 전략 탐색의 중심이다.
- Report는 Overview, Performance, Trades, Properties 성격으로 분리한다.
- 차트 마커와 거래 목록이 왕복되어야 한다.
- 전략 속성에 commission, slippage, initial capital, order size, pyramiding, margin 같은 실행 가정이 항상 붙는다.
- Deep Backtesting처럼 "현재 차트에 로드된 범위"와 "더 긴 검증 범위"의 차이를 제품 언어로 분리한다.

DartLab 적용:

- 현재 범위의 즉시 실행은 차트 내 `Run`.
- 장기 검증/워크포워드/파라미터 견고성은 `Robustness` 탭.
- "Strategy Properties"에 해당하는 내용은 숨은 모달이 아니라 리포트 푸터와 Assumptions 탭에 남긴다.

### 1.2 MetaTrader 5에서 흡수할 것

출처:

- https://www.metatrader5.com/en/terminal/help/algotrading/testing
- https://www.metatrader5.com/en/terminal/help/algotrading/strategy_optimization
- https://www.metatrader5.com/en/terminal/help/algotrading/testing_report
- https://www.metatrader5.com/en/terminal/help/algotrading/visualization

흡수:

- Visual mode: 체결을 차트 위에서 시간 순서로 확인할 수 있어야 한다.
- Optimization: 파라미터 탐색 결과를 표와 히트맵으로 볼 수 있어야 한다.
- Report: drawdown, recovery, profit factor, expected payoff, Sharpe, trade distribution, time distribution을 별도 영역으로 제공한다.
- Report에는 데이터 품질과 모델링 품질이 함께 따라야 한다.

DartLab 적용:

- 리플레이 모드와 백테스트는 같은 시간 절단을 공유한다. 리플레이 중 미래 데이터로 결과를 계산하지 않는다.
- 파라미터 탐색은 "최고값 찾기"가 아니라 "민감도와 과최적화 위험 확인"으로 설계한다.
- 거래별 MAE/MFE, 보유기간, 월별/연도별 수익 분포를 리포트에 둔다.

### 1.3 QuantConnect/LEAN에서 흡수할 것

출처:

- https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts
- https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/key-concepts
- https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/slippage/key-concepts
- https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/report

흡수:

- Reality modeling은 백테스트의 핵심이다.
- Fill, fee, slippage, brokerage, buying power, security initializer 같은 모델을 명시적으로 분리한다.
- Report는 수익률뿐 아니라 rolling metric, exposure, drawdown, benchmark 대비를 함께 보여준다.

DartLab 적용:

- `ExecutionSpec`, `CostSpec`, `BenchmarkSpec`, `DataSpec`를 `BacktestRunSpec`에 박는다.
- 모든 성과는 RunSpec과 provenance 없이는 노출하지 않는다.
- 비용 OFF 결과도 허용하되 항상 `costsOff` 경고와 cost drag 비교를 붙인다.

### 1.4 Backtrader, vectorbt, NautilusTrader에서 흡수할 것

출처:

- https://www.backtrader.com/docu/
- https://www.backtrader.com/docu/slippage/slippage/
- https://vectorbt.dev/
- https://nautilustrader.io/docs/latest/concepts/backtesting/

흡수:

- Backtrader: strategy/analyzer/broker 개념 분리, slippage 모델 명시.
- vectorbt: 대량 파라미터 실험을 배열 기반으로 빠르게 계산하고 히트맵화.
- NautilusTrader: 백테스트와 실전 사이의 execution semantics를 엄격히 다룬다.

DartLab 적용:

- 엔진은 `strategy -> signal/target -> order -> fill -> position/cash -> equity -> metrics` 파이프라인으로 쪼갠다.
- 단일 실행은 main thread sync, 파라미터 grid/워크포워드는 worker 또는 후속 quant engine으로 분리한다.
- "전략 작성"보다 먼저 "체결과 원장 계약"을 안정화한다.

### 1.5 DSR/PBO 계열에서 흡수할 것

출처:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- https://arxiv.org/abs/2603.20319

흡수:

- 파라미터 스윕과 전략 선택은 data snooping 위험을 만든다.
- Sharpe가 높다는 사실만으로 전략을 고르면 안 된다.
- Deflated Sharpe Ratio, Probability of Backtest Overfitting, CPCV, walk-forward 같은 검증 표면이 필요하다.

DartLab 적용:

- "Best parameter" 문구는 금지한다.
- 히트맵은 `selected`, `stable region`, `fragile spike`, `insufficient trades` 중심으로 표시한다.
- 스윕 결과를 노출하는 순간 Robustness 탭과 overfit warning이 필요하다.

## 2. 현재 DartLab 자산 기준선

### 2.1 landing TS 엔진

> **→ §0.5.1 경로 정합**: 실측 거처는 `ui/packages/surfaces/src/terminal/lib/backtest.ts`(`data/` 아님). 아래 자산 목록은 *이미 라이브*이며 §0.5.2 가 정확성 척추 실측 SSOT.

현재 `landing/src/lib/terminal/data/backtest.ts`는 순수 TypeScript 백테스트 엔진이다.

이미 갖춘 것:

- Svelte, klinecharts, DOM에 의존하지 않는다.
- 신호는 `t`일 종가 확정 후 `t+1`일 시가 체결로 계산한다.
- target을 1봉 shift하여 look-ahead를 방지한다.
- `volume=0` 봉은 체결을 이연한다.
- B&H도 같은 엔진을 통과시켜 체결/비용/지연 비교를 공정하게 한다.
- 비용 기본값: commission 1.5bp, sell tax 15bp, slippage 10bp.
- 프리셋: MA cross, RSI reversion, Bollinger reversion, MACD cross, Donchian breakout, momentum.
- 결과: strategy equity, B&H equity, trades, ret/CAGR/MDD/MDD days/Sharpe/Sortino/win rate/profit factor/avg trade/avg hold/exposure/cost drag.
- 경고: few trades, short range, split suspect, costs off.

한계:

- 브라우저 TS 엔진과 Python quant 엔진의 계산 계약이 완전히 동일하지 않다.
- 열린 포지션의 최종 mark-to-market/가상 청산 비용 convention을 명시해야 한다.
- 배당 재투자 total return이 아니다.
- 유니버스, 상장폐지, 과거 구성종목, survivorship bias는 차트 단일 종목 범위 밖이다.

### 2.2 차트 레이어

현재 `landing/src/lib/terminal/charts/btLayer.ts`는 klinecharts custom indicator로 `BT_TRADES`, `BT_EQUITY`를 등록한다.

유지할 것:

- 트레이드마다 overlay를 만들지 않는다.
- indicator 내부 Map lookup과 LOD를 유지한다.
- 전략/B&H 에쿼티와 MDD 음영을 차트 보조 페인에서 그린다.
- 차트 표시용 aligned series는 adapter에서 만든다. 엔진 결과 자체는 compact series를 유지한다.

### 2.3 UI 상태

현재 `ChartCtl`은 PriceChart, ChartMenus, ChartRibbon이 공유하는 상태 SSOT다.

유지할 것:

- 백테스트 활성 상태, 전략 key, params, 비용 설정은 `ChartCtl`에 둔다.
- 무거운 결과 본문은 별도 derived/result state로 둔다.
- fullscreen과 일반 차트는 같은 상태를 쓴다.
- `btKey`는 session 성격으로 유지한다. 사용자가 명시적으로 템플릿 저장하기 전까지 prefs에 영구 저장하지 않는다.

### 2.4 Python quant 엔진

현재 `src/dartlab/quant/strategy/backtest.py`와 `_backtestAdvanced.py`는 next-open/close, fee/slippage, gap/ADV impact, walk-forward, multi-asset, CPCV, DSR/PBO 표면을 갖는다.

주의:

- 현 Python `vectorBacktest`의 trade ledger와 equity/returns 계산은 비용/체결 반영 방식이 완전히 일치하지 않는다.
- 현 상태를 공식 성과 통계 엔진으로 부르면 안 된다.
- ledger 기반 재정의 또는 TS/Python golden parity 전까지는 terminal single-stock 즉시 실행은 TS 엔진이 책임지고, Python은 후속 견고성/연구용으로 다룬다.

## 3. 제품 원칙

1. 차트가 작업대다. 리본, 설정, 리포트는 모두 차트를 해석하기 위한 보조 표면이다.
2. 리포트는 수익률 자랑이 아니라 검산 도구다.
3. 모든 결과에는 RunSpec, 기간, 기준일, 데이터 원천, 수정주가 여부, 배당 미반영, 비용, 체결모델, 벤치마크가 붙는다.
4. 비용은 기본 ON이다. OFF는 가능하지만 경고와 cost drag 비교가 필수다.
5. B&H는 항상 같은 체결/비용 엔진을 통과한다.
6. 파라미터 탐색은 추천/최적화가 아니라 민감도와 과최적화 위험 확인이다.
7. 전문가 도구는 없는 데이터를 포장하지 않는다. intraday, 실시간, 호가, 실제 주문 체결, 배당 총수익률이 없으면 없다고 표시한다.
8. UI 밀도는 덧붙이는 패널 수가 아니라 항상 필요한 상태를 가까이 두는 것이다.
9. 기능 추가보다 실패 조건 노출이 우선이다.
10. 공개 터미널은 무중단 원칙을 따른다. 구현은 `/lab/terminal-dev` 격리 후 검증된 단위만 본선에 연결한다.

## 4. 전체화면 UX 정보구조

### 4.1 화면 골격

전체화면은 "차트 확대 모달"이 아니라 단일 종목 전략 작업대다.

권장 구조:

```text
fixed fullscreen workbench
  sticky top ribbon, 2 rows, 68-78px
  chart workspace, 60-70vh target height
    left drawing toolbar
    main candle canvas
    indicator/equity/drawdown panes
  sticky backtest summary strip when BT active
  scroll report dock
    tabs: Overview | Trades | Drawdown | Calendar | Sensitivity | Robustness | Assumptions
```

세부:

- 전체화면 컨테이너 자체가 스크롤 루트다.
- 리본은 sticky top이다.
- BT가 꺼진 상태에서는 차트가 화면 대부분을 차지하고, 하단에는 얇은 출처/기준일 띠만 둔다.
- BT가 켜진 상태에서는 차트 아래에 summary strip과 report dock이 붙는다.
- 차트가 카드 안에 갇힌 것처럼 보이면 실패다. 차트는 full-bleed 작업면이어야 한다.
- 하단 리포트는 카드 중첩을 만들지 않고 full-width band + 내부 grid/table로 구성한다.

### 4.2 상단 리본

Row 1 - 시장/차트 조작:

- 종목명, 코드, 시장, 기준일, 등락률.
- 기간, 봉주기. BT 실행 시 일봉이 아니면 일봉 전환 제안 또는 자동 전환 후 이유 표시.
- 캔들 타입, 축, 로그, 수정주가, 실적 마커, 밴드, 기준선, 매물대.
- VS 비교, ECON overlay.
- 리플레이, 스냅샷, 전체화면 닫기.

Row 2 - 활성 상태 중심:

- 켜진 지표 칩과 핵심 파라미터.
- 백테스트 strategy chip, params chip, costs chip, benchmark chip.
- Run slot chip: Current, Previous, Benchmark ghost. 최대 3개.
- Report toggle, export JSON/CSV.

원칙:

- 모든 후보를 펼쳐두지 않는다.
- 활성 상태는 칩, 후보 목록은 메뉴, 상세 설정은 팝오버다.
- 버튼에는 가능한 lucide icon을 쓴다.
- 텍스트 버튼은 명확한 명령에만 사용한다.

### 4.3 좌측 도구

전체화면 좌측에는 드로잉 툴바를 둔다.

포함:

- trendline, channel, horizontal, vertical, Fibonacci, anchored VWAP, risk/reward, measure, text/note.
- magnet, lock, continuous drawing, clear drawings.

백테스트와 관계:

- 차트 드로잉은 전략 계산에 영향을 주지 않는다.
- 전략 계산에 영향을 주는 것은 Strategy Builder에서 명시한 조건뿐이다.
- 드로잉 기반 알림/수동 조건은 후속 기능으로 분리한다.

### 4.4 차트 본체

BT 활성 시 차트 위에 표시:

- 진입/청산 마커. 용어는 UI에서 신중하게 쓴다. "진입/청산" 또는 "entry/exit"는 내부/도구 맥락에서는 허용하되 투자 권유처럼 보이면 안 된다.
- 선택된 거래의 entry, exit, holding span.
- 전략 에쿼티와 B&H 에쿼티 페인.
- Drawdown 페인 또는 MDD 음영.
- selected drawdown window의 peak/trough/recovery highlight.

금지:

- 모든 거래에 R:R 박스, SL/TP 라인, DCA 라인을 기본 표시하지 않는다.
- 수익 거래를 과도한 초록색/축포 UI로 강조하지 않는다.
- 가격축을 왜곡하는 overlay를 남발하지 않는다.

### 4.5 백테스트 Summary Strip

BT 활성 시 차트 바로 아래에 붙는 고정 요약이다.

첫 줄:

- Strategy name/version
- 기간
- bars/trades
- data as-of
- adjusted/raw
- dividend excluded
- execution: close(t) signal -> next open(t+1) fill
- costs ON/OFF
- B&H same costs

둘째 줄:

- Strategy return
- B&H return
- CAGR
- MDD
- MDD days
- Sharpe
- Sortino
- win rate
- profit factor
- avg trade
- exposure
- cost drag

원칙:

- 숫자가 좋아도 결론 문구를 붙이지 않는다.
- 경고는 숫자보다 가까이 둔다.
- `X`는 "리포트 숨김"이 아니라 "백테스트 해제"로 해석한다.
- BT 결과가 활성인 동안 핵심 가정 푸터는 숨길 수 없어야 한다.

## 5. 리포트 상세 설계

리포트는 차트 아래 스크롤 도크다. 첫 화면 차트를 먹지 않도록 summary strip만 상시 노출하고, 상세는 탭과 표로 밀도 있게 제공한다.

### 5.1 Overview

목적: 이 실행이 무엇인지, 어떤 가정으로 계산됐는지, 전략/B&H 차이가 무엇인지 빠르게 검산한다.

구성:

- RunSpec summary: symbol, date range, bars, strategy id/version, params, costs, benchmark.
- KPI grid: return, B&H return, CAGR, annualized vol, Sharpe, Sortino, Calmar, MDD, MDD duration, exposure, turnover, cost drag.
- Warning band: 계산 불가, 신뢰도 저하, 단순 고지를 구분한다.
- Equity mini chart: strategy/B&H/underwater.
- Data/provenance: source, as-of, adjusted, dividend, timezone/calendar.

### 5.2 Trades

목적: 성과가 실제로 어떤 거래 분포에서 나왔는지 확인한다.

표 컬럼:

- No.
- entry signal date
- entry fill date
- entry fill price
- exit signal date
- exit fill date
- exit fill price
- holding bars/days
- gross return
- net return
- costs
- MAE
- MFE
- R multiple 또는 normalized excursion
- exit reason

상호작용:

- row click -> 차트가 해당 거래 구간으로 이동하고 marker highlight.
- hover -> chart tooltip에 entry/exit/net PnL/MAE/MFE 표시.
- filter: winners, losers, open, long hold, high cost.
- export CSV.

원칙:

- 기본 상태에서 모든 거래를 크게 펼치지 않는다.
- 거래 상세는 선택 시 하단 drawer 또는 inline expansion으로 제한한다.

### 5.3 Drawdown

목적: 손실의 깊이와 기간을 수익률보다 더 강하게 검산한다.

구성:

- underwater curve.
- top drawdown table: peak, trough, recovery, depth, duration, recovered yes/no.
- current drawdown status.
- recovery ratio, Calmar/MAR.

상호작용:

- drawdown row click -> 차트 peak/trough/recovery highlight.
- unrecovered drawdown은 명확히 표시한다.

### 5.4 Calendar

목적: 성과의 시간 분포를 확인한다.

구성:

- 월별 return heatmap.
- 연도별 return, B&H return, MDD, trades, exposure.
- rolling 63d/252d Sharpe 또는 rolling return.

상호작용:

- month click -> 차트 해당 기간 zoom.
- year row click -> 리포트/차트 범위 sync.

### 5.5 Sensitivity

목적: 파라미터 결과가 우연한 단일 spike인지 안정된 ridge인지 확인한다.

구성:

- 1D 또는 2D parameter grid.
- cell metric 선택: net return, CAGR, MDD, Sharpe, Calmar, trade count, cost drag.
- insufficient trades cell dim.
- selected spec marker.
- stability score: 주변 cell과의 연속성, trade count, MDD penalty.

문구 원칙:

- `best` 금지.
- `selected`, `current`, `stable region`, `fragile spike`, `insufficient trades` 사용.

상호작용:

- cell click -> 해당 params를 preview run.
- apply는 별도 명령. click만으로 영구 상태 변경하지 않는다.
- grid 크기는 기본 제한을 둔다. 큰 grid는 worker 또는 chunked execution.

### 5.6 Robustness

목적: in-sample 성과를 검증 결과로 오해하지 않게 한다.

구성:

- walk-forward split summary.
- in-sample/out-of-sample metric 비교.
- purged/CPCV 결과가 가능한 경우 PBO.
- DSR 또는 multiple-testing adjusted Sharpe.
- parameter stability by period.
- regime slices: bull, bear, high-vol, low-vol, gap-heavy.

원칙:

- Robustness가 계산되지 않은 실행은 "검증 안 됨"으로 표시한다.
- 검증이 없는데 전략 우열을 결론 내리는 문구는 금지한다.
- Python quant 엔진 사용 시 ledger parity가 확보된 범위만 공식 수치로 노출한다.

### 5.7 Assumptions

목적: 모든 결과의 해석 조건을 한 곳에 고정한다.

필수 항목:

- 데이터 원천: `workbench.price` / gov EOD source.
- 기준일: `dataAsOf`.
- 시간대와 거래일 calendar.
- 가격: adjusted/raw 여부.
- 배당: 미반영 또는 total return 여부.
- 신호 시점: close(t).
- 주문 시점: close(t) 이후 market order로 가정.
- 체결 시점: next open(t+1).
- 체결 불가: volume=0 또는 suspend는 tradable bar까지 이연.
- 비용: commission, sell tax, slippage, future impact model 여부.
- benchmark: B&H, same costs.
- fractional share convention.
- open position final valuation convention.
- 투자 권유 아님 고지.

필수 고지 문구:

> 과거 일별 데이터 기반 시뮬레이션입니다. 미래 수익을 보장하지 않으며 투자 권유가 아닙니다. 신호는 t일 종가 확정 후 t+1일 시가에 체결된 것으로 가정합니다. 수수료·거래세·슬리피지 가정, 배당 미반영, 수정주가 적용 여부, 데이터 기준일을 함께 확인해야 합니다.

## 6. 경고 체계

경고는 3단계다.

### 6.1 계산 불가

예:

- 데이터 없음.
- 일봉이 아님.
- 체결 가능한 bar 부족.
- 전략 파라미터 invalid.
- benchmark 생성 불가.

동작:

- 결과 숫자를 만들지 않는다.
- 차트에는 실패 상태만 표시한다.
- 가능한 경우 일봉 전환처럼 안전한 자동복구를 제공하고 이유를 표시한다.

### 6.2 신뢰도 저하

예:

- 기간 252봉 미만.
- Sharpe/Sortino 계산에 필요한 60봉 미만.
- 거래 수 10건 미만.
- costs off.
- split suspect.
- adjusted off.
- dividend excluded.
- volume=0 체결 이연 다수.
- open trade 비중 과다.

동작:

- 결과는 표시하되 경고를 숫자 가까이 둔다.
- 해당 metric은 필요하면 `—`로 비운다.
- 닫을 수 없는 compact warning chip으로 둔다.

### 6.3 단순 고지

예:

- EOD/T+1.
- 공공데이터 출처.
- 배당 미반영.
- 하이킨아시 변형값.
- ECON 자기정규화.

동작:

- Assumptions 탭과 summary strip의 provenance 줄에 표시한다.

## 7. 성과 지표 정의

모든 지표는 ledger 기반 equity에서 계산한다. trade PnL과 equity PnL이 맞지 않으면 결과는 invalid다.

필수:

- `retPct`: 기간 총 순수익률.
- `benchmarkRetPct`: 같은 비용/체결 가정의 B&H 수익률.
- `cagrPct`: 252 거래일 연율화. 252봉 미만은 `null`.
- `volPct`: 일별 수익률의 연율화 변동성.
- `sharpe`: risk-free 명시. 60봉 미만은 `null`.
- `sortino`: downside deviation 기준. 60봉 미만은 `null`.
- `mddPct`: peak-to-trough 최대 낙폭.
- `mddDays`: peak에서 recovery까지 또는 unrecovered duration.
- `calmar`: CAGR / |MDD|.
- `winRatePct`: closed trade 기준.
- `profitFactor`: gross profit / gross loss.
- `expectancyPct`: 평균 trade 순수익률.
- `avgWinPct`, `avgLossPct`.
- `bestTradePct`, `worstTradePct`.
- `avgHoldBars`.
- `exposurePct`: 포지션 보유 bar 비율.
- `turnoverPct`: 기간 총 매매회전.
- `costDragPct`: costs off result - costs on result.
- `maePct`, `mfePct`: 거래 중 불리/유리 excursion.

후속:

- alpha/beta/information ratio vs market/sector.
- VaR/CVaR.
- skew/kurtosis.
- rolling 63d/252d metrics.

Null 규칙:

- 252봉 미만 CAGR null.
- 60봉 미만 Sharpe/Sortino null.
- closed trades 0이면 trade metrics null.
- gross loss 0이면 profitFactor는 capped display 또는 `∞`가 아니라 `—`와 설명.
- NaN/Infinity는 UI에 절대 노출하지 않는다.

## 8. 엔진 계약

### 8.1 RunSpec

`BacktestRunSpec`은 결과 재현의 SSOT다.

```ts
export interface BacktestRunSpec {
  schemaVersion: 1;
  runId: string;
  symbol: {
    code: string;
    name?: string;
    market?: 'KR' | 'US';
  };
  data: {
    timeframe: 'D';
    source: 'workbench.price';
    dataAsOf: string;
    timezone: 'Asia/Seoul';
    adjusted: boolean;
    dividend: 'excluded' | 'totalReturn';
    range: {
      kind: 'bars' | 'dateRange';
      bars?: number;
      from?: string;
      to?: string;
    };
    replayCutDate?: string;
  };
  strategy: {
    id: string;
    version: string;
    params: Record<string, number | boolean | string>;
    signalTiming: 'closeT';
    targetKind: 'longFlat' | 'targetWeight';
  };
  execution: {
    orderType: 'market';
    fill: 'nextOpen';
    suspendPolicy: 'deferUntilTradable';
    partialFillPolicy: 'none' | 'volumeParticipation';
    allowFractional: boolean;
    initialEquity: number;
    finalOpenPosition: 'markToMarket' | 'liquidateNextOpenIfAvailable';
  };
  costs: {
    enabled: boolean;
    commissionBp: number;
    sellTaxBp: number;
    slippageBp: number;
    impactModel?: 'none' | 'advParticipation';
  };
  benchmark: {
    kind: 'buyAndHold';
    sameCosts: true;
  };
}
```

### 8.2 Result

`BacktestResult`는 차트와 리포트가 같이 쓰는 단일 결과다.

```ts
export interface BacktestResult {
  schemaVersion: 1;
  runId: string;
  specHash: string;
  status: 'ok' | 'invalidSpec' | 'insufficientData';
  input: {
    bars: number;
    startIdx: number;
    startDate: string;
    endDate: string;
  };
  series: {
    dates: string[];
    strategyEquity: number[];
    benchmarkEquity: number[];
    drawdownPct: number[];
    position: number[];
    cash?: number[];
  };
  orders?: BacktestOrder[];
  fills: BacktestFill[];
  trades: BacktestTrade[];
  metrics: BacktestMetrics;
  benchmarkMetrics: Pick<BacktestMetrics, 'retPct' | 'cagrPct' | 'mddPct' | 'sharpe'>;
  drawdownWindows: BacktestDrawdownWindow[];
  warnings: BacktestWarning[];
  provenance: {
    engineVersion: string;
    strategyVersion: string;
    dataSource: string;
    dataAsOf: string;
    generatedAt: string;
  };
}
```

### 8.3 Ledger model

> **→ §0.5.4 정합(SSOT)**: 아래 6원장은 multi-asset 어휘 — long/flat 단일종목엔 과모델. v1 = **2구조(equity+trades) + reconciliation 가드 + deferred/exitReason 필드**. 독립 Order/Cash/Position 원장 REJECT. 아래 6원장 서술은 *개념 참조*로만.

전문가급 기준은 equity curve만 만드는 것이 아니다. 다음 원장을 분리한다.

- `OrderLedger`: 전략이 어느 시점에 어떤 target/order를 냈는지.
- `FillLedger`: 실제 체결일, 체결가, 비용, 체결 불가/이연 이유.
- `PositionLedger`: bar별 position, average price, exposure.
- `CashLedger`: 현금, 비용, 세금, 슬리피지 반영.
- `TradeLedger`: entry/exit로 묶인 거래 단위 PnL.
- `EquityLedger`: cash + position mark-to-market.

규칙:

- 모든 성과 지표는 `EquityLedger`에서 계산한다.
- 거래표 PnL 합과 equity PnL이 reconcile되어야 한다.
- B&H도 같은 ledger path를 통과한다.
- 체결 모델이 바뀌면 `specHash`가 바뀐다.

### 8.4 기본 체결 모델

기본:

- `signal close(t) -> market order -> fill open(t+1)`.
- `volume=0` 또는 거래정지 bar는 다음 tradable open까지 이연.
- fractional share 허용. 실제 주식 수 단위 반영은 후속 옵션.
- 일봉 전용. 주봉/월봉에서 BT를 실행하면 일봉으로 전환하고 이유를 표시한다.

후속:

- volume participation.
- gap/slippage impact.
- partial fill.
- limit-up/down no-fill.
- intraday stop/limit은 intraday 데이터가 없으면 공식 기능으로 넣지 않는다.

## 9. 전략 탐색 설계

### 9.1 고정 프리셋

현재 6개 프리셋은 유지한다.

- MA cross.
- RSI reversion.
- Bollinger reversion.
- MACD cross.
- Donchian breakout.
- Momentum.

원칙:

- 프리셋은 교육용/탐색용이다.
- 프리셋 이름을 "추천 전략"처럼 보이게 하지 않는다.
- 각 프리셋은 version과 param schema를 갖는다.
- param default는 registry에서 관리한다.

### 9.2 Strategy Builder

계약과 리포트가 안정된 뒤 Strategy Builder를 붙인다.

Builder 모델:

- Entry conditions.
- Exit conditions.
- Risk/position conditions.
- AND/OR groups.
- indicator condition: MA, RSI, MACD, BB, Donchian, price breakout.
- price condition: close crosses, high/low range, gap.
- event condition: earnings marker, disclosure marker, fundamentals later.
- target: long/flat, target weight.

저장:

- strategy JSON import/export.
- local template 저장은 명시적 저장 명령에서만.
- strategy id/version/specHash로 재현성 확보.

금지:

- Pine Script 호환을 첫 목표로 잡지 않는다.
- 자연어 "AI 전략 생성"은 후순위다.
- "이 종목에 맞는 전략 추천"은 금지한다.

## 10. 파라미터 탐색과 견고성

### 10.1 Sensitivity grid

기본:

- 1D slider sweep.
- 2D heatmap.
- metric selector.
- selected cell marker.
- insufficient trade count dim.
- cost-off forbidden by default for grid. 비용 OFF grid는 명시적 실험 모드.

성능:

- 기본 grid는 25 x 25 이하.
- 큰 grid는 worker/chunked execution.
- signal cache와 result cache 사용.

문구:

- `Best` 금지.
- `Selected`, `Current`, `Stable region`, `Fragile spike`, `Insufficient trades` 사용.

### 10.2 Robustness

제공:

- walk-forward.
- purged/CPCV 가능한 범위.
- IS/OOS split.
- DSR.
- PBO.
- multiple-testing 경고.

출시 원칙:

- 파라미터 스윕 결과가 제품에 보이면 Robustness 탭도 같이 필요하다.
- Robustness 미계산 상태는 "검증 안 됨"으로 표시한다.
- OOS 결과 없이 "우수" 표현 금지.

## 11. 아키텍처 계획

### 11.1 모듈 구조

> **→ §0.5.3 정합(SSOT)**: 거처는 `ui/packages/surfaces/src/terminal/lib/backtest/`(landing 아님). 11파일 → **~4파일**(index barrel + types + presets + engine). ledger/robustness/cache/runner/worker/chartAdapter/metrics/validation 독립 파일 CUT — chartAdapter 는 이미 `btLayer.publishBt`. 아래 11파일 목록은 *최대 가정* 참조.

권장:

```text
landing/src/lib/terminal/backtest/
  types.ts
  strategies.ts
  engine.ts
  ledger.ts
  metrics.ts
  validation.ts
  robustness.ts
  cache.ts
  runner.ts
  worker.ts
  chartAdapter.ts

landing/src/lib/terminal/charts/
  btLayer.ts
  BtConfig.svelte
  BacktestStrip.svelte
  BacktestReport.svelte
  BacktestOverview.svelte
  BacktestTradesTable.svelte
  BacktestDrawdownPanel.svelte
  BacktestCalendar.svelte
  BacktestSensitivity.svelte
  BacktestAssumptions.svelte
```

마이그레이션:

- 기존 `landing/src/lib/terminal/data/backtest.ts`는 1차 동안 compatibility re-export 또는 thin wrapper로 둔다.
- 계산 본체는 `terminal/backtest/*`로 이동한다.
- `data/`는 데이터 원천, `backtest/`는 계산 도메인, `charts/`는 렌더 어댑터로 분리한다.
- `PriceChart.svelte`는 runner 호출, result 수신, chart adapter apply만 담당한다.

### 11.2 상태 관리

유지:

- `ChartCtl`은 UI 설정 SSOT다.
- `btKey`, `btParams`, `btCosts`, `btCostsBp`는 현재 패턴을 유지하되 새 RunSpec builder에서 읽는다.

추가:

- `BacktestRunState`: idle, running, ok, invalid, stale.
- `runId`: 비동기/worker stale result 폐기.
- `specHash`: cache key와 export 재현성.
- `activeResult`: 차트와 리포트가 공유.
- `compareSlots`: max 3, local memory only.

### 11.3 차트 어댑터

원칙:

- 엔진 결과는 compact window series.
- klinecharts indicator에 필요한 aligned array는 `chartAdapter.ts`에서 생성.
- `btLayer.ts`는 렌더링만 담당한다.
- publish/apply/clear API는 기존 호환성을 최대한 유지한다.

### 11.4 캐시와 worker

Main thread sync:

- 단일 종목, 일봉 4천-1만 봉, 단일 전략 실행.

Worker:

- parameter grid.
- walk-forward.
- multi-strategy compare.
- multi-symbol future scan.
- Monte Carlo future extension.

Cache:

- price source cache: 기존 workbench/priceSeries 유지.
- signal cache: `dataRev + strategyId + params + adjusted + replayCut`.
- result cache: `specHash + dataKey + engineVersion`.
- localStorage 결과 캐시는 금지. 명시 export만 허용.

## 12. 성능 목표

목표:

- 단일 전략 4천 봉 실행: 20ms 이하.
- 1만 봉 단일 실행: 50ms 이하.
- report tab switch: chart 재초기화 없음.
- marker rendering: visible bar 기준 O(n).
- grid 25 x 25: chunked/worker로 UI freeze 없음.
- fullscreen open/close: 기존 차트 상태 보존.

금지:

- trade마다 DOM overlay 생성.
- 차트 옵션을 매번 full reset.
- 스크롤 중 리포트 테이블 전체 재계산.
- deep watch로 모든 param 변경마다 grid 전체 재실행.

## 13. 테스트와 검증 게이트

### 13.1 엔진 단위 테스트

필수 fixture:

- close(t) 신호가 open(t+1)에 체결된다.
- 마지막 봉 값을 바꿔도 과거 신호/체결이 바뀌지 않는다.
- volume=0 bar에서 체결이 이연된다.
- B&H가 같은 체결/비용 엔진을 통과한다.
- 비용 ON 결과는 비용 OFF 대비 cost drag를 갖는다.
- split suspect 경고가 고정된다.
- 252봉 미만 CAGR null.
- 60봉 미만 Sharpe/Sortino null.
- 거래 10건 미만 fewTrades warning.
- replayCut 이후 데이터가 결과에 들어가지 않는다.
- NaN/Infinity는 결과 schema에서 차단된다.
- open position final convention이 명시대로 동작한다.

### 13.2 TS/Python parity

필수 전제:

- Python quant를 공식 리포트 수치에 연결하기 전 synthetic golden fixture를 만든다.
- 단일 long/flat, next-open, 비용/세금/슬리피지, volume=0, open trade convention이 TS와 Python에서 일치해야 한다.
- parity가 없으면 Python 결과는 `research/robustness reference`로만 표기한다.

### 13.3 UI/브라우저 검증

구현 시 최소:

- `cd landing && npm run check`.
- `cd landing && npm run build`.
- Browser/Playwright로 `/terminal?sym=005930` 또는 dev route 확인.

브라우저 체크:

- BT 메뉴 열기 -> preset 선택 -> summary strip 표시.
- fullscreen에서 BT 실행 -> 차트 marker/equity/report가 같이 보임.
- trade row click -> chart highlight.
- drawdown row click -> chart highlight.
- month heatmap click -> chart range sync.
- 주/월봉에서 BT 실행 -> 일봉 전환 또는 계산 불가 이유 표시.
- 비용 토글/기간 변경/수정주가 토글 -> result 갱신.
- replay 중 -> cut date 이후 결과 없음.
- 1440x900, 390x844에서 텍스트 겹침 없음.
- canvas pixel check: candle, equity pane, marker nonblank.
- console error 0, Svelte warning 0.

주의:

- 저장소 규칙상 전체 pytest 금지.
- Python을 만지는 경우 해당 operation skill과 preflight 규칙을 따른다.
- 공개 terminal은 바로 건드리지 말고 dev isolation 후 final UI review를 거친다.

## 14. 법적/표현 가드

이 제품은 투자 자문/추천이 아니다. UI와 문서에서 다음 문구를 피한다.

금지:

- 추천.
- 매수/매도 추천.
- 타점.
- 검증된 전략.
- 수익 전략.
- 시장 초과 성과 보장.
- 전문가가 쓰는 전략.
- 실시간.
- 라이브.
- 안정적 수익.
- Sharpe가 높으니 우수.
- 승률이 높으니 좋음.

허용:

- 과거 일별 데이터 기반 시뮬레이션.
- 가정 노출형 차트 백테스트.
- 동일 비용 B&H 비교.
- 미래 수익 보장 없음.
- 투자 권유 또는 투자자문 아님.
- 이 기간과 이 가정에서는 이렇게 계산됨.

외부 규제 참고:

- SEC Marketing Rule FAQ: https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/marketing-compliance-frequently-asked-questions
- 17 CFR 275.206(4)-1: https://www.law.cornell.edu/cfr/text/17/275.206%284%29-1
- FINRA communications public rules reference: https://www.finra.org/sites/default/files/2020-09/communications-public-rules-reference-guide.pdf

법률 판단은 별도 자문 대상이다. 제품 설계는 보수적으로 둔다.

## 15. Out of Scope

명시 제외:

- 실시간/분봉/호가 기반 백테스트.
- 실제 주문/브로커 연결.
- 실제 체결 품질 주장.
- short/margin/pyramiding.
- options/futures.
- intraday stop/limit.
- 자동 최적화 추천.
- AI 매수/매도 해설.
- 종목별 "적합 전략" 추천.
- 현재 구성종목으로 과거 유니버스 백테스트.
- scan universe 결과를 chart BT strip에 섞기.
- 배당 total return claim. 데이터가 확보되기 전까지 배당 미반영으로 표시.

후속 가능하지만 별도 PRD 필요:

- portfolio/universe backtest.
- survivorship-free historical universe.
- total return price track.
- advanced impact model.
- server-side quant robustness engine.
- strategy marketplace/templates.

## 16. 구현 순서

> **→ §0.5.6 v1 스코프 확정(SSOT)**: **CORE = Phase 1-3**(타입화 재현 결과 + ~4파일 + reconcile 가드 + 리포트 도크 4탭 Overview/Trades/Drawdown/Assumptions + row→chart sync + 날짜/replay 입력). **Phase 4 Sensitivity·Phase 5 Robustness/Python parity·Phase 6 Strategy Builder = 각자 별도 PRD DEFER**(Calendar 만 P3 후 선택 CORE-lite). ★빈 Robustness 탭 금지. 아래 6-phase 상세는 *그 분리된 PRD들의 설계 자산*으로 보존.

MVP로 축소하지 않는다. 다만 위험을 낮추기 위해 계약부터 단계적으로 고정한다.

### Phase 0 - PRD와 메모리 확정

완료 기준:

- 이 문서가 memory에 존재한다.
- `MEMORY.md`에서 참조된다.
- 사용자와 "차트 중심 + 하단 리포트 + EOD 가정 노출" 방향이 합의된다.

### Phase 1 - 결과 계약과 현 기능 고정

목표:

- 기존 숫자를 바꾸지 않고 fixture를 먼저 고정한다.
- `BacktestRunSpec`, `BacktestResult`, `BacktestWarning` 타입을 만든다.
- 기존 `BtResult`를 새 Result로 매핑하는 adapter를 둔다.

완료 기준:

- 기존 6개 프리셋이 계속 동작한다.
- B&H 동일 엔진 계약이 테스트된다.
- warning/null 규칙이 테스트된다.

### Phase 2 - 모듈 분리와 원장화

목표:

- `terminal/backtest/*` 구조로 계산 도메인을 분리한다.
- order/fill/position/cash/trade/equity ledger를 도입한다.
- metrics는 ledger에서만 계산한다.

완료 기준:

- trade PnL과 equity PnL reconcile.
- open position convention 명시.
- PriceChart 백테스트 effect가 runner 호출로 얇아진다.

### Phase 3 - 전체화면 리포트 도크

목표:

- fullscreen chart 아래 summary strip과 report tabs를 붙인다.
- 기존 BacktestStrip을 대체하거나 내부 컴포넌트로 흡수한다.

완료 기준:

- Overview/Trades/Drawdown/Assumptions 탭.
- trade row -> chart sync.
- drawdown row -> chart sync.
- 모바일/데스크톱 겹침 없음.

### Phase 4 - Calendar와 Sensitivity

목표:

- 월별/연도별 성과 분포.
- parameter 1D/2D grid.
- stable/fragile/insufficient 표시.

완료 기준:

- `Best` 문구 없음.
- insufficient trades dim.
- grid worker/chunking으로 UI freeze 없음.

### Phase 5 - Robustness

목표:

- walk-forward, IS/OOS, DSR/PBO 표면.
- Python quant와 parity 가능한 범위 연결.

완료 기준:

- 검증 미계산 상태를 명확히 표시.
- 과최적화 경고.
- TS/Python golden parity 또는 Python 결과 제한 표기.

### Phase 6 - Strategy Builder

목표:

- 프리셋 실행기를 넘어 조건 조합형 전략 작업대로 확장한다.

완료 기준:

- strategy JSON import/export.
- entry/exit condition groups.
- RunSpec 재현성.
- 추천/자동 최적화 문구 없음.

## 17. 실행 보강 - 단계별 Acceptance Criteria

이 절은 PRD를 실제 개발 티켓으로 내릴 때의 판정 기준이다. 각 Phase는 "동작한다"가 아니라 "어떤 파일, 어떤 상태, 어떤 테스트로 끝났다고 말할 수 있는지"까지 가져야 한다.

### 17.1 Phase 1 acceptance criteria

범위:

- 기존 결과 숫자를 바꾸지 않는다.
- 타입 계약과 adapter만 먼저 만든다.
- 현재 `runBacktest` 호출부를 깨지 않는다.

필수 산출:

- `landing/src/lib/terminal/backtest/types.ts`
- `landing/src/lib/terminal/backtest/runSpec.ts`
- `landing/src/lib/terminal/backtest/resultAdapter.ts`
- 기존 `landing/src/lib/terminal/data/backtest.ts` 호환 export 유지

판정:

- 기존 6개 프리셋 key가 그대로 동작한다.
- 기존 `BtConfig`, `BacktestStrip`, `btLayer`가 type adapter를 통해 동작한다.
- `BacktestRunSpec`이 없으면 `BacktestResult`를 만들 수 없다.
- 모든 result에 `runId`, `specHash`, `provenance`, `warnings`가 존재한다.
- result metric에 `NaN`, `Infinity`, 빈 문자열 날짜가 없다.
- 비용 OFF 결과는 항상 `costsOff` warning을 가진다.
- 252봉 미만 CAGR, 60봉 미만 Sharpe/Sortino는 null이다.

### 17.2 Phase 2 acceptance criteria

범위:

- 계산 도메인을 `terminal/backtest/*`로 분리한다.
- ledger 기반 계산으로 이동한다.
- 숫자 변화가 생길 수 있으므로 golden fixture와 migration note가 필수다.

필수 산출:

- `engine.ts`: signal/target/order/fill/position/equity pipeline
- `ledger.ts`: order, fill, cash, position, trade, equity ledger
- `metrics.ts`: metric 공식 구현
- `validation.ts`: spec/result guard
- `strategies.ts`: preset registry

판정:

- trade ledger의 closed trade PnL과 equity ledger 변화가 reconcile된다.
- B&H도 같은 engine path를 통과한다.
- open position final valuation convention이 spec과 result에 남는다.
- volume=0 bar 체결 이연이 ledger에 reason으로 기록된다.
- `PriceChart.svelte`는 백테스트 계산 세부를 알지 않는다.
- 기존 `btLayer.ts`는 렌더 adapter 외 계산 로직을 갖지 않는다.

### 17.3 Phase 3 acceptance criteria

범위:

- 전체화면 차트 아래에 report dock을 붙인다.
- 기존 strip은 summary 역할로 축소하거나 내부 컴포넌트로 흡수한다.

필수 산출:

- `BacktestReport.svelte`
- `BacktestOverview.svelte`
- `BacktestTradesTable.svelte`
- `BacktestDrawdownPanel.svelte`
- `BacktestAssumptions.svelte`
- chart/report selection sync state

판정:

- fullscreen에서 BT 실행 시 chart marker, equity pane, summary strip, report dock이 같은 result를 본다.
- trade row click이 chart range와 marker highlight를 바꾼다.
- drawdown row click이 peak/trough/recovery highlight를 만든다.
- Assumptions 탭 없이도 summary strip에 핵심 가정이 보인다.
- mobile 390x844에서 리본/차트/리포트 텍스트가 겹치지 않는다.
- report를 스크롤해도 chart가 재초기화되지 않는다.

### 17.4 Phase 4 acceptance criteria

범위:

- Calendar와 Sensitivity를 붙인다.
- 파라미터 탐색은 추천이 아니라 민감도 진단이다.

필수 산출:

- `BacktestCalendar.svelte`
- `BacktestSensitivity.svelte`
- `sensitivityRunner.ts`
- bounded grid config

판정:

- 월별 heatmap cell click이 차트 범위를 해당 월로 이동한다.
- 연도별 표는 strategy, B&H, trades, exposure, MDD를 함께 보여준다.
- Sensitivity grid에 `Best` 문구가 없다.
- selected cell과 주변 안정성이 구분된다.
- trade count 부족 cell은 dim 처리된다.
- grid 실행 중 UI가 멈추지 않는다.
- 비용 OFF grid는 기본 비활성이다.

### 17.5 Phase 5 acceptance criteria

범위:

- Robustness 탭을 추가한다.
- Python quant 연결은 parity가 확보된 범위만 공식 표면으로 둔다.

필수 산출:

- `robustness.ts`
- walk-forward result schema
- IS/OOS summary schema
- overfit warning mapper

판정:

- Robustness 미계산 상태가 "검증 안 됨"으로 보인다.
- IS와 OOS를 같은 말로 표시하지 않는다.
- PBO/DSR가 계산되지 않으면 null과 reason이 보인다.
- Python 결과를 쓰는 경우 TS/Python golden fixture가 통과한 계약만 사용한다.
- 파라미터 스윕이 있는 result에는 overfit warning 영역이 존재한다.

### 17.6 Phase 6 acceptance criteria

범위:

- 프리셋 실행기에서 Strategy Builder로 확장한다.

필수 산출:

- strategy condition schema
- entry/exit group editor
- strategy JSON import/export
- strategy version/hash

판정:

- builder로 만든 전략도 `BacktestRunSpec`만으로 재현된다.
- import한 JSON이 invalid면 실행하지 않고 reason을 보여준다.
- natural language strategy generation은 없다.
- "종목별 적합 전략" 추천 문구가 없다.

## 18. Fullscreen UI 상태 매트릭스

상태 매트릭스는 화면이 기능 추가로 흩어지는 것을 막는 기준이다.

| State | Chart | Ribbon | Summary strip | Report dock | Primary action | Guard |
| --- | --- | --- | --- | --- | --- | --- |
| Idle | candle/indicators only | BT strategy chip inactive | hidden | hidden | select strategy | source/as-of thin line remains |
| Configuring | preview none | params/costs popover open | hidden | hidden | apply run | invalid params block run |
| Running | previous result dim or cleared | run chip spinner | compact running row | optional skeleton | cancel or wait | stale runId must be discarded |
| Ok | markers/equity/drawdown visible | active strategy/cost chips | visible | active tabs | inspect trades/report | assumptions always near metrics |
| Warning | same as Ok | warning chip visible | warning band visible | warning details | inspect warning | costsOff/fewTrades cannot be hidden |
| Invalid | no new markers | invalid chip | reason row | Assumptions/errors only | fix spec | no partial metric display |
| Stale | old result visually marked stale | pending chip | stale badge | disabled apply | rerun | old result cannot be exported as current |
| Replay | chart cut at replay date | replay chip + cut date | only cut-range result | report says replay-limited | move replay date | no future bars in result |
| Compare | current plus ghost series | slot chips max 3 | compact compare row | compare table | toggle slot | too many slots blocked |
| ReportScroll | chart remains stable | sticky top | sticky or compact | scroll active | tab/row click | no chart reinit on scroll |

반응형 기준:

- Desktop 1440x900: ribbon 2 rows, chart 60-70vh, report dock below.
- Laptop 1280x720: chart min-height를 지키고 report 첫 탭 일부만 보인다.
- Mobile 390x844: ribbon은 horizontal scroll 또는 compact groups, chart는 먼저, report는 아래 single-column.
- 모든 viewport에서 summary strip의 긴 문구는 줄바꿈되며 버튼 텍스트를 밀어내지 않는다.

## 19. 타입 계약 보강

아래 타입은 실제 구현 시 `types.ts`의 starting point다. 이름은 조정 가능하지만 필드 의미는 유지한다.

```ts
export type BacktestWarningSeverity = 'info' | 'degraded' | 'blocking';

export interface BacktestWarning {
  code:
    | 'notDaily'
    | 'insufficientBars'
    | 'fewTrades'
    | 'costsOff'
    | 'splitSuspect'
    | 'dividendExcluded'
    | 'adjustedOff'
    | 'suspendedBars'
    | 'openPosition'
    | 'robustnessNotRun'
    | 'overfitRisk'
    | 'pythonParityMissing';
  severity: BacktestWarningSeverity;
  message: string;
  blocking: boolean;
  evidence?: Record<string, number | string | boolean | null>;
}

export interface BacktestOrder {
  id: string;
  signalDate: string;
  createdAtDate: string;
  targetWeight: number;
  orderType: 'market';
  reason: string;
}

export interface BacktestFill {
  orderId: string;
  fillDate: string;
  fillPrice: number;
  quantity: number;
  targetWeightAfter: number;
  commission: number;
  sellTax: number;
  slippage: number;
  deferredBars: number;
  deferredReason?: 'zeroVolume' | 'suspended' | 'notTradable';
}

export interface BacktestTrade {
  id: string;
  entrySignalDate: string;
  entryFillDate: string;
  entryPrice: number;
  exitSignalDate: string | null;
  exitFillDate: string | null;
  exitPrice: number | null;
  status: 'closed' | 'open';
  holdBars: number;
  grossRetPct: number | null;
  netRetPct: number | null;
  costPct: number;
  maePct: number | null;
  mfePct: number | null;
  exitReason: 'signal' | 'finalMark' | 'finalLiquidation' | null;
}

export interface BacktestMetrics {
  retPct: number;
  cagrPct: number | null;
  volPct: number | null;
  sharpe: number | null;
  sortino: number | null;
  mddPct: number;
  mddDays: number | null;
  calmar: number | null;
  winRatePct: number | null;
  profitFactor: number | null;
  expectancyPct: number | null;
  avgWinPct: number | null;
  avgLossPct: number | null;
  bestTradePct: number | null;
  worstTradePct: number | null;
  avgHoldBars: number | null;
  exposurePct: number;
  turnoverPct: number;
  costDragPct: number | null;
}
```

필수 구현 규칙:

- warning code는 UI 문자열의 대체물이 아니다. code는 테스트와 조건 분기에 쓰고, message는 표시용이다.
- `blocking=true`인 warning이 있으면 metric grid를 만들지 않는다.
- `BacktestTrade.status='open'`이면 closed-trade metric에는 포함하지 않는다.
- `fillDate`는 항상 `signalDate`보다 같거나 뒤여야 한다. 기본 모델에서는 최소 다음 거래일이다.
- `costPct`는 gross/net 차이와 reconcile되어야 한다.

## 20. 지표 공식 정본

모든 지표는 split/adjusted 여부가 명시된 equity series에서 계산한다.

기호:

- `E_t`: t일 close 기준 equity.
- `r_t = E_t / E_{t-1} - 1`.
- `n`: 사용된 일별 return 수.
- `rf_d`: 일별 risk-free rate. 없으면 0으로 두고 RunSpec에 남긴다.
- `excess_t = r_t - rf_d`.

공식:

- Total return: `E_last / E_0 - 1`.
- CAGR: `(E_last / E_0) ** (252 / n) - 1`, 단 `n >= 252`.
- Annualized volatility: `std(r_t) * sqrt(252)`, 단 `n >= 2`.
- Sharpe: `mean(excess_t) / std(excess_t) * sqrt(252)`, 단 `n >= 60`이고 표준편차가 0이 아님.
- Sortino: `mean(excess_t) / downsideStd(excess_t) * sqrt(252)`, 단 `n >= 60`이고 downsideStd가 0이 아님.
- Drawdown: `E_t / max(E_0..E_t) - 1`.
- MDD: drawdown의 최솟값.
- MDD days: peak date에서 recovery date까지. 미회복이면 end date까지.
- Calmar: `CAGR / abs(MDD)`, CAGR과 MDD가 유효할 때만.
- Profit factor: closed trades의 gross profit 합 / gross loss 절댓값. gross loss가 0이면 null과 reason.
- Win rate: closed trades 중 `netRetPct > 0` 비율.
- Expectancy: closed trades의 평균 `netRetPct`.
- Exposure: position이 0이 아닌 bar 수 / 전체 bar 수.
- Turnover: 기간 중 `abs(positionWeight_t - positionWeight_{t-1})` 합.
- Cost drag: 같은 RunSpec에서 costs only on/off를 바꾼 두 결과의 `retPct` 차이. 단 이 비교 run이 없으면 null.
- MAE/MFE: entry fill 이후 exit/final valuation까지의 최저/최고 excursion.

Reconciliation:

- `finalEquity = cash + positionMarketValue`.
- realized trade PnL, open unrealized PnL, costs, taxes가 equity change와 허용 오차 내 일치해야 한다.
- 허용 오차는 floating point 누적을 감안해 `1e-8` 또는 equity scale 기반 상대오차로 둔다.
- reconcile 실패 시 result status는 `invalidSpec` 또는 internal invalid로 처리하고 UI에는 metric을 노출하지 않는다.

## 21. 테스트 매트릭스

| Area | Fixture | Assertion | Gate |
| --- | --- | --- | --- |
| signal timing | 상승 후 신호 발생 synthetic | close(t) 신호가 open(t+1)에 체결 | unit |
| look-ahead | 마지막 봉 급등/급락 변경 | 과거 신호와 체결 불변 | unit |
| suspend | volume=0 중간 봉 | fill 이연, deferredReason 기록 | unit |
| same engine B&H | 단순 상승 series | strategy와 B&H 모두 ledger path 통과 | unit |
| costs | 비용 0 vs 기본 비용 | 기본 비용 ret가 낮거나 같고 costDrag 기록 | unit |
| null rules | 50봉, 200봉 fixture | Sharpe/CAGR null 규칙 | unit |
| open trade | 마지막까지 보유 | open trade status, final convention 기록 | unit |
| split warning | 급격한 가격 단절 | splitSuspect warning | unit |
| replay | replayCut 중간일 | cut 이후 fill/trade/equity 없음 | integration |
| chart adapter | compact result -> aligned arrays | visible marker/equity mapping 정확 | unit |
| fullscreen | BT run in fullscreen | chart, strip, report same runId | browser |
| trade sync | trade row click | marker highlight and range move | browser |
| warning UX | costsOff/fewTrades | warning visible and not hidden | browser |
| mobile | 390x844 | no overlap, no clipped buttons | browser screenshot |
| console | full flow | console error 0, Svelte warning 0 | browser |
| TS/Python parity | shared synthetic fixture | fills/equity/metrics match within tolerance | parity |

구현 순서:

- Phase 1은 unit 중심으로 기존 숫자 고정.
- Phase 2는 ledger와 reconciliation fixture를 우선.
- Phase 3 이후는 Browser/Playwright screenshot과 canvas nonblank check를 필수로 추가.

## 22. 개발 티켓 분해

### 22.1 Phase 1 tickets

- BT-001: 기존 `runBacktest` 대표 fixture 6개 생성.
- BT-002: `BacktestRunSpec` 타입과 `buildRunSpec` 작성.
- BT-003: `BacktestResult`/`BacktestWarning` 타입 작성.
- BT-004: 기존 `BtResult` -> `BacktestResult` adapter 작성.
- BT-005: warning/null 규칙 unit test.
- BT-006: `PriceChart` 호출부에 runId/specHash 전달만 추가.

### 22.2 Phase 2 tickets

- BT-101: `terminal/backtest/strategies.ts` registry 분리.
- BT-102: `ledger.ts` order/fill/cash/position/trade/equity 모델 작성.
- BT-103: `engine.ts` next-open pipeline 작성.
- BT-104: `metrics.ts` 공식 정본 구현.
- BT-105: B&H same-engine path 구현.
- BT-106: reconciliation guard와 invalid result 처리.
- BT-107: `data/backtest.ts` compatibility wrapper 정리.

### 22.3 Phase 3 tickets

- BT-201: fullscreen report dock layout 추가.
- BT-202: Summary strip을 RunSpec/provenance 중심으로 개편.
- BT-203: Overview tab 구현.
- BT-204: Trades table + chart selection sync.
- BT-205: Drawdown tab + chart highlight sync.
- BT-206: Assumptions tab + 필수 고지.
- BT-207: desktop/mobile screenshot 검증.

### 22.4 Phase 4 tickets

- BT-301: Calendar heatmap data builder.
- BT-302: Calendar tab UI.
- BT-303: Sensitivity RunSpec grid builder.
- BT-304: sensitivity worker/chunk runner.
- BT-305: stable/fragile/insufficient cell classifier.
- BT-306: cell preview/apply interaction.

### 22.5 Phase 5 tickets

- BT-401: walk-forward schema.
- BT-402: IS/OOS summary UI.
- BT-403: DSR/PBO placeholder with null reason.
- BT-404: Python parity fixture.
- BT-405: Robustness tab warning mapper.

### 22.6 Phase 6 tickets

- BT-501: strategy condition schema.
- BT-502: entry/exit condition editor.
- BT-503: strategy JSON import/export.
- BT-504: invalid strategy diagnostics.
- BT-505: builder strategy -> RunSpec integration.

티켓 운영 원칙:

- 각 티켓은 public terminal에 바로 연결하지 않는다.
- 계산 계약 변경 티켓은 fixture를 먼저 만든다.
- UI 티켓은 Browser/Playwright 눈검수 전 완료 처리하지 않는다.
- 기존 dirty worktree와 무관한 파일은 건드리지 않는다.

## 23. 성공 기준

제품 성공:

- 사용자가 차트에서 전략을 켜고, 마커와 에쿼티를 보고, 아래 리포트에서 손익/위험/거래/가정을 한 화면 흐름으로 검산한다.
- 전략 결과를 투자 추천으로 오해하지 않는다.
- 비용, 체결, 데이터 기준일, 배당 미반영이 결과 가까이에 보인다.
- 단일 실행, 차트 인터랙션, 리포트 탭이 빠르다.
- 지표가 많아도 차트가 덕지덕지해지지 않는다.

엔지니어링 성공:

- `PriceChart.svelte`가 백테스트 계산을 직접 품지 않는다.
- 계산 도메인과 렌더 어댑터가 분리된다.
- RunSpec/Result 계약이 테스트로 고정된다.
- TS/Python 계산 차이를 숨기지 않는다.
- public terminal에 미검증 변경이 바로 연결되지 않는다.

실패 기준:

- 수익률/승률이 UI의 주인공이 된다.
- EOD/T+1/배당 미반영/비용 가정이 모달 안에 숨는다.
- 파라미터 스윕이 "최고 전략"처럼 보인다.
- 실시간/라이브/체결 품질을 암시한다.
- 리포트가 카드 더미가 되어 차트를 밀어낸다.
- terminal chart가 Quant Lab, broker terminal, research report를 동시에 하려 한다.
