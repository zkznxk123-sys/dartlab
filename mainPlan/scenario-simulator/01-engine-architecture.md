# 01. Engine Architecture

상태: PRD v0.4 (2026-06-14 구현 정합 — 결정론 코어 졸업[4노드 DAG·random.Random·proforma-FCFF·공개 verb] 반영, §3/§5/§6/§7/§12/§15/§16 코드 정본으로 정정. v0.2 본문 = 거처 3안 경합·경합 메커니즘 설계)
범위: 시뮬레이션 계산의 거처, AI 경합 메커니즘, 계층 경계, 기존 자산 매핑, 외과 추출 범위, 공개 계약

> **★구현 정합 표기 규약:** 본 문서는 *설계*(거처·경합·gate·lens)와 *구현*(4노드 결정론 코어)이 섞여 있다. 구현 완료 = `§5a`·`§6.1`(자료구조)·`§6.2`(단일 실행기). 미구현/후속 = `§5b`(mc/macro.beta/reverseDcf/credit/lens 노드)·`§6.3`(gate.py)·`§6.2`(dirty recompute)·DisagreementLedger(ledger.py)·Brier(recordForecast). **코드가 정본** — 충돌 시 코드 기준으로 읽는다.

---

## 0. 아키텍처 결론 (한 문장)

**시뮬레이션은 새 독립 묶음 `src/dartlab/simulate/`(L2.5)로 짓는다. 이 묶음은 ① 드라이버 노드/sheet 자료구조 ② 위상정렬 결정론 실행기 ③ 엣지 transfer(현 `_applyMacroShock` 적출) 셋만 소유하고, 그 외 모든 leaf 계산은 기존 L2(`buildProforma`·`calcMacroRegression` 등)를 한 줄도 옮기지 않고 호출(단일 SSOT)한다. AI는 노드의 `.det`(결정론)와 절대 섞이지 않는 평행 `.ai` 슬롯으로만 개입하며, AI 코드 절반은 `ai/tools/lens.py`에 물리 분리해 no-graph-regression을 구조적으로 준수한다.**

이것이 운영자의 두 불변 요구를 동시에 만족한다 — **(1) AI 없이도 결정론 미세 계산이 완결되고, (2) AI가 포함되면 결정론이 약한 곳을 근거로 메우고 빠진 driver를 더해 결론이 *나아진다*(보완).** 즉 목적은 **보완(더 나은 결론)**이고, **경합(평행 보존·사후 Brier 채점)은 그 보완이 진짜 개선인지 — 아니면 확신-오정렬 환각인지 — 를 증명하는 안전장치**다. 보완이 가치, 경합이 가드.

> 토론 경위: 거처 3안(A 제자리 리팩토링 / B 별도 묶음 / C L3 래퍼+외과추출)을 경합시켰다. 세 논증 모두 안C로 수렴했고(B 스탠스조차 "일관 정의하면 안C로 붕괴" 자인), 심판이 안C를 **L3-story 동거가 아니라 L2.5 독립 묶음**으로 정정했다. 적대 검증이 4개 필수 수정을 박았다(§10·§11·§12·§13). 코드가 강제한 결론이다.

---

## 1. 사실 정정 — 박제 (PRD가 거짓 전제를 들고 가지 않게)

토론 중 실측으로 정정된 사실. 이전 문서·논의의 오류를 바로잡는다.

1. **"simulation.py 1106줄 god module"은 거짓이다.** 실측: `simulation.py` = **244줄**. 이미 `_simScenario`(310)·`_simMonteCarlo`(416)·`_simHistorical`(366)·`_simTypes`(162)로 해체됨. "1106줄 한복판 대수술"은 존재하지 않는 적. 잔여 작업량은 가볍다.
2. **lazy-import proxy는 1곳이 아니라 4개 파일에 산재.** `_simScenario.py:35-38`·`_simMonteCarlo.py:36-40`·`_simHistorical.py:34-47` 가 `_applyMacroShock`/`_extractBaseMetrics`/`_extractVolatility`를 함수 내부 재import 프록시로 갖고, `simulation.py:240-244`의 `# noqa: E402` 끝단 re-export가 별개. `feedback_no_import_evasion` 위반이 4파일 산재.
3. **MC 정확성 버그 실재(재현성 문제와 별개).** `_simMonteCarlo.py:205` `simRev = meanRevPath[yr]*(1+revNoise)` — 루프가 `=`(덮어쓰기)라 horizon 노이즈가 **마지막 해만** 반영(누적 아님). 전역 시드 문제(line 145)와 분리해 다룬다.
4. **`getPresetScenarios` docstring은 이미 정직.** (이전 v0.1·일부 논의가 "거짓 정정 부채"로 올렸으나) 실 docstring은 DFAST/BOK + 자체 시나리오·정적 상수를 정직하게 명시. **진짜 부채는 `SECTOR_ELASTICITY`** — 실측 **35키(KR 23 + US 12, `synth/scenario.py:229` inline 하드코딩)**, "36업종"·"11업종"은 전부 오기. seed/CI 0 무출처 prior(folk-stat 위험)이고, `getElasticity` docstring이 "2010~2024 회귀 패널"·"`data/synth/sectorElasticity.json` 로드"를 단정한 것은 **provenance 날조**(실제 inline) — 정정 완료(`synth/scenario.py` docstring honest 라벨). DriverRegistry pooled-panel β로 대체(02 §2B.4-B).
5. **가치평가 leaf는 2층이다**(가치평가 융합 감사, 08 §3.1): `analysis/valuation/`(순수 수학 — `dcf.py`·`priceImplied.py`·`pricetarget.py`) ← `analysis/financial/valuation.py`+`_valuation*.py`(`calc*` 회사-바인딩 래퍼: series/shares/price fetch) ← story. **simulate는 `analysis/financial/`의 `calc*` 래퍼를 호출**(순수 leaf 직접 아님)해야 company 바인딩을 재구현하지 않는다. 중앙 적정주가 leaf = `calcDFV`(삼각검증), **`fullValuation`은 deprecated**(docstring "calcDFV 우선")라 fallback.
6. **역DCF·적정주가 범위는 이미 story에 배선·가동 중**: `reverseImpliedGrowth`+`computeGap`(`priceImplied.py:27,167`), `fairValueRange`+`verdict`(`dcf.py`), story `reverseImplied` 블록(`registry.py:854,890,914`). 갭은 "보고서 *전면* 승격"이지 배선 아님. **MC 전역시드 kill-test 대상은 2곳** — `_simMonteCarlo.py:145` + `pricetarget.py:278`. ⚠`credit/publisher.py`는 *미존재*(환각) — publisher 선례는 `story/publisher.py` 단독.
7. **scanMacroBeta firm-level t-stat은 *수학적으로 부재*다(설계 가정 정정 — 코드 그라운드).** 실측: `scan/macroBeta.py:113`이 연간 컬럼(`endswith("A")`)을 쓰고 `:115` ≥4개만 요구 → 성장률 obs = N−1 = 3개. `_quickOLS:343`이 k=4(절편+gdp+rate+fx) 적합 → 자유도 df = N−k = 3−4 = −1. `:339` 게이트는 `len(validY) >= 3`만 막아 df≤0에서도 적합이 통과한다. residual σ² = ssRes/(n−k)의 분모가 음수/0이라 SE_j = √(σ²·(XtX)⁻¹_jj)가 정의 불가 → **firm-level t-stat이 존재하지 않는다.** 02 §2B의 "회사 회귀 N~13이 정직" 서술은 *연간 데이터에선 한 단계 더 낙관*(실제 N=3)이다. 정정: firmRefine은 t-stat 게이트를 *계산 자체 금지*, leave-last-k point-forecast hitrate만 쓴다(02 §2B.9). account-struct '확신오정렬 > 정렬실패' 재현 차단.

---

## 2. 3분할 SSOT 규율 — 계산을 어디에 두나 (코드 위치로 못박음)

| 소유물 | 거처 | 내용 | 불가침 여부 |
|---|---|---|---|
| **그래프 구조 + 실행 + 엣지 transfer** | `src/dartlab/simulate/` (신규, L2.5) | ① `DriverNode`/`DriverSheet` 자료구조 ② 위상정렬 결정론 실행기 ③ `transfer.py::transferMacroToFundamentals`(적출된 `_applyMacroShock`) | 신규 — 본진 졸업 후 |
| **leaf 결정론 계산** | 기존 L2 제자리 | `buildProforma`(`_proformaCore.py`, 매출경로→IS/BS/CF cash plug 완전연결·bs_balanced·11구조비율), `calcMacroRegression`(`_signalsMacroSensitivity.py`, 다변량 OLS lag0/1/2·R²≥0.3) | **한 줄도 안 옮김** |
| **가정 상수·preset SSOT** | L1.5 `synth/scenario.py` 제자리 | `MacroScenario` preset, `SECTOR_ELASTICITY`, noise | 제자리 (transfer는 승격 안 함) |
| **AI lens (경합)** | `ai/tools/lens.py` (신규) | `annotateNodes`(모드 N)·`judgeSheet`(모드 J) 2함수 | 신규 — 본체 `agent.py` 불변 |

원칙: **`simulate/`는 leaf 계산 0줄(L2 SSOT 호출), 엣지 transfer만 자기 것.** transfer는 거시(macro 개념)와 펀더멘털(analysis 개념)을 잇는 계산이라 어느 L1.5 형제(scan/frame/synth/reference) 단독 책임이 아니므로 묶음이 소유한다(L1.5 승격 조건 불충족).

---

## 3. 거처: 왜 L2.5 독립 묶음인가 (L3-story 동거 기각, 신규 L2 기각, 별도 엔진 기각)

**왜 story 동급 L3가 아닌가:** story 헌법 = "순수 조합기, 자체 계산 0, 모든 숫자는 하위 엔진 ref". 그런데 `simulate`는 엣지 transfer **계산을 소유**한다. 둘을 한 L3에 두면 "조합만 하는 계층"에 계산이 섞여 `feedback_clean_module_tree` 위반의 씨앗이 된다. 따라서 story 동거 기각.

**왜 신규 L2가 아닌가:** L2 분석엔진(`test_l2_no_cross_import.py` `L2_PEERS=("analysis","credit","macro","quant","industry")`)은 **서로 import 금지**(CI 강제). 시뮬레이션은 forecast(analysis)+financial(analysis)+macro+quant+credit/distress를 **동시 결합**해야 하므로 L2에 두면 즉시 cross-import 차단.

**왜 L2.5 독립 묶음이 정답인가 (합법성 근거):** `simulate`는 `L2_PEERS` 5개에 **속하지 않는다.** 따라서 analysis·macro·quant를 동시에 호출해도 L2↔L2 가드가 자동 통과한다. import 방향(L0→L1→L1.5→L2→**L2.5 simulate**→L3 story→L4 ai)도 단방향 합법. story는 `simulate` 결과를 ref로 받아 서사만 조립(역할 분리 유지).

**정체성**: 안B(별도 엔진, leaf 소유)가 아니라 **안C(L2 leaf 호출 래퍼)**. leaf를 재구현하면 SSOT 분열(터미널 카드 proforma ≠ 시뮬 proforma)이므로, 묶음은 leaf를 호출만 한다.

**공개 계약 (verb 1개, public-contract-only) — ★구현 정합(2026-06-14):**

(1) **현재 구현 시그니처**(`simulate/entry.py`, 졸업 완료 `ac3905fd9`):
```python
dartlab.simulate(code: str, *, scenario="baseline", horizon=3, asOf=None) -> SimulationResult
Company.simulate(*, scenario="baseline", horizon=3, asOf=None) -> SimulationResult   # company.py:1990
```
- 첫 인자 = **`code: str`**(종목코드 "005930" 또는 한글명 "삼성전자") — Company 객체 아님. `dartlab.Company(code)`로 내부 해소.
- **KR 전용 가드**: `market != "KR"`(US ticker → EDGAR)면 `entry.py:111` `ValueError`. ⚠ US 프리셋(`PRESET_SCENARIOS_US` 5종)·elasticity(US 12키)는 `scenario.py`에 *실재*하나 (a) 이 가드 (b) `getPresetScenarios("KR")` 하드코딩(registry/run) (c) EDGAR sector 도달경로 부재로 *정책 차단* — US 해금 = 데이터 신설 아닌 market threading(09 §10.4 fatal④). 또한 가드는 `entry` 에만 — `Company.simulate`(`company.py:1990`)는 `runScenario(self)` 직접 호출이라 가드 우회(실 KR-only 강제 = `buildSnapshot` market threading 부재, 09 §10.4 FIX 일관).
- `drivers`/`lens`/`mode` **인자 부재**: inert stub은 clutter라 *추가하지 않고* 후속 단계로 deferred(entry.py docstring AntiPatterns "drivers/lens/mode 인자를 기대 — 현재 결정론 subset만"). 따라서 현 verb는 **결정론 경로 단독**(lens 분기 없음).
- 결과는 항상 ref + per-node 품질 상태(`NodeAudit.status` ok/partial) + provenance(asOf·latestAsOf) 동반. honest-gap: 결손은 None·partial(0 대체 금지).
- **★silent 값-대체 표면화 계약(honest-gap 확장 — ★졸업 AC, 현재 미배선; run.warnings 는 base-revenue/shares 2건만 실측):** honest-gap 교리는 None 결손뿐 아니라 *값 대체*에도 적용한다 — `buildSnapshot`이 `sectorKey` 부재로 `DEFAULT_ELASTICITY`를, `sectorParams.discountRate` 부재로 `_DEFAULT_BASE_WACC`를 대체하면 (a) 해당 노드 provenance 에 `default:no-sector`/`default:no-wacc` 접두(provenance 문자열 재사용), (b) `run.warnings`에 `"sector elasticity defaulted — approximation(honest-gap)"` 추가(baseRevenue/shares 결손과 동일 채널). KR 신규상장사·US Phase A(09 §10.4 ① DEFAULT_ELASTICITY) 공통 — 09 §10.4 ①의 'US=DEFAULT 근사'를 docstring 넘어 `run.warnings`(사용자용)로 끌어올린다.

(2) **후속 단계 목표 시그니처**(미구현 — lens/Play/다중드라이버 phase):
```python
dartlab.simulate(code, *, scenario, drivers=None, lens=None, mode="whatif"|"replay"|"walkforward", horizon, asOf) -> SimulationResult
```
- `lens=None` → 순수 결정론(불변1). `lens="annotate"|"judge"` → AI 경합 on(불변2).
- verb 후보 평가: `simulate`(동사 1개, scan/compare 결, mode 흡수) 채택. `scenario`(명사형, `macro.scenarios`/`ScenarioOverlay`/`ScenarioCompareN` 충돌) 기각.
- ⚠ EngineCall/MCP 등록: `__init__.py` 라이브 capability 카탈로그(=`__all__`+Company public methods)로 **자동 등록됨**(별도 allowlist 파일 0). AI 3-티어 공개계약이 verb 호출에 의존하므로 등록 상태는 07에서 검증.

---

## 4. 외과 추출 범위 + 불가침 경계

**적출(이사) — 단 1개:**
- `_applyMacroShock`(`simulation.py:180-235`, 선형 1차식 `rev×(1+βgdp·gdp+βfx·fxΔ)`+마진 가산+wacc 0.5) → `simulate/transfer.py::transferMacroToFundamentals` 순수함수로 **이사(복제 아님, 원위치 삭제)**. 시뮬 전용(`_simScenario`·`_simMonteCarlo`만 호출)이라 SSOT 분열 표면 0.
- **부수효과 = cycle 해소**: 적출하면 `_simScenario.py`·`_simMonteCarlo.py`·`_simHistorical.py`의 함수내부 재import 프록시(§1.2)가 사라진다. `no_import_evasion` 부채를 갚으면서 transfer 노출을 얻는 1석2조.

**삭제:**
- `scenarioSim.py`의 simulation↔proforma 수동 봉합(`createSimulation:380` buildProforma 직접 호출 + `_scenarioDCF` 손배선). DAG 엣지가 봉합을 흡수하면 자연 소멸(`feedback_always_check_clutter`).

**불가침 (한 줄도 안 건드림):**
- `buildProforma`/`_proformaCore.py` 전체 — 터미널·compare·scan 카드가 의존하는 leaf SSOT.
- `calcMacroRegression`/`_signalsMacroSensitivity.py` — 이미 addressable fine-grained primitive.
- `simulateScenario`/`monteCarloForecast`/`stressTest`/`createSimulation` **공개 시그니처** — BC re-export(`simulation.py`에서 검증된 사내 관용)로 보존. 묶음 성숙 후 *내부적으로* 묶음에 위임하되 반환 형태 byte-identical.

---

## 5. 노드 입자도 규율 — 3중-좌표 SSOT, 차원폭발 차단

**노드 키 = (driverId, scenarioId, periodKey) 3중 좌표.** revenuePath는 *시나리오당 1노드*(연도/분기당 1노드가 아님). 연도·분기 축은 `NodeValue.vector`(tuple)로 노드 *내부*가 흡수한다.

- 노드 수 = **O(드라이버종류 × 시나리오)**. *설계 상한* ≈ 8 driver × 3 branch ≈ 24 노드(모든 후속 노드 포함 시); **현 구현은 시나리오당 4노드**(§5a) — 차원폭발 차단 원리는 동일(연도·분기는 vector 흡수). **O(드라이버 × 시나리오 × 연도 × 분기)**(폭발)가 *아님*.
- 근거(실측): leaf 자체가 시계열을 반환(`buildProforma`→연도별 ProFormaYear[], `monteCarloForecast`→분기 백분위, `_applyMacroShock`→연도 loop). 노드는 leaf를 1회 호출해 vector를 받는 **얇은 어댑터**. 연도를 노드로 쪼개면 leaf를 연도별 N회 호출 = OOM(§13 'leaf N회 금지').
- 단면 노드(periodKey="2025Q1")는 Play가 *특정 분기에서* 단면 비교(신용 등급·BS 항등식)가 필요할 때만 vector를 slice해 *파생*(저장 아님).

**노드다:** 주소(driverId) 가질 가치 + AI 의견 가능 + Brier 사후채점 단위. **노드 아니다:** ① leaf 내부 중간(cash plug 3회 이자수렴은 buildProforma 내부 — 쪼개기 금지) ② `_baseMetrics`(입력 준비) ③ BRIEF/WORK식 고정단계(금지).

### §5a 구현 완료 코어 — 4노드 (`registry.py` 와이어링, `096e84c43` 졸업)

`buildScenarioSheet`가 와이어링하는 결정론 DAG는 정확히 4노드: `macro.path → rev.path → proforma → dcf`. 모두 `DRIVER_MACRO`/`DRIVER_REV`/`DRIVER_PROFORMA`/`DRIVER_DCF` 상수로 등록.

| 노드 (driverId) | fn (registry) | det provenance (실측) | vector 차원 | AI 의견 |
|---|---|---|---|---|
| `macro.path` | `_fnMacroPath` → `getPresetScenarios("KR")` 프리셋 | `preset:{scenarioId}` | 연도(horizon) | △(후속) |
| `rev.path` | `_fnRevPath` → `transferRevenuePath`(엣지, 자기 소유 산수) | `transfer:rev*(1+bgdp*gdp+bfx*fxDelta),...`(실측, `registry.py:319`) †elasticity=curated prior seed/CI 0 — provenance 라벨·warnings 는 **졸업 AC(현재 미배선)**, 아래 footnote | 연도(horizon) | O(후속) |
| `proforma` | `_fnProforma` → L2 leaf `buildProforma`(불가침) | `proforma:cashplug,wacc=..,years=..` | 연도별 FCF | △(후속) |
| `dcf` | `_fnDcf` → **proforma-FCFF 직접할인**(Gordon TV, `calcDFV` 회피) | `dcf:fcff,wacc=..,g=..` | perShare + EV(1-tuple) | △(후속) |

> **★dcf 노드 = proforma-FCFF, `calcDFV` 회피(09 P3·08 §2.3 정합):** `_fnDcf`는 proforma 노드의 per-year FCF 벡터를 WACC로 직접 할인 + Gordon TV(섹터 terminalGrowth 캡) + netDebt 차감 + shares 분배로 주당가치를 낸다. `calcDFV`/`multiStageDcf`를 **호출하지 않는다** — calcDFV는 자체 내부 proforma를 다시 돌려 *이 시나리오의* proforma FCF를 무시하므로 scenario-coherence가 깨진다(외부 proforma 무시). 정적 가치평가용 calcDFV(08 §1 ⑤ 표)와 시나리오 dcf 노드는 *중복 아닌 2 정당 경로*다.

> **★rev.path elasticity provenance 정직(졸업 AC):** `rev.path` 노드의 elasticity 계수는 curated `SECTOR_ELASTICITY` priors(`synth/scenario.py:229`, 35키, OOS provenance 없음·seed/CI 0)다. DriverRegistry pooled-β(02 §2B.4-B)가 pooled-OOS partial-R² 를 공급하기 *전까지* `SimulationResult.warnings` 가 `"elasticity_prior_unvalidated"` 를 싣는다(`run.py` warnings 튜플의 base-revenue/shares honest-gap 동일 패턴) — 결과 표면에서 magic-constant fan-out 이 *침묵*하지 않게.

### §5b 후속 단계 노드 — 미구현 가설 (4노드 코어에 미포함)

아래는 *설계 가설*이며 `simulate/` DAG에 **아직 와이어링되지 않았다.** 졸업 데모 byte-패리티로 위상 확정 후 추가.

| 노드 (driverId) | fn → leaf (후속) | 상태 | 비고 |
|---|---|---|---|
| `macro.gdp.beta` | `calcMacroRegression`/pooled-panel | 미구현 | OLS R² provenance 자체가 아직 없음(02 §2B pooled-β SSOT 선결) |
| `mc.distribution` | `monteCarloForecast` (legacy, `random.Random`) | 미구현 | ✅ OQ8 결정: `deps=(proformaId,)` — proforma 노드의 **FCF 벡터(`NodeValue.vector`)** 소비(leaf 아님), mean path=proformaNv.vector(단일 SSOT)+noise σ=snapshot elasticity, 벡터화(buildProforma 재호출 0=OOM 없음, `_simMonteCarlo.py:203-211` cumprod). **frozenInputs 확장 불필요**(macro 분포 파라미터 아닌 proforma vector 소비 → '직접계산 vs deps' 이분법 해소). byte-parity 제외, 분포통계 ±ε(04 §5 OQ8) |
| `reverseDcf` | `reverseImpliedGrowth`+`computeGap` | 미구현 | story에 배선 있으나 simulate/ 노드 미등록 |
| `credit.rating` / `ai.lens` | `synth.distress` / `ai/tools/lens.py` | 미구현 | 신용=09 §4 solvency 뷰, lens=§6.4 후속. 07 로드맵에 phase 미배정 |

**⚠ 졸업 데모(게이트 ②④):** §5b 노드는 가설. 삼성/카카오/현대 실측으로 (a) macro.gdp.beta 단일/분기별 (b) mc.distribution 위상(OQ8) — byte-패리티로 확정(04 §5).

**★NodeValue 계약 갭 + frozenInputs 형상 핀(구현 정직):** 현 `NodeValue`(sheet.py:50-56, 7필드)는 frozenInputs를 노출하지 않고, `evaluateSheet`(sheet.py:361-363)는 fn 반환 7-튜플의 frozenInputs를 `computeInputsHash` 에만 쓰고 *저장 안 한다*. 그 결과 *두 개의 recompute 우회*가 실재 — `registry._macroFrozen`(rev 노드가 rate/FX 경로 프리셋 재유도)·`run._marginPathFromSnapshot`(marginPath 같은 transfer 재계산). 둘 다 "감사 노드는 권위 provenance/refs/hash 그대로, 표시 숫자만 byte-동일 재산출"하는 정직 패턴이나 우회다. **★형상 핀(09 §10.3 T-A1 미결 해소): NodeValue에 frozenInputs 추가 시 = RAW pre-normalize 수치값 저장(소비 전용)** + 해시는 `evaluateSheet`가 `_normalize(frozenInputs)`로 *별도* 산출(해시 전용) — 한 필드 두 파생, 경쟁 두 타입 아님. `_freezeInputs`(09 T-A1의 `tuple((k,_normalize(v))...)`)는 해시 경로 한정. **이 추가의 목적 = *우회 삭제*(엔진트랙)지 mc.distribution 아니다**(mc 는 proforma vector 소비라 frozenInputs 불필요 — 위 §5b 표·OQ8). 두 우회는 종전 PRD 미기재 — 본 절이 정직 기록.

**명명(no-graph-regression):** `DriverNode`/`DriverSheet`. `*Graph`/`*Loop`/`*Kernel`/`*Dag` 금지.

**모듈 (실측):**
- **구현 완료**: `simulate/{sheet,transfer,registry,run,entry,__init__}.py`.
  - `sheet.py` = NodeValue/DriverNode/DriverSheet + `computeInputsHash` + `buildOrder`(Kahn) + `evaluateSheet`(단일 결정론 실행기).
  - `registry.py` = `buildSnapshot`(read-once) + 4 노드 fn + `buildScenarioSheet`.
  - `run.py` = `runScenario`(내부 end-to-end) + `SimulationResult` + `NodeAudit`.
  - `entry.py` = 공개 verb `dartlab.simulate`(thin wrapper).
- **후속 단계(미생성)**: `simulate/{gate,ledger,admission}.py`. (`eval.py`는 신설하지 않고 실행기를 `sheet.py`로 통합 — 아래 §6.2.)

---

## 6. AI 경합 메커니즘 + 위상정렬 실행기 — det/ai 평행, 블렌딩 금지

### 6.1 자료구조 (simulate/sheet.py)

```python
@dataclass(frozen=True)
class NodeValue:
    value: float | None              # 대표 스칼라(시계열이면 vector 끝값). None = 데이터 부재(block).
    vector: tuple[float | None, ...] | None   # ★원소별 None 허용 — horizon 중간 분기 결손 시 0 대체 금지(missing!=0 불변). Play fan-band가 None 구간을 끊어 그림.
    provenance: str                  # "ols:R²=0.41,gdp,fx" | "pooled:sector,fe" | "preset:baseline" | "elasticity:반도체" | "ai-hypothesis"
    refs: tuple[str, ...]            # 근거 ref 주소(grounding check 대상). det=leaf ref, ai=AI 인용 ref.
    inputsHash: str                  # 부모 inputsHash들 + fn ref + 동결 input 정규화의 blake2b 16hex
    asOf: str                        # 사용 데이터 vintage
    latestAsOf: str                  # 최신 가용 vintage(staleness 판정)

@dataclass(frozen=True)
class DriverNode:                       # ★실제 필드 순서(sheet.py) = deps/fn 이 det/ai 보다 앞
    nodeId: str                          # f"{driverId}@{scenarioId}#{periodKey}" — 3중 좌표 SSOT
    driverId: str                        # "macro.path" / "rev.path" / "proforma" / "dcf"
    scenarioId: str                      # "baseline" / "adverse" / ...
    periodKey: str                       # "all"=시계열 노드 / (후속) "2025Q1"=단면
    deps: tuple[str, ...]                # 상류 nodeId
    fn: str                              # registry 디스패치 키 (예 "simulate.dcf")
    det: NodeValue | None = None         # L2 leaf 출력. 실행기가 항상 채움(lens 무관).
    ai: NodeValue | None = None          # AI 의견. 기본 None. (후속) lens on + fork/gap 노드만.
```
⚠ frozen dataclass라 선언 순서 = 생성자 순서다. 이전 문서가 `det`/`ai`를 `periodKey` 바로 뒤에 둔 것은 코드와 어긋났다 — 실제로는 `deps`/`fn`이 먼저고 `det`/`ai`가 마지막(기본값 None).

`inputsHash = blake2b(sorted([parent.inputsHash …], node.fn, _normalize(frozenInputs)))`. `_normalize` = float round(1e-9) 정규화(부동소수 비결정성·TS 패리티 차단). **메모이제이션 키 SSOT.**

### 6.2 위상정렬 실행기 — 불변1을 *구조적으로* 증명 (simulate/sheet.py) — ★구현 정합

**구현 완료**(`sheet.py`, eval.py 신설 안 함): 실행기는 `evaluateSheet` **단일 함수**다. `lens` 파라미터·`_evalDet`/`_evalWithLens` 물리 분리·`_dirtyClosure`는 **미구현**(lens 단계 계획). 현재 함수 2개:
```python
def buildOrder(sheet) -> tuple[str, ...]:   # Kahn 위상정렬. deps cycle/누락 → ValueError. (캐시는 미구현 — 매 호출 재계산)
def evaluateSheet(sheet) -> dict[str, NodeValue]:   # topo 순서로 각 노드 registry fn 호출 → NodeValue 포장 → det 기록.
```
- **불변1 증명(현재, 더 강함)**: `evaluateSheet` 본문에 `lens`/AI 심볼이 *문법적으로 전혀 없다* → "deterministic without AI"가 런타임 if가 아니라 **AI 진입점의 물리 부재**로 보장(`sheet.py` 모듈 상단 docstring 박제). lens 파라미터 자체가 없으므로 `lens=None` 분기조차 불필요. 단일 함수가 곧 결정론 경로.
- **후속 단계(미구현)**: lens 도입 시 `_evalWithLens`(det 결과 위에 fork/gap 노드만 ai 주입) + `ai/tools/lens.py` 신설. 이때 lens 경로 물리 부재를 유지하려면 `_evalDet`/`_evalWithLens` 분리 또는 `assert lens is not None` 박제(§6.4).
- **★증분 dirty recompute = 미구현(§13b-1, Play if토글 1차 엔진 — 후속)**: 현 `evaluateSheet`는 dirty/memo 파라미터가 없어 **항상 전체 sheet를 처음부터 평가**한다. inputsHash는 모든 노드에 계산되어 *재현·향후 메모이제이션의 키*로 이미 실재하나, sub-DAG만 재계산하는 `_dirtyClosure`는 Play if-토글 단계에서 신설 예정. (설계: dirty 노드의 transitive descendants만 deps 역방향 BFS로 수집 → 부모 inputsHash 불변이면 memo 히트 → leaf 재호출 0. 순수함수라 안전.)

### 6.3 결정론 gate 4분기 (simulate/gate.py 순수함수) — ★미구현(후속, AI lens 단계 신설)

> **★현재 구현엔 gate 없음.** `gate.py`는 `simulate/`에 *존재하지 않는다*(`gateUsable`/`_isStrongDet`/`groundingCheck`/`DisagreementLedger` 미구현). 현 4노드 결정론 코어는 강도 분류 없이 모두 deterministic으로 처리되고(provenance = `preset:`/`transfer:`/`proforma:`/`dcf:fcff`), 품질은 `run._audit`이 `det.value is None ? "partial" : "ok"`로만 판정한다(honest-gap). 아래 설계는 **AI lens(`.ai` 슬롯) 도입 시 신설**할 후속 단계다 — gate의 *근거*(SimulationResult→gate source)가 아직 배선되지 않았으므로 03 §9.3 게이트 매트릭스·08 §11 발간 게이팅의 "gate 기계강제"도 그때까지 설계 상태다.

```python
def gateUsable(node, snapshot) -> Literal["det","ai","fork","block"]:
    if node.det is None or node.det.value is None: return "block"   # 데이터 부재(0 대체 금지)
    strong = _isStrongDet(node.det.provenance)
    if node.ai is None: return "det"
    gap = _disagreement(node.det, node.ai)
    if strong: return "fork" if gap > FORK_THR else "det"   # 강한 det는 AI 못 이김
    return "ai" if groundingCheck(node.ai, snapshot) else "fork"   # 약한 det → grounded AI로 통째 교체
```

**`_isStrongDet` — ★in-sample folk-stat 가드(requiredFix):** provenance `ols:R²≥0.3` 단독 화이트리스트는 **확신오정렬을 만든다**. `calcMacroRegression`은 nObs~36 분기에 gdp/rate/fx × lag0/1/2(≤9 후보)에서 best-R²를 고르는 *in-sample 적합* → 스퓨리어스 고-R²가 약한 driver를 '강함→AI 못 이김'으로 잠가 fork를 억제. 강함 판정은 다음 중 **최소 하나 강제**: adjusted-R² / held-out OOS R² / 관측치 대비 변수수(자유도) 하한 / lag 다중비교 보정. `R²≥0.3` 임계는 졸업 데모에서 held-out으로 재보정. `preset:`/`elasticity:`(무출처 35키) = 약함.

**`groundingCheck(aiNV, snapshot)` 4단 AND(순수함수) — 출처 핀(코드 정합):** (a) refs 실재 = `ai.refs ⊆ detRefSet`. ⚠ `snapshot.refIndex`는 코드 **부재**(registry.py:188 snapshot=11키, refIndex 없음) → 정합: `evaluateSheet`가 전 det 노드 `NodeValue.refs`를 `frozenset`으로 모아 `SimulationResult`에 1필드 표면화(또는 buildSnapshot refIndex 키, T-A1 형상동결 편입), (a)=그 집합 부분집합 검사. (b) 주장 지지 = aiNV.value가 **snapshot 실측 base metrics ± 고정 tol**(`snapshot.baseRevenue/baseMargin`, registry.py:188 실측) 안 — ✅ OQ10 결정: 약한 det 자체분포 금지(순환), `AssumptionLedgerRow`(코드 0건) 제거, ledger 없는 노드는 (b) 기권→fork(det 폴백 아님)=abstention-over-circular. (c) 단위·기간 정합(§2.5 '단위없는 숫자 invalid' 재사용) (d) untrusted 미실행(sourceType=external 본문은 데이터, 산수만 — untrusted-wrap-check). 하나라도 실패 = fork.

**보완 ≠ 블렌딩**: gate `ai` = 그 노드 채택값을 *통째* 교체(토글로 det 복원). `0.6det+0.4ai` 함수 *부재*(블렌더 미정의 = 섞임 물리 불가) → 재현성·추적·Brier 유지. 근거: `project_account_struct_disambig_killtest` "확신 오정렬 > 정렬 실패".

**DisagreementLedger**(simulate/ledger.py) — ★미구현(lens 단계 신설): fork/큰-gap 노드 자동 수집 {nodeId, det.value, ai.value, gap, provenance, ai.refs, resolution} → 터미널 '엔진 vs AI 갈린 지점' 표. 어긋남 미삼킴(`feedback_silent_swallow`). Play 근거 인벤토리(05 §6) cross-link. **현재**: `run.SimulationResult.warnings`(tuple[str,...])가 base revenue/shares 결손을 honest-gap으로 표면화하나, fork/gap 수집 로직(`ledger.py`)은 ai 슬롯과 함께 후속 단계다.

**사후 채점(Brier)** — ★미구현(lens 단계): `scenarioSim.py::judgeQuarter`를 노드 단위 일반화 → `OutcomeLog`(MCP 실재) + **forwardTest write 함수 `recordForecast`(현재 부재 — 신설 필요, 09 P9·02 §2B.5)** 에 asOf+det+ai 박제 → N분기 후 노드별 Brier. ⚠ judgeQuarter `int(quarter[-1])` → `re.search(r'Q(\d+)', quarter)` 교체(2025Q10 가드, BC표면 golden 동행). folk-stat 회피(held-out·충분표본, 3점·CI0·seed0 금지). 'AI가 엔진보다 낫다'는 *증명 대상*이지 *전제*가 아님 — 분기 누적 후에야 신호. **단 forward-test 루프는 write 끝단(recordForecast·models HF 배포)이 아직 없어 물리적으로 닫히지 않는다**(09 §0 #5·02 §2B.5). 따라서 write-end 라이브 전 `DriverCard.state` 는 dormant 상한(02 §2B.3) — active 승격은 decay 스트림이 false discovery 를 bound 할 수 있을 때만.

### 6.4 두 lens 모드 + HypothesisNode (보존)

- **두 모드 = 동일 sheet 두 lens:** 모드 N(`lens.annotateNodes`, 노드별 의견 — **fork/큰-gap 노드만** 호출, 비용·지연·환각 관리) + 모드 J(`lens.judgeSheet`, 전체 sheet 읽고 서사·결론만, 노드 불변).
- **HypothesisNode(AI 제안, 기본 off):** AI가 새 노드/가정 제안 시 `enabled=False` 격리. 실행기가 무시(결정론 보존). 사용자 on 시 confidence 부여 + `fork` 강제(곱하지 않음). transferFn은 사용자 눈검 가능한 명시 산수(AI가 식에 "이전 지시 무시" 심어도 산수만 실행 — `untrusted-wrap-check`).

---

## 7. 두 불변 요구 — 명시 입증

- **불변1 (AI 없이 결정론):** `evaluateSheet(sheet)`는 AI 호출 0(lens 파라미터 자체가 없음). 모든 노드 `det`=L2 leaf 순수함수 출력 → 같은 회사·시나리오·asOf면 노드별 `inputsHash` byte-identical(현 경로에 **난수 0** — MC 노드 미구현). **증명 = 실행기 경로에 AI 토큰·RNG가 들어갈 코드 지점이 물리적으로 없음.** ⚠ `sheetSeed`/`random.Random(blake2b(...))`는 *후속* mc.distribution 노드 전제 — 현 결정론 코어는 seed 없이도 순수함수라 재현 보장(레거시 MC의 `random.Random(seed)`는 별개 경로, §12).
- **불변2 (AI 경합, 통제):** AI는 노드 `.ai` 슬롯(모드 N) 또는 `judgeSheet`(모드 J) 두 통제 표면으로만 진입. `.det` 못 바꾸고, gate는 순수함수, 블렌더 부재로 섞임 불가, 어긋남은 ledger 보존·Brier 사후채점. **증명 = AI 진입이 입력/메타판단으로만 제한, 평가 제어흐름 미지배(no-graph-regression 선).**

---

## 8. 계층 단방향 표 (v0.2 갱신)

| 계층 | 위치 | 시뮬레이션에서의 역할 | 금지 |
|---|---|---|---|
| L0 core | `core/` | ref·date·schema primitive | 외부 provider 직접 호출 |
| L1 gather/providers | `gather/` | source 관측(가격·뉴스·거시·지수·customs) | 분석 결론 생성 |
| L1.5 synth/scenario | `synth/scenario.py` | preset·elasticity 상수 SSOT | 형제(scan/frame/reference) import |
| L2 analysis/financial | `_proformaCore.py`·`_signalsMacroSensitivity.py` | leaf 결정론 계산(proforma·OLS beta) SSOT | L2 형제 import |
| L2 macro/quant/credit | macro·quant·credit/distress | 거시 시그널·beta·생존 leaf | L2 형제 import |
| **L2.5 simulate (신규)** | `src/dartlab/simulate/` | **드라이버 sheet·실행기·엣지 transfer 소유, L2 leaf 호출 결합** | leaf 재구현·panel 변형. ★역방향(analysis/macro/quant→simulate) 차단 = `test_import_direction.py` downward-only(LIVE pytest 정본, `LAYER_OF["simulate"]=2.5`:26) + importlinter forbidden(미배선·09 §6② Phase1 신설예정, continue-on-error 가시화 only) |
| L3 story | `story/` | `simulate` 결과 ref → 서사 조립 | 자체 숫자 계산 |
| L4 ai/mcp | `ai/tools/lens.py` | 노드 의견(annotate)·sheet 판단(judge) | `agent.py` 본체 오염·고정노드 |

---

## 9. 거시경로 예측 부재 — 정직 처리

**실측 확정:** `macro/forecast/`에 `gdpNowcast`(Kalman 현재국면)·`walkForwardBacktest`만, **미래 경로 투영 함수 0건**(`def project*/path*/forecast*` grep 0). 시뮬은 `synth/scenario.py`의 사람이 박은 `PRESET_SCENARIOS` 상수에 의존.

**처리:** `macro.path` 노드는 **자리만 만들고 preset 상수를 노드 입력으로 승격**하는 데서 멈춘다. DAG가 그 자리를 *비워둘 수 있게* 설계하는 것까지가 이번 약속. 진짜 거시경로 예측(변수 미래 투영 AR/VAR)은 **별도 능력·별도 `_attempts` 라운드** — driver 골격이 선 *뒤에* 새 leaf를 꽂는다. 한 번에 다 하겠다는 약속 거부.

---

## 10. 회귀 표면 — 정직 (적대검증 수정 1)

⚠ "코드 소비처 0건"은 협소 검증의 거짓 안심이었다. 실측 정정:

1. **코드 소비처는 대부분 `analysis/` 내부**(`valuation/{pricetarget,analyst}.py`, `financial/_registryAxesB.py`·`_forecastCalcsScenarios.py`, `forecast/` 형제). macro/quant/credit/story 직접 코드 소비처 0건 — 회귀 표면은 좁다.
2. **단, 숨은 표면 2건:**
   - `analysis/valuation/analyst.py:322-347` = `__getattr__` 기반 **lazy re-export 레지스트리**가 simulateScenario/simulateAllScenarios/monteCarloForecast/stressTest 4개를 **모듈경로 문자열**에 강결합. BC 위임 commit의 **명시 갱신 대상**으로 박는다(누락 시 getattr 호출 시점 silent 깨짐).
   - **MCP "0건"은 거짓.** `ai/tools/engineCall.py`는 `loadCapabilities()` 카탈로그 기반 **동적 dispatch**(`getattr(dartlab, method)`). 시뮬 함수가 capability 카탈로그(skills/*.json)에 등재되면 MCP 표면에 노출. "카탈로그 경유 1표면"으로 정직 기록, 실측 후 회귀 표면 포함.

**회귀 0 전략 (3중):**
1. **born-clean 병행 신설.** `simulate/`는 소비처 0에서 출발, 기존 `createSimulation`/`simulation.py` 경로를 건드리지 않고 신설 → 기존 소비처 자동 무회귀.
2. **byte-identical golden test 선행** (단 §12 분리 적용 — MC 제외). 삼성·카카오 등 2~3사 소비처별 스냅샷(`feedback_ui_rules`: 정량 PASS가 디테일 못 봄).
3. **BC 위임은 묶음 성숙 후 별도 commit** + `analyst.py` 레지스트리 4엔트리 + 카탈로그 갱신 동반.

---

## 11. no-graph-regression 준수 — 구조적 + 키워드 (적대검증 수정 2)

- **구조적:** `DriverNode`/`DriverSheet`/실행기는 `simulate/`(ai/ 밖, 순수 자료구조)에 산다 — 가드 `checkAgentBoundary.py`의 `*Loop/*Graph/*Kernel` AST·5패스 고정노드 검사는 `ai/`만 스캔하므로 면제. AI 진입은 `ai/tools/lens.py` 새 도구 1종으로만, `agent.py` 본체 불변. AI는 그래프를 *돌리지* 않고, 그래프가 AI 의견을 *입력으로 먹는다*.
- **⚠ 키워드(수정 2):** `_check_regression_keywords`(`checkAgentBoundary.py:158`)는 **`src/dartlab` 전체를 스캔**한다(ai/ 한정 아님). `_REGRESSION_KEYWORDS`에 한국어 `"회귀 가드"` 등이 있다. `simulate/`·`lens.py` docstring·주석에서 이 한국어 substring을 **명시 회피**한다(9섹션 docstring 영어 `AntiPatterns:`는 substring 무관 — 확인). 면제는 `feedback_no_graph_regression`/`DARTLAB_CHAT_SYSTEM` 포함 파일만이라 신규 파일은 면제 못 받음.

---

## 12. MC 재현성 — byte-parity 범위 명문화 (과대주장 분리, 적대검증 수정 3)

**byte-identical 헤드라인을 둘로 분리**(requiredFix):
- **(a) 결정론 경로 = 자명참(구현 실재)**: transfer + 4노드 실행기(`evaluateSheet`)는 순수 산술이라 byte-identical이 *정의상* 보장 — 현 코어엔 RNG가 없다. 골든 byte 테스트의 *강제 검증 범위 = `inputsHash` 정규화 규칙*(blake2b + float round, `computeInputsHash` 실재)에 한정 명문화. TS(V8) 포팅도 동일 정규화 규칙으로 패리티.
- **(b) MC 경로 = byte-parity 제외(후속 mc.distribution)**: Play fan-band 핵심인 레거시 MC는 stdlib `random.Random`(Mersenne)이 TS 표준 구현 부재 → byte-parity 불가. MC는 *분포통계 패리티(평균·분위 ±ε)만*. 05 §5 'TS=격자 lookup만, RNG 미사용'으로 회피. ⚠ 현 `simulate/` 코어엔 MC 노드 자체가 없다(§5b) — 이 절은 mc.distribution 합류 시 적용.

**전역시드 → 로컬 `random.Random(seed)`(2곳) — ✅ 완료(2026-06-14, 09 P1)**: `_simMonteCarlo.py:145` / `pricetarget.py:278`의 전역 `random.seed`/`random.gauss` → 로컬 `rng = random.Random(seed)` 인스턴스(`fe9e66c0a`). **★PCG64/numpy 아님** — stdlib `random.Random` 채택(동작 무변경=같은 seed→같은 Mersenne 시퀀스, **외부 의존성 0·pyodide 안전**, jumpable stream은 simulate 엔진이 필요할 때 재방문). 이전 문서의 "PCG64 노드-로컬"·`numpy.random.Generator(PCG64(...))`는 코드와 어긋난 stale 주장이다. ⚠ 이 수정은 *레거시 MC 경로* 한정 — 신생 `simulate/` 결정론 코어엔 MC 노드가 아예 없다(§5b). mc.distribution이 후속에 생기면 그 노드-로컬 RNG도 `random.Random(blake2b(...))`로 파생.

**:205 덮어쓰기 버그 — ✅ 수정 완료(09 P1)**: 이전 제안 `=`→`*=`는 **평균경로 소실로 기각**(`simRev=rev` 시작이면 `meanRevPath` 복리 곱이 빠져 거시충격 경로를 통째 소실). 채택 = **연도별 성장계수 cumprod**(`cumRevFactor *= (1+revNoise)` × mean path 보존 + margin random-walk, `ad112b171`). 정당화 순서 준수 = `test_horizon_widens_cone` kill-test가 옛 코드의 '호라이즌-끝 단년 노이즈' 버그를 먼저 *증명*(cv h1≈h3=cone 일정)한 뒤 전환(cone 확대). '기존은 버그'를 증명한 후에만 전환한 정공법.

- 순수함수 leaf는 전역 가변 상태를 못 만지므로 이 수정은 §6 leaf 순수함수 계약의 강제 따름.

**Phase 0 선결 kill-test — ✅ 완료**: 레거시 MC 전역시드 재현성·cone 버그를 로컬 RNG·cumprod 전환 *전에* 먼저 죽였다(Play 결정론·URL 공유·TS 패리티 척추). 신생 `simulate/` 코어는 RNG가 없어 이 kill-test 대상 밖.

---

## 13. OOM / 비용 상한 (적대검증 수정 4)

- **OOM 가드:** MC iterations=10000 × `_applyMacroShock` 호출(`_simMonteCarlo.py:197-213`)을 노드화하면 노드당 1만 회 → Polars/Company 객체 누적 OOM 위험(CLAUDE.md Company 1개 200~500MB). **MC 노드는 leaf 1회 호출 후 numpy 벡터화**(루프 내 buildProforma 재호출 금지). `buildProforma`/`panel` 재호출 상한 명시.
- **분기 동시 보유 상한:** `sim.branches[]`(baseline/adverse/severe 동시 재생) ≤ 3 + buildProforma 순차 호출(병렬 금지).
- **AI 비용:** 모드 N lens는 fork/gap 노드만 호출(전수 금지).

---

## 13b. 성능 아키텍처 — 심오하지만 빠르게 (운영자 핵심 요구)

깊이(전 노드 3-statement·MC·다중분기·수백 근거)와 속도(토글·Play·스크럽 즉답)를 5장치로 동시 달성. **안C의 순수함수 DAG가 이 모두의 전제**다.

1. **증분 재계산 (dirty recompute — 핵심, ★현재 미구현/후속):** 노드는 `inputsHash`(부모 노드값 결정론 해시)를 *이미* 갖는다(`computeInputsHash` 실재) → if 토글 1개 변경 시 *그 하류 sub-DAG만* 재계산(메모이제이션) 설계. 단 현 `evaluateSheet`는 dirty/memo 파라미터가 없어 **항상 전체 sheet를 처음부터 평가**한다 — `_dirtyClosure`는 Play if-토글 단계 신설 예정(§6.2). 순수함수라 메모이제이션은 안전(부작용 0). **인터랙티브 토글·Play 즉답의 1차 엔진(후속).**
2. **사전계산 + 동결 (precompute & freeze):** 대표 분기 격자(baseline/adverse/severe × 주요 토글 조합)를 Python이 오프라인 사전계산 → 정적 artifact 발간(`?sim=`). 브라우저 토글 = *격자 lookup*(재계산 0). Play = 사전계산된 path를 시간순으로 *드러내기*(매 프레임 재계산 아님). 기존 `crossRegression` pre-fit JSON 캐시 패턴과 동형.
3. **벡터화 (heavy bits):** MC(현 1만 iter × `_applyMacroShock` Python 루프 = 느림·OOM) → numpy 벡터화(leaf 1회 + 벡터 노이즈, §13). 민감도 격자도 벡터 연산. **Python 루프로 leaf N회 호출 금지.**
4. **AI는 hot path 밖:** lens는 opt-in·비동기, 결정론 Play/토글 루프를 *절대 블록하지 않음*. 불변1(AI 없이 빠른 det)이 곧 hot path. AI 의견은 fork/gap 노드만, 백그라운드로 채워 ledger 갱신.
5. **스냅샷, 재로드 금지:** leaf는 평가 전 동결된 panel snapshot(asOf 고정)만 읽음 — 평가 중 재쿼리·재로드 0. Company 1개 200~500MB OOM 가드(§13)와 정합.
6. **사전계산 격자 artifact 구조(정밀):**
   ```
   gridArtifact = { specKey → { candles:{p5..p95:[float/분기]}, events:[{date,type,kind}],
                                macro:[float/분기], report:{IS,BS,CF/분기}, credit:[survival/분기] } }
   ```
   - 축 = branch(3) × **핵심 토글 subset(2^k, k≤6 → ≤64조합)** × horizon. `specKey = serialize(branchId, sorted toggleState, mcSeed, asOf)` = `?sim=` URL 직렬화(05 §5). 브라우저 = 격자 lookup(재계산 0). 로컬 Python = 전체 DAG 재계산(신규 저작).
   - ⚠ '핵심 토글'(격자 축) vs '드릴다운'(로컬 재계산) 경계는 **Sobol S_T(02 §2B.4-C)로 S_T≈0 토글을 제거해 k≤6 보장**하는 가지치기가 선결. 데모 전 미확정(04 §5).

**2티어 실행:** landing = 사전계산 격자 lookup(즉시·WebGPU 불필요) / 로컬 Python = 전체 재계산(새 시나리오 저작). 브라우저 패리티는 순수함수 TS 포팅(viewer hyparquet 0.6ms 전례) + 골든 테스트.

## 13c. 횡단면 스캔 — 전체 회사 빠른 시뮬레이션 스캔 (운영자 추가 요구)

"이 거시 시나리오를 전 상장사에 적용해 가장 취약/수혜 회사를 찾기" 같은 횡단면 시뮬은 강력하나, **2,900사 × 전체 proforma를 인터랙티브 루프 = OOM·초 단위 지연으로 불가**(Company 1개 200~500MB). 정공법:

1. **경량 횡단면 모델(벡터):** 전 회사 elasticity/sensitivity를 오프라인 사전계산해 *compact 횡단면 테이블*로 저장(`crossRegression` pre-fit + `scan` L1.5 횡단면 패턴 재사용). 시나리오 스캔 = `shock 벡터 × elasticity 행렬` 벡터 연산 → 전 회사 노출도 랭킹을 **밀리초**에. 회사마다 full 3-statement 안 돎.
2. **경량 스크린 → 심층 드릴다운:** 횡단면 스캔은 *랭킹·스크리닝*(어느 회사가 취약/수혜)만 경량으로. 사용자가 한 회사 클릭 → 그때 *그 회사만* full 결정론 DAG(무거운 단일사). "빠른 스크린 → 깊은 한 종목"이 OOM·속도 동시 해소.
3. **거처:** 횡단면 슬라이스는 **기존 `scan`(L1.5) 엔진에 위임**(재발명 금지) — `simulate`가 단일사엔 proforma를, 횡단면엔 scan을 호출. 공개 계약 verb 하나에 흡수: `dartlab.simulate(scenario=..., universe=...)` → 횡단면 노출 랭킹(scan 위임), `universe` 없으면 단일사 DAG.
4. **정직 경계:** 경량 횡단면은 elasticity 기반 *근사*(full 3-statement 아님) — "정밀 손익 투영"이 아니라 "시나리오 노출 스크리닝"으로 라벨. 회사 클릭 시에만 정밀.

이 둘(속도·횡단면)은 안C를 *바꾸지 않고 강화*한다 — 순수함수 DAG = 메모이제이션·벡터화·사전계산의 전제이고, 횡단면은 기존 scan 위임이다.

## 14. 기각된 안 (코드 근거)

- **안A(제자리 리팩토링) 기각:** transfer를 `analysis/forecast` 제자리에 두면 analysis(L2)가 macro 개념을 계속 품어 L2 경계 영속 오염. 결정적으로 가격 백테스트(`quant/strategy/`)를 시뮬에 통합하는 순간 **L2↔L2 cross-import 가드 즉시 차단**. (단 안A의 "1106줄 거짓"·"transfer 거처 교정=cycle 해소" 통찰은 흡수.)
- **안B(별도 엔진, leaf 소유) 기각:** "자체 조건 그래프 소유"를 일관 정의하면 leaf 재구현(SSOT 분열: 터미널 proforma ≠ 시뮬 proforma) 또는 L2 import(=안C). B 스탠스 스스로 "안C로 붕괴" 자인. B의 합법성 근거(L2_PEERS 미소속)는 안C 묶음에도 그대로 적용되므로 B 고유 가치 없음.

**셋의 좋은 절반은 모두 안C와 동일하고, 안C가 더하는 것(L2 leaf 호출 래퍼 + transfer 외과 적출 + lens를 ai/tools 분리)은 두 불변을 만족시키는 최소 골격이다.**

---

## 15. _attempts 졸업 게이트 → 본진 진입

> **★진척(2026-06-14):** 결정론 코어가 이미 졸업해 본진 `src/dartlab/simulate/`에 실재한다 — foundation(`sheet`/`transfer`, LAYER_OF simulate:2.5 등록) + deterministic core(4노드 `registry`/`run`, `096e84c43`) + 공개 verb(`entry`, `ac3905fd9`). 아래 8단계 중 1~4·6~8의 *결정론 부분*은 완료(transfer byte-identical 골든·9섹션 docstring·dartlabGuard exit 0). **잔여 = MC·lens·DriverRegistry·Play 단계**(§5b 노드, §6.3 gate, 02 §2B admission). 아래 원본 게이트는 그 잔여 단계의 척추로 유지. ★졸업 AC(추가): `rev.path` 노드가 pooled-panel transfer provenance(pooled-OOS partial-R², 02 §2B.1) *또는* `SimulationResult.warnings=["elasticity_prior_unvalidated"]` 중 하나를 보장 — 결과 표면에서 silent magic-constant fan-out 금지.

`tests/_attempts/scenarioSimulator/`에서:
1. 카테고리 scenarioSimulator
2. **개념확립:** 삼성/카카오/현대 2~3사로 노드 분해가 현 `createSimulation`/`simulateScenario` 출력과 **byte-identical 재현**(§12: 결정론 경로만, MC는 분포 패리티) + `transferMacroToFundamentals` 적출 골든
3. 모듈화: lazy-proxy 4파일 철거(DI 재조립), `simulate/` 스켈레톤
4. **데모:** DriverSheet + 경합 모드(det vs ai 평행 + DisagreementLedger) + Brier 누적 신호. 노드 입자도 실측 확정(§5 수정 4). 결과 docstring+README
5. 덕지덕지 제거: scenarioSim 수동 봉합 + 6개 프록시 + DCF/WACC 3중 중복 단일화
6. 클린코드
7. 9섹션 docstring(`docstring4Section.py` hook 강제, §11 키워드 회피)
8. 본진: `simulate/` + `ai/tools/lens.py` (`engine-add` 5점 + `skill-os-add` 4단계 `specs/engines/simulate/SKILL.md`)

**착수 전 선결 kill-test (Phase 0) — ✅ 완료(09 P1):** MC 전역시드 재현성·cone 버그(§12)를 로컬 `random.Random(seed)`·cumprod 전환 *전에* 먼저 죽였다(numpy Generator 아님 — stdlib). Play 결정론·URL 공유·TS 패리티 척추.

---

## 16. 확인한 핵심 파일 (절대경로, 재조사 불필요)

**구현 완료 `simulate/` (본진 졸업, 정본):**
- `src/dartlab/simulate/sheet.py` (NodeValue/DriverNode/DriverSheet + computeInputsHash + buildOrder + evaluateSheet — 단일 결정론 실행기, lens 심볼 부재)
- `src/dartlab/simulate/transfer.py` (transferMacroToFundamentals/transferRevenuePath — 자기 소유 엣지 산수)
- `src/dartlab/simulate/registry.py` (buildSnapshot + 4 노드 fn `_fnMacroPath/_fnRevPath/_fnProforma/_fnDcf` + buildScenarioSheet; `_fnDcf`=proforma-FCFF, `_macroFrozen` recompute 우회 실재)
- `src/dartlab/simulate/run.py` (runScenario + SimulationResult + NodeAudit + `_marginPathFromSnapshot` recompute 우회 + warnings honest-gap)
- `src/dartlab/simulate/entry.py` (공개 verb `dartlab.simulate(code,*,scenario,horizon,asOf)`, KR 전용 가드)
- `src/dartlab/providers/dart/company.py:1990` (`Company.simulate` 메서드 — 실재)
- ⚠ 미생성: `simulate/{gate,ledger,admission}.py` (후속 단계)

**레거시·불가침(엔진 경로 불변):**
- `src/dartlab/analysis/forecast/simulation.py` (244줄, `_applyMacroShock:180-235` 적출 대상, `:240-244` E402 re-export)
- `src/dartlab/analysis/forecast/_simScenario.py:35-38` · `_simMonteCarlo.py:36-40` · `_simHistorical.py:34-47` (lazy proxy 4파일)
- `src/dartlab/analysis/forecast/_simMonteCarlo.py:145` (전역 seed) · `:205` (덮어쓰기 버그) · `:197-213` (MC 1만회 호출 — OOM 근거)
- `src/dartlab/analysis/forecast/scenarioSim.py` (`createSimulation:380` 수동 봉합, `judgeQuarter` = forward-test 일반화 기반)
- `src/dartlab/analysis/financial/_proformaCore.py` (637줄 leaf SSOT — 불가침)
- `src/dartlab/analysis/financial/_signalsMacroSensitivity.py` (640줄 `calcMacroRegression` OLS — 불가침)
- `src/dartlab/analysis/valuation/analyst.py:322-347` (`__getattr__` lazy 레지스트리 — 회귀 표면, BC 위임 갱신 대상)
- `src/dartlab/ai/tools/engineCall.py:142,555-566` (카탈로그 동적 dispatch — MCP 노출 표면)
- `src/dartlab/synth/scenario.py` (preset+SECTOR_ELASTICITY, simulateScenario docstring만 언급·import 0 — L1.5→L2 가드 준수)
- `src/dartlab/macro/forecast/nowcast.py` (gdpNowcast Kalman 현재국면 — 경로예측 부재 확정)
- `tests/architecture/test_l2_no_cross_import.py` (`L2_PEERS` 5개 — `simulate/` 묶음 자동 합법 근거)
- `tests/architecture/test_import_direction.py` (`LAYER_OF["simulate"]=2.5`:26 + downward-only 검사 — L2→L2.5 역방향 차단 LIVE pytest 정본)
- `tests/audit/checkAgentBoundary.py:158` (`_check_regression_keywords` SRC 전체 스캔 — §11 근거)
