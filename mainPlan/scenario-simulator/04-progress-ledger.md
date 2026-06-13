# 04. Progress Ledger

상태: PRD v0.3 (2026-06-13 12-에이전트 워크플로 심화 — 지수 차트 완전 명세 + 시뮬 backbone/데이터배선 코드-그라운드 재설계 + 적대검증 반영)
범위: 현재 확정 결정, 미작성/정정 갭, NEXT 시퀀스, 구현 전 체크리스트

> ⚠ v0.1 폐기 박제: 이전 04는 "초기 아키텍처 = story 동격 L3 `scenarioWorkbench`, 공개 verb `dartlab.scenario`(미결)"을 현재 결정으로 들고 있었다. **01 §3이 이를 코드로 기각**했다(story=순수 렌더러라 동거 불가, `scenario` 명사형은 `macro.scenarios`/`ScenarioOverlay` 충돌). 본 v0.2가 정본.

---

## 1. 현재 확정 결정 (v0.2)

1. 제품은 주가 예측기가 아니라 **조건부 손익-주가 시뮬레이터 + 재생(Play) 미래 리플레이**. scenario≠forecast.
2. **엔진 거처 = 새 L2.5 독립 묶음 `src/dartlab/simulate/`** (드라이버 DAG + 엣지 transfer 소유, leaf 계산은 L2 SSOT 호출). story 동급 L3 기각, 신규 L2 기각(L2↔L2 cross 금지). `L2_PEERS` 미소속이라 analysis+macro+quant 동시 결합 합법. → 01.
3. **공개 verb = `dartlab.simulate(...)` / `Company.simulate(...)`**, `mode=whatif|replay|walkforward`·`universe`(횡단면=scan 위임) 흡수. `scenario` 명사형 verb 기각. → 01 §3.
4. **AI = 노드 평행 `.det`/`.ai` 슬롯.** 목적=보완(약한 노드를 grounding 통과 AI로 교체→결론 개선), 경합(평행 보존+Brier 사후채점)=그 보완이 진짜인지 검증하는 안전장치. 블렌딩 금지. AI 코드=`ai/tools/lens.py`(no-graph-regression). → 01 §6.
5. **driver 수렴/확장 = DriverRegistry**(카드+6게이트 입장, pooled-panel transfer). factor-zoo 규율(다중검정·OOS·차원붕괴·민감도 가지치기·decay). → 02 §2B.
6. **중심 산출물 = Play 미래 리플레이**(기존 터미널 replay 상태기계 미래방향 대칭 확장). 미래 캔버스 개방(EOD "여백 0"은 live 모드 한정). → 05(미작성).
7. **가치평가 = simulate(mode="whatif")의 정적 단면.** 적정주가=조건부 범위+reverseDCF 닻(단일 목표가·rating 금지). 신용=solvency 뷰(같은 단면의 지급능력 렌즈). 보고서=story 렌더, 발간=`story/publisher.py`. → 08·09 §4.
8. **시뮬레이터-앵커 = 정합화 원리.** "모든 시뮬 숫자=하나의 SSOT leaf"가 DCF 5중·회귀 4중·축 이중화를 구조적으로 청산. 실행은 외과적·census 단조·byte-identical·무중단(빅뱅 금지). → 09.
9. 결손은 0 대체 금지(missing/blocked/partial). 결과는 ref+quality gate status+provenance. look-ahead 차단(t종가→t+1시가). 단일 base 금지(bear/base/bull).
10. **v0.3 심화(12-에이전트 워크플로, 코드 그라운드)** 4 정정 박제:
    - **노드 차원폭발 차단 = 3중 좌표 (driverId, scenarioId, periodKey).** rev.path = 시나리오당 1노드, 연도·분기는 `NodeValue.vector`가 흡수 → 노드 수 O(driver×branch)≈24(폭발 아님). 01 §5.
    - **데이터 추가 = exogenousAxes 1줄(수동) → 전 과정 자동(driverPrefit→admission→decay).** if 상한 = 검증된 축 수(6~8), 시리즈 수와 독립(Stock-Watson). 02 §2B.7~2B.9.
    - **치명 신규 ① models HF 배포 경로 0건** — pre-fit 적합이 `~/.dartlab/`(ephemeral)에만 저장돼 cron 켜도 소비처 영구 None. DATA_RELEASES 'models' 1줄 + `data/models/` 리다이렉트 + `_uploadModels`가 전체 배선의 load-bearing. 02 §2B.5.
    - **치명 신규 ② scanMacroBeta firm-level t-stat 수학적 부재** (연간 N=3, df=N−k≤−1). "N~13 정직"이 한 단계 더 낙관 → firmRefine은 t-stat 게이트 *계산 금지*(pooled에서만 valid), leave-last-k hitrate만. 01 §1 #7·02 §2B.1·§2B.9. **★:205 버그 수정 제안 `*=`도 틀림**(평균경로 소실) — per-year 성장계수 cumprod, 단 kill-test로 '기존이 버그'임 먼저 증명. 01 §12.

---

## 2. 작성 문서 + 상태

| 문서 | 상태 | 비고 |
|---|---|---|
| README | ✅ v0.2 | 문서지도·L2.5 정정 (06 v0.3 반영 1줄 갱신 필요) |
| 00-product-prd | ⏳ v0.1 잔재 | "Scenario Workbench" 본문·제품명 미결 → §5에 v0.2 동기화 필요 |
| 01-engine-architecture | ✅ v0.3 | §5 노드 3중좌표·§6 NodeValue/실행기/gate/grounding·§12 byte-parity+:205 수식정정·§13b 격자구조·§1 #7(scanMacroBeta N=3) 심화 |
| 02-assumption-method | ✅ v0.3 | mode enum 본문 통일(replay/walkforward/whatif)·§2B.7 end-to-end 데이터배선·§2B.8 수렴증명·§2B.9 tier가드·§2B.10 스키마가드·§2B.5 models HF 배포 갭(치명) |
| 03-validation-ai-review | ⏳ v0.1 | §9.3 본진 승격에 08 §11 발간 게이팅 미반영 |
| 04-progress-ledger | ✅ v0.3 (본 문서) | — |
| 08-valuation-report | ✅ v0.2 | 가치평가 융합·발간 계약(코어 졸업 후) |
| 09-architecture-consolidation | ✅ v0.2 | 부채 원장·앵커·신용 뷰·Phase 시퀀스 |
| 05-play-future-replay | ✅ v0.3 | ★중심 산출물. fan-band None구간 끊기·byte-parity 범위 명시 |
| 06-index-chart | ✅ v0.4 | subject 소유권 seam(CenterStack-local $state, ctl 미상향)·IndexPort(catalog/search/series)·**US=FRED 종가 라인 subject 통합(KR OHLCV 캔들 평행, candleStyle='area' degenerate)·종가전용 지표 3분기 매트릭스·FRED 데이터 라이브 실측** |
| 07-integration-roadmap | ✅ v0.2 | 지수→이벤트레일→백테스팅→시뮬 시퀀스·공유 DNA·Phase |
| 10-backtesting-strategy-tester | ✅ 이관 | 메모리 `project_terminal_backtesting_prd`에서 repo 이관(포인터화) |
| 11-disclosure-event-rail | ✅ 이관 | 메모리 `project_terminal_disclosure_event_rail_prd`에서 repo 이관(포인터화) |

---

## 3. ★워크스페이스 변동 (이 세션 중 실측 — 중요)

mainPlan UI 플랫폼 리팩토링이 **이 세션 동안** 단계-4b~5-2b로 진척(git log 오늘). 핵심:
- **터미널 전체 이동**: `landing/src/lib/terminal/` → **`ui/packages/surfaces/src/terminal/`**(commit `ff9099ba0` "data/→lib/ git mv"). `landing`엔 `terminal-shell/{routeLoad,terminalShell}.ts`만 잔존.
- **결과**: PRD의 모든 `landing/.../terminal/...` UI 경로 stale. 새 SSOT = `ui/packages/surfaces/src/terminal/`(charts/PriceChart.svelte·chartState.svelte.ts 실재) + 포트 `ui/packages/contracts` + 런타임 `ui/packages/runtime`. 엔진 경로(`src/dartlab/*`)는 불변.
- **함의**: PRD가 "mainPlan 이후 착수"라며 가정한 post-refactor 토폴로지가 *조기 도래*. 05(Play)·06(지수)는 새 토폴로지로 재기반 필수. `chartState.svelte.ts` 실재 확인 → README "replay 상태기계 재사용" 옳음, 08 "부재" 정정 대상.
- ui/apps/local SvelteKit 앱 신설(단계-5), createLocalRuntime AiPort SSE 배선(단계-5-2b) — 로컬 고급 엔진 경로 진행 중.
- **★v0.3 워크플로 코드-그라운드 확정**: 정본 = `ui/packages/surfaces/src/terminal/charts/PriceChart.svelte`(klinecharts 1051줄). `ChartCtl`은 PriceChart **내부** 생성(`new ChartCtl` 1곳, setContext 0건) → CenterStack은 ctl 모름 ⟹ 06 v0.2 "ctl.subject 분기"는 컴파일 불가, 정정=CenterStack-local `$state`(06 §2.5). soft-swap은 실재하나 *회사 전환 전용*. replay 상태기계는 *과거 backward-only*(미래 sim.play 필드 신설 필요). 미래여백 0은 *무조건 적용*(05 §2 live 분기 신설 필요). PricePort 실제 메서드 = initial/older/loaded/govCandles/govRecent(PRD `indexInitial` 발명 폐기). `ui/shared/chart/PriceChart.svelte`는 별개 SVG 컴포넌트(혼동 금지).

---

## 4. NEXT — PRD 닫기 체크리스트 (v0.3 갱신)

### ✅ 완료 (v0.2→v0.3)
1. ~~05-play-future-replay.md~~ ✅ — ★중심 산출물 작성(v0.3 fan-band None구간 끊기 포함).
2. ~~06-index-chart.md~~ ✅ — v0.3 전면 대체(subject 소유권 seam·IndexPort catalog/search/series·US 부재 가드).
3. ~~07-integration-roadmap.md~~ ✅ — 시퀀스·의존성·Phase.
4. ~~02 mode enum 통일~~ ✅ — 본문 §2.3·§3.1 → `replay/walkforward/whatif` SSOT 단일.
5. ~~01 §1/§5/§6/§12/§13b 심화~~ ✅ — v0.3 워크플로(노드 3중좌표·NodeValue/실행기/gate·byte-parity·격자·N=3 #7).
6. ~~02 §2B 심화~~ ✅ — §2B.7 데이터배선·§2B.8 수렴증명·§2B.9 tier가드·§2B.10 스키마가드·§2B.5 models 배포 갭.
7. ~~06 OQ12(US 지수)~~ ✅ — 운영자 결정=FRED 채택, 종가 라인 subject로 06 v0.4 통합. FRED 데이터 라이브 실측(SP500/NASDAQ/다우/VIX 4종)·종가전용 지표 3분기 매트릭스·candleStyle 격리. 잔여=구현만.

### ⏳ 남은 정합성 (v0.1 잔재 + lint 범위)
7. **00 v0.2 동기화** — 제품명 `simulate` 확정, §2 본문 "Scenario Workbench" 치환, §5에 "Valuation Report + Credit View = simulate 발간 단면" + 비범위에 L2.5 합법성 1줄. (현 헤더 정정 헤더로 정본 우선, 본문 전면개정은 선택)
8. **03 §9.3 발간 게이팅 반영** — 08 §11 우선순위 역전 가드(발간은 코어 졸업 후)를 본진 승격 기준에 추가.
9. **08 §2.2·§7 금지어 lint 범위** — `priceImplied.py` + `_valuationOther.py` 2파일.
10. **README 1줄** — 06 v0.3 반영(완료) + 06 문서지도 갱신(완료).

---

## 5. Open Questions (v0.2 — v0.1 미결 close 후 잔여)

> v0.1 OQ1(verb 위치)·계층 결정은 01 §3이 close. 아래는 잔여.

1. 거시 미래경로 예측(AR/VAR) — 부재 확정(01 §9). 별도 _attempts 라운드 시점.
2. pooled-panel transfer의 섹터 풀 경계(WICS 11업종? sub-sector?) — G2 데이터 밀도 감사에서 실측.
3. AI lens 의견 노출 수준(노드 전수 vs fork/gap만) — 01 §6 "fork/gap만" 잠정, 데모 실측.
4. 횡단면 스캔(`universe=`)의 제품 UI 위치 — 06/07에서 결정.
5. ReportDock credit mode 착수 시점 — P7(extractChsFeatures proforma 주입) 졸업 후.

### v0.3 신규 잔여 (워크플로 심화)

6. **driverPanel pre-fit 적합 주기** — scan 증분마다 vs 분기 cron. pooled 베타는 분기 단위로만 유의하게 변함 → 권장 = dataPrebuild full(주1회) step 또는 별도 분기 cron(매 증분 재적합은 낭비+노이즈). 운영자 주기 결정 1건.
7. **tier(core|exploratory) 지정** = 운영자 수동 vs axis 기준 자동(척추 6축=core, 뉴스·customs=exploratory). 권장 = axis 자동 + 카드별 override(예외만).
8. **mc.distribution 노드 위상** — proforma vector를 deps로 받는가(OOM 위험) vs 평균경로 직접 계산(현 `_simMonteCarlo`가 `_applyMacroShock` 직접 호출 → SSOT 분열). 졸업 데모 byte-패리티가 노드 그래프 위상 가름. 01 §5.
9. **:205 누적 전환 정당성** — 현 `meanRevPath[yr]*(1+revNoise)`가 '하라이즌-끝 단년 노이즈 분포'인지 버그인지 kill-test 선행(전환 시 결과 바뀌어 회귀 위험). 01 §12.
10. **groundingCheck '주장 지지' 범위 출처** — AssumptionLedgerRow(§2.5) vs 약한 det 분포. 후자면 순환(약한 det 교체 기준이 그 약한 det 자신) → AssumptionLedgerRow 우선. 01 §6.3.
11. **사전계산 격자 '핵심 토글'(2^k, k≤6) Sobol S_T 컷오프** — S_T≈0 제거로 k≤6 보장하는 임계값 데모 전 미정(02 §2B.4-C). 01 §13b.
12. **(close — 운영자 결정=FRED 채택)** ★US 지수(SP500/NASDAQ/다우/VIX) = **FRED 종가 라인 subject로 06 통합 확정**. 운영자 결정 '미국 지수는 FRED 고려' 반영. 로컬 `data/macro/fred/observations.parquet` 실측으로 4종 라이브 확정(SP500 2609행 2016~·NASDAQCOM 14440행 1971~·DJIA 2609행 2016~·VIXCLS 9508행 1990~) — '데이터 전무(grep 0건)' 정정(grep은 ui 코드 미배선이지 데이터 부재 아님). KR=OHLCV 캔들 / US=종가(o=h=l=c, v=0) degenerate candle + `candleStyle='area'`. 새 차트·포트 0(IndexRef.market 분기 + 변환 1함수). 종가전용 제약=캔들·ATR·KDJ·CCI·WR·DMI·ICHI·AO·CR·VP 불가(06 §4.2), MA/RSI/MACD/BOLL 등 close-기반만 정상. 06 §3.2~§3.6·§6. **잔여=구현만**(데이터 선결 0). 표면 선호 1건(macroSource srcCache 공유 vs 소스 독립, 06 §7 OQ2).
13. **CMP-지수 통합(VS 벤치마크에 KOSPI/KOSDAQ)** — compares 타입 IndexRef 동반 확장 vs 별도 indexCompares 경로 분리. 06 핵심(subject)에서 분리된 후속 선택 작업. 06 §5.1.

---

## 6. 구현 전 체크리스트

- [x] main memory 포인터 (project 메모리 — 본 세션 추가 예정)
- [x] 엔진 거처 L2.5 simulate 확정·근거 기록 (01)
- [x] driver 수렴/확장 메커니즘 (02 §2B)
- [x] AI 보완/경합 + no-graph-regression (01 §6)
- [x] 가치평가·신용 = simulate 뷰 (08·09 §4)
- [x] 부채 원장 + 외과 시퀀스 (09)
- [x] MC seed kill-test 선결 명시 (P1)
- [ ] 05/06/07 작성 + 00/02/03 v0.2 동기화 (NEXT §4)
- [ ] 워크스페이스 새 토폴로지(ui/packages/surfaces) 반영 (05/06)
- [ ] 착수 = mainPlan 완료 후 (조기 진척 중 — 의존성 07에서 확정) + 운영자 go
