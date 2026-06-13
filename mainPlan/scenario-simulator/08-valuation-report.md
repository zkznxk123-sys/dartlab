# 08. Valuation Report — 시뮬레이터 = 가치평가 엔진, 프로급 보고서 발간 계약

상태: PRD v0.2 (2026-06-13 다모다란 융합 리서치 + dartlab 자산 감사 + 적대 검증 후 확정)
**지위: 발간 *계약* 문서 — 구현은 `simulate/` 코어가 `tests/_attempts/scenarioSimulator/` 졸업한 *후*에 착수(§11 게이팅).** 코어가 0줄인 지금 보고서 파이프라인을 먼저 짓는 것은 우선순위 역전(적대검증 C-1).

---

## 0. 결론

**시뮬레이터는 이미 가치평가 엔진이다.** 다모다란 "Narrative and Numbers"(story→drivers→numbers→value→story break)가 확정된 `simulate/`(L2.5) 아키텍처와 노드 대 노드 동형이고, 대응 leaf가 *전부 본진에 실재*한다(DCF 5변종·역DCF·RIM·실물옵션·SOTP·5시나리오 MC·thesisKillChain·publisher→blog). 따라서 "가치평가 보고서 발간"은 **새 엔진이 아니라 `SimulationResult`를 시간(Play)이 아닌 *논증 순서*(narrative→drivers→numbers→value→falsifier)로 펼친 정적 단면**이다. 새 계산 0, 새 verb 0 — `dartlab.simulate(mode="whatif")` → story가 `type="simulation"`으로 렌더.

"프로급"은 **품질 바**이지 유료 제품이 아니다(운영자 명시: "아직 pro 안 만든다, 그냥 프로급"). monetization·티어 분할 설계 없음.

---

## 1. 동형 확정 (덧붙임 아닌 같은 엔진 다른 각도)

| 다모다란 5단계 | `simulate/` 자료구조 (01) | 호출 leaf (2층 — §3.1) |
|---|---|---|
| ① Narrative (story) | `ScenarioSpec`/`ScenarioBranch` (02 §2.3-4) | — (가정 입력) |
| ② Story → drivers | `DriverNode`/`DriverSheet` (01 §5) | `transfer.transferMacroToFundamentals` |
| ③ 3P test (possible/plausible/probable) | DriverRegistry 6게이트 (02 §2B) | `calcMacroRegression`(pooled-panel OOS) |
| ④ Drivers → numbers | `DriverSheet` leaf 노드 | `buildProforma` (불가침) |
| ⑤ Numbers → value | ValuationBridge (02 §2.8) | **`calcDFV`/`dFV`**(quality-WACC 삼각검증, *not* deprecated `fullValuation`) |
| ⑥ **현재가가 요구하는 믿음** | reverseDCF 닻 (§2) | **`reverseImpliedGrowth`+`computeGap`** |
| ⑦ Story break | `HypothesisNode`·`tripwireMonitor`·`DisagreementLedger` | `synth/thesisKillChain.py` |
| ⑧ Feedback loop open | AI `.ai` 평행 슬롯 + Brier | `ai/tools/lens.py`(신설)·`OutcomeLog`(MCP) |

다모다란 6단계 라이프사이클(startup→young→growth→mature growth→mature stable→decline)마다 story/number 균형·driver·multiple이 다르다 → DriverRegistry가 라이프사이클별 토글 카드 집합을 결정(young=TAM/share/survival, mature=FCF/multiple, **금융사=residualIncome/bankDFV leaf 스위치**(FCFF 부적합), cyclical=정규화 마진). AI lens가 단계 분류.

---

## 2. 적정주가(fair value) — 단일 목표가·rating 금지, reverseDCF 닻 + 조건부 범위

### 2.1 정의

> 적정주가 = 단일 점이 아니라 두 좌표의 **조건부 진술**:
> (A) **조건부 가치 범위** — bear/base/bull × P10/P50/P90 (시나리오 토글 파생)
> (B) **reverseDCF 닻** — 현재가가 *요구하는* 매출성장 g/영업마진 m/ROIC r. *예측이 아니라 시장이 priced-in 한 믿음의 해부*(Mauboussin Expectations Investing).

질문 전환: "미래 성장률이 얼마?"(추측·환각)→"시장이 박은 성장률이 plausible?"(판정·검증). **컨센서스 부재를 강점으로 뒤집는** 메커니즘. dartlab `reverseImpliedGrowth`(`priceImplied.py:27`)+`computeGap`(`:167`) 이미 실재, story `reverseImplied` 블록 이미 배선(`registry.py:854,890,914`) — 갭은 "보고서 *전면*으로 승격"이지 배선 아님.

### 2.2 단일점·rating 차단 (적대검증 B-1·B-2 — 규제선 실제 구멍)

- **`signal` 필드 차단/리네임(B-1):** `reverseImpliedGrowth`의 `PriceImpliedRevenue.signal`이 `underpriced|overpriced|fair`(`priceImplied.py:23,222`)를 반환 — 이건 사실상 매수/매도 rating이다("underpriced"=한국어 "사라"로 직역). **발간 표면에서 `signal` 노출 금지**, "현재가 함의 vs 회사 과거범위 정합성(consistent/optimistic/pessimistic)"으로 리네임. `underpriced`/`overpriced` 단어 자체가 금지어 lint 대상.
- **★`computePriceTarget` rating·단일목표가 차단(B-1', 평가 P0):** `pricetarget.py`의 `weighted_target`(단일 목표가)+`signal: strong_buy/buy/hold/sell/strong_sell`(`_classifySignal:644`)도 동일 금지 출력 — **§2.3 어댑터가 두 필드를 drop**하고 P10~P90 분포+reverseDCF 닻만 발간. 금지어 lint **3파일**(`priceImplied.py`+`_valuationOther.py`+**`pricetarget.py`** — signal enum·`weighted_target`/`strong_buy`/`strong_sell` 차단). 09 P12 범위 확대.
- **priceP50 단독 금지(B-2):** `PriceSimulationResult.priceP50`/`perShare`(02 §2.8-9) 단독 표시는 목표가로 읽힌다. **발간 게이트 기계 규칙: perShare/P50 단독 출력 시 build fail — 항상 P10·P90 + reverseDCF 닻 동반.** 무료 공개 발간이 더 위험(불특정 다수).
- `verdict`(저평가/적정/고평가) = 조건부 *분류*이지 Buy/Sell *rating* 아님 — 단 §7 가드로 강제.

### 2.3 leaf (전부 실재 — 단 ★computePriceTarget rating 정면충돌, 어댑터 필수)

범위(A): `calcDFV`(`dFV.py:56`, 4엔진 통합 quality-WACC)·`computePriceTarget`(`pricetarget.py:460`, 5시나리오×proforma×DCF + `_monteCarloPriceDistribution` P10~P90). 닻(B): `reverseImpliedGrowth`+`computeGap`. WACC: `computeCompanyWacc`(`_proformaCore.py:145`)+`calcQualityWACC`. **한국기업 CRP 토글**을 DriverCard로(지정학 악화→CRP +1.5pp).

> **★평가 P0 정정 — computePriceTarget는 "거의 선구현"이 아니라 금지 출력 반환체다:** `computePriceTarget`은 P10~P90 분포 외에 **`weighted_target: float`(단일 목표가) + `signal: strong_buy/buy/hold/sell/strong_sell`(`_classifySignal:644` = 매수/매도 rating)**을 함께 반환한다 — 00·§2가 가장 강하게 금지한 바로 그것. §2.2 금지어 lint이 `priceImplied.py`만 잡고 *이 중추 함수를 놓쳤다*. ⟹ 발간에 그대로 쓰면 안 되고, **발간 어댑터(P10/P50/P90 분포 + reverseDCF 닻만 추출, `weighted_target`·`signal` 필드 drop)**를 거친다. 졸업 AC = "calc 직접호출 0"과 **동급으로 "rating/단일목표가 필드 누출 0"** 명문화. (~80% 재사용 자평은 실재하나 *그대로는 못 씀* — 어댑터가 추가 작업.)
> **★구현 정합(2026-06-14):** deterministic core의 dcf 노드(`registry._fnDcf`)는 **proforma-FCFF**를 쓰고 `calcDFV`를 의도적으로 회피(외부 proforma 무시→scenario-coherence 깨짐, 09 P3). 발간 ⑤ Numbers→value도 *시나리오 일관성*을 위해 simulate dcf 노드(proforma-FCFF) 결과를 ref로 받아야지 calcDFV/computePriceTarget을 재호출하면 SSOT 분열(§1 ⑤ 표는 정적 가치평가용 calcDFV — scenario 발간과 구분).

---

## 3. 프로급 보고서 구성 — 12블록, 2층 leaf, story 렌더

### 3.1 2층 leaf SSOT (적대검증 A-1·A-3 — 핵심 정정)

가치평가 호출은 **2층**이다: `analysis/valuation/`(순수 수학 leaf) ← `analysis/financial/valuation.py`+`_valuation*.py`(`calc*` 회사-바인딩 래퍼: series/shares/price fetch) ← story. **simulate는 `analysis/financial/`의 `calc*` 래퍼를 호출**(순수 leaf 직접 아님) — 그래야 company 바인딩(`_getSeriesAndShares`·`_fetchPriceContext`)을 재구현하지 않는다(0줄 보장). 중앙 적정주가 leaf = `calcDFV`(삼각검증), **`fullValuation`은 deprecated(docstring "calcDFV 우선")라 fallback으로 강등**.

### 3.2 12블록 (괄호=기존 story 블록/leaf, 대부분 재사용)

1. Thesis/Narrative (ScenarioSpec+assumptionLedger) 2. Environment Snapshot (02 §5.1) 3. **DriverGraph→Profit Bridge waterfall (★신규 렌더러 2개)** 4. Proforma IS/BS/CF (`buildProforma`) 5. DCF range (`dFV`/`priceTarget` 블록) 6. Relative (`valuationSynthesis` 블록) 7. **Reverse 닻 (`reverseImplied` 블록 — 상단 승격)** 8. Sensitivity (`sensitivityGrid`) 9. Robustness (walk-forward, replay 모드) 10. Falsifier (`thesisKillChain`) 11. Assumptions ledger (각 행 status+falsifier+ref) 12. Provenance (셀 ref+sourceRef+latestAsOf, 결손 0대체 금지).

신규 렌더러 단 2개: `businessDriverBridgeBlock`(02 §5.3)·`profitBridgeBlock`(02 §5.4) — builders.py 확장(새 모듈 0). story type 11→12(`type="simulation"`).

### 3.3 역할분리 + 14키 ref 치환 매트릭스 (적대검증 D-3 = 졸업 AC)

story는 렌더만(헌법 "자체 계산 0"). 현 registry가 `calcDcf(company,...)`를 *직접 호출*(`:897`)하는데, 융합 후 **valuation 14키(`_CORE_KEYS`, registry `:848-863`) 전수를 `SimulationResult` ref 읽기로 치환**(키→필드 매트릭스 명시). 일부만 치환하면 story가 계산 트리거를 유지 → 헌법 회색지대. **졸업 AC = "simulation type 보고서에 calc 직접호출 잔존 0".**

---

## 4. 발간 표면 (적대검증 A-2·E-2)

- **정적 blog:** `story/publisher.py::publishReport`(`:27`)→`_buildFullReport`(`:118`, 면책 자동삽입 `:169`)→`blog/05-company-reports/{순번}-{코드}-{명}/index.md`→landing `company-reports` 카테고리(`posts.ts:15`)→GH Pages. **publisher 선례는 `story/publisher.py` 단독**(`credit/publisher.py`는 *미존재* — A-2 환각 삭제).
- **기존 company-reports 충돌 규약(E-2):** 같은 카테고리에 기존 6막 리포트와 시뮬 리포트가 공존하면 혼란. **`reportType` 메타(또는 서브카테고리)로 구분 + asOf 표시** 필수. 충돌 미설계로 같은 카테고리 재사용 금지.
- **terminal `?sim=`:** URL 공유=Play 결정론 척추. 단 현 terminal에 replay 상태기계·ReportDock 둘 다 부재(§5가 채움).
- **viewer AskDrawer:** 결정론 Tier0 답 안 "이 회사 시나리오 보기" 링크(공개 AskDrawer 회귀 금지 준수).

---

## 5. ReportDock — 단일 valuation 모드로 시작 (적대검증 C-2·B-3)

세 보고서(가치평가·백테스트·시뮬)는 같은 정직 골격 공유(RunSpec·provenance·assumption ledger·quality gate·면책·look-ahead 차단). 그러나 **백테스트·시뮬 모드는 둘 다 미존재 → 2-mode 추상화 선투자는 YAGNI.** ReportDock은 **valuation 단일 모드로 시작**, backtest/sim 모드는 그 엔진 졸업 시 추가. ReportDock은 landing 측 *셸*(렌더만, 계산기 아님). 백테스팅 PRD([[project_terminal_backtesting_prd]])와 교차참조.

**금지어 lint(B-3):** "백테스팅 PRD와 SSOT 공유"는 거짓(둘 다 미존재) → **본 작업이 `tests/audit/` 투자권유 금지어 lint를 *선신설***하고, 백테스팅이 나중에 import. 의존 방향: 본 작업이 선행 정의자.

---

## 6. 프로급 품질 체크리스트 (= "전문가급" 라벨의 정의, 발간 게이트)

전 항목 PASS여야 발간(`thesisKillChain.premortemQualityGate` + 03 Gate Matrix가 기계 강제):
1. ☐ 단일 목표가 부재 — 범위로만 (§2) 2. ☐ reverseDCF 닻 노출 + 충돌 판정 (03 §6.2) 3. ☐ 최소 3시나리오 (bear/base/bull) 4. ☐ 모든 숫자→ref 5. ☐ 모든 가정→falsifier 6. ☐ terminal 규율 통과 (g≤Rf, reinvest=g/ROC, ROC→WACC 수렴 or 명시 moat) 7. ☐ 결손=결손(0대체 0건) 8. ☐ provenance asOf 일치(look-ahead 0) 9. ☐ DisagreementLedger 노출 10. ☐ qualityGateStatus 표시 11. ☐ 라이프사이클 인지(young/mature/금융/cyclical leaf 분기) 12. ☐ 면책+금지어 가드 통과.

"전문가급" = **방법 엄밀함**(독점 데이터 아님). 컨센서스 부재(감사 확정) → "방법 투명성" 라벨이 정직. AI 3-티어(advanced/onDevice/deterministic)는 *기능 가용성*(어디서 도나)이지 과금 아님 — 공개 GH Pages=결정론 reverseDCF+3시나리오 토글(WebGPU 열화·숨김 금지), 로컬=multiStageDcf·thesisKillChain 전체·특수경로.

---

## 7. 정직·법적 불가침선 (가드 — 문구·UI·테스트)

**한 줄:** dartlab은 *impersonal·일반·재현·반증가능 분석 도구*(Publisher's Exclusion, Lowe v. SEC)로 남는다. 개별 재무상황 *적응*·점 추천 *발행*·자금 *운용* 순간 Advisers Act/FINRA 본체로 넘어간다.

| 안전 | 위험(가드 차단) |
|---|---|
| 회사 단위 조건부 시나리오 | 사용자 포트폴리오 맞춤 최적화 |
| 사용자가 가정 토글 | dartlab이 "이 가정 쓰라" 개인화 추천 |
| reverseDCF 함의 노출 | 단일 target + Buy/Hold/Sell rating, `signal` 노출 |
| 확률가중 bear/base/bull | "예상 수익률 N%" 약속 |

가드 구현(테스트 강제): ① **금지어 lint 신설**(매수/매도/추천/목표가단일점/예상수익률/검증된전략/Buy·Hold·Sell/underpriced·overpriced/"당신의 상황에서"→발간 차단) ② 대체 어휘 강제("조건부 perShare 범위"/"현재가 함의"/"시나리오 분석"/"반증 조건") ③ 면책 자동삽입 확장(`publisher.py:169` 기존 "투자 권유 아님"에 "hypothetical scenario analysis, not a forecast" + criteria·assumptions·falsifier 명시 = SEC Marketing Rule·FINRA 2210 hypothetical performance 충족) ④ FINRA 2241 형식 차용(rating 미발행이라 본체 비적용, 형식만: reasonable basis=panel ref+ledger / valuation method 명시=어느 leaf / risks=falsifierLedger). 네 규제가 *모두* 같은 것(criteria/assumptions 노출+risk 명시+reasonable basis)을 요구 → 가정-노출이 곧 규제 안전 + 전문가급.

---

## 8. 재현성 (적대검증 F-1)

- 같은 입력→같은 출력. 순수함수 DAG+메모이제이션(01 §0). RunSpec(03 §4.1)=scenario+drivers+asOf+vintage+fee/slippage.
- **선결 kill-test: 전역 `random.seed` 2곳(`pricetarget.py:278`·`_simMonteCarlo.py:145`)→`numpy.random.default_rng(seed)` 주입**(Phase 0).
- **★브라우저 패리티 정정(F-1):** numpy Generator(PCG64)와 JS RNG는 다른 알고리즘 → TS 패리티 자동 보장 *안 됨*. **결정론 path는 엔진이 사전계산, 브라우저는 *드러내기만*(RNG 미사용)** — 05 Play 전제와 일관. **AI lens(`.ai` 슬롯)는 비결정론 → fact 미승격·재현성 보증 밖(hypothesis 라벨), 보고서 면책에 명시.**

---

## 9. 거처·계약 (새 verb 0)

leaf=L2 SSOT 불변(`analysis/valuation/*`·`analysis/financial/calc*`·`buildProforma`·`computeCompanyWacc`). simulate(L2.5)가 `calc*` 래퍼 호출, story(L3)가 렌더. 가치평가=`simulate(mode="whatif")`의 한 읽기 방식, 새 톱레벨 verb 없음. 신설 총량(좁음): builders 렌더러 2개 + story `type="simulation"` + 금지어 lint 1개 + landing `ReportDock` 셸(valuation 단일 모드). _attempts 졸업 후 본진. 덕지덕지 금지(reverseDCF·fairValueRange·thesisKillChain·publisher 재발명 금지 — 조립).

---

## 10. 신설 vs 재사용 (정직)

**재사용(~80%):** DCF 5변종·역DCF·RIM·실물옵션·SOTP·5시나리오 MC·`computePriceTarget`(§5.6 선구현)·`buildProforma`·story 조립기 11타입+100+렌더러+업종 템플릿+6막·publisher→blog 가동·thesisKillChain·`judgeQuarter`+OutcomeLog(Brier 기반).
**신설:** `simulate/` 묶음(0줄)·`ai/tools/lens.py`·렌더러 2개·금지어 lint·ReportDock 셸·역DCF 보고서 전면 승격. **불가(후속):** 거시 미래경로 투영(AR/VAR, `macro/`에 부재 — preset 의존).

---

## 11. ★우선순위 게이팅 (적대검증 C-1 — 가장 중요)

`src/dartlab/simulate/`·`dartlab.simulate` verb·`tests/_attempts/scenarioSimulator/` 전부 **현재 0줄**. 보고서 발간을 코어보다 먼저 짓는 것은 우선순위 역전. 순서 강제:

1. **Phase 0:** MC seed kill-test(`mcSeedReproKill.py`, 전역 random→numpy Generator).
2. **simulate 코어 _attempts 졸업**(01 §15) — DriverSheet·DriverRegistry·`SimulationResult` 실측 확정.
3. **그 후에야** 본 08의 보고서 모드(렌더러 2개·14키 ref 치환·ReportDock·lint)를 착수.

07 통합 로드맵상 시뮬레이션은 시퀀스 4번(지수→이벤트레일→백테스팅→시뮬). 본 08은 그 4번의 *발간 단면*이므로 **시뮬 코어와 동기**, 단독 선행 금지.

---

## PRD 반영 (이 문서 외 삽입)

- 01 §1 사실정정: reverseImplied 이미 배선(`registry.py:854`) + 2층 valuation SSOT(`analysis/financial/calc*`←`analysis/valuation/`) + `fullValuation` deprecated.
- 01 §4 외과추출: 신설 builders 2개 행 추가.
- 03 §9: "발간 게이트"(금지어 lint·면책 확장·FINRA 2241 형식·priceP50 build-fail).
- 00 §5: "Valuation Report = simulate 발간 단면" 1줄.
- README: 문서지도에 08 추가.
