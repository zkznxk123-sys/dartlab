# Macro Lens 초강화 PRD
## "묻어둔 전향(前向) 축의 표면화 — Foresight, not Verdict"

> 거처: `ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte` (기존 다이얼로그 EXTEND). 데이터: `.github/scripts/sync/buildMacroRegime.py`(신규) → HF `macro/regime/{kr,us}.json` → `.github/scripts/prebuild/buildMacroJson.py`(조립 확장) → `landing/static/dashboards/macro.json` `regime` 키 → `ui/.../lib/macroLens.ts` view-model.
> 본 문서는 자기충족적이다. 이 문서만 보고 재조사 없이 구현 가능하도록 영향 파일·함수·필드 매핑·ASCII 목업·데이터 계약 스키마·테스트·롤백을 모두 담는다. SSOT는 함수명·필드명·콜사이트명이며 줄번호는 보조다(현 소스 실측 기준).
> 토대: `mainPlan/macro-lens-redesign/01-redesign-prd.md`(시각 재설계). 본 PRD는 그 4블록 계기판 IA·시각 토큰 SSOT·height 예산·면적 게이트·한계 가드·grep 게이트·`buildExposureMatrixRows`/`pickFocusCell` 신설을 **불변 계승**하고, 그 위에 분석 *깊이*만 progressive disclosure로 더한다.

---

## 0. 하드 선행조건 (착수 게이트)

본 PRD는 **재설계 PRD가 먼저 머지된 base 위에 선다.** 재설계는 `MacroLensDialog`를 13섹션 verdict UI에서 4블록 계기판으로 깎고, `macroLens.ts`에 `buildExposureMatrixRows`·`pickFocusCell`을 신설하며 `buildMacroVerdict`·verdict 타입군·`transitionLabel`(L1754 함수·L1757 `${tr.progress}%` 방출·L1791 `transitionLabel:tr.label`)을 삭제한다. 현 소스 실측 기준 이들은 아직 적용되지 않았다. 따라서:

- **게이트:** 재설계 PRD(4블록 dashboard 탭·`buildExposureMatrixRows`/`pickFocusCell` export·`buildMacroVerdict`/verdict 타입군/`transitionLabel` 삭제) 머지 완료가 본 PRD MUST 1 이전의 차단 게이트다.
- **충돌 처리(초강화가 먼저 착수될 경우 — 정공법):** 우회·임시 shim 금지. 재설계의 view-model 삭제·4블록 재조립을 먼저 끝내고(재설계 PRD §8~§10 그대로) 그 commit 위에 본 PRD를 쌓는다. 본 PRD는 재설계가 신설하는 함수·삭제하는 함수를 전제하므로 base 없이는 빌드가 깨진다 — base를 먼저 세우는 것이 유일한 정공법이다.
- **transition 함수 경계:** 재설계가 `transitionLabel`(verdict 빌더 소속·L1754 함수·L1757에서 `${tr.progress}%` 누출·L1791 `transitionLabel:tr.label`)을 삭제하므로, 본 PRD는 백분율 없이 정수 분수만 내는 **신규 전용 함수 `transitionFraction`**(§6.2)을 세운다 — 기존 함수 재사용 금지. 특히 L1757의 `%` 방출 코드 경로를 신규 함수에서 재현하지 않는다(정수 분수만).

---

## 1. 한 줄 결론 + 제품 비전

**한 줄 결론:** Macro Lens는 회고적 국면(phase/quadrant)을 *고신뢰 단정*처럼 보여주지만, 그 국면을 *반증·전향*할 엔진의 핵심 축 — forecast의 multi-model 침체 confluence 와 GaR 조건부 분포 — 은 다이얼로그에 0% 표면화된 채 묻혀 있다. 초강화는 새 메커니즘을 *쌓는* 게 아니라, 이미 numpy로 직접 구현해 묻어둔 전향 축(침체확률 4모델·수익률곡선·Growth-at-Risk 분포·전향 추적기·국면 방향)을 **단일 점수로 붕괴시키지 않고 있는 그대로 배선**하는 것이다. 강함은 쌓아서가 아니라 깎아서·바르게 배선해서 나온다.

**단일 핵심 결정:** 첫 화면 4블록 계기판(A 국면 → B 펄스 → C 노출지도 단일 주역 → D 게이트/릴리스)은 **픽셀 불가침**이다. 깊이는 첫 화면에 *쌓지 않고* 단 하나의 진입점 — **A블록 Phase Strip 클릭 → 인라인 `<details>` 1개 "국면 렌즈(Regime Lens)"** — 에만 흘려보낸다. 새 탭 0·새 라우트 0·새 상주 패널 0. 첫 화면 유일한 증분은 A블록 Phase 칩 옆 *전향 분수 1줄*(이미 라이브인 `us.transition` triggered/pending)뿐이다. 침체 confluence·수익률곡선·GaR 분포·Hamilton regime band·LEI 기여도는 **전부 Regime 렌즈 `<details>` 안에만** 산다(첫 화면 불가침).

**무엇을 표면화하는가 (결정유관 5요소·전부 Regime 렌즈 details):**
- **forecast 침체 confluence** — Cleveland Fed probit · Sahm rule · Conference Board LEI · Hamilton 수축확률을 *나란히 놓인 가변 N신호 스트립*으로. 합산 점수 0. 각 타일은 **자기 호라이즌·자기 척도·자기 freshness를 독립 표기**한다(§3.4). 회고적 phase를 검증하는 유일한 축이고, 엔진 docstring이 "단일 모델 cherry-pick 금지·복수 모델 인용"을 강제 설계했다(`forecast.py` AIContext: "recessionProb.probability 만 인용 — LEI/Sahm 무시" AntiPattern).
- **rates 수익률곡선 1줄** — 곡선 형태 라벨(가파른정상/정상/평탄/역전·엔진 `interpretation` enum 기반·§4.3) + 10Y-3M spread 값. **spread는 `forecast.recessionProb.spread`에서 가져온다**(`rates.yieldCurve`에는 spread 필드가 없다·beta0/beta1/beta2/lambda/rmse/interpretation/description만·§4.3). probit과 *동일 T10Y3M 입력*이므로 confluence에서 독립 신호로 이중계상하지 않는다(§3.5).
- **Growth-at-Risk(GaR) 조건부 분포** — FCI 조건부 GDP 성장률 5분위(5/25/median/75/95)+비대칭도(skewness)+tailRisk. probit 점확률과 달리 **진짜 분포를 산출**하는 유일한 모델이므로 분위 막대/미니 fan으로 표면화한다(§3.7·Adrian-Boyarchenko-Giannone Vulnerable Growth 표준). horizon=4분기 전향·US 중심.
- **quadrant 방향 라벨** — 이미 bake됨(kr:stagflation, us:reflation). `growth`/`inflation` 방향(rising/falling)과 `assetImplication`만. raw `growthSignal`/`inflationSignal` 숫자는 단위 불명·환각 위험이라 **비노출**.
- **transition 전향 추적기** — 이미 `us.transition`에 라이브(triggered/pending). **신규 sync·bake 0**, view-model 신규 함수 1개만으로 표면화되는 최저비용 결정유관 축. 첫 화면 A블록 1줄 증분.

**무엇을 표면화하지 않는가 (의도적 제외):** liquidity·sentiment·crisis(GaR 제외)·assets·corporate·trade·inventory·narrative·scenario·nowcast(점추정·구간 부재)·summary(6막 점수). 사유는 §3.6에 박제한다. 특히 **summary 6막 점수는 단일 macro score라 절대 표면화 금지**(verdict의 엔진측 쌍둥이) — grep 게이트로 봉인한다.

**비전 문장:** Macro Lens는 "경제지표를 보여주는 화면"이 아니라 **"매크로가 이 종목에 어디로(국면), 얼마의 확률·어떤 분포로(다모델 confluence·GaR·각자 다른 호라이즌), 언제(lag·전향 trigger) 닿을 수 있는지를 7초에 읽되, 화면이 *판정하지 않고* 회고/확률/분포/freshness/호라이즌을 있는 그대로 분리해 보여주는 검증 계기판"**이다. 화면은 판정하지 않는다 — 모델이 *동의하면 어느 모델들이 동의하는지, 불일치하면 어느 모델이 어긋나는지*를 그대로 보여준다.

---

## 2. 현상 진단 — 묻어둔 엔진과 표면화 갭

엔진(`src/dartlab/macro`)은 6막 14축의 세계급 깊이를 가진다. 그러나 공개 터미널 `macro.json`은 6키(version·asOf·kr·us·transmission·sectorTailwind)뿐 — 엔진 깊이의 ~5%만 bake된다(실측 13,570 bytes·650줄·§4.6).

**함수 lineage 실측(불가침·GROUND-TRUTH):** 침체 4모델·수익률곡선의 *정의*는 forecast.py에 있지 않다. `clevelandProbit`·`conferenceBoardLEI`·`_LEI_WEIGHTS`·`sahmRule`은 `src/dartlab/macro/cycles/_regimeSwitchingLei.py`에 정의되고, `hamiltonRegime`은 `src/dartlab/macro/cycles/_regimeSwitchingHamilton.py`에 정의된다. 공개 import는 `from dartlab.macro.cycles.regimeSwitching import clevelandProbit, conferenceBoardLEI, hamiltonRegime, sahmRule`다. `forecast.py`(L15)는 `cycles.regimeSwitching`에서 import만 한다(정의 아님). yieldCurve는 `src/dartlab/macro/rates/`의 `nelsonSiegel`이 산출한다. GaR은 `src/dartlab/macro/crisis/growthAtRisk.py::growthAtRisk`다.

| 묻어둔 축 (실측) | 엔진 산출 (정의 위치 기준) | 현재 표면화 | 결정유관성 |
|---|---|---|---|
| forecast.recessionProb | `clevelandProbit(t10y3m)`(`cycles/_regimeSwitchingLei.py` 정의) → result key `{probability, zone(low/moderate/elevated/high 4단계), zoneLabel, spread, description}` (US 전용·forecast.py L232) | **0%** | 최상 (국면 검증·12M 선행) |
| forecast.sahmRule | UNRATE → result key `{value, triggered, zone(normal/warning/recession), zoneLabel, description}`. forecast.py L342에서 `len(ur_vals)>=15`일 때만 호출, 아니면 `result["sahmRule"]=None`(US 전용·L340) | **0%** | 최상 (실시간 침체 *시작* 트리거) |
| forecast.lei | US=Conference Board → result key `{level, mom, mom6m, signal(expansion/caution/recession_warning), signalLabel, availableComponents(개수), totalComponents(개수), description}` — **per-component dict·weight 미노출**(L287-288). KR=CLI composite(다른 shape: `{cliMomentum, cliLevel, growthApprox, growthLabel, ...}`·L303-333) | **0%** | 상 (US 6~9M 선행) |
| forecast.hamiltonRegime | `hamiltonRegime`(`cycles/_regimeSwitchingHamilton.py` 정의·EM). forecast.py result key `{currentRegime, currentProb, params(mu_expansion/mu_contraction/sigma_expansion/sigma_contraction/phi/p_stay_*), converged, iterations, contractionProb(=smoothedProbs[-1,1]·**회고적**), description}` (L359-371). market 무관 호출(L354 gdp_id KR='GROWTH') — 단 GDP 시리즈 길이<20이면 미산출(L356) | **0%** | 중 (분리도 게이트 통과 시·회고적) |
| forecast.nowcast | Kalman DFM → gdpEstimate + confidence(**범주형 str high/medium/low**). 구간 배열 없음 | **0%** | 하 (점추정·표준오차 미산출) |
| **GaR (crisis/growthAtRisk.py)** | `growthAtRisk(fci, gdp_growth, horizon=4)` → `{currentGaR5/25/median/75/95, currentFCI, tailRisk, tailRiskLabel, skewness, horizon, observations, description}`. **진짜 5분위 조건부 분포 + 비대칭도**. analyzeForecast 자체엔 없고 `summary.py::_addGrowthAtRisk`가 FCI(liquidity)+GDP로 직접 호출해 `forecastResult['growthAtRisk']`로 주입 | **0%** | 상 (4Q 전향 분포·12~24M lag 아님) |
| rates.yieldCurve | nelsonSiegel beta0~2/lambda/rmse/**interpretation(steep_normal/normal/flat/inverted enum)**. **spread 필드 없음**. spread는 forecast.probit.spread에만 존재 | 텍스트만 | 상 (probit과 동일 입력) |
| quadrant | `growth`/`inflation`/`assetImplication`/`growthSignal` | **bake됨·다이얼로그 미표면화** | 상 (방향만) |
| us.transition | from/to/progress/triggered/pending | **bake됨 · 다이얼로그 미표면화** | 상 |
| crisis (GaR 외 22+키) | creditGap·ghsScore·minskyPhase·recessionDashboard.composite | 0% | 하 (12~24M lag·가드충돌) |
| summary | 6막 점수 + 자산배분 + 40 투자전략 | 0% | **금지 (단일 macro score)** |

**진단:** 가장 결정유관하고 *cherry-pick 금지가 코드 docstring에 박힌* forecast 축과, *유일하게 진짜 분포를 산출하는* GaR 축이 다이얼로그에 0% 표면화된 채 묻혀 있다. `quadrant`·`us.transition`은 이미 bake되었으나 MacroLensDialog dashboard 탭에는 미표면화다. 초강화는 이 갭을 — 묻어둔 함수를 sync에서 계산해 HF push하고(forecast/rates/GaR), 이미 bake된 것을 다이얼로그에 배선하고(transition/quadrant), 결정유관성 낮은 축은 가차없이 컷하는 — *직접 배선*으로 닫는다.

---

## 3. 표면화 축 선별 (결정유관성 컷 라인)

### 3.1 표면화 5요소 (이것만)

| 요소 | 형태 | 거처 | 데이터 경로 | 결정유관 근거 |
|---|---|---|---|---|
| **forecast confluence** | 가변 N신호 가로 **텍스트 타일** 스트립(probit·Sahm·LEI·Hamilton, 각 호라이즌·척도·zone·asOf) | Regime 렌즈 `<details>` | sync 신규 계산 → HF `macro/regime` → prebuild 조립 | 회고 phase 검증축. 엔진이 multi-model 교차 강제 설계 |
| **rates 수익률곡선** | 형태 라벨(엔진 interpretation enum) + 10Y-3M spread 1줄 | Regime 렌즈 `<details>` | spread=forecast.probit.spread 재사용·형태=rates.yieldCurve.interpretation → sync 추출 | probit 입력(동일 T10Y3M·이중계상 금지) + transmission 금리채널 닻 |
| **GaR 분포** | 5분위 막대/미니 fan + skewness + tailRisk + horizon 라벨 | Regime 렌즈 `<details>` | sync `growthAtRisk(fci, gdp, horizon=4)` 직접 호출 → HF `macro/regime` | 유일한 진짜 조건부 분포 (4Q 전향·점확률 보완) |
| **quadrant 방향** | growth/inflation 방향 라벨 + assetImplication (raw 숫자 비노출) | A블록 보강 + Regime 렌즈 | 이미 bake (kr/us.quadrant) — 신규 계산 0 | 자산배분 방향. C블록 초점채널과 정합 라벨(§6.3) |
| **transition 추적기** | "둔화→수축 1/3 충족" 전향 분수 1줄 | A블록 Phase 칩 옆 (첫화면 유일 증분) | 이미 `us.transition` bake — view-model 신규 함수 배선만 | 국면 전환 임박 여부. 충족 trigger 분수(% 아님) |

### 3.2 KR/US 비대칭 (실측 기반 — 불가침)

`forecast.py` 실측: recessionProb·sahmRule·nowcast는 **US 전용**(KR이면 해당 키 `None`·L293/L339/L379). GaR도 US 중심(FCI 입력)이다. KR `lei`는 US와 **완전히 다른 shape**(`{cliMomentum, cliLevel, growthApprox, growthLabel}`·L303-333). `hamiltonRegime`은 market 무관 호출(L354 gdp_id KR='GROWTH')이라 KR에서도 `contractionProb` 산출 *가능*하다 — 단 GROWTH 시리즈 길이<20이면 미산출(L356).

**KR Hamilton 단위 parity 미확정 → US-primary·KR 보류(불가침·결정 D6):** KR Hamilton의 입력 `GROWTH`는 ECOS 시리즈로, US `A191RL1Q225SBEA`(분기 실질 GDP 연율 QoQ%)와 단위·빈도·deflator가 동일하다는 보장이 없다. EM regime mean과 분리도(separation)는 입력 단위에 직접 민감하므로, KR contractionProb를 US probit과 같은 신뢰도로 오독하면 가짜 정밀이 된다. 따라서 **Hamilton은 US-primary로 표면화하고, KR Hamilton은 GROWTH↔A191RL1Q225SBEA 단위 parity가 확인되기 전까지 표면화를 보류한다**(`status:'단위 parity 미확정·표시 보류'`). 즉 KR confluence는 **CLI momentum 1타일만**으로 구성되며(probit/Sahm/nowcast는 'US 전용' 라벨), KR Hamilton은 산출 가능하더라도 *단위 동일성 미확정*이라 표면화하지 않는다. 향후 단위 parity가 확인되거나 시장별 임계가 분리되면 KR Hamilton 표면화를 재검토한다(§11 SHOULD).

**KR 비대칭 처리:** KR Regime 렌즈는 US 4타일 틀에 N/A를 채우는 *대칭 레이아웃*이 아니라 **비대칭 레이아웃**이다: CLI momentum 1타일(cliMomentum + growthLabel). probit/Sahm/nowcast/Hamilton(단위 보류)은 'US 전용(`notApplicable`)' 또는 '단위 parity 미확정' 라벨로 명시하되 빈 회색 N/A 셀로 그리지 않는다(데이터 깨짐 오독 차단). KR Phase Strip 옆 전향 분수는 `kr.transition===null`(macro.json 실측)이라 **렌더하지 않는다**(빈칸 금지). KR confluence는 CLI 1타일만 남으므로 `agreementOf`는 '교차 불가(유효 1개)'를 낸다(§6.2 결손표 박제).

### 3.3 confluence 정규화 — 결정론적 공통 3단계 매핑 (산출식 SSOT·거짓 divergence 차단)

4모델의 zone 어휘가 호환되지 않는다(probit 4단계·sahm 3단계·lei 범주형·hamilton 생 float). agree/diverge를 정의하려면 **결정론적 공통 3단계 bucket** {확장(0)·경계(1)·침체(2)}로 사상한다. **4단계가 아니라 3단계인 이유:** probit의 `moderate`만 중간 bucket을 산출하고 다른 3모델은 중간값을 내지 않으므로, 4단계로 두면 probit moderate(흔한 중간값)가 항상 소수파가 되어 'probit 어긋남'이 구조적으로 거짓 빈발한다. probit `moderate`를 `expansion`(0)으로 흡수해 3단계로 collapse하고, 추가로 **인접 bucket(0-1, 1-2)은 `agreementOf`에서 동의로 처리**한다(§3.5). 이 매핑표가 산출식 SSOT이며 view-model `bucketOf`가 구현한다(점수 아님·서수 bucket 뿐):

| 모델 | 원 출력 | → 공통 bucket |
|---|---|---|
| probit | zone='low' | 0 (확장) |
| probit | zone='moderate' | 0 (확장 — 흡수) |
| probit | zone='elevated' | 1 (경계) |
| probit | zone='high' | 2 (침체) |
| sahm | zone='normal' | 0 |
| sahm | zone='warning' | 1 |
| sahm | zone='recession'(triggered) | 2 |
| lei | signal='expansion' | 0 |
| lei | signal='caution' | 1 |
| lei | signal='recession_warning' | 2 |
| hamilton | contractionProb < 0.25 | 0 |
| hamilton | 0.25 ≤ p < 0.50 | 1 |
| hamilton | p ≥ 0.50 | 2 |

`bucketOf` 임계는 모델별로 의도적으로 다르다(각 모델의 자연 컷오프) — **공통 bucket은 "동일 색=동일 의미"가 아니라 "동일 방향성 묶음"이다.** UI는 bucket을 *색 정렬*에 쓰지 않고 *agree/diverge 텍스트 파생*에만 쓴다(§3.5). 막대 길이·서수 badge 0(척도 비통일이 막대로 가짜 비교되지 않게·§5.3).

### 3.4 모델별 신뢰성 게이트 (4모델 전체에 엔진-정합 엄밀성)

cherry-pick과 가짜 정밀을 구조적으로 닫으려면 각 모델에 *엔진 실측에 정합하는* 신뢰성 게이트를 둔다. sync `_extractForecast`가 게이트하고 status를 동결한다:

- **probit:** 모델 게이트 없음(스칼라 입력·항상 산출). **단 점추정 정밀 가드:** Cleveland Fed probit은 고정계수(Estrella-Mishkin)·표준오차 미산출이라 `probability` 소수 2자리(0.18)는 가짜 정밀이다. zone 4단계를 *주역*으로, 확률은 *보조*(5%p 반올림 `~20%`)로 강등하고 타일에 "Estrella-Mishkin 고정계수·표준오차 미산출(점추정)" 라벨(§5.3)을 단다.
- **sahm:** `result["sahmRule"]`이 **None**(forecast.py L342에서 15개월 미만이면 sahmRule 미호출→None) → `status:'데이터부족·표시 보류'`. **분기 대상은 정확히 둘뿐이다 — None(키 부재)와 정상계산(value/triggered 실재).** analyzeForecast 경유 시 엔진 내부 `데이터부족` zone(0값)은 도달 불가하므로(L342 게이트가 차단), sync는 "None이면 보류 / 아니면 정상" 단일 분기만 둔다(dead path 이중 게이트 금지). 정상계산이 value 0 근처(미발동)인 경우는 그대로 'normal'로 표시하되, 0값이 데이터부족 누출이 아님은 None 분기가 이미 보장한다.
- **lei:** **사용가능 구성요소 *개수* 게이트(count·GROUND-TRUTH 정합·결정 D5).** `forecast.lei` result는 per-component dict·weight를 노출하지 않고 `availableComponents`(int)/`totalComponents`(int) 개수만 노출한다(L287-288). 따라서 가중치 질량(Σweight)은 result만으로 계산 불가다 — **엔진이 노출하는 `availableComponents/totalComponents` 개수 게이트**를 쓴다: `availableComponents / totalComponents ≥ 0.6`(전체 10개 중 ~6개 이상 — components dict 실측 10키, forecast.py L248-278). 미달이면 level/signal은 노이즈 → `status:'구성요소 부족·표시 보류'`(availableComponents/totalComponents 동반). `signalLabel==='데이터부족'`(available==0)도 동일. **`_LEI_WEIGHTS` 재계산·참조에 의존하지 않는다**(엔진 산출형태 변경 0·result 키만으로 게이트).
- **hamilton:** **converged 게이트 + 분리도(separation) 게이트.** 엔진 `regimeLabels`는 무조건 상수 `("expansion","contraction")`이고, mu-swap(`_regimeSwitchingHamilton.py` L246-248 init·L330-336 매 iteration)이 column 1=낮은 평균=수축을 *구조적으로 항상 보장*한다. 따라서 `contractionProb=smoothedProbs[-1,1]`은 항상 수축확률이고 `regimeLabels[1]==='contraction'` 검증은 *상수==상수*로 100% 참 = **죽은 가드**다(부활 금지). 진짜 신뢰성 위험은 라벨 뒤집힘이 아니라 **두 regime이 통계적으로 구분 안 되는 약한 분리**다. 게이트 = `converged===true` AND **regime 분리도 `separation = (mu_expansion − mu_contraction) / max(sigma_expansion, sigma_contraction) ≥ 0.5`**(params에서 직접 계산·`params.mu_expansion/mu_contraction/sigma_expansion/sigma_contraction` 실재). **임계 0.5 근거:** Cohen's d=0.5는 표준 *중간 효과크기*다 — 두 regime 평균의 차이가 (큰 쪽) regime 표준편차의 절반 이상일 때만 두 분포가 실질적으로 구분된다고 본다. 0.5 미만이면 EM이 두 평균을 가깝게 수렴해 smoothedProbs의 침체확률이 통계적으로 무의미하다. 미수렴 → contractionProb null + `status:'EM 미수렴'`. 분리 약함 → contractionProb null + `status:'레짐 분리 약함'`. (KR Hamilton은 §3.2대로 단위 parity 미확정으로 표면화 자체 보류 — 분리도 게이트 이전 단계에서 컷.)
- **호라이즌·시간축 라벨(불가침·결정 D2):** 각 타일은 자기 호라이즌과 시간 성격을 라벨로 단다 — probit `[12M 선행·확률]`, Sahm `[실시간·침체 시작 트리거(동행)]`, LEI `[6~9M 선행]`, **Hamilton `[동행·회고적 regime·smoothed]`**(전향 아님·docstring "smoothedProbs=회고적"). GaR은 confluence 스트립이 아니라 별도 분포 블록이며 `[4Q 전향 분포]` 라벨을 단다(§3.7). 스트립 헤더는 '침체 신호(12M·확률)' 단일 프레임을 **쓰지 않고** "침체 신호 (N모델 — 호라이즌·시간성 상이)"로 둔다. 호라이즌 분리는 한계 가드(§7)로 강제한다.
- **분기 vintage freshness:** Hamilton·GaR·nowcast는 분기 GDP 기반(BEA advance→3rd estimate 2개월·revision 잦음). §6.1 스키마에 `staleAfterDays:120` + `revisionLabel:"분기 GDP·수정 대상"`을 단다(probit 일간·LEI 월간과 다른 vintage 명시). nowcast는 표면화 보류(§3.6)지만 스키마에 vintage 필드는 둔다(근거 탭 1줄 노출 시 명시).

### 3.5 이중계상 가드 — probit/yieldCurve 동일 입력 + LEI 내포 상관 + agreement 명시

**probit·yieldCurve 동일 시리즈(결정 D3):** probit = `clevelandProbit(t10y3m)`(forecast.py L231)이고 수익률곡선 spread도 동일 T10Y3M다. 게다가 yieldCurve 자체는 spread 필드가 없어 spread는 probit.spread를 재사용한다(§4.3). 따라서 둘은 *동일 T10Y3M의 두 측정*이지 독립 confluence 신호가 아니다. Regime 렌즈에 '곡선 평탄'과 'probit 낮음'을 나란히 두면 한 신호가 두 confluence 표로 읽혀 이중계상된다. 가드: ① 수익률곡선 1줄과 probit 타일의 `aria-label`/`title`에 "형태=Nelson-Siegel interpretation·spread=T10Y3M, 동일 곡선의 두 측정 — probit과 독립 신호 아님" 명시. ② agreement 파생에서 둘을 **1표로 묶는다**(probit bucket 채택·곡선은 별도 표 아님).

**LEI 내포 상관(완전 독립 아님):** CB-LEI 구성요소는 `term_spread`(10Y−FF·forecast.py L274)와 `initial_claims`(역수·L253)를 포함해 probit(수익률곡선)·Sahm(실업)과 입력을 *부분 공유*한다. '4모델 동의'가 부분적으로 같은 원천을 재계상하는 confluence inflation 위험을 honesty 라벨에 박제한다 — LEI 타일 `title`에 **"LEI는 term-spread·initial-claims를 내포 — probit/Sahm과 부분 상관, 완전 독립 아님"**. agreement는 '독립 4모델 합의'가 아니라 '부분 상관 N모델 묶음'으로 읽혀야 한다.

**agreement = verdict 백도어 차단(결정 D4):** view-model `agreementOf`는 점수·순서·badge를 만들지 않는다. (a) 유효 타일(게이트 통과·§3.4) <2면 `'교차 불가 (유효 1개)'`. (b) ≥2면 다수 bucket과 **불일치 모델명을 명시**하되 **인접 bucket(0-1, 1-2)은 동의로 처리**한다(§3.3·거짓 divergence 차단) — 2단계 이상 벌어질 때만 불일치로 표기. 예: `'동의 낮음 — LEI 둔화 vs probit 확장(선행지표 우려, 곡선 미반영)'`. 다수결 숫자만 압축한 단일 요약은 verdict 약화판이므로 금지. agreement는 ordinal/score/badge로 렌더하지 않고 *불일치 모델명 동반 텍스트*로만 렌더한다.

### 3.6 의도적 제외 + 4종 결손 상태 (PRD 박제)

| 제외 축 | 사유 |
|---|---|
| liquidity (NFCI·자체FCI) | transmission HY spread(BAMLH0A0HYM2)와 신용채널 중복. **단 FCI 시리즈 자체는 GaR 입력으로 sync 내부에서 쓰인다(§3.7) — liquidity *표면화*만 제외**. 7초 판단 안 바꿈 |
| sentiment (VIX 구간·JLN) | VIX 단일값 공포 단정 가드 충돌. 모멘텀 편향 주입. 종목 transmission에 안 닿음 |
| crisis (Credit-to-GDP·Minsky·R-R·composite) — **GaR 제외** | 12~24M lag를 forecast(12M)와 같은 깊이 레인에 두면 시간축 불일치로 '위기 임박' 오독. `recessionDashboard.composite`는 차원 안 맞는 가중합산(숨은 단일점수)=verdict 벡터. **GaR은 4Q 전향 분포라 crisis lag 축과 다르며 §3.7로 표면화한다(crisis 제외에서 명시 분리).** crisis의 나머지는 근거 탭 GHS zone 1줄(다중매칭 라벨)이 절대 상한 |
| scenario (~146 프리셋) | 압도적 과부하. 시뮬레이터 영역. 재설계가 이미 경로 탭 `<details>`로 강등 |
| nowcast (GDP 점추정) | 이미 산출되나 confidence가 **범주형 str high/medium/low**뿐이고 GDP 분포·표준오차 미산출. 구간 없는 단일 % = 가짜 정밀·fan chart 유혹 → 표면화 보류(`computedButSuppressed`). **GaR과 대비: GaR은 진짜 5분위 분포라 fan/분위 정당, nowcast는 점추정이라 fan 금지** |
| assets·corporate·trade·inventory·narrative | 결정유관성 낮음·analysis/quant 경계 침범·중복·과부하 |
| summary (6막 점수) | **단일 macro score 절대 금지** — verdict 엔진측 쌍둥이. grep 게이트로 봉인 |

> **'fan chart 금지'의 정확한 범위(결정 D1):** fan/분위 시각화 금지는 *분포를 산출하지 않는 모델*(probit 점확률·nowcast 점추정)에만 적용한다. **GaR은 진짜 조건부 5분위 분포(5/25/median/75/95)+skewness를 산출하므로 분위 막대/미니 fan이 정당하다**(Adrian-Boyarchenko-Giannone Vulnerable Growth 표준). §7 가드의 "fan chart 0"은 "분포 미산출 모델 한정"으로 못 박는다.

**4종 결손 상태 라벨 (서로 다른 결손 유형 — 뭉뚱그리기 금지):**
- `의도적 제외` — crisis(GaR 외)/liquidity/sentiment 등. "결정유관성 낮아 표면화 안 함".
- `미표면화 배선만` — transition/quadrant. 이미 bake·다이얼로그 미표면화 → view-model 신규 함수로 즉시 표면화.
- `blocked 표본부족` — exposureQuality status='blocked'. 시도했으나 겹친 표본 부족(재설계 §3.3).
- `computedButSuppressed` — nowcast. **산출은 되나** 신뢰구간 부재로 표면화 보류(미구현 `notWiredYet`과 구분).

### 3.7 Growth-at-Risk 분포 표면화 (결정 D1 — Regime 렌즈 details 안·첫 화면 아님)

GaR은 forecast 4모델과 **다른 성격**이다: probit·Sahm·LEI·Hamilton은 *점신호/확률 스칼라*인데, GaR은 FCI 조건부 GDP 성장률의 **진짜 5분위 조건부 분포**를 낸다. 따라서 confluence 스트립의 한 타일로 압축하지 않고 **Regime 렌즈 안의 별도 "GaR 4Q 전향 분포" 요소**로 둔다(첫 화면 불가침).

- **데이터 출처:** analyzeForecast 자체에는 GaR이 없다 — `summary.py::_addGrowthAtRisk`가 FCI(liquidity)+GDP growth로 `growthAtRisk(fci_series, gdp_growth, horizon=4)`를 직접 호출해 `forecastResult['growthAtRisk']`로 주입한다. 본 PRD의 sync `buildMacroRegime.py`는 동일 패턴 — FCI 시리즈+GDP growth를 fetch해 **`growthAtRisk(..., horizon=4)`를 직접 호출**한다(US 중심·FCI 입력). analyzeForecast 결과에 의존하지 않고 crisis 함수를 직접 호출하는 것이 정공법이다(summary가 이미 그렇게 한다).
- **표면화 형태(분위 막대/미니 fan):** `currentGaR5 / currentGaR25 / median / currentGaR75 / currentGaR95`를 **분위 막대 5개**(또는 좌우 비대칭 미니 fan)로. **단일 숫자로 붕괴 금지** — GaR5만 인용하고 median 무시하는 것이 엔진 docstring AntiPattern이다. skewness(음수=하방 꼬리 두꺼움)와 tailRisk(high/elevated/moderate/low) 라벨을 동반.
- **명시 라벨:** `[4Q 전향 분포]` 호라이즌 + asOf + `staleAfterDays:120`(분기 GDP vintage·revision 라벨) + `currentFCI`(조건 입력) + `observations`(shift 후 유효 회귀 표본 = len(fci)−horizon·원시 시계열 수 아님). "FCI 조건부 GDP 성장률 분위 — 점추정 아닌 조건부 분포" 라벨로 점확률(probit)과 시각·의미 분리.
- **게이트:** `growthAtRisk`는 관측치<20이면 None을 반환(엔진 L138/L149/L160). None이면 GaR 요소 미렌더(`status:'표본 부족·표시 보류'`).
- **fan 정당성 명시:** §7 가드는 GaR fan/분위 막대를 허용한다(분포 산출 모델). probit/nowcast의 fan만 금지.

---

## 4. 데이터 파이프라인 — sync 풍부화 → HF → prebuild 조립

### 4.1 책임 경계 (불가침)

- **sync (online)** = `.github/scripts/sync/`. 외부 FRED/ECOS fetch 가능. 깊은 축(forecast·rates·GaR)은 **반드시 여기서 계산**해 HF push.
- **prebuild (offline only)** = `.github/scripts/prebuild/buildMacroJson.py`. `enforceOffline()` 강제(L189)·외부 API 0. HF 다운로드 + 조립만.
- prebuild에서 직접 `analyzeForecast`/`analyzeRates`/`growthAtRisk` 호출은 **offline guard 위반**(전부 `getGather`→FRED/ECOS fetch 또는 시리즈 입력 의존). **정적 봉인:** `tests/architecture/test_prebuild_offline.py`의 `_FORBIDDEN_IMPORTS`는 현재 **5종**(`dartlab.providers.{dart,edgar,edinet}.openapi` + `dartlab.macro.cycles.cycle` + `dartlab.macro.seriesFetch`·L34-40)이다. 여기에 **`dartlab.macro.forecast.forecast`·`dartlab.macro.rates.rates` 2모듈을 추가**해 7종으로 확장한다 — 미래 개발자가 prebuild에 deep-axis를 실수로 import해도 정적 가드가 침묵 통과하지 않게 봉인.

> **`_FORBIDDEN_IMPORTS` 문구 정정(결정 D12):** 기존 5종에 포함된 `cycle`/`seriesFetch`는 'fetch 강제 모듈'이라기보다 *`seriesFetch`(FRED/ECOS 직호출)를 호출하는 상위/하위 모듈*이라 prebuild에서 import 자체를 정적으로 막는 belt-and-suspenders 가드다. 추가하는 `forecast.forecast`·`rates.rates`도 같은 성격(둘 다 내부에서 `getGather`/`fetchSeriesList`로 online fetch) — "fetch 강제"가 아니라 "seriesFetch 경유 online 호출 상위 모듈"로 문구를 정정한다. GaR(`crisis.growthAtRisk`)은 시리즈를 인자로 받는 순수 함수라 그 자체는 fetch하지 않으나, sync에서 FCI/GDP를 fetch해 넘기므로 prebuild가 호출할 일이 없다 — forbidden 목록에 추가하지 않고 forecast/rates 2종만 추가한다(과봉인 회피).

### 4.2 신규 sync 도구 — `buildMacroRegime.py` (단일 도구·단일 HF 경로)

`buildMacroCycle.py` 패턴(analyze → write → deploy) 복제. forecast 4모델 + rates 곡선 + GaR + Hamilton regime band를 **한 묶음**으로 계산해 `macro/regime/{kr,us}.json` 단일 경로로 push(분리 금지 — KR은 forecast가 CLI composite뿐이라 별 파일이 빈약해짐).

```python
# .github/scripts/sync/buildMacroRegime.py (신규·scripts/ 폴더 금지 가드 준수)
"""macro forecast 4모델 + 수익률곡선 + GaR 분포 + Hamilton regime band
→ HF macro/regime/{kr,us}.json (sync 단계).

analyzeForecast(probit·Sahm·LEI·Hamilton) + analyzeRates(yieldCurve)
+ growthAtRisk(FCI 조건부 GDP 분위) 는 FRED/ECOS fetch 의존이라 sync 단계
책임. Hamilton regime band(smoothedProbs)는 analyzeForecast 결과에 없으므로
cycles.regimeSwitching.hamiltonRegime 을 직접 호출해 HamiltonResult.smoothedProbs
에서 추출한다(forecast.py 는 contractionProb 만 노출·smoothedProbs 드롭).
prebuild buildMacroJson.py 가 본 JSON 을 다운로드해 regime 키로 조립(offline).
buildMacroCycle.py 와 동형 — 같은 cron·같은 머신.

런타임 예산(fetch vs CPU 분리):
  - fetch: analyzeForecast(~12 LEI 시리즈 + UNRATE + GDP) + analyzeRates(DGS
    8만기) + GaR(FCI + GDP) ≈ 기존 analyzeCycle 대비 ~30 FRED fetch 증분.
    HF bulk parquet cache(data/macro restore-keys) hit 시 online fetch 최소.
  - CPU: Hamilton EM(maxIter=50·2-regime AR(1)) + GaR IRLS 분위회귀(5분위
    ×maxIter 50) + nowcast Kalman DFM 은 *순수 numpy CPU* — network 아닌
    연산 시간. 분기 시계열(~수십~수백 관측)이라 초 단위. macroData.yml
    timeout-minutes:120 에 fetch+CPU 둘 다 충분.
시리즈 단위 try/except — 실패는 missing payload, FRED rate-limit 시에도 전체 중단 0.

실행:
    uv run python -X utf8 .github/scripts/sync/buildMacroRegime.py
    uv run python -X utf8 .github/scripts/sync/buildMacroRegime.py --push
환경변수: HF_TOKEN(--push), FRED_API_KEY/ECOS_API_KEY(fetch·HF cache 우선).
"""
def _analyzeRegime(market: str) -> dict:
    from dartlab.macro.forecast.forecast import analyzeForecast
    from dartlab.macro.rates.rates import analyzeRates
    from datetime import datetime, timezone
    out = {"market": market, "computedAt": datetime.now(timezone.utc).isoformat()}
    forecast = None
    try:
        forecast = analyzeForecast(market=market)
        out["forecast"] = _extractForecast(forecast, market)   # §3.3/§3.4 게이트
    except Exception as e:
        out["forecast"] = {"models": {}, "missing": [_miss("forecast", e)]}
    try:
        r = analyzeRates(market=market)
        out["rates"] = _extractRates(r, forecast, market)       # §4.3
    except Exception as e:
        out["rates"] = {"missing": [_miss("rates", e)]}
    if market.upper() == "US":
        try:
            out["gar"] = _extractGaR(market)        # §3.7 — growthAtRisk 직접 호출
        except Exception as e:
            out["gar"] = {"status": "표본 부족·표시 보류", "missing": [_miss("gar", e)]}
        try:
            out["regimeBand"] = _extractRegimeBand(market)   # §4.3 — smoothedProbs 직접
        except Exception as e:
            out["regimeBand"] = {"missing": [_miss("regimeBand", e)]}
    return out
```

빌드/deploy는 `buildMacroCycle.py`의 `buildCycle`/`deploy`와 동형 — `for market in ("KR","US")`·축별 try/except(continue 아닌 missing payload·전체 중단 금지)·`api.upload_file(path_in_repo=f"macro/regime/{market}.json", ...)`. `argparse --push`·`--repo-id eddmpython/dartlab-data` 동일.

### 4.3 추출 규칙 — 가차없는 bake 최소화 (artifact 예산 §4.6)

**forecast 추출 (`_extractForecast` — §3.3/§3.4 게이트 동반):** 평면 묶음 `{models:{...}, missing}`. 합산 필드 스키마에 부재 → verdict 부활 구조적 차단. agreement는 **bake 안 함**(view-model 파생·SSOT drift 회피).
- `probit`: {probability, probabilityRounded(5%p 반올림·예 0.20), zone(low/moderate/elevated/high·4단계), zoneLabel(낮음/보통/경계/높음), spread, horizon:"12M", timeKind:"leading", precisionNote:"Estrella-Mishkin 고정계수·표준오차 미산출", asOf, seriesId:"T10Y3M", staleAfterDays:7}.
- `sahm`: result가 None 아니면 {value, triggered, zone(normal/warning/recession), zoneLabel, horizon:"realtime", timeKind:"trigger(동행)", asOf, seriesId:"UNRATE", staleAfterDays:45}. result None이면 {status:"데이터부족·표시 보류"}. (분기 대상 둘뿐·dead path 없음·§3.4.)
- `lei`: 개수 게이트(§3.4) 통과 시 US={level, mom6m, signal(expansion/caution/recession_warning), signalLabel, availableComponents, totalComponents, overlapNote:"term-spread·initial-claims 내포(probit/Sahm 부분 상관)", horizon:"6-9M", timeKind:"leading", asOf, staleAfterDays:75}. KR={cliMomentum, cliLevel, growthApprox, growthLabel, asOf, staleAfterDays:75}(shape 다름 명시). `availableComponents/totalComponents < 0.6`이면 {status:"구성요소 부족·표시 보류", availableComponents, totalComponents}.
- `hamilton`(US만): converged + 분리도 이중 게이트(§3.4). 통과 시 {contractionProb, converged, iterations, separation(=(mu_exp−mu_con)/max σ·params 산출), timeKind:"retrospective", horizon:"동행", staleAfterDays:120, revisionLabel:"분기 GDP·수정 대상", asOf, seriesId:"A191RL1Q225SBEA", seriesSource:"FRED"}. 미수렴/분리약함 시 contractionProb null + status. **KR Hamilton은 표면화 보류**(§3.2·단위 parity 미확정)이므로 KR forecast.models에 hamilton 키를 두지 않고 `missing:[{id:"hamilton", status:"단위 parity 미확정·표시 보류", reason:"GROWTH↔A191 단위 동일성 미확정"}]`로 둔다.
- `params`(전이행렬 전체) **컷**(분리도 계산에 쓴 mu/sigma만 separation 스칼라로 압축). `nowcast` 전체 **컷**(§3.6·단 vintage 필드는 둠).

**rates 추출 (`_extractRates(r, forecast, market)`):** `{spread10y3m, sign, curveShape, curveShapeLabel, asOf, seriesId:"T10Y3M", curveSource:"NelsonSiegel.interpretation", staleAfterDays:7, missing}`. 두 가지 설계 정정:
- **spread 출처(결정 D3·GROUND-TRUTH 7):** `rates.yieldCurve`에는 spread 필드가 없다(beta0/beta1/beta2/lambda/rmse/interpretation/description만). T10Y3M spread는 `forecast.recessionProb.spread`에만 존재 → spread10y3m은 **forecast.probit.spread를 재사용**한다(rates 축에서 직접 추출 금지·null 빠짐 방지). US 전용(probit 없으면 missing).
- **curveShape 출처:** beta1 부호 직역은 금지(엔진 docstring과 구현 부호가 엇갈림). beta1을 *직접 쓰지 않고* 엔진이 이미 계산한 **구조화 enum `yieldCurve.interpretation`**(steep_normal/normal/flat/inverted)를 채택한다. sync는 이 4개 고정 enum 값을 한국어 라벨로 매핑한다(SSOT 매핑·prose 파싱 0): `steep_normal→"가파른정상"`, `normal→"정상"`, `flat→"평탄"`, `inverted→"역전"`. beta0~2·lambda·rmse·termPremium·bondRiskPremium 나머지 **전체 컷**.

**GaR 추출 (`_extractGaR(market)` — US만·§3.7):** sync 내부에서 GDP growth + FCI 시리즈(`liquidity.fci.history` 있으면 그것을, 없으면 `fetchSeriesList(NFCI)`≥20로 대체 — `summary._addGrowthAtRisk`(L271-287) fallback 패턴 복제)를 확보해 `growthAtRisk(fci, gdp, horizon=4)`를 직접 호출. None이면 `{status:"표본 부족·표시 보류"}`. 통과 시 `{gar5, gar25, median, gar75, gar95, skewness, tailRisk, tailRiskLabel, currentFCI, observations, horizon:4, timeKind:"forward", asOf, seriesNote:"FCI 조건부 GDP 성장률 분위(점추정 아닌 조건부 분포)", staleAfterDays:120, revisionLabel:"분기 GDP·수정 대상"}`. description은 컷(view-model이 분위에서 직접 렌더).

**Hamilton regime band 추출 (`_extractRegimeBand(market)` — US만·§4.3·GROUND-TRUTH 2 정합):** forecast.py result는 `contractionProb`(=smoothedProbs[-1,1])만 노출하고 **smoothedProbs 전체 배열은 드롭**한다(GROUND-TRUTH 2). regime band(시간축 스파크)는 배열이 필요하므로 sync가 `cycles.regimeSwitching.hamiltonRegime(gdp_vals, maxIter=50)`를 **직접 호출**해 `HamiltonResult.smoothedProbs`에서 최근 ~24분기의 침체확률 열(`smoothedProbs[-24:, 1]`)을 추출한다. analyzeForecast 결과에 의존하지 않고 lower-level cycles 함수를 직접 호출하는 것이 정공법이다(sync는 online·cycles import 정당). `{band: [수축확률 ~24개 float], converged, separation, timeKind:"retrospective", horizon:"동행", asOf, staleAfterDays:120}`. 게이트 탈락(미수렴·분리약함) 시 `{status: "..."}`(band 미산출). 값 길이는 시계열 길이에 따라 ≤24(부족하면 가진 만큼).

### 4.4 prebuild 조립 확장 — `buildMacroJson.py`

`_analyze_market`(cycle·L113-145)와 동형 `_load_regime(market)`를 추가: localCache(`data/macro/regime/{lower}.json`) → `hf_hub_download(filename=f"macro/regime/{lower}.json")` → missing payload 3단(현 `_analyze_market` 패턴 복제·외부 API 0·`enforceOffline` 통과).

```python
# buildMacroJson.py main() 확장 (현 output 직전 L218)
kr_regime = _load_regime("KR")   # transmission 패턴(L217)과 동일: 동결 전달, freshness 재계산 0
us_regime = _load_regime("US")
output = {
    "version": "v20",  # v19→v20 bump
    "asOf": date.today().isoformat(),
    "kr": kr, "us": us,
    "transmission": transmission, "sectorTailwind": sector_tailwind,
    "regime": {"kr": kr_regime, "us": us_regime},  # 신규 키
}
```

**freshness 동결 전달 불변규칙:** 깊은 축은 sync 시점 asOf로 동결된다. prebuild가 freshness를 재계산하면 거짓 신선도가 된다 → prebuild는 transmission payload처럼 *그대로 통과*(L217-224 패턴). 각 모델 sub-key의 독립 asOf + staleAfterDays(probit 7일·Sahm 45일·LEI 75일·Hamilton/GaR 120일 — vintage 다름)를 단일 `regime.asOf`로 뭉뚱그리지 않는다.

### 4.5 워크플로 배선 + 첫 배포 순서 게이트

워크플로 파일명은 **`.github/workflows/macroData.yml`**(GROUND-TRUTH 5)이며 raw 스크립트가 아니라 **`dartlab.pipeline macro` 스테이지**를 호출한다(`uv run python -X utf8 -m dartlab.pipeline macro`). 그 macro 스테이지(`src/dartlab/pipeline/stages/macro.py::runMacro`)가 `buildMacroData(--source --push)` + `buildMacroCycle(--push)`를 동형 호출한다. 따라서 배선은 yml step이 아니라 **`runMacro`에 `buildMacroRegime` 호출을 추가**한다(워크플로 무수정·과증식 회피).

**runMacro rc 구조(결정 D11·GROUND-TRUTH 6):** 현재 `runMacro`는 rc1=buildMacroData(--source --push), rc2=buildMacroCycle(--push) if rc1==0 else 1, 실패 msg `macro rc=data:{rc1}/cycle:{rc2}`다. regime 추가:

```python
# src/dartlab/pipeline/stages/macro.py::runMacro 확장
rc1 = runScript("buildMacroData.py", "--source", source, "--push")   # 기존
rc2 = runScript("buildMacroCycle.py", "--push") if rc1 == 0 else 1     # 기존
rc3 = runScript("buildMacroRegime.py", "--push") if rc1 == 0 else 1    # 신규
# 실패 집계: ok = (rc1 == 0 and rc2 == 0 and rc3 == 0)
# 실패 msg: f"macro rc=data:{rc1}/cycle:{rc2}/regime:{rc3}"
```

- **rc2↔rc3 독립(불가침·결정 D11):** rc3(regime)는 `rc1 == 0`에만 의존하고 **rc2(cycle) 결과에 의존하지 않는다.** cycle 빌드가 실패해도(rc2≠0) regime 빌드는 막히지 않는다 — 둘 다 buildMacroData FRED bulk 캐시(rc1)만 공유하고 서로 독립이다. rc3가 rc1==0을 게이트하는 이유는 buildMacroData가 채운 FRED bulk 캐시(data/macro)가 있어야 fetch 비용이 적기 때문이지 cycle 산출물 때문이 아니다. 따라서 `rc3 = ... if rc1 == 0 else 1`(rc2 무관)이 정공법이다.
- **MONITORED_WORKFLOWS:** `macroData.yml`이 이미 등록되어 있으면 변경 0(새 scheduled 워크플로 미신설).

**첫 배포 순서 게이트(차단):** 머지 후 sync가 `macro/regime/{kr,us}.json`을 publish하기 *전에* prebuild가 먼저 돌면 `hf_hub_download`가 파일 부재로 raise→missing payload→Regime 렌즈 첫 배포 창에서 빈 렌더. §10이 롤백-safe로 덮으나 침묵 결손을 피하려면 런치 순서를 차단 게이트로 박는다: **① 머지 → ② sync 1회 수동/dispatch 실행(`workflow_dispatch source=all`) → ③ HF `macro/regime/{kr,us}.json` publish 확인 → ④ 그 다음에 prebuild(landing 빌드)**. 운영자는 ③ 확인 전 landing 재배포를 보류한다.

### 4.6 artifact 예산 (measured baseline·결정 D11)

현 macro.json = **13,570 bytes(`wc -c` 실측·650줄·대부분 transmission)**. regime payload 추정: 시장당 forecast 4모델 ×~9필드 + rates ~8필드 + GaR ~12필드 + regimeBand(~24 float) ≈ 2.5~4KB → 2시장(KR은 CLI 1타일이라 작음) ~4~6KB. **착수 직후 의무 절차:** `buildMacroRegime.py`를 1회 실행해 `macro/regime/{kr,us}.json` 산출 후 `wc -c`로 실측 byte를 측정하고, 그 실측값을 본 §4.6과 §9.2 테스트 단언에 박는다(스키마 실제 필드수·regimeBand 길이 반영). 잠정 단언 = **≤25,600 bytes(25KB)**(반증 가능한 baseline·실측 13,570 + regime ~6KB + 여유). 1회 측정 후 여유가 부족하면 regimeBand 길이를 16분기로 줄이거나 description 컷을 강화해 ≤25.6KB를 재확인한다. crisis(GaR 외)/scenario/nowcast/params 컷이 예산을 지킨다.

### 4.7 edge 캐시 무효화

macro.json은 `landing/static/dashboards/`의 정적 자산이다(CF worker proxy 경유 HF range fetch 대상 아님). landing 배포 시 정적 자산은 새 빌드 해시로 서빙되어 client·edge 모두 갱신된다. version body bump(v20)은 client 디버그 확인용이며, edge 무효화는 **landing 재배포가 담당**한다. worker 캐시 endsWith 함정(market_filings 교훈)은 macro.json에 비해당(worker 캐시 경로 아님) — 단 §9.2에서 `checkUiDataWiring`로 origin 무변경을 단언한다.

---

## 5. UI — 재설계 토대에 progressive disclosure 통합

### 5.1 첫 화면 4블록 = 픽셀 불가침 + 단 1줄 증분

재설계 §3.2의 4블록(A Phase / B Pulse / C Exposure Map 단일주역 / D Gate+Release)·§5.2 height 예산·§5.4 면적 ≥40% 게이트·§5.1 시각 토큰 SSOT는 **전부 불변**. 첫 화면 유일한 증분:

- **A블록 Phase Strip 전향 분수** — `us.transition`이 있으면 US 국면 라벨 옆에 마이크로라벨: `· 둔화→수축 1/3 충족`. `kr.transition===null`이라 KR엔 렌더 안 함. transition.progress 백분율·진행바 금지 — 정수 분수 "1/3 충족"만(gauge 시각 혼동 차단).
- **52px·무wrap height 안전성(불가침 게이트 보호):** 재설계 A블록은 이미 `KR ▓스태그(성장↓물가↑) US ▓리플레(성장↑물가↑) 업종 ▓반도체 +0.31`로 데스크톱 한 줄을 채운다. 전향 분수 추가가 960px 한 줄을 넘칠 위험이 실재한다. **규칙:** 전향 분수는 US 국면 칩에 *inline 시도*하되, `.mlPhaseStrip`이 **데스크톱에서 overflow(한 줄 초과) 감지 시 전향 분수를 US 칩의 두 번째 줄(`display:block`·9.5px dim)로 강등**한다(A블록 height 52→그대로 유지). 즉 A블록 height 재예산(64) 없이 무스크롤 692px 게이트를 보존한다. 두 번째 줄로 내려가도 첫 화면 증분은 1줄이며 .mlBody 합계 불변.
- 침체확률 4모델·수익률곡선·GaR 분포·regime band·LEI 기여도·quadrant 방향은 **첫 화면 금지** — 전부 Regime 렌즈로. (confluence는 *나란히 놓여야* 비교 가능한데 첫 화면 1줄 압축은 cherry-pick 부활.)

### 5.2 깊이의 단일 진입점 — A블록 클릭 → Regime 렌즈 `<details>` 1개

신설 4번째 탭 **거부**(재설계가 5→3탭으로 깎은 성과 역행). 대신 **A블록 Phase Strip 클릭 → 인라인 `<details>` 1개**(기본 닫힘·7초 첫인상 오염 0). 재설계 §3.4 `<details>` 상한을 **"경로 탭 ≤2 + 계기판 탭 Regime ≤1"**로 재정의(탭 신설 0).

Regime 렌즈 내부 = **≤6 줄/칩 상한**(13섹션 재현 방지). 얇은 가로 띠로 쌓되 누적 아님:
1. **침체 confluence 스트립** (가변 N 텍스트 타일 + agree/diverge 불일치 모델명 텍스트·§3.5)
2. **수익률곡선 1줄** (형태 라벨 + spread + "역전≠즉시침체" + "형태=NS·spread=T10Y3M 동일곡선" 라벨·§3.5)
3. **GaR 4Q 전향 분포** (분위 막대 5개 + skewness + tailRisk + "조건부 분포·점추정 아님" 라벨·§3.7)
4. **Hamilton regime band** (최근 ~24분기 수축확률 가로 스파크 1줄·시간축 명시·회고 라벨·§5.4)
5. **quadrant 방향** (growth/inflation 방향 + assetImplication + C블록 초점채널 정합 라벨·§6.3, raw 숫자 0)
6. (KR) CLI momentum 1타일 / (US) 위 1~5

crisis(GaR 외)/liquidity/sentiment는 Regime 렌즈에 **없음** — crisis만 근거 탭 GHS zone 1줄.

### 5.3 침체 confluence 시각 인코딩 — fan chart·막대 구조적 금지 (GaR은 예외)

`forecast.recessionProb`는 단일 probit 확률 1개(분포 배열 없음). probit·Sahm·LEI·Hamilton 4모델은 서로 다른 척도(probit 0~1 확률·Sahm %p·LEI %YoY·Hamilton 0~1 확률)라 **동일 높이 막대로 나란히 두면 막대 길이=비교가능 오독**이 발생한다. 인코딩 = **N개 가로 "값+zone 칩" 텍스트 타일**(막대 아님). 각 타일: modelName · 값(자기 단위·probit은 zone 주역+`~20%` 보조·§3.4) · zoneLabel · **호라이즌·시간성 라벨**(§3.4) · asOf · seriesId · stale. 각 타일에 척도 한계 라벨(`title`): probit "Estrella-Mishkin 고정계수·표준오차 미산출(점추정)" / LEI "term-spread·initial-claims 내포(부분상관)" / 공통 "zone은 모델별 임계로 산출된 범주 — 모델 간 동일 확률 아님". agree/diverge는 점수 아닌 불일치 모델명 텍스트(§3.5). 색=zone/evidence 상태지 방향(빨강=악재) 아님(재설계 §5.4 단일 색축 계승). 게이트 탈락(분리약함 Hamilton·구성요소부족 LEI·데이터부족 Sahm)은 타일이 dim·"표시 보류"로 빠지고 헤더에 "N개 중 M개 유효".

> **GaR만 분위 막대/미니 fan 허용(§3.7):** GaR은 confluence 타일이 *아니다* — 별도 분포 요소다. probit 점확률을 막대/fan으로 그리는 것은 금지지만, GaR의 5분위(5/25/median/75/95)는 진짜 조건부 분포라 분위 막대 5개 또는 좌우 비대칭 미니 fan이 정당하다. GaR 막대는 confluence 타일 스트립과 *시각적으로 분리된 행*에 두어 점확률과 분포가 섞이지 않게 한다.

### 5.4 Regime 렌즈 펼침 height 예산 + 면적 게이트 관계

재설계 §5.2 height 예산(.mlBody 556px·C Map 296px·모달 692px)은 SSOT다. Regime 렌즈는 **A블록 inline 확장**(A블록 안에서 아래로 펼쳐짐)이지 별도 블록·Map 자리 침범이 아니다. 펼침 height 증분:

| Regime 렌즈 요소(펼침) | height |
|---|---|
| 헤더(N모델·유효 M) | 16px |
| confluence 텍스트 타일 1줄(가로·N타일) | 56px |
| 수익률곡선 1줄 | 18px |
| GaR 분위 막대 행 | 40px |
| Hamilton regime band 스파크 1줄 | 20px |
| quadrant 방향 + 초점 정합 1줄 | 18px |
| 구분선·패딩 | 16px |
| **펼침 총 증분** | **~184px** |

- **regime band 시각 규칙(결정 D7):** Hamilton smoothedProbs 최근 ~24분기를 **가로 스파크 1줄**(시간축 좌→우, 높이 20px)로 그린다. **막대 차트 아님·점추정 아님** — 시계열이라 fan 유혹 없이 그대로 읽힌다. 라벨: "Hamilton 수축확률 24분기(회고적 regime·smoothed)" + 시간축 시작/끝 분기. 첫 화면 무오염(Regime 렌즈 details 안에만).
- **면적 게이트 관계(불가침 보존):** 첫 화면(렌즈 닫힘) Map 면적 비율은 재설계 §9.3대로 유지된다. **렌즈 펼침은 A블록을 ~184px 늘려 .mlBody가 ~740px가 되고 내부 스크롤이 발생**한다(692 모달 무스크롤 게이트는 *닫힘 상태*에만 적용·재설계 §9.3과 동일). 펼침 시 Map은 여전히 유일 테두리 주역이고 Regime 렌즈는 A블록 inline 확장이라 **Map과 면적 경쟁하지 않는다**(렌즈는 텍스트 띠+얇은 분위 막대·테두리 0). 따라서 면적 ≥40% 게이트는 *닫힘 상태 측정*으로 단언하고, 펼침 상태는 "Map 단일 테두리 유지 + 렌즈 텍스트 띠(테두리 0)" 구조 단언으로 대체한다(§9.1).

### 5.5 타일 내부 px 위계 (결정 D9 — redesign Pulse tile 밀도 초과 금지)

confluence 텍스트 타일·GaR·regime band의 내부 정보 위계를 못 박는다(mono 박스 벽 회귀 방지). 시각 토큰표(재설계 §5.1)에 다음 행을 추가한다:

| 타일 내부 요소 | 위계 | px |
|---|---|---|
| zoneLabel (낮음/경계/침체 등) | 1차 (주역) | 13px / weight 700 |
| modelName + horizon 라벨 | 2차 | 10px / weight 600 |
| asOf + seriesId + stale | 3차 (메타) | 9px / `--dl-ink-dim` |

타일 내부 3단 위계가 재설계 Pulse tile(값 13px·라벨 10px·메타 9.5px)의 밀도를 *초과하지 않는다* — confluence 타일은 Pulse tile과 동일 밀도 천장을 공유한다(박스-in-박스 벽 회귀 차단). GaR 분위 막대 라벨도 동일(분위명 9px·값 10px). regime band는 스파크+9px 캡션만.

### 5.6 ASCII 목업 — Regime 렌즈 (US, 데스크톱)

```
┌─ MACRO LENS ─────────────────────────────────────────────────────────────┐
│ 삼성전자  005930  반도체            macro 2026-06-18 · price 06-19 · fin 1Q26 │
├──────────────────────────────────────────────────────────────────────────┤
│  [ 계기판 ]   경로    근거                                                   │
│  노출 점검표입니다. 정량 민감도·투자 결론·가격 산출은 표시하지 않습니다.(░)    │
├──────────────────────────────────────────────────────────────────────────┤
│ A 국면 ▾  KR ▓스태그(성장↓물가↑)[회고]  US ▓리플레[회고]                     │ ← 클릭 ▾
│           · 둔화→수축 1/3 충족  ← (overflow 시 US 칩 2번째 줄로 강등·§5.1)    │
│  └ (클릭) ───────────────────────────────────────────────────────────────  │
│  ╭─ 국면 렌즈 (Regime Lens) · 회고는 phase, 검증은 아래 ────────────────────╮│ ← <details> 1개
│  │ 침체 신호 (4모델 중 3 유효 · 호라이즌·시간성 상이 · 동의: 낮음           ││
│  │           — LEI 둔화 vs probit 확장, 곡선 미반영)                        ││ ← 불일치 모델명(§3.5)
│  │  ┌probit────┐ ┌Sahm──────┐ ┌LEI───────┐ ┌Hamilton──┐                   ││
│  │  │낮음 ~20% │ │미발동    │ │경계      │ │표시 보류 │ ← 분리약함/미수렴 dim││
│  │  │12M 선행  │ │실시간동행│ │6~9M 선행 │ │동행·회고 │                   ││ ← 호라이즌·시간성(§3.4)
│  │  │확률T10Y3M│ │%p UNRATE │ │%YoY CBLEI│ │ 분리약함 │                   ││
│  │  │░06-15    │ │░05-01    │ │░05월     │ │  ░       │                   ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                   ││
│  │  ░ probit=고정계수·SE미산출(점추정) · LEI=term/claims 내포(부분상관)     ││ ← 척도/독립 한계
│  │ 수익률곡선  평탄 · 10Y-3M +0.40%p ░06-15 (역전≠즉시침체·형태=NS·spread=동일곡선)││
│  │ GaR 4Q 전향 분포 [조건부 분포·점추정 아님] tail 주의 · 비대칭 −0.8 ░Q1   ││
│  │   5%▏▁  25%▏▃  중위▏▆  75%▏█  95%▏█  (FCI 조건부 GDP 성장률 분위)        ││ ← 분위 막대(§3.7)
│  │ Hamilton 수축확률 24분기(회고적·smoothed) ▁▁▂▂▃▅▆▅▃▂▁ ░23Q1→26Q1        ││ ← regime band(§5.4)
│  │ 국면 사분면 성장↑ 물가↑ → 원자재·TIPS 유리 [회고] · 초점채널 EXPORT 방향 정합 ││ ← C 정합(§6.3)
│  ╰──────────────────────────────────────────────────────────────────────╯│
├──────────────────────────────────────────────────────────────────────────┤
│ B 무엇이 움직였나  …(재설계 그대로·불변)…                                    │
│ C 어느 채널에 닿나 (Exposure Map · 단일 주역 · 테두리 패널) …(불변)…          │
│ D 증거 게이트 · 언제 다시 보나 …(불변)…                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

KR은 confluence 타일을 **CLI momentum 1타일**만으로 두고 "probit/Sahm/Hamilton/GaR: US 전용 또는 단위 parity 미확정(N/A)" 회색 라벨 1줄(빈 타일 금지). KR엔 GaR·regime band 행 없음(US 중심).

### 5.7 모바일 (≤560px)

Regime 렌즈 N 타일은 가로 스와이프(`overflow-x:auto`) 또는 2×N 그리드. GaR 분위 막대는 세로 5행 stack 허용. regime band 스파크는 가로 전폭. A블록 전향 분수는 세로 줄바꿈 허용(데스크톱 overflow 강등 규칙이 모바일에선 자연 줄바꿈). Exposure Map 주역성·재설계 모바일 레이아웃 불변.

---

## 6. 데이터 계약 — `regime` 키 스키마 + view-model 매핑

### 6.1 macro.json `regime` 키 (신규)

```jsonc
"regime": {
  "us": {
    "market": "US",
    "computedAt": "2026-06-18T...Z",
    "forecast": {
      "models": {
        "probit":   {"probability":0.18,"probabilityRounded":0.20,"zone":"low","zoneLabel":"낮음","spread":0.40,"horizon":"12M","timeKind":"leading","precisionNote":"Estrella-Mishkin 고정계수·표준오차 미산출","asOf":"2026-06-15","seriesId":"T10Y3M","staleAfterDays":7},
        "sahm":     {"value":0.10,"triggered":false,"zone":"normal","zoneLabel":"정상","horizon":"realtime","timeKind":"trigger(동행)","asOf":"2026-05-01","seriesId":"UNRATE","staleAfterDays":45},
        "lei":      {"signal":"caution","signalLabel":"경계","mom6m":-1.2,"availableComponents":9,"totalComponents":10,"overlapNote":"term-spread·initial-claims 내포(probit/Sahm 부분 상관)","horizon":"6-9M","timeKind":"leading","asOf":"2026-05","staleAfterDays":75},
        "hamilton": {"contractionProb":null,"converged":false,"separation":0.31,"iterations":50,"status":"EM 미수렴","timeKind":"retrospective","horizon":"동행","staleAfterDays":120,"revisionLabel":"분기 GDP·수정 대상","asOf":"2026-Q1","seriesId":"A191RL1Q225SBEA","seriesSource":"FRED"}
      },
      "missing": []
    },
    "rates": {"spread10y3m":0.40,"sign":"+","curveShape":"flat","curveShapeLabel":"평탄","curveSource":"NelsonSiegel.interpretation","asOf":"2026-06-15","seriesId":"T10Y3M","staleAfterDays":7,"missing":[]},
    "gar": {"gar5":-1.5,"gar25":0.4,"median":2.1,"gar75":3.2,"gar95":4.4,"skewness":-0.8,"tailRisk":"elevated","tailRiskLabel":"주의","currentFCI":0.32,"observations":42,"horizon":4,"timeKind":"forward","seriesNote":"FCI 조건부 GDP 성장률 분위(점추정 아닌 조건부 분포)","asOf":"2026-Q1","staleAfterDays":120,"revisionLabel":"분기 GDP·수정 대상"},
    "regimeBand": {"band":[0.05,0.04,0.06,0.09,0.14,0.22,0.31,0.28,0.19,0.12,0.08],"converged":true,"separation":0.74,"timeKind":"retrospective","horizon":"동행","asOf":"2026-Q1","staleAfterDays":120}
  },
  "kr": {
    "market":"KR",
    "computedAt":"...",
    "forecast":{"models":{
      "lei":{"cliMomentum":1.10,"cliLevel":99.8,"growthApprox":1.4,"growthLabel":"확장","asOf":"2026-04","staleAfterDays":75}
    },"missing":[
      {"id":"probit","status":"notApplicable","reason":"US 전용"},
      {"id":"sahm","status":"notApplicable","reason":"US 전용"},
      {"id":"hamilton","status":"단위 parity 미확정·표시 보류","reason":"GROWTH↔A191RL1Q225SBEA 단위 동일성 미확정"},
      {"id":"gar","status":"notApplicable","reason":"US 중심(FCI 입력)"}
    ]},
    "rates":{"missing":[{"id":"yieldCurve","status":"notApplicable","reason":"US 전용"}]}
  }
}
```

quadrant/transition은 **regime 키에 재bake 금지** — 기존 `kr.quadrant`/`us.quadrant`/`us.transition` 단일 SSOT를 view-model이 직접 소비(중복 bake = SSOT drift).

### 6.2 view-model 매핑 (`macroLens.ts`)

| Regime 렌즈 요소 | 사용 필드 | 결손 시 |
|---|---|---|
| A블록 전향 분수 | `transitionFraction(macro.us)` (신규) → "{t}/{t+p} 충족". `kr.transition===null`→렌더 0 | transition null → 미표시 |
| 침체 타일 | `macro.regime.us.forecast.models.{probit,sahm,lei,hamilton}` | status 있는 모델 → dim·"표시 보류" |
| agree/diverge | `agreementOf(models)` — `bucketOf`(§3.3·3단계) 파생·인접 bucket 동의·불일치 모델명 동반(§3.5). probit·곡선 1표 | 유효 <2 → "교차 불가(유효 1개)" |
| 수익률곡선 1줄 | `macro.regime.us.rates.{curveShapeLabel, spread10y3m, sign, asOf}` | missing → "수익률곡선 N/A" |
| GaR 분위 막대 | `macro.regime.us.gar.{gar5,gar25,median,gar75,gar95,skewness,tailRiskLabel,horizon,asOf}` | status/부재 → "GaR 표본 부족" |
| Hamilton regime band | `macro.regime.us.regimeBand.{band,converged,separation,asOf}` | status/부재 → band 미렌더 |
| quadrant 방향 + 초점 정합 | `macro.us.quadrant.{growth, inflation, assetImplication}` + `focusChannelAlignment`(§6.3) (growthSignal/inflationSignal **미매핑**) | quadrant 부재 → "국면 상세 없음" |
| KR CLI 타일 | `macro.regime.kr.forecast.models.lei` (hamilton은 missing status 표시·표면화 보류) | 부재 → "CLI N/A" |
| freshness | 각 요소 `asOf`+`staleAfterDays` → `daysLag > staleAfterDays` 시 STALE | asOf 없음 → "asOf 없음" |

**신규 함수 `transitionFraction(side)`:** 백분율 없이 정수 분수만 — `{ fraction: "${triggered}/${triggered+pending} 충족", from, to } | null`. `side?.transition`이 null이면 null 반환(렌더 0). 재설계가 삭제하는 `transitionLabel`(`${tr.progress}%` 방출·L1757·verdict 빌더 소속)을 **재사용하지 않는다**(L1757 % 방출 경로 재현 금지). `bucketOf`/`agreementOf`/`focusChannelAlignment`도 신규(점수 아님·서수 bucket·인접 동의·불일치 모델명 텍스트). GaR·regime band는 payload를 그대로 분위 막대/스파크로 렌더하는 얇은 매핑만(파생 계산 0).

`MacroLensSnapshot`에 `regime?: MacroRegimeView` sub-view 추가(읽기전용 표시 데이터·verdict 아님). 기존 `freshnessFromAsOf`·daysLag 재사용·모델별 staleAfterDays는 payload 값 우선. `MacroFile` 타입에 `regime?` 추가(`types.ts`). `data/origins` macro.json origin 그대로(새 origin 0).

### 6.3 국면 ↔ 종목 노출 다리 (forecast/quadrant ↔ Exposure Map·미션 성공기준)

미션 성공기준 "종목 transmission과 연결"을 view-model 차원에서 닫는다. forecast confluence는 *시장 침체국면* 축이고 C블록 Exposure Map은 *종목 노출* 축이라, 둘을 잇는 다리가 없으면 7초 사용자는 분리된 두 그림을 본다. **신규 view-model 헬퍼 `focusChannelAlignment(quadrant, focusCell)`** — 재설계 `pickFocusCell`(C블록 초점채널)의 채널 sign과 현 국면(`quadrant.growth`/`inflation` 방향)의 정합을 *라벨*로 낸다(점수·판정 아님). 예: reflation(성장↑물가↑) 국면 + 초점채널 EXPORT(+민감) → `"초점채널 EXPORT 방향 정합 — 현 국면(성장↑)과 같은 방향"`; 역방향이면 `"초점채널 RATES 역방향 — 현 국면(물가↑)과 반대"`. 정합/역방향 *서술*만 하고 "수혜/유리" 확정·민감도 숫자·매수 시사는 0(가드 §7). 이 1줄은 Regime 렌즈 quadrant 줄에 붙어(§5.6) 국면축과 노출축을 시각적으로 인접시킨다. `pickFocusCell` 결과가 blocked/없으면 라벨 미렌더(빈칸 금지).

---

## 7. 가드 체크리스트

**절대 금지 (위반 시 설계 무효):**
- [ ] forecast 합산 점수 필드 — bake·view-model·UI 0 (N타일 나란히만·0~100 합산·gauge 금지).
- [ ] summary 6막 점수·`recessionDashboard.composite`·`probabilityComposite` — bake·표면화 0 (단일 macro score=verdict 벡터).
- [ ] agreement를 ordinal/score/badge로 렌더 — 불일치 모델명 동반 텍스트만·인접 bucket 동의(§3.5·D4).
- [ ] confidence(high/medium/low) 기반 타일 ordinal 정렬·강조 — 금지(verdict 백도어·grep 게이트).
- [ ] 단일 모델 침체 단독 노출 — probit만 크게 금지(N모델 동반·cherry-pick 구조적 차단).
- [ ] confluence 타일을 동일 높이 막대로 — "값+zone 칩" 텍스트 타일만(척도 비통일·막대 길이 비교 오독 차단·§5.3).
- [ ] **4모델을 단일 호라이즌으로 묶음 — 타일별 호라이즌·시간성 라벨 강제(probit 12M선행·Sahm 실시간트리거(동행)·LEI 6~9M선행·Hamilton 동행·회고적·GaR 4Q전향 분포·§3.4·D2).** 스트립 헤더 단일 '12M·확률' 프레임 금지.
- [ ] probit·수익률곡선을 독립 신호로 이중계상 — 동일 T10Y3M 명시(형태=NS·spread=T10Y3M) + agreement 1표(§3.5·D3).
- [ ] LEI를 완전 독립 신호로 표기 — term-spread·initial-claims 내포 `overlapNote` 강제(§3.5).
- [ ] Hamilton을 '전향'으로 라벨 — `[동행·회고적·smoothed]` 강제(§3.4).
- [ ] Hamilton 신뢰성을 상수 `regimeLabels[1]==='contraction'`로 게이트 — **죽은 가드**(부활 금지). converged + 분리도 `separation≥0.5`(Cohen's d 중간효과·params mu/sigma 산출) 게이트(§3.4·D6).
- [ ] 미수렴/분리약함 Hamilton contractionProb 표시 — null 동결 + status(§3.4).
- [ ] **KR Hamilton을 US와 동급 신뢰도로 표면화 — 단위 parity 미확정이므로 표면화 보류·`단위 parity 미확정` status(§3.2·D6).** KR confluence는 CLI 1타일.
- [ ] 데이터부족 Sahm을 '미발동'으로 표시 — result None이면 보류 분기(None vs 정상계산 둘뿐·dead path 이중게이트 금지·§3.4·D11).
- [ ] **LEI 게이트를 Σweight(가중질량)으로 — result에 per-component dict·weight 미노출(GROUND-TRUTH 2)이라 계산 불가. `availableComponents/totalComponents` 개수 게이트(≥0.6)로 대체·`_LEI_WEIGHTS` 의존 0(§3.4·D5).**
- [ ] probit `probability` 소수 2자리를 주역으로 — zone 주역·확률 5%p 반올림 보조·"고정계수·SE미산출" 라벨(§3.4·§5.3).
- [ ] **fan chart / gauge / donut — 분포 미산출 모델(probit 점확률·nowcast 점추정) 한정 0. GaR 5분위는 진짜 조건부 분포라 분위 막대/미니 fan 정당(§3.7·D1).**
- [ ] GaR을 단일 숫자(gar5만)로 붕괴 — median 동반·5분위 전부·skewness(§3.7·엔진 AntiPattern).
- [ ] Hamilton regime band를 막대/점추정으로 — 시계열 가로 스파크 1줄·회고 라벨(§5.4·D7).
- [ ] transition.progress 백분율·진행바 — 정수 분수 "1/3 충족"만. `transitionLabel`(L1754 함수·L1757 `%` 방출) 재사용 금지·신규 `transitionFraction`(§6.2·D10).
- [ ] quadrant `growthSignal`/`inflationSignal` raw 숫자 노출 — 방향 라벨(rising/falling)만.
- [ ] rates spread를 rates.yieldCurve에서 추출 — 없는 필드(null 빠짐). forecast.probit.spread 재사용(§4.3·D3·GROUND-TRUTH 7).
- [ ] curveShape를 beta1 부호 직역 / prose prefix 파싱 — 엔진 `interpretation` enum 4값 매핑(§4.3).
- [ ] 국면↔초점채널 정합을 '수혜/유리' 확정·민감도 숫자로 — 방향 정합 *서술*만(§6.3).
- [ ] crisis를 Regime 렌즈/forecast 교차 진열 — 근거 탭 GHS zone 1줄이 절대 상한(GaR은 §3.7로 분리·crisis 제외에서 명시 분리).
- [ ] nowcast를 'notWiredYet'로 표기 — 산출됨·구간 부재로 `computedButSuppressed`(§3.6).
- [ ] 셀 배경 방향색(--up/--dn) — 색=zone/evidence 상태. 방향 빨강 금지.
- [ ] 신설 4번째 탭 — A블록 클릭 `<details>` 1개만 (탭 3개 IA 불변).
- [ ] 첫 화면 신규 축 — Regime 렌즈 기본 닫힘, 첫 화면 증분은 A블록 전향 분수 1줄(overflow 시 US 칩 2번째 줄). GaR·regime band·confluence·LEI 기여도 전부 details 안(첫 화면 불가침).

**허용 상태 라벨만:** `OBS`/`PRIOR`/`TPL`/`LOCK`/`STALE`/`MISSING`/`notApplicable`/`computedButSuppressed`/`EM 미수렴`/`레짐 분리 약함`/`데이터부족·표시 보류`/`구성요소 부족·표시 보류`/`단위 parity 미확정·표시 보류`/`표본 부족·표시 보류`/`회고적`/`전향`.

**구조 가드:**
- [ ] 회고/전향 시간축 분리(D2) — phase/quadrant/Hamilton band=[회고적], transition/probit/LEI=선행, Sahm=실시간 동행, GaR=4Q 전향 분포. 각자 자기 호라이즌·같은 칩에 섞지 않음.
- [ ] 모델별 freshness 분리 — 단일 asOf 뭉치기 금지(probit 일간·LEI 월간·Hamilton/GaR 분기 vintage 다름·revision 라벨).
- [ ] sync 동결 전달 — prebuild는 freshness 재계산 0(transmission 패턴 복제).
- [ ] offline 정적 봉인 — `_FORBIDDEN_IMPORTS`(현 5종)에 forecast.forecast/rates.rates 추가→7종(§4.1·D12 문구).
- [ ] L2 경계 — macro 엔진은 analysis import 0. 결합은 view-model만.
- [ ] 공통배선 — 로컬 :8400 없이 퍼블릭 HF만. `data/fetch`+`data/origins` 경유. `checkUiDataWiring` 신규 위반 0.
- [ ] artifact ≤25,600 bytes — 실측 13,570 + regime baseline·**1회 빌드 후 byte 실측 박제**(§4.6·D11).
- [ ] 첫 배포 순서 — sync regime publish 확인 후 landing 재배포(§4.5).
- [ ] 파이프라인 rc2↔rc3 독립 — cycle 실패가 regime 안 막음(둘 다 rc1==0 의존·§4.5·D11).

---

## 8. 영향 파일·함수 (SSOT)

### 8.1 신규
- **`.github/scripts/sync/buildMacroRegime.py`** — `_analyzeRegime`/`_extractForecast`(§3.3/§3.4 게이트: probit 정밀·sahm None분기·lei 개수게이트·hamilton 분리도)/`_extractRates`(spread=probit.spread·curveShape=interpretation enum)/`_extractGaR`(growthAtRisk horizon=4 직접 호출)/`_extractRegimeBand`(cycles.regimeSwitching.hamiltonRegime 직접 호출·smoothedProbs[-24:,1])/`buildRegime`/`deploy`/`main`. `buildMacroCycle.py` 패턴 복제·축별 try/except·런타임 예산 docstring(fetch vs CPU 분리)·HF `macro/regime/{kr,us}.json` push.

### 8.2 변경
- **`tests/architecture/test_prebuild_offline.py`** — `_FORBIDDEN_IMPORTS`(현 5종·L34-40)에 `dartlab.macro.forecast.forecast`·`dartlab.macro.rates.rates` 추가→7종(§4.1). 문구 정정(D12·"seriesFetch 경유 online 호출 상위 모듈").
- **`.github/scripts/prebuild/buildMacroJson.py`** — `_load_regime(market)` 신규(localCache→HF→missing 3단). `main()` `regime` 키 조립(L218 직전)·version v19→v20(L9·L220). `enforceOffline` 불변(L189).
- **`src/dartlab/pipeline/stages/macro.py`** — `runMacro`에 `rc3 = runScript("buildMacroRegime.py","--push") if rc1==0 else 1`(rc2 무관·D11) + 실패 집계 `ok=(rc1==0 and rc2==0 and rc3==0)` + msg `macro rc=data:{rc1}/cycle:{rc2}/regime:{rc3}`. (yml 무수정 — `macroData.yml`은 `dartlab.pipeline macro` 호출.)
- **`ui/packages/surfaces/src/terminal/lib/macroLens.ts`** — `MacroRegimeView` 인터페이스 + `transitionFraction`/`bucketOf`(3단계)/`agreementOf`(인접 동의·불일치 모델명)/`focusChannelAlignment` 헬퍼(신규·전부 점수 아님) + GaR·regimeBand 얇은 매핑. `MacroLensSnapshot`에 `regime?` 추가. `buildMacroLensSnapshot`/`buildMarketMacroLensSnapshot`에서 regime sub-view 생산. (재설계가 `transitionLabel` L1754 삭제하므로 본 PRD는 신규 `transitionFraction`만·기존 함수 미사용.)
- **`ui/packages/surfaces/src/terminal/lib/types.ts`** — `MacroFile`에 `regime?: {kr: MacroRegimePayload; us: MacroRegimePayload}` 추가.
- **`ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte`** — A블록 Phase Strip 전향 분수 inline(overflow 강등·§5.1) + 클릭 핸들러 + Regime 렌즈 `<details>`(confluence 텍스트 타일·수익률곡선·GaR 분위 막대·regime band 스파크·quadrant 방향+초점 정합). 타일 내부 px 위계(§5.5). 근거 탭 crisis GHS zone 1줄(SHOULD). 셀 배경 방향색 0·CSS 도형 칩 재사용.

### 8.3 불변 (계승)
- `RegimeQuadrant.svelte`/`LeftRail.svelte` 입구·재설계 4블록·시각 토큰·height 예산·면적 게이트·`pickFocusCell`.
- macro 엔진(`forecast.py`/`rates.py`/`cycles/_regimeSwitchingLei.py`/`cycles/_regimeSwitchingHamilton.py`/`cycles/regimeSwitching.py`/`crisis/growthAtRisk.py`/`__init__.py`) — 산출 형태 변경 0(읽기만). sync는 `cycles.regimeSwitching`·`crisis.growthAtRisk` 공개 함수를 호출(정의 복제 금지·`_LEI_WEIGHTS` 참조 0).

---

## 9. 테스트·검증

### 9.1 회귀 가드 (신규 테스트)
- **첫 화면 무오염** — Regime 렌즈 기본 닫힘·계기판 진입 시 신규 축 0개 노출(confluence·GaR·band·LEI 기여도 전부 details 안). A블록 증분은 전향 분수 1줄(닫힘 시 height 52px 유지·무스크롤 692px 게이트). overflow 시 US 칩 2번째 줄 강등.
- **펼침 구조 가드** — 렌즈 펼침 시 Map은 유일 테두리 주역 유지·렌즈는 테두리 0 텍스트 띠+얇은 분위 막대(면적 경쟁 0). 면적 ≥40%는 닫힘 측정(§5.4).
- **verdict/score grep 게이트** — (1)forecast 합산 필드 부재 (2)`summary`/`composite`/`probabilityComposite` 표면화 0 (3)recessionProb 단일모델 단독 노출 0 (4)probit/nowcast fan/gauge/donut 0 (GaR 분위 막대는 허용) (5)셀 방향색 0 (6)`transitionLabel`/백분율 미사용 (7)confidence 기반 ordinal 정렬 0.
- **confluence 정규화(3단계)** — `bucketOf` 4모델 결정론 매핑(§3.3) 단언·probit moderate→0 흡수. `agreementOf` 유효<2→"교차 불가", ≥2→인접 bucket 동의·2단계 이상만 불일치·불일치 모델명 동반·점수/badge 부재. probit·곡선 1표.
- **모델별 신뢰성 게이트** — Sahm result None→"데이터부족·표시 보류"(None vs 정상계산 둘뿐·dead path 이중게이트 부재 단언)·**LEI 게이트는 availableComponents/totalComponents 개수(≥0.6)·Σweight 미사용·`_LEI_WEIGHTS` 미참조 단언**·Hamilton converged false→null·separation<0.5→null+"레짐 분리 약함"(상수 라벨 게이트 부재 단언·임계 0.5 Cohen's d 주석).
- **KR Hamilton 보류** — KR forecast.models에 hamilton 키 부재·missing에 "단위 parity 미확정" status·KR confluence=CLI 1타일·`agreementOf`="교차 불가(유효 1개)".
- **probit 정밀 가드** — zone 주역·`probabilityRounded`(5%p) 보조·precisionNote 존재·소수 2자리 단독 노출 0.
- **GaR 분포 가드** — 5분위(gar5/25/median/75/95) 전부 매핑·median 동반·skewness 존재·tailRisk 라벨·`[4Q 전향]` horizon·분위 막대 렌더(단일 숫자 붕괴 0)·표본 부족 시 미렌더·**fan/분위 막대는 GaR에만 허용(probit fan 0)**.
- **regime band 가드** — band 배열 ≤24·가로 스파크 렌더(막대/점추정 아님)·"회고적·smoothed" 라벨·시간축·게이트 탈락 시 미렌더·smoothedProbs는 sync 직접호출 산출(analyzeForecast result에 없음 확인).
- **호라이즌·시간성 라벨(D2)** — 각 타일 horizon/timeKind 존재·Hamilton=retrospective/회고적·Sahm=trigger(동행)·GaR=forward·probit=leading·단일 호라이즌 묶음 부재.
- **이중계상·내포상관(D3)** — probit·수익률곡선 aria-label "형태=NS·spread=T10Y3M 동일곡선"·agreement 1표·LEI overlapNote 존재.
- **국면↔노출 다리** — `focusChannelAlignment` 정합/역방향 *서술*만·민감도 숫자/수혜 확정 0·pickFocusCell blocked 시 미렌더.
- **transition 분수 정정(D10)** — `us.transition` triggered/pending → "t/(t+p) 충족"(백분율 환각 차단·L1757 % 경로 미재현).
- **nowcast 상태** — `computedButSuppressed`(notWiredYet 아님)·confidence str 인지·vintage 필드 존재.
- **모델별 freshness** — probit/Sahm/LEI/Hamilton/GaR/band 각 staleAfterDays(7/45/75/120/120/120) 독립 STALE·Hamilton/GaR revisionLabel.

### 9.2 파이프라인 가드
- **prebuild offline** — `test_prebuild_offline.py`가 `buildMacroJson.py` 정적 import·main 첫 stmt(`enforceOffline`·L189) 검사 통과(`_load_regime`는 HF download만). `_FORBIDDEN_IMPORTS` 7종 후 prebuild가 forecast.forecast/rates.rates import 시 fail(정적 봉인 단언). `buildMacroRegime.py`는 sync라 비대상.
- **축별 격리** — forecast/rates/GaR/band 중 하나 sync 실패해도 cycle/transmission 빌드·해당 축 missing payload(전체 중단 0). `runMacro` rc3 실패 집계·**rc2↔rc3 독립(cycle 실패가 regime 빌드 안 막음·rc3는 rc1==0만 의존)**.
- **artifact 예산** — macro.json ≤25,600 bytes 단언(baseline 13,570·**1회 빌드 byte 실측 박제 후 재단언**·§4.6).
- **공통배선** — `checkUiDataWiring` 신규 위반 0·macro.json origin 그대로.

### 9.3 실행 (메모리 안전)
`uv run python -X utf8 tests/run.py preflight`(CI 27 게이트 SSOT). 단일 파일은 `bash tests/test-lock.sh tests/<path> -m "<marker>" -v`. svelte-check 0 errors. 수동: `buildMacroRegime.py` 로컬 실행(FRED 캐시)→`wc -c` byte 실측 박제→`buildMacroJson.py`→landing dev(5173) 눈검수. 첫 배포는 §4.5 순서 게이트 준수. UI 변경이라 commit까지만 자율·push는 운영자 명시 승인.

---

## 10. 롤백

- **데이터:** `regime` 키 미존재(prebuild가 HF에서 못 받음) → view-model `macro.regime` 옵셔널 접근, Regime 렌즈 자동 숨김·A블록 전향 분수만(이미 라이브) 또는 미표시. version v20→v19 되돌림으로 즉시 복귀.
- **sync:** `runMacro` rc3 step 제거 시 HF `macro/regime` stale → prebuild가 동결값 전달(STALE 라벨)·붕괴 0. rc2↔rc3 독립이라 rc3 제거가 cycle에 무영향.
- **UI:** Regime 렌즈 `<details>` + 전향 분수 inline만 git revert(4블록·엔진·다른 탭 무관). 각 변경 독립적.

---

## 11. Phase (MUST / SHOULD / WONT)

**MUST (1차 초강화·재설계 머지 후):**
1. `_FORBIDDEN_IMPORTS` 7종 확장(forecast.forecast/rates.rates 추가·문구 정정·정적 봉인 선행).
2. `buildMacroRegime.py` sync 도구(§3.3 3단계·§3.4 4게이트[probit 정밀·sahm None분기·lei 개수게이트·hamilton 분리도 Cohen's d 0.5]·spread=probit.spread·curveShape=interpretation enum·GaR horizon=4 직접 호출·regimeBand smoothedProbs 직접 추출·런타임 예산 fetch/CPU 분리 docstring) + HF push + `runMacro` rc3 배선(rc2↔rc3 독립).
3. `buildMacroJson.py` `regime` 키 조립(offline 불변·1회 빌드 byte 실측 후 ≤25.6KB 재확인·v20).
4. forecast confluence 텍스트 타일 스트립 + 호라이즌 라벨(D2) + `bucketOf`(3단계)/`agreementOf`(인접 동의·불일치 모델명·D4) + 4모델 신뢰성 게이트(probit 정밀·sahm None·lei 개수·hamilton 분리도).
5. rates 수익률곡선 1줄(이중계상·NS/spread 출처 라벨·D3).
6. **GaR 4Q 전향 분위 막대(D1·median 동반·skewness·tailRisk·점추정 분리 라벨) + Hamilton regime band 가로 스파크(D7·smoothedProbs sync 직접 추출).**
7. quadrant 방향 라벨(raw 0) + `focusChannelAlignment` 다리 + `transitionFraction`(백분율 없는 A블록 1줄·overflow 강등·D10) + 타일 내부 px 위계(D9).
8. KR 비대칭(CLI 1타일·Hamilton 단위 parity 보류·D6) + grep 게이트 + 회귀 테스트(죽은 가드 부재·분리도·개수 게이트·인접 동의·이중계상·내포상관·GaR 분포·regime band·nowcast 상태·다리).

**SHOULD (후속 사이클·운영자 go):**
- 근거 탭 crisis GHS zone 1줄(다중매칭·composite 절대 컷).
- nowcast — 엔진이 신뢰구간/표준오차를 산출하게 되면 `computedButSuppressed`→표면화 재검토.
- **KR Hamilton — GROWTH↔A191RL1Q225SBEA 단위 parity 확인 또는 시장별 임계 분리 후 표면화 재검토(D6).** 단위 동일성이 검증되면 KR confluence에 Hamilton 타일 추가 + GROWTH lineage(seriesId/seriesSource/seriesNote) 동반.

**WONT (의도적 제외·봉인):**
- liquidity/sentiment/assets/corporate/trade/inventory/narrative 표면화(FCI는 GaR 입력으로만 내부 사용).
- scenario 146·summary 6막 점수·composite·신설 탭·gauge·probit/nowcast fan chart·confluence 막대 비교.
- crisis(GaR 외) Regime 렌즈 진열(근거 탭 GHS zone 1줄 상한).

---

## 12. 이중 평가

**전문 개발자:** 데이터 경로가 검증된 사실 위에 선다. 침체 4모델·수익률곡선의 정의는 `cycles/_regimeSwitchingLei.py`(probit·LEI·`_LEI_WEIGHTS`·sahm)·`cycles/_regimeSwitchingHamilton.py`(hamilton)에 있고 공개 import는 `cycles.regimeSwitching`이며 forecast.py(L15)는 import만 하므로, sync는 정의 모듈이 아니라 공개 함수를 호출한다. `analyzeForecast` result는 hamilton의 `contractionProb`만 노출하고 `smoothedProbs` 배열을 드롭하므로(GROUND-TRUTH 2), regime band는 sync가 `hamiltonRegime`을 *직접 호출*해 `HamiltonResult.smoothedProbs`에서 추출하는 것이 유일 정공법이다(sync online·cycles import 정당). LEI는 result에 per-component dict·weight가 없고 `availableComponents/totalComponents` 개수만 있으므로 Σweight 게이트는 계산 불가 → 개수 게이트(≥0.6)로 대체하고 `_LEI_WEIGHTS` 의존을 제거했다(엔진 산출형태 변경 0). GaR은 `crisis/growthAtRisk.py::growthAtRisk(fci, gdp, horizon=4)`가 진짜 5분위 조건부 분포+skewness를 내고 `summary.py::_addGrowthAtRisk`가 이미 동일 패턴으로 주입하므로, sync도 동일하게 직접 호출한다(4Q 전향·crisis lag 아님). spread는 `rates.yieldCurve`에 필드 부재라 `forecast.probit.spread` 재사용이 강제되고, curveShape는 beta1 부호가 docstring/구현 모순이라 엔진의 결정론 enum `interpretation`(steep_normal/normal/flat/inverted)을 매핑한다. Hamilton `regimeLabels`는 상수 튜플이고 mu-swap이 column 1=수축을 매 iteration 보장하므로 `regimeLabels[1]==='contraction'`은 죽은 가드였고, 진짜 신뢰성 신호인 분리도 `(mu_exp−mu_con)/maxσ≥0.5`(Cohen's d 중간효과·params 산출)로 교체했다. 워크플로는 `macroData.yml`이며 `dartlab.pipeline macro`를 호출하므로 배선은 `runMacro`에 `rc3` 추가(rc2↔rc3 독립·둘 다 rc1==0 의존)가 정공법이다. `MacroFile.regime?`·`MacroLensSnapshot.regime?` 옵셔널이라 롤백·결손 붕괴 0.

**PM:** 무게중심이 정확하다 — "축을 더 표면화"가 아니라 "A블록 phase 단정의 회고성·전향성 미표시를 forecast/transition/GaR로 검증화하고, 그 검증을 종목 노출(C블록)과 다리로 잇는" 보강이다. 깊이(confluence·GaR·regime band·LEI 기여도·yield curve)는 전부 Regime 렌즈 `<details>` 1클릭 아래로 격리되어 첫 화면 4블록은 픽셀 불가침이고 7초 무오염이다(증분 1줄·overflow 시 2번째 줄). 4모델은 같은 호라이즌으로 묶지 않고(Sahm 실시간 동행·Hamilton 회고·GaR 4Q 전향) agreement를 점수가 아닌 불일치 모델명으로 풀되 인접 bucket을 동의로 처리해 probit moderate의 거짓 divergence를 닫았다. GaR은 유일하게 진짜 분포를 내는 모델이라 분위 막대/미니 fan을 정당하게 쓰되(점확률 probit의 fan은 금지로 분리), median 동반·단일 숫자 붕괴 금지로 분포를 지킨다. KR Hamilton은 단위 parity 미확정이라 US와 동급 신뢰도로 표면화하지 않고 보류해 가짜 정밀을 막았다(parity 확인 후 SHOULD로 재개). LEI 개수 게이트·내포 상관·probit 점추정 정밀 라벨로 '독립 4모델 합의' 오독을 막고, `focusChannelAlignment`가 국면축↔노출축을 시각 인접 라벨로 묶어 미션 성공기준 '종목 transmission 연결'을 view-model에서 닫되 '수혜 확정'은 0이다. 결정유관성 컷이 백과사전화·verdict 부활을 동시 차단한다.

---

## 13. 성공·실패 기준

**성공:** 분석가가 (1)7초에 4블록 + US 전향 분수를 읽고, (2)클릭 한 번에 침체 모델들이 동의/불일치하는지(어느 모델이 어긋나는지)·각 모델의 호라이즌·신뢰성 게이트·수익률곡선 형태·GaR 4Q 조건부 분포(꼬리 리스크·비대칭)·Hamilton 회고 regime band·국면 방향·**그 국면이 종목 초점채널과 정합인지**를 읽으며, (3)모든 숫자에 모델명·호라이즌·시간성(회고/전향)·asOf·staleAfterDays·정밀/독립 한계 라벨이 붙어 단정 0·판정 0이고, (4)종목 transmission(C 노출지도)과 시장 국면이 한 다이얼로그에서 다리로 연결된다.

**실패:** 13섹션 재현 · verdict/단일 macro score 부활 · 침체확률 단일모델 단독 · probit/nowcast fan/gauge · GaR 단일 숫자 붕괴 또는 GaR fan 금지 오적용 · confluence 막대 비교 · 4모델 단일 호라이즌 묶음 · probit/곡선 이중계상·LEI 독립 오표기 · Hamilton 죽은 라벨 게이트·분리약함 가짜 정밀·전향 오라벨 · **KR Hamilton 단위 parity 미확정인데 US 동급 표면화** · **LEI Σweight 게이트(result 미노출 필드 의존)·`_LEI_WEIGHTS` 참조** · probit 소수2자리 가짜 정밀 · Sahm None분기 누락(dead path 이중게이트) · regime band 막대/점추정 렌더 · transition 백분율 노출(L1757 % 경로 재현) · rates spread null(yieldCurve 직접 추출) · curveShape beta1 sign 역전 · 국면↔노출 다리 부재 또는 '수혜 확정' · nowcast notWiredYet 오분류 · 첫 화면 누적(GaR/band/confluence 첫화면 노출)·overflow 한 줄 초과 · growthSignal raw 노출 · rc2↔rc3 결합(cycle 실패가 regime 막음) · 경로/파일명 오인용(forecast.py에 정의 인용·buildMacroData.yml 오기) · 전문용어 벽.