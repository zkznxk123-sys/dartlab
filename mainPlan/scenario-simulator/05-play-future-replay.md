# 05. Play — 미래 리플레이 (★중심 산출물)

상태: PRD v0.2
범위: 재생버튼으로 미래가 시간순 펼쳐지는 퍼포먼스 뷰. 미래 캔버스 개방·다중분기 동시재생·if 토글 실시간·근거 인벤토리·결정론 재현·graceful degradation.
UI 토폴로지: **`ui/packages/surfaces/src/terminal/`**(이 세션 중 `landing/src/lib/terminal/`에서 이동, 04 §3). 포트=`ui/packages/contracts`, 런타임=`ui/packages/runtime`.

---

## 0. 결론

**Play는 시뮬레이터의 정점 산출물이다 — 보조 차트가 아니라 심오한 최강 뷰.** 재생버튼을 누르면 시간이 미래로 흐르고, 예측된 주가·사건·지표·재무가 시간순으로 펼쳐지는 *퍼포먼스* 자체가 결과물이다. 핵심 통찰: **과거 replay = "이미 존재하는 시계열을 idx까지만 보여주기" / 미래 replay = "사전 계산된 결정론 path를 t까지만 보여주기" — 메커니즘 동일.** 따라서 새 재생 엔진 0 — 기존 터미널 replay 상태기계의 미래 방향 대칭 확장 + 결정론 산출물 *드러내기*(매 프레임 재계산 아님).

두 불변(01 §0): **(1) AI 없이도 결정론 재생** — path는 순수함수 DAG가 사전계산, Play는 드러내기만. **(2) AI 보완** — 약한 노드를 grounding 통과 의견으로 채워 더 나은 path(경합=검증). Play 위 모든 픽셀이 검증 엔진(buildProforma/monteCarloForecast/forwardTest)·정전 기법(fan chart/GMA/CIB)에 1:1 대응, 지어낸 것 0.

---

## 1. 기존 replay 상태기계 대칭 확장 (코드 실측 선행)

**선결 실측**: `ui/packages/surfaces/src/terminal/charts/chartState.svelte.ts`의 replay 상태(`replay`/`replayStep`/`replayStepBack`/`replayRestart`·`replayMs 400|150`, project_terminal_round3_overhaul에서 정비됨)가 미래 방향 확장 가능한지 Read로 확정. 실재 확인됨(파일 새 토폴로지에 존재) → replay 상태기계와 **동형(同型)인 미래 방향 상태기계를 신설**하되, 재생 컨트롤 UI·타이머 루프·렌더 파이프는 **공유** — 별도 차트 인스턴스 0, 새 재생 엔진 0(README "replay 재사용"의 정밀 의미).

상태 확장(conservative 최소주의 + ambitious 명세 병합 — 01 §6 sim 상태):
```typescript
sim.play = { on, t, len, ms:400|150 }   // t=0 → asOf, t=len → horizon 끝
playStep()      // t++ 미래 전진, 예측 캔들·이벤트·지표·재무 펼침
playStepBack()  // t-- 미래 되감기(자동재생 정지)
playRestart()   // t=0(asOf 복귀)
playExit()      // sim.on=false, 미래 캔버스 닫고 live 차트 복원
```
Play/일시정지/속도(400/150ms)/스크럽(t 드래그)/⏮ = 기존 replay 컨트롤 재사용. `mode:"live"|"simulate"` 전환(차트 모드 토글, 둘째 차트 금지).

**불변식(상호배타):** replay(과거)·sim.play(미래)는 `mode:live|simulate` 로 상호배타 — `replay.on`·`sim.play.on` 동시 true 금지(전환 시 진입 측이 상대 `.on=false` 보장).

---

## 2. 미래 캔버스 개방 (운영자 명시: live는 여백 0, sim은 연다)

"우측 미래 여백 0" 불변식은 **`mode:"live"` 한정**으로 명시 변경. `sim.on`일 때만 klinecharts xAxis를 `asOf + horizon`까지 패딩. 미래 봉 = candle 아닌 **fan band polyline**(`nextTradingDateOnOrAfter` 트레이딩데이 snapping 재사용 — 11 이벤트레일과 공유). Play → t가 0→len 전진하며 미래 path가 왼쪽→오른쪽 채워짐.

**★future-band 렌더 계약(plan 갭 — '재생 파이프 공유'의 정확한 경계):** 기존 `valBand`(PriceChart.svelte:523-534)는 `createOverlay('priceLine')` 수평 3선(시간불변)이라 미래 fan band(다점 시변)에 *재사용 불가* — 새 multi-point figure 필요. replay 는 `fullSeries().slice(0,idx)`(:279-307)로 *기존* 시리즈를 자르지만 미래는 자를 소스가 없다 → **컨트롤/타이머만 공유, data·band 렌더는 신규**(klinecharts `applyNewData` 미래-timestamp 행 또는 별도 overlay 레이어 + 미래 `replayCutT` + None-구간 끊기). §1 '동형 신설·엔진 공유' 경계의 렌더 측 정밀화.

**미래 구간 시각 구분(정직 가드, 03 §10·08 §7):** 미래 봉 점선·반투명, 배경 톤 구분, "가정 구간" 워터마크, 상시 "가정 하의 가상 경로 · 투자권유 아님 · [conf:30]". fan chart 단일선 거부, 단일 path 강조 금지(항상 밴드/다중분기).

---

## 3. 펼쳐지는 5갈래 (시간순 동기, 전부 결정론)

1. **예측 주가**: `monteCarloForecast` P50 중심선 + P5/25/75/95 fan chart(미래로 갈수록 벌어짐). seed=로컬 `random.Random(seed)`(09 P1, **stdlib·pyodide 안전 — numpy PCG64 아님**; MC는 분포통계 패리티 ±ε — byte 재현은 결정론 경로 한정, 01 §12). ⚠ **현재 `simulate/` 코어엔 mc.distribution 노드가 없다**(레거시 `monteCarloForecast`는 별개 경로, 01 §5b) — Play의 fan chart는 MC 노드가 simulate DAG에 합류한 *후*에 결정론 path로 드러난다. **결손 구간**: `NodeValue.vector`가 원소별 None을 허용(01 §6.1, missing≠0 불변) → fan band는 None 구간을 **0으로 잇지 않고 끊어** 그린다(데이터 부재를 0 추정으로 위장 금지). **★fan-chart 출력 shape 핀(plan 갭)**: `SimulationResult`(run.py)는 revenuePath/marginPath/fcfPath/dcfPerShare 만 — *일별 가격 path·가격 백분위 밴드 부재*, 레거시 `monteCarloForecast` 백분위도 **펀더멘털**(rev/OI/FCF)이지 가격 아님. ⟹ mc.distribution 노드는 **펀더멘털 분포(rev/OI/FCF P5~P95) emit** + Play 가격 밴드는 *결정론 매핑*(시나리오별 perShare → asOf 가격 anchor × 성장계수 path)으로 파생; `SimulationResult` 에 `pricePath:{p5..p95}, freq, dates` frozen 필드 추가(01 §5b mc.distribution + 09 §10 빌드티켓 동반). 노드 빌드는 진짜 천장이나 *shape·매핑 규칙*은 지금 박음. **★fan band σ provenance 시각 규율(A6 흡수, 01 §5b 미러)**: σ가 pooled-OOS residual(검증)이면 **실선 fan**, elasticity prior(`elasticity_prior_unvalidated`, 미검증)이면 **점선·회색 근사 fan** — LucaNet/Causal의 매끈한 단일 fan과 정직하게 가르는 디테일(cosmetic 가우시안 폭 = 통계적 연극 방지).
2. **예측 사건**: 정기보고서 캘린더(결정론적 알려진 미래 날짜) + 가정 이벤트 점선. **뉴스·shock은 미래에 안 찍음**(데이터 부재·예측 아님 — 정직 경계). 11 이벤트레일의 미래 공시 마커가 여기로 흡수(07 의존성).
3. **예측 지표·지수**: ECON 오버레이 미래 연장 = preset 거시 경로(가정 라벨). 지수 subject(06)면 지수 자체 미래 재생(가정 경로).
4. **예측 재무 IS/BS/CF**: t가 분기 노드 통과 시 하단 ReportDock에 `buildProforma` 투영 분기 펼침, bridge waterfall 시간순 갱신(08 §3.2).
5. **예측 신용(09 §4 solvency 뷰)**: 같은 분기 단면에서 survival curve·dCR 등급 궤적이 함께 전진(opt-in).

---

## 4. if 토글 실시간 연동 (증분 재계산)

차트-스코프 인셋(01 §Q4, colL region rule 회피)에 AssumptionLedger if 토글. 토글 → `assumptionSet` 변경 → 결정론 gate 재판정 → usable 가지 path 재계산 → fan band·이벤트·재무 ReportDock 즉시 갱신.

**속도(01 §13b)**: 노드 `inputsHash` dirty recompute — 토글 1개 변경 시 하류 sub-DAG만 재계산(전체 아님). landing=사전 동결 격자 lookup(재계산 0·즉시) / 로컬=Python 증분. 디바운스만 하면 인터랙티브(순수함수). 드라이버 클릭 → DriverGraph 엣지 하이라이트 + 미래 구간 강조(11 cross-panel highlight bus 재사용).

> **★A4 흡수(Causal/FinChat 편집가능 드라이버셀 + 라이브 레버, absorb-as-defer):** "레버 드래그→fan 즉시 재렌더"는 이 §4의 제품 요구지만 신규 발명 0이며 **두 미구현 엔진 선결**을 명시 후속 라벨로 단다 — ⓐ dirty recompute `_dirtyClosure`(01 §6.2·§13b-1, 현 `evaluateSheet`는 항상 전체 재평가) + ⓑ Sobol S_T 가지치기(04 §5 OQ11 = 데모-의존 잠정값, k≤6은 proven bound 아닌 design target). 즉시 재렌더는 (1) landing = 01 §13b 사전 동결 격자 lookup(재계산 0, **격자축 = top-6 누적 S_T≥0.9 토글만**) (2) 로컬 = Python 증분 — 둘 다 정직(퍼블릭 서버0 floor), 격자 밖 토글은 "로컬 Python 재계산 필요" 정직 라벨. 레버 = **차트-스코프 인셋 AssumptionLedger 토글**이지 자유 슬라이더 무더기 금지(Causal 무제한 편집셀 복제 = if-폭발 = `feedback_always_check_clutter` 위반). 레버 입력 = `AssumptionLedgerRow`(user source) 생성으로 단위·기간·falsifier 강제 — 단 이 *사용자-입력* row는 grounding-check(b) 순환에서 제거된 *AI-grounding* row와 구분된다(01 §6.3 OQ10의 "AssumptionLedgerRow 코드 0건 제거"는 약한-det 자체분포 순환 차단이지 사용자 입력 ledger 부정 아님). 결과는 항상 fan band(단일 path 강조 금지)·결손 None 끊김(0 대체 금지). **reject 경계 = 사용자 토글만 합법, "dartlab이 이 가정 쓰라" 개인화 추천 금지**(08 §7 Advisers Act 가드).

---

## 5. 다중 분기 동시 재생 + 결정론 재현

- **단일 분기**: P50 중심선 + fan band(seed 고정).
- **다중 분기**(`sim.branches[]`, ≤3 — 09 §13 OOM 상한): baseline/adverse/severe 동시 전진(색상 구분 P50 3선 + 반투명 밴드 중첩). 분기 갈라지는 시점(예: 금리 결정 분기)에서 부채처럼 벌어짐. 트리 노드=RunSpec, 부모 분기말 BS 상속.
- **결정론 재현**: 같은 `ScenarioSpec`(assumptionSet `on` 상태 + MC seed + asOf + branch) → 바이트 단위 같은 재생. 현 결정론 코어는 **난수 0**이라 seed 없이도 노드별 inputsHash byte-identical(MC seed는 mc.distribution 노드 합류 후 적용, 로컬 `random.Random(seed)`, numpy/PCG64 아님). `sim.specKey`=직렬화 키, URL `?sim=` 공유(08 §8 — 단 브라우저는 사전계산 path 드러내기, RNG 미사용). 두 번 눌러도 같은 미래.

**★격자 직렬화 계약(01 §13b.6 보강):** (i) `gridArtifact` TS 인터페이스 = `{specKey → {candles:{p5..p95:number[]}, fanBand, events:SimEvent[], macro:number[], report, credit}}`(SimSeries/FanBand/SimEvent 타입, candles freq); (ii) `specKey = serialize(branchId, sorted(toggleState), mcSeed, asOf)` 결정론 — float round·sorted keys 정규화(01 §6 `_normalize` 미러, TS/Python byte-parity 골든); (iii) `sim.play.t(0..len)` → gridArtifact 시간-인덱스 매핑. 격자 *스키마*는 지금 박음(OQ11 의 k≤6 축 선택은 데모 의존, 분리).

---

## 6. 근거 인벤토리 + 결정론 내러티브 (완전성 ADD)

운영자 "과거 근거 + 미래 수십~수백 예측 근거 나열·연결" — DriverGraph 엣지 하이라이트만으로는 "연결"만 되고 "나열"이 빠진다. 보강:
- **근거 인벤토리 뷰**: ReportDock 한 탭으로 `evidence ledger`(과거 fact ref + 미래 driver, 출처/asOf/provenance 컬럼, DriverGraph 엣지 cross-link). 수백 근거를 표로 나열, 토글 상태 표시.
- **결정론 내러티브 슬롯**(story 재활용 금지 — AI 산문 환각 차단): "X 가정 → Y 분기 영업이익 Z원(ref) → 목표가 W(ref)" 식 fill-in 결정론 템플릿(scan 결정론 서사 패턴). AI 생성 산문 금지, 결정론 슬롯만.

---

## 7. Graceful degradation (완전성 ADD — 데이터 공백 종목)

시뮬레이션 불가/부분가능 종목의 명세(03 §6 가드):
- 신규상장사(과거 시계열 < 회귀 최소 nObs) → pooled-panel 섹터 transfer 폴백(02 §2B.1), 그래도 부족하면 **Play 버튼 비활성 + 사유 표시**("시계열 부족 — 시뮬 불가").
- 분기 결측·정정공시로 BS 항등식 과거 미닫힘 → buildProforma 상속 체인 붕괴 시 blocked status, 결과 미생성.
- walk-forward 모드: Play는 whatif/replay 시각화, **walk-forward는 ReportDock 리포트-only**(시간축 애니메이션 아님 — 명시 결정).

---

## 8. 거처·계약

- **UI**: `ui/packages/surfaces/src/terminal/charts/`(PriceChart `subject`/`sim` 모드, chartState 확장). ReportDock 셸(08 §5, valuation→sim mode). 새 패널·차트 인스턴스 0.
- **엔진**: Play는 `dartlab.simulate(mode="replay"|"whatif", ...)` 결과(`SimulationResult`)를 시간축으로 드러냄. 계산은 L2.5 simulate(01), UI는 드러내기만.
- **선결**: 09 Phase 0 MC seed kill-test(결정론 재현 척추) → simulate 코어 졸업 → Play UI. mainPlan 완료(터미널 ui/packages 정착) 후.

---

## 9. 왜 심오하면서 정공법인가

운영자의 미래 리플레이 퍼포먼스(Play·일시정지·속도·스크럽·다중분기·if 토글 실시간·결정론 재현)를 *완전히* 구현하되 새 재생 엔진 0 — 기존 replay 와 동형인 미래 상태기계(sim.play 1객체 + play* 4메서드) 신설, 재생 엔진(타이머·렌더·컨트롤)은 공유 + 결정론 산출물 드러내기. 화려한 모든 픽셀이 검증 엔진·정전 기법에 1:1 대응. **"강함은 쌓아서 아니라 깎아서."**
