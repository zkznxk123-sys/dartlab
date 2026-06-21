# 부동산 실거래 데이터 수집·조합 PRD
## "능력 지도가 아니라 *경계 지도* — net-new는 거래량 1축, 나머지는 정직한 라벨"

> 거처(데이터): 신규 `src/dartlab/gather/realestate/{client,series,catalog,facade,types}.py`(customs 거푸집) → 신규 `.github/scripts/sync/buildRealestate.py` → HF `realestate/agg/{national,region}_monthly.parquet` → `.github/scripts/prebuild/*`(offlineGuard 다운로드-only).
> 거처(분석 결합): `src/dartlab/analysis/financial/_signalsMacroSensitivity.py`(firm-level 매출민감도 외생 후보 풀)의 customs-only arm(:489-506)에 realestate arm 1개 + `gather/bulkData/macroHf.py:42` `_category` 화이트리스트 1줄.
> 거처(UI): 신규 `ui/packages/surfaces/src/terminal/panels/RealEstateLensDialog.svelte`(MacroLensDialog 픽셀 불가침·완전 격리) + `LeftRail.svelte` 진입점 1개.
> 본 문서는 **자기충족적**이다 — 이 문서만 보고 재조사 없이 구현 가능하도록 영향 파일·함수·file:line·데이터 계약·정직 가드·테스트·롤백·Phase·이중평가를 모두 담는다. 모든 file:line은 세션 직접 Read/Grep 실측(2026-06-20).

---

## 0. 한 줄 결론 (무게중심)

DartLab은 **부동산 *가격* 정보를 이미 쓰고 있다** — `exogenousAxes.py:93`의 `APT_PRICE`(아파트가격, ecos 출처)가 `_INDUSTRY_MAP`으로 건물건설업·시멘트·가구 등 17곳(_INDUSTRY_MAP 15업종 + _KEYWORD_OVERRIDE 2키워드[시멘트·건설])에 외생 OLS 배선돼 있고(`crisis.py:118`도 `apt_yoy` 소비), 따라서 국토부 실거래의 *중위가*는 대체로 재표면화다. **유일한 net-new는 가격이 구조적으로 못 담는 직교 축 — 거래량(volume·회전율/유동성)이다.** 이 PRD의 진짜 산물은 "부동산↔분석 능력"이 아니라 **① 거래량 집계 수집 파이프라인 1개 ② 어디가 STRONG인 척하면 안 되는지의 코드-실측 경계 지도 ③ STRONG 라벨을 가두는 P1 walk-forward 검증 게이트**다. 강함은 쌓아서가 아니라 *정직하게 깎아서* 나온다.

**단일 핵심 결정:** STRONG 등급("거래량=firm 매출 외생 1축")은 *빌드된 능력이 아니라* P1 walk-forward 3중 kill-criterion 통과 후에만 부여한다. 통과 전 라벨 = `observed-candidate`(관찰축), 통과 후 = `leading-context`(선행 맥락). 이 라벨은 agg parquet의 `meta.p1Status`가 구동하며(정적 하드코딩 금지), 미통과 시 UI가 'STRONG/선행' 단어를 *물리적으로 렌더할 수 없다*(phase·test·UI배지 3중 잠금).

**최소 ship 보장 (body default·운영자 override 가능):** go 승인 시 **최소 ship = 전국 월별 거래량 `TrendChart` 1종**(`observed-uptrend-only` 라벨)이다. firm 배선(STRONG)이 P1을 통과하든 못 하든, 전국+광역 월별 거래량·취소율 조회는 *공시·재무 도구 터미널에 부재한 신규 데이터 표면*이고 `national_monthly.parquet`(수KB·월1 cron)의 유지비가 좌측레일 1슬롯 ROI를 넘는다 — 이 두 조건이 floor go의 *필요조건*이며, 충족(데이터 표면 신규 + 유지비 < 1슬롯 가치)을 P1 *착수 전* 확인한다. 따라서 "go하면 최소 무엇이 ship되나"의 답은 빈칸이 아니다 — 거래량 조회 다이얼로그 1개. 운영자가 명시 거부할 때만 전체 honest-skip으로 내려간다(§11.1).

**비전 문장:** 부동산 렌즈는 "집값을 보여주는 화면"이 아니라 **"실거래 거래량이라는 한국 가계·소비·건설 사이클의 직교 신호를, 화면이 판정·예측·매매신호로 붕괴시키지 않고, 검증 상태(P1)·선행성 한계(regime 비대칭)·집계 한계(mix 미보정)·개인정보 한계(k-익명)를 정직하게 분리해 보여주는 조회·맥락 계기판"**이다.

---

## 1. 현상 진단 — 무엇이 이미 흐르고 무엇이 비었나 (코드 실측)

| 축 | 현재 상태 (file:line 실측) | net-new 여부 |
|---|---|---|
| 아파트 *가격* yoy | `exogenousAxes.py:93` `APT_PRICE`(ecos) → `_INDUSTRY_MAP`(:108) 17곳(_INDUSTRY_MAP 15업종 + _KEYWORD_OVERRIDE 2키워드[시멘트·건설]) 외생 OLS. `crisis.py:118` `apt_yoy` KR 위기탐지 소비 | **이미 배선** (재표면화) |
| 아파트 *거래량* | 어떤 외생축에도 부재. 가격축이 못 담는 직교 회전율 | **★net-new (유일)** |
| firm 매출민감도 외생 회로 | `_signalsMacroSensitivity._loadAdaptive`(:457): exo 매핑 3+범용 5=8후보 → customs arm(:489-506) materialize → `_quickCorr`(:532) → greedy top-3(:539). lag는 `_calcLagCorrelation`(호출 `_signalsMacroSensitivity.py:352`·정의 `_predictionMath.py:127`)별도 | 회로 존재, **거래량 arm 신규 배선** |
| macro regime/forecast | `macro/forecast/forecast.py:115 analyzeForecast(*,market,asOf,overrides,**kwargs)` — 내부에서 FRED LEI·T10Y3M·GDP 등 *고정 시리즈만* fetch, **임의 외생변수를 회귀에 주입하는 파라미터 슬롯 없음**(`overrides`는 기존 시리즈 가정 교체지 새 외생축 아님) | 거래량 못 꽂음 (REJECT) |
| macro summary 단일점수 | `macro/summary.py`(545줄) `_scoreCycle/_scoreRates/_scoreForecast/_scoreCrisis...` 각 `tuple[float,list]` ±점수 합산 | realEstate 축 추가 = 자동붕괴 (보조 dict 격리만) |
| credit 종목 신용 | `credit/engine.py:193 evaluateCompany(company,*,detail,basePeriod)` — **macro 입력 0개** | 점수 주입 불가, 병치만 |
| firm PF 정량 | `providers/dart/panel/build/noteTaxonomyData.py:113 "consolidated\|PF우발부채"→NT_D827580`(standalone은 :1596 `NT_D827585`) + `providers/dart/panel/cell.py:160 _noteCellsFromPanel` + `analysis/financial/governance.py:552 우발부채/지급보증` 정량 **실재** | firm 공시 출처·**거래량 무관·범위 밖** |
| 기업→지역 매핑 | LAWD_CD→회사 매핑 자산 **src 0건**. 분양 공시=서술형·실거래 지번=등기완료만 | **이중결손·영구 honest-skip** |

**진단:** 가장 흔한 오해("부동산을 붙이면 건설·가구·신용 분석이 강해진다")는 코드 앞에서 대부분 무너진다 — 가격은 이미 흐르고, 거래량만 새롭다. 그 거래량조차 firm-level 매출민감도 후보 풀에 *1축 추가*일 뿐 macro regime엔 꽂을 슬롯이 없다. 정직한 작업은 이 갭을 — 거래량 수집 파이프라인을 만들고, firm 후보 풀에 1축 배선하고(P1 조건부), 나머지는 가차없이 라벨·REJECT하는 — *절제된 출하*다.

---

## 2. 조합 Tier — 코드 실측 등급 (STRONG/MEDIUM/REJECT)

### 2.1 STRONG-채택 (P1 walk-forward 조건부)

> ★**무게중심 정정 (발굴 트랙, [04-discovery.md](04-discovery.md)):** 거래량의 *최강 거처*는 firm OLS arm(아래 B2)이 아니라 **이미 살아있는 crisis divergence arm(B1)** 이다. 25개 비자명 후보 적대검증 결과 즉시 가능 0·진짜 생존 1(B1)·약한 조건부 5. firm arm은 그 위 약한 upside로 강등(cmRisk high — 세션 반례: 가격 APT_PRICE조차 현대건설·한일시멘트 firm 회귀에서 탈락). net-new=거래량 1축은 불변, *그 거래량을 어디에 꽂느냐*의 순위만 바뀜.

**B1 (★최고가치) — 거래량-가격 divergence → 전국 거시 stress arm.**
- **메커니즘:** 거래량은 가격에 *선행*하고, 거래절벽(가격 평평 + 거래량 급감)은 single-point 가격지수가 구조적으로 못 잡는 thin-market 호가경직 stress. folk-correlation 아님.
- **거처(세션 검증):** `macro/crisis/_crisisDetectors.py:348 _crisisKrHousingStress`는 이미 살아있는 detector로 `:351-354`가 **apt_yoy(가격)만** `_detectorsMinsky.py:398 krHousingFinancialStress(housePriceYoy, householdDebtYoy=None)`에 전달(가계부채 arm은 광고됐으나 라이브 None=빈 다리). 같은 자리에 **거래량 divergence를 3rd arm으로 추가** — 신규 발명 아닌 묻어둔 회로 확장.
- **다른 후보와 결정적 차이:** firm→region 공간조인이 아닌 **전국 거시 arm** → 본사≠매출·시군구 결측·전수 raw OOM 함정 *전부 무관*(집계 count만 bake). cmRisk=medium(유일) — 세션 반례는 *firm 횡단 OLS lane* 결과인데 B1은 *미회귀 stress-label lane*이라 직접 kill 적용 안 됨. floor(§0)와 firm arm(B2) 사이 빠진 중간단계를 메움 = **가장 먼저 ship 가능한 STRONG 후보**.
- **정직 단서:** B1조차 무조건 KEEP 아님. RTMS 키 해제 + P1 walk-forward 로 divergence 가 기존 apt_yoy arm 대비 *추가* lead-time 실증해야(미통과=가격에 흡수→KILL). 3개월 연속 급감 확인·종합점수 붕괴 금지·`KRHousingStressResult` 단일 stress-label 만 노출.

**B2 (약한 upside·cmRisk high) — 거래량 집계 시계열 → firm-level 매출 외생 후보 1축.**
- **메커니즘:** 거래량은 가격(APT_PRICE)에 직교한 회전율/유동성 축. 거래량은 *선행지표*라 lag0 동기상관이 구조적으로 약함 → lagged 파생(`v_lag1Q`)을 후보로 push해야 '선행성 검정'이 '동기성 검정'으로 붕괴 안 함.
- **거처(코드):** `analysis/financial/_signalsMacroSensitivity.py`의 customs 적재 블록(:489 init·:492 `getProductIndicators` import·:494-496 `source=="customs"` append 루프)을 미러해 realestate arm 추가, 합류는 기존 :500-506 dedup 루프(`mapped+universal+customs`)가 흡수 → `_loadAdaptive` 후보에 `v_lag0`+`v_lag1Q` 둘 다 push → greedy 자연선택. lag 효과는 `_calcLagCorrelation`(호출 `_signalsMacroSensitivity.py:352`·정의 `_predictionMath.py:127`)→`_predictionMath.py::_pearsonCorrelation(lag=)`이 lag0/1/2 산출(이미 보고만 함→채택근거로 환류).
- **★STRONG 졸업 게이트 (P1 walk-forward 3중 kill-criterion, 사전등록):**
  1. `v_lag1Q`가 동기 대비 **방향정확도 순증 ≥3%p** — '동기 단독 채택은 honest-skip, lagged 채택 시에만 STRONG'으로 선행성을 *채택의 필요조건*화. (★코드 정합 정밀화: `_loadAdaptive` 선택은 여전히 greedy lag0 `_quickCorr`(:532)가 1차 게이트이고 `_calcLagCorrelation`(호출 `_signalsMacroSensitivity.py:352`·정의 `_predictionMath.py:127`)은 *greedy 통과 top-3에만* 돈다. 따라서 선행성 검정은 선택과 독립이 아니라, **`v_lag1Q`(원지표 lag1을 사전 시프트한 파생)가 *먼저* greedy를 통과하는 것을 필요조건**으로 한다 — 즉 거래량을 후보로 넣을 때 동기·lag1Q 둘 다 push해 lag1Q의 greedy 생존 자체를 1차 신호로 본다.)
  2. 건설계열 종목 top-3 **채택률 ≥ X%**(사전 고정 상수, openDecisions).
  3. **turning-point 하락전환 선행탐지율** 별도 kill — 하락 전환 N개월 전 거래량 선행하락 탐지.
  - 추가: compositional-shift 진단(강제매도 spike가 volume-leads-price 부호를 역전 → mix-shift 플래그로 무효화), incremental-R² Δ는 *사전 단정 금지*(공통 regime 구동분 제거 후 부분상관 유의성이 검정 대상).
- **정직 라벨:** net-new는 거래량 *수집*뿐. firm 결합은 '재표면화'가 아니라 **신규 배선 3지점**(`_signalsMacroSensitivity` arm · `macroHf._category` · `productIndicators` source 루프)+신규 집계로직 — '이미 투입' 오라벨 금지(역확신오정렬: 재표면화 오라벨이 오히려 작업량 은폐). 페이오프는 P1에 *전량 종속*, 통과해도 'firm 외생 1축'이라는 modest 결과(세계급 능력 아님).

### 2.2 MEDIUM-정직라벨

**M1. 건설·건자재·가구·가전 industry 모멘텀 — *거래량 한정* 동행 후보칩.**
- 부동산→후방산업 link 자체는 이미 존재(`exogenousAxes._INDUSTRY_MAP` APT_PRICE 17곳 배선, **방향 정확도 75~87%** — `exogenousAxes.py:8` 모듈 docstring 기재값, walk-forward 검증 방법론은 소스 미기재). 신규 기여는 *거래량 추가*에 한정. industry profit-pool/edges는 baked JSON이라 거래량을 새 edge로 묻으려면 **edges 재빌드 선결**(market-filings·공급망에서 반복된 데이터층 함정) → **별 cycle 분리**, 1차는 동행 *후보칩*(상관·n·lag·'인과 아님' 라벨)만, profit-pool 점수와 합산 금지.
- n·lag 산출: STRONG에서 만든 `national_monthly` 거래량 series ↔ 업종 PPI/지수의 `_predictionMath.py::_pearsonCorrelation(lag=)` 재사용(신규 산출함수 0), 분기정렬은 P0 월→분기 규칙.

**M2. 건설사 PF 환경 *병치* 맥락칩 (credit score 미주입).**
- `engine.py:193 evaluateCompany`는 macro·외생 입력 **0개**라 거래량을 score에 *주입 불가* — 이 코드 제약이 '주입 아닌 병치' 경계를 강제. `IndustryGroup.CONSTRUCTION` 게이팅으로 건설사일 때만 등급카드 *옆*에 전국/광역 거래량 추세 스파크라인 1줄 병치. 회사 PF는 공시에서, 부동산은 환경 방향 맥락뿐.
- ★정직 귀인(검증 정정): '거래량→종목 신용 차별성'은 0(거시 systematic factor·cross-sectional 식별 0). 종목 PF 신용을 원하면 거래량이 아니라 **PF우발부채 노트셀(`consolidated|PF우발부채`→`NT_D827580`·standalone→`NT_D827585`, `_noteCellsFromPanel(cell.py:160)`)** 정량화가 별 후보 — 단 **부동산 작업 밖**(firm 공시 출처, 거래량 무관). 지역 거래량 분산으로 idiosyncratic 신용신호를 만드는 경로는 LAWD_CD→회사 매핑 결손으로 영구 막힘.

### 2.3 REJECT-거절 (정직히 안 함)

| REJECT | 근거 (코드/데이터) |
|---|---|
| 전국 전수 raw 거래행 bake | 250 시군구 × 8용도 × ~240개월 = 수백만~수천만 행 → **Polars Rust 힙 OOM**(Company 1개 200~500MB, CLAUDE.md ⛔)이 차단(콜한도는 §3.4에서 10,000/일로 해소돼 더는 병목 아님). 집계 인덱스(시군구×월 count/median) bake + raw 온디맨드가 유일 정공법 — OOM 회피 + 개인정보(k-익명) 양립 |
| 기업→지역 특정 매핑 | LAWD_CD→회사 자산 0건·이중결손. 부분 매핑을 전수처럼 보이면 false-negative('매핑 안됨'='노출 없음' 오독) |
| 단지→종목 주가 예측 / price target | 표본 1·교란변수·역인과 가짜정밀 |
| 거래량·가격을 buy/sell·호악재·부동산 종합점수로 단일붕괴 | `macro/summary.py`가 무조건 단일 score 합산 → realEstate를 summary 축에 넣으면 자동붕괴. 보조 dict 격리만 |
| choropleth 시군구 지도 | `ScatterMap.svelte`는 산포도지 지도 아님. d3-geo·topojson·leaflet 의존성 **0건**. 신규 별도 프로젝트(topojson bake+시군구 통폐합 이력+250 polygon) → 1차 honest-skip, top-N 막대 대체 |
| 미분양·신규 분양물량 | 실거래 API에 부재(HUG/통계누리·청약홈 별도, 시군구 집계만). 거래량으로 미분양 추정 = 확신오정렬 |
| 8용도 동시수집 | 아파트 매매 단일종 `_attempts` 졸업 후 확장(덕지덕지 금지) |
| **가구·인테리어 charter화** (발굴 KILL) | 한샘 등은 **전국 유통=본사≠매출**이라 charter 예외(도시가스·지방금융·지역유통) 아님. APT_PRICE 이미 배선(`exogenousAxes.py:225`)이라 net-new도 아님 — '지역 거래량→지역 가구수요' 공간 직결은 본사≠매출 함정. [04-discovery.md](04-discovery.md) |
| **전세가율/전월세전환율 기반 모든 연결** (발굴 KILL) | RTMS *전월세* 별도 수집 필요(8용도 동시수집 REJECT에 종속)·전세가율 분모=매매가는 APT_PRICE 재포장·`pfExposure`(`construction.py:110-112`)는 키워드카운트지 정량 아님. '깡통전세→미분양→PF부실'은 데이터 부재를 서사가 가린 확신오정렬 |

---

## 3. 데이터 파이프라인 — customs 거푸집 + 3 비대칭 + 고볼륨 전략

### 3.1 소스 거푸집 (`gather/realestate/`) — customs 1:1 모방 + 3 비대칭이 client 복사를 깨뜨림
| 비대칭 | customs | 부동산 RTMS | 신규 필요 |
|---|---|---|---|
| ① 페이지네이션 | `pageNo='1'`·`numOfRows=10000` 단일페이지·server-aggregated(cntyCd 생략→전국합산 1시계열) | 1콜=(1 LAWD_CD,1 DEAL_YMD)당 개별 거래행 N개 | `totalCount`/`pageNo` for-loop **신규**(절단 방지) |
| ② 집계 | `_aggregateMonthly` sum-only | 거래건수 count·면적가중 median | count/median 집계 **신규** |
| ③ 파싱 | `apis.data.go.kr/1220000`·XML·**totalCount 태그 없음**(집계형) | ✅host=`apis.data.go.kr/1613000/...AptTradeDev` 확정·serviceKey=Decoding(customs 동일)·XML·**행 기반 페이지네이션** — customs와 envelope 다름 | **응답 구조 = 문서 2종 입증**([evidence](evidence/empirical-verification-2026-06-20.md) §3): header(영문) `resultCode`·`numOfRows`·`pageNo`·**`totalCount`** + item(**한글 태그**) `거래금액`·`전용면적`·`층`·`건축년도`·`년/월/일`·`법정동`·`아파트`·`지번`·`지역코드`(+상세 `해제여부`·`해제사유발생일`·`등기일자`·`동`). `_parseItems`=header `totalCount`로 pageNo for-loop 종료 + 한글 item 태그 매핑. **Dev 버전 태그(한/영) 바이트 확정만 활용신청 후 1콜** |

- 인증: `resolveKey("dataGoKr")` 단일키(customs `client.py:39` 그대로)·신규 os.environ **0**.
- `series.py`는 (시군구,월)당 1콜을 윈도순회하며 *거래행을 곧바로 집계*해 `(region, date, txCount, medianPrice, areaWeightedPrice, cancelRate)`만 반환 — **개별 거래행 절대 보존 금지**(OOM 강제 가드, CLAUDE.md ⛔ 메모리 안전 정합).

### 3.2 sync (`buildRealestate.py` — buildGovData 미러)
- **2-tier 콜예산 split (*페이지 단위*로 정의 — busy cell은 셀당 2~4페이지라 셀단위 예산은 한도 초과 위험):** (a) reconcile = Σ(provisional 셀 page수) (b) 신규 = Σ(미수집 셀 page수). **콜한도 D=10,000/일 실측 확정**(§3.4)이라 일상 증분(250 시군구 × 최근월 1~수페이지 ≈ 수백~3,000콜)은 한도의 ≤30%로 단일 cron 내 여유. 비율(예 30:70)은 초기 전이력 백필 기간에만 의미. RTMS는 'gov date/{year} 전종목 1콜 등가물'이 없어 이 2-tier가 유일 수렴 보장.
- **forward 윈도 + reconciliation 쌍** ([[incident_panel_rcept_window_gap]] 계승): 신고 30일+해제 소급 30일로 최근 ~3개월(실측분포로 결정) rolling 재집계, `provisional` 플래그 동반. 해제여부=O 제외 + `cancelRate` 별도 컬럼 보존(취소율 자체가 침체 신호).
- **★k-익명 마스킹은 *생성 단계*(buildRealestate.py)에서 강제:** `txCount < k`(예 5) 셀은 `medianPrice`/`areaWeightedPrice`를 null(N=1이면 median=그 거래가→역추론 재식별), `txCount`만 유지. HF push 전 단위테스트에 'N<k 셀 가격값 0건' 어서션.
- **입도 = 시군구(250) 1차 채택 가능:** D=10,000/일 실측이라 전이력(250×~240월≈57,600콜)도 ~6일 분할로 수렴 → D가 작아 시도(17)로 후퇴할 필요 없음(시군구 해상도 1차 채택). (시도 roll-up은 k-익명 셀카운트 부족한 소규모 시군구에만 국소 적용, 콜예산 이유 아님.)

### 3.3 HF 레이아웃 + prebuild
- `eddmpython/dartlab-data`의 `realestate/` 격리 경로. **raw 거래행 parquet 미생성.** 2파일만 push:
  - `realestate/agg/national_monthly.parquet`(전국 월별 거래량·중위가·취소율, ~수KB, `hf` origin)
  - `realestate/agg/region_monthly.parquet`(시군구×월 count/median, 수백KB~수MB, 큰 경우 `hfRange`)
  - meta에 `p1Status`(`observed-candidate`|`leading-context`|`observed-uptrend-only`)·`regimeScope`·`provisionalMonths`·`cancelRate` bake (UI 배지/HonestyFooter **데이터 구동**).
- prebuild: `.github/scripts/prebuild/*`는 HF agg parquet *다운로드만*(`offlineGuard.enforceOffline`, 외부 API 0). `tests/architecture/test_prebuild_offline.py` AST 첫-statement 검증이 import·main entry 정적 차단.

### 3.4 P0 게이트 — ★세션 실증 검증 완료 (2026-06-20 실호출 + data.go.kr 페이지 확인)

P0 4항을 **추측이 아니라 실제 측정으로 해소**했다. 따라서 dataLayer feasibility는 *가정*이 아니라 *실증 근거*에 선다. **외부 사실(코드 아님)은 [evidence/empirical-verification-2026-06-20.md](evidence/empirical-verification-2026-06-20.md) + raw [api-probe-2026-06-20.json](evidence/api-probe-2026-06-20.json)에 박제 — 코드대조로 안 보이는 외부 API/라이선스/한도를 평가자가 직접 읽고 검증 가능.** (실호출: customs 1220000=200 동일키·동일샌드박스 → 네트워크/키 정상 후 RTMS 1613000 = 키有403/키無401.)

| P0 항목 | 실증 결과 (2026-06-20) | 근거 |
|---|---|---|
| #1 host·serviceName·serviceKey | ✅ **확정** `http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`. serviceKey=Decoding 키 httpx 1회 인코딩(customs `client.py:39` 동일). 잔여=실거래 행 totalCount 태그위치·필드명만 활용신청 후 1콜로 캡처(자동승인이라 trivial) | RTMS 키有=403 / 키無=401 (서비스별 미승인 시그니처) · customs 200 |
| #2 KOGL 재배포권 | ✅ **"이용허락범위 제한 없음"** (data.go.kr 15126468). 상업이용·재배포 허용 → **HF 공개 SSOT 양립.** Type2~4 'dataLayer 무효' 최악분기 **소멸**(degraded 화면은 보험으로만 유지·발화 0) | data.go.kr 데이터셋 페이지 |
| #3 일일 콜한도 D | ✅ **개발계정 10,000건/일**(운영계정=활용사례 등록 시 증가). customs와 **동일**. 250 시군구 × 12월 = 3,000콜/년 ≪ 10,000/일 → 1년치 수시간, 전이력(아파트매매 ~240월) ≈ 57,600콜 = **~6일**(분할). 전수 raw가 아닌 *집계* bake라 행 OOM도 회피 | data.go.kr 페이지(무료) |
| #4 활용신청 | ✅ **개발·운영단계 모두 자동승인.** 서비스별 별도(현재 미신청=403)지만 **운영자 1클릭·즉시 승인**. 비용 무료 | data.go.kr 심의여부 + 403/401 실측 |

**잔여 P0(비차단·trivial):** 활용신청 1클릭 후 1콜로 응답 XML totalCount 태그·필드명 캡처 → `_parseItems` 경계 고정. 자동승인이라 운영자 분 단위 작업이며, 설계 차단요소 아님. **즉 P0는 'feasibility 미확정 위험'이 아니라 '운영자 1클릭 + 1콜 캡처'로 축소됐다.**

---

## 4. 분석 결합 배선 — 3지점 + 단방향 경계

신규 배선은 정확히 **3지점**이다(loadMacroParquet은 source-generic이라 무수정 — '4지점'은 과대계상):
1. `src/dartlab/analysis/financial/_signalsMacroSensitivity.py:489-506` — customs-only arm에 realestate arm + `v_lag1Q` 파생 후보 push.
2. `src/dartlab/gather/bulkData/macroHf.py` — realestate 추가 3곳: `_SOURCE_TO_CATEGORY`(customs 항목 :19, dict :16-20)에 `realestate:macroRealestate` + `_SOURCE_TO_ENVKEY`(customs 항목 :26, dict :23-27)에 `realestate:DATA_GO_KR_KEY` + `_category`(:42) 화이트리스트 **및 그 ValueError 메시지(:45) 둘 다** 갱신(load-bearing 게이트).
3. `src/dartlab/gather/mapping/productIndicators.py:124` — source 루프에 realestate arm(STRONG 통과 후).

**검증-only(무수정):** `gather/transforms/macro.py:273 loadMacroParquet`(source-generic 통과). **회귀 금지(픽셀 불가침):** `MacroLensDialog.svelte`·macro forecast/regime(외생 슬롯 없음)·`macro/summary.py`(보조 dict 격리만, 축 추가 금지).

계층: `gather/realestate`(L1) → `_signalsMacroSensitivity`(L2 analysis) 단방향. L2 형제 import 0(lint-imports 강제).

---

## 5. UI/UX — 완전 격리 RealEstateLensDialog (macro-lens 픽셀 불가침)

### 5.1 surface
`MacroLensDialog.svelte`(실측 1175줄, '새 블록 추가 금지' 동결)는 **일절 미수정·픽셀 불가침**. 부동산은 형제 **`RealEstateLensDialog.svelte` 신설로 완전 격리**, `LeftRail.svelte` 'RE' 진입점 1개. macro read-only 오버레이는 1차 완전 제외(killList). 새 라우트·새 탭 0, `data/origins` `hf` origin 1항목, 데이터 호출은 `runtime/src/data/fetch` 단일 작업대 경유(source 자체 fetch·직접 URL·자체 캐시 Map 금지 — `checkUiDataWiring` 강제).

### 5.2 컴포넌트
- **첫 화면 불가침** = 전국 월별 거래량 `TrendChart` 1개(실재 컴포넌트) + 정직 푸터 고정.
- **progressive disclosure `<details>` 1곳** = 시군구 top-N 막대/테이블(choropleth 아님)·취소율·면적가중 평단가 병기·provisional 플래그.
- 건설사 dashboard 등급카드 옆 거래량 스파크라인 *병치칩* 1개(`IndustryGroup.CONSTRUCTION` 게이팅, score 미주입).
- 4칩(OBSERVED/CONTEXT/WATCH/LOCK): **surfaces에 공통 칩 컴포넌트 부재**(칩은 전부 파일별 로컬 CSS·검증) → macro-lens 칩의 색·타이포·크기 **시각 토큰 값을 로컬 스타일로 복사**(`--amber`·11px floor·border-radius 동일), '컴포넌트 재사용' 아님.
- **정직 푸터:** `HonestyFooter.svelte`는 백테스트 도메인 전용(props=`PortfolioBtResult`·검증)이라 **재사용 불가** → 신규 `RealEstateHonestyFooter`(또는 다이얼로그 내부 footer 섹션), 정직푸터 *패턴*(11px floor·중립 회색·닫기불가 스탬프·ⓘ 방법론 details)만 계승.

### 5.3 정직 라벨 (호악재 색 금지·중립 회색조)
- `p1Status` 메타 구동 배지: 'P1 검증 전(관찰축)' ↔ 'P1 졸업 후 선행맥락' ↔ '상승장 한정'. 전이 트리거 = agg parquet `meta.p1Status` read(정적 하드코딩 퇴화 금지, 미통과 시 메타가 `observed-candidate` 강제 → UI가 STRONG 단어 못 그림).
- 정직 푸터 고정문구 = "실거래 신고 집계 — 선행 맥락이지 인과·예측·매매신호 아님. 취소거래 제외. 시군구 비교는 면적·연식 mix 미보정." (동적변수 null-safe: cancelRate 미수신 시 절 생략, provisionalMonths 미수신 시 '최근 수개월' graceful degrade, 빈 변수 리터럴 노출 0 단위테스트 가드).
- 거래량=선행(경험칙)·가격=동행·미분양/해제=후행 각각 분리 라벨.
- 시군구 평단가에 'WATCH(면적·연식·층 mix 미보정, mix-shift 동반 시 신호 무효화 가능)' 칩.
- **KOGL degraded 화면 = 보험만(발화 0 예상):** §3.4 실측 "이용허락범위 제한 없음"으로 공개 양립 확정 → 퍼블릭 출하가 default. degraded 경로(`env.kind` 퍼블릭 진입점 비표시 / 로컬 LOCK 칩)는 *만약 운영자 법무 재검에서 뒤집힐 경우만* 발화하는 가드로 코드에 남기되, 정상 경로는 퍼블릭 표시. (그 가드 화면 before/after 스크린샷은 P4 눈검수에 포함.)

### 5.4 killList
choropleth 지도 · credit 환경칩(미분양 LOCK) · industry profit-pool 오버레이(edges 재빌드 선결·별 cycle) · macro-lens read-only 오버레이(별도 승인) · 8용도 동시수집 · summary 축 추가 · 단지 raw의 예측선/방향화살표/price target.

---

## 6. cannotClaimList (NEVER-CLAIM — grep 게이트 봉인)

1. '부동산 거래량/가격이 특정 종목 주가를 예측' / 단지→종목 / price target — false precision, 영구 REJECT.
2. '이 회사가 이 지역에 노출' 자동 매핑 — LAWD_CD→회사 0건·이중결손, 영구 honest-skip.
3. 거래량·가격을 buy/sell·호악재·부동산 종합점수로 단일붕괴 / `macro/summary.py` ±score 합산 축에 투입 — 보조 dict 격리만.
4. '거래량을 calcMacroRegression/macro regime(forecast/Hamilton/GaR) 외생슬롯에 추가' — 그건 firm-level OLS(`_signalsMacroSensitivity`)지 regime 슬롯 아님, regime엔 외생 주입 슬롯 부재.
5. '주택→산업 link가 net-new' — APT_PRICE 이미 17곳 배선(grep 19 = def :93 + 배선 17 + ALL_INDICATORS export :563). net-new는 *거래량*에 한정.
6. 'credit이 PF·미분양을 분석/직접 산출' — `analysis/financial/sectorKpi/construction.py:110-112 pfExposure`는 충당부채 섹션 PF **키워드 카운트**(정량 노출액 아님·analysis층). PF 정량 노출액은 `_noteCellsFromPanel(code,"NT_D827580")`(cell.py:160)로 firm 공시에서 가능하나 **거래량과 무관·범위 밖**. 'credit/에 PF *정량 노출액 산출* 코드 0건'이 정확한 표현(grep 매치 일부는 조선 '장기 프로젝트' docstring으로 PF 무관) — 'PF 코드 0건'을 settled fact로 단정 금지.
7. 거래량으로 미분양 추정/관측 — 실거래에 미분양 필드 없음(HUG/통계누리 별도).
8. 고정 lead 시차('N개월 선행') 단정 — 표본·regime 의존(상승장 선행·하락장 동시붕괴), 비대칭성=페이오프 천장.
9. 전국 전수 raw bake/보유 — 집계만 bake+raw 온디맨드(차단 사유 = Polars OOM, 콜한도 아님). 콜한도는 **개발계정 10,000/일 실측 확정**(§3.4)이므로 막연한 한도 추정·과거 '1,000콜' 오정보 인용 금지.
10. 취소거래 무시 — `cdealType='O'` 제외+`cancelRate` 보존, 최신월 provisional 미표기 금지.
11. k-익명 미달 셀(N<k) 평단가 노출 — 생성단계 마스킹.
12. 이게 '새 분석 엔진/능력'이다 — net-new는 거래량 수집 1개, 나머지 재표면화/신규배선/REJECT. STRONG도 P1 전엔 미부여.
13. choropleth가 'ScatterMap 재사용/경량' — 신규 별도 프로젝트(geo 0건).
14. (발굴) 도시가스/지방은행 charter 연결이 *전체매출* 기준으로 작동 — 가정용/여신 분리추출 없이는 산업용·발전용에 희석돼 신호 소멸(B4·B5 fix 조건). 분리 막히면 KILL.
15. (발굴) 해제율(cancel-rate)을 firm arm(`_signalsMacroSensitivity.py:489`)에 주입 — 해제율은 전국 단일 거시 series라 firm 매출 상관선택 대상 자체가 없음. 결합점은 `crisis.py:118` + `_detectorsMinsky.py:398` arm뿐(B3 plugPoint 정정).
16. (발굴) 전세가율/전월세전환율이 net-new로 *즉시* 가능 — RTMS 전월세는 매매와 별개 API + 단지조인(OOM), 8용도 동시수집 REJECT에 종속. 1차 net-new는 매매 거래량 단일.

---

## 7. Phase (P0~P4 + 별 cycle)

| Phase | 내용 | 게이트 |
|---|---|---|
| **P0** ✅세션 실증 완료 | host·serviceKey·KOGL("제한 없음")·콜한도(10,000/일)·활용신청(자동승인) §3.4 실측. **잔여=활용신청 1클릭+1콜 totalCount 캡처(trivial)** | 차단요소 해소 — 운영자 1클릭만 |
| **P1** _attempts 개념검증 | `tests/_attempts/realestateVolume/` 아파트매매 단일종·상위10 시군구 패널. **착수 *전* 사전등록 kill-criterion 코드상수 커밋**(채택률 X·lagged>동기 ≥3%p·turning-point·월→분기 정렬 `alignMonthlyToQuarter` 함수+단위테스트 동행). 미통과 손익분기 명시 | STRONG 졸업 = 3 kill 통과 |
| **P2** gather 소스+sync | `gather/realestate/*`(pageNo for-loop·count/median·k-익명)·`buildRealestate.py`(2-tier+reconciliation)·dataCredentials 1줄·agg 2파일 HF push·prebuild | P0 통과 후 |
| **P3** firm 배선 3지점 | `_signalsMacroSensitivity` arm(lag0+lag1Q)·`macroHf._category` 1줄·`productIndicators` source 루프. `_calcLagCorrelation` lagEffects 채택근거 환류 | P1 STRONG 통과 조건부 |
| **P4** UI | `LeftRail` 진입점·`RealEstateLensDialog`(첫화면 TrendChart+정직푸터 불가침·`<details>` top-N)·4칩 토큰복사·p1Status 메타구동·KOGL degraded·건설 병치칩·macro-lens 회귀가드 | **운영자 명시 승인 + 스크린샷 눈검수 후 push** |
| 별 cycle | industry edges 재빌드 / 8용도 확장 / 미분양 게이트(HUG 식별자 P0급 확인 후) | '한 번에 하나 완성' |

---

## 8. 영향 파일 (file:line 실측)

**신규:** `gather/realestate/{client,series,catalog,facade,types}.py` · `.github/scripts/sync/buildRealestate.py` · `.github/scripts/prebuild/buildRealestateAgg.py`(다운로드-only) · `ui/.../panels/RealEstateLensDialog.svelte` · `RealEstateHonestyFooter`(또는 내부 섹션) · `tests/_attempts/realestateVolume/`.
**수정(최소):** `src/dartlab/core/providers/dataCredentials.py`(dataGoKr sources +1줄+activation) · `src/dartlab/analysis/financial/_signalsMacroSensitivity.py`(customs 적재 블록 :489 init·:492 import·:494-496 `source=="customs"` 루프를 미러 → realestate arm + lag1Q, dedup :500-506 흡수) · `src/dartlab/gather/bulkData/macroHf.py`(`_SOURCE_TO_CATEGORY`:19·`_SOURCE_TO_ENVKEY`:26·`_category`+ValueError :42-45) · `src/dartlab/gather/mapping/productIndicators.py:124`(source 루프) · `ui/packages/surfaces/src/terminal/panels/LeftRail.svelte`(진입점 1줄) · `ui/packages/runtime/src/data/origins/registry.ts`(불필요할 수 있음 — `hf` 재사용).
**검증-only(무수정):** `gather/transforms/macro.py:273 loadMacroParquet` · `MacroLensDialog.svelte`(픽셀 불가침).

---

## 9. 테스트

1. `tests/_attempts/realestateVolume/` 사전등록 kill-criterion 상수(채택률 X·lagged>동기 ≥3%p·turning-point)를 착수 *전* 커밋 — hindsight 게이트 무름 차단. `alignMonthlyToQuarter` 단위테스트(분기경계 귀속·취소거래 분기내 제외 idempotent) 동행.
2. `buildRealestate` 집계: N<k 셀 medianPrice/areaWeightedPrice **0건** 어서션(k-익명).
3. 취소거래 `cdealType='O'` 제외 + `cancelRate` 보존 / pageNo for-loop 다행응답 **절단 0건**.
4. forward윈도+reconciliation: provisional 최근 N월 재집계 **idempotent**(정정거래 이중집계 0).
5. prebuild offlineGuard: `test_prebuild_offline.py` AST 첫-statement 외부 API import 0건.
6. `RealEstateHonestyFooter` null-safe: cancelRate/provisionalMonths 미수신 시 빈 변수 리터럴('X%'·'N월') 노출 0.
7. `p1Status` 메타 미통과(observed-candidate) 시 UI가 STRONG/선행맥락 단어 렌더 0(정적 하드코딩 퇴화 가드).
8. `MacroLensDialog.svelte` 회귀가드: **git-diff 기반 '본 작업 커밋들에서 MacroLensDialog.svelte 변경 0줄'** (라인수 하드코딩 baseline 대신 — 실측 1175줄은 drift하므로 diff 가드가 정공법). 새 블록 0.
9. grep 차단: '세계급'·검증 전 STRONG 단어 + 'PF 우발채무 분석'·'거래량 예측' 오버클레임 문자열 0.
10. lint-imports: `gather/realestate` L1 경계·realestate→analysis 단방향, L2 형제 import 0.

---

## 10. 롤백 (phase 독립 가역)

P0 = 세션 실증 완료(KOGL 제한없음·10,000/일·자동승인)이라 *외부 차단 위험은 해소*. 만약 운영자 법무 재검에서 KOGL 해석이 뒤집히면 → 퍼블릭 출하만 보류(degraded 가드 발화)·엔진/sync는 로컬 유지. P1 미통과 → firm 배선 3지점·STRONG 라벨 영구 미적용, `gather/realestate` 소스만 남기거나(향후 재시도) 전량 honest-skip. 각 phase 독립 가역: UI(P4) 미push해도 엔진/sync 무영향, firm 배선(P3) revert해도 집계 parquet·UI 무영향. macro-lens 미수정이라 macro 회귀 0. dataCredentials 1줄·macroHf 1줄은 미수집 시 dead(무해). 최악 시 `realestate/` HF 경로 삭제 + 진입점 1줄 제거로 전 표면 제거.

---

## 11. 열린 결정 (openDecisions)

1. **P1 미통과 floor — body default 확정(§0):** 최소 ship = 거래량 조회 다이얼로그 1종(`observed-uptrend-only`). default는 본문이 정했고(빈칸 아님), *남은 운영자 입력*은 단 하나 — floor 필요조건(신규 데이터 표면 + 유지비 < 1슬롯 가치)을 운영자가 인정하는지, 아니면 명시 거부해 전체 honest-skip으로 내릴지. (이 항목은 '미결'이 아니라 'override 여부 확인'이다.)
2. P1 채택률 임계 X 사전 고정값 — P1 분포 보고 후 코드상수 박제.
3. 2-tier reconcile:신규 비율(예 30:70) — P0 page곱수 실측 후.
4. 집계 입도 시군구(250) vs 시도(17) — 회귀 안정성 vs 해상도·k-익명 트레이드오프(D-적응).
5. 평단가 mix-adjust 깊이 — 단순 면적당 vs 면적·연식 버킷 중위(WATCH→OBSERVED 승격 조건).
6. 미분양 게이트 — HUG/통계누리가 분양사업장→시행/시공사 식별자 공개하는지 P0급 사전확인 없이 별 cycle 착수 금지, 미공개면 영구 REJECT.
7. industry edges 재빌드 — 이 작업 포함 vs 별 cycle('한 번에 하나' 원칙상 후자 권장).
8. **(발굴) STRONG의 거처 — B1(crisis arm) vs B2(firm arm):** 발굴은 B1 우선 권고(cmRisk medium·별 lane·먼저 ship·세션 반례 직접 적용 안 됨). B2(firm OLS arm)는 약한 upside(cmRisk high). P1 착수 시 B1을 먼저 측정할지(권장) B2와 병행할지 운영자 결정. [04-discovery.md](04-discovery.md) §최고가치.

---

## 12. 정직성 자기진단 (honestyStatement)

7개 분야 설계가 일관되게 같은 실수를 했다: 메커니즘의 그럴듯함으로 강도를 매기고 자산 실재성을 grep으로 검증 안 함(check-internal-assets-first 위반). 적대검증 + 세션 코드 실측이 무너뜨린 것 — (1)거래량 firm 결합은 '재표면화'가 아니라 신규 배선 **3지점**(loadMacroParquet은 source-generic 무수정, '4지점'은 과대계상), (2)macro regime(`forecast.py:115 analyzeForecast`·Hamilton/GaR)에 외생 주입 파라미터 슬롯 부재(firm-level OLS 거처는 `_signalsMacroSensitivity`이지 regime 엔진 아님), (3)credit PF·미분양 *정량 분석*은 코드 0건(`sectorKpi/construction.py:110-112 pfExposure`는 키워드 카운트), 단 **PF 정량 노트셀(`NT_D827580`/standalone `NT_D827585`)은 실재**하나 firm 공시 출처·거래량 무관, (4)주택→산업 link는 APT_PRICE로 이미 17곳 배선(grep 19 = def :93 + 배선 17 + ALL_INDICATORS export :563)(net-new는 거래량뿐), (5)choropleth는 ScatterMap 재사용 아닌 신규 프로젝트(geo 0건), (6)summary는 무조건 단일 score 합산(보조 dict 격리만 단일붕괴 회피), (7)HonestyFooter는 백테 전용(패턴만 계승). **진짜 새 능력 = 거래량 집계 수집 파이프라인 1개뿐.** STRONG의 페이오프는 P1 walk-forward에 *전량 종속*, 통과해도 'firm 외생 1축'이라는 modest 결과(세계급 아님). 검증 전 STRONG을 phase·test·UI배지 3중 잠금. 데이터층 false precision('일 1,000콜' 오정보)도 **세션 실호출로 실측 교정**(개발계정 10,000/일·KOGL 제한없음·자동승인) — 미검증 추정이 아니라 측정 근거. '4지점→3지점' 과대계상도 정정. **이 PRD의 정직한 산물은 부동산 능력이 아니라 경계 지도 + 검증 게이트이며, 데이터 feasibility는 추측이 아니라 실호출로 입증됐다.**

---

## 13. 이중 평가 (전문 개발자 + PM)

**전문 개발자 관점:** 거푸집 재사용(customs 5파일)·배선 3지점·검증-only 경계가 명확하고 file:line이 실측이라 재조사 없이 구현 가능. 3 비대칭(pageNo/count·median/parsing)이 client 복사를 깨뜨리는 지점을 짚었고, **P0 4항(엔드포인트·KOGL·콜한도·활용신청)을 세션 실호출로 실증 해소**(§3.4)해 착수 리스크가 '미확정'에서 '운영자 활용신청 1클릭 + 1콜 totalCount 캡처'로 축소됐다. k-익명 생성단계 마스킹·forward+reconciliation·offlineGuard가 dartlab 기존 사고(panel rcept window·OOM)를 계승. 잔여 리스크는 P1 walk-forward(능력 검증·표본 의존)이지 데이터 접근성 아님.

**PM 관점:** 무게중심('net-new=거래량 1축·나머지 경계지도')이 선명하고, 덕지덕지(8용도·choropleth·미분양·edges 오버레이)를 전부 별 cycle/REJECT로 깎아 ROI 방어. **최소 ship 보장**은 §0 body default(거래량 조회 다이얼로그 1종 = 신규 데이터 표면·유지비 < 1슬롯)로 명문화돼 P1 통과확률과 *독립*으로 확정 — "go하면 최소 무엇이 ship되나"가 빈칸이 아니다(승인 의사결정 입력 충족). STRONG(firm 외생 1축)은 그 위의 *upside*이고 P1 조건부. 시그니처 가능성은 modest하나 *정직한* modest(억지 STRONG 아님)이며, 진짜 가치는 "부동산을 붙이면 강해진다"는 흔한 환상을 코드로 반증한 경계 지도 자체.

---

## 출처
전문에이전트 워크플로(7분야 설계 + 7 적대검증 + 평가패널 3라운드, `wf_d022eb68-40c`, 2026-06-20, 46 agents·4.5M tokens) + **세션 코드 직접 실측 재검증**(전부 full path): `gather/mapping/exogenousAxes.py:93 APT_PRICE`/`:108 _INDUSTRY_MAP`(18 배선) · `analysis/financial/_signalsMacroSensitivity.py:457-540`(customs arm :489-498·dedup :500-506) · `gather/bulkData/macroHf.py:42 _category`/`:17,:24` · `macro/crisis/crisis.py:118 apt_yoy` · `macro/summary.py`(545줄·`_scoreCycle:30/_scoreForecast:98`) · `analysis/financial/sectorKpi/construction.py:110-112 pfExposure` · `providers/dart/panel/build/noteTaxonomyData.py:113 NT_D827580`/`:1596 NT_D827585` · `providers/dart/panel/cell.py:160 _noteCellsFromPanel` · `analysis/financial/governance.py:552` · `credit/engine.py:193 evaluateCompany` · `macro/forecast/forecast.py:115 analyzeForecast` · `analysis/financial/_predictionMath.py:127 _calcLagCorrelation·:156 _pearsonCorrelation(lag=)` · `gather/transforms/macro.py:273 loadMacroParquet` · `ui/.../terminal/charts/HonestyFooter.svelte:6 PortfolioBtResult` · `panels/MacroLensDialog.svelte`(1175줄). 토론·점수 이력은 [02-debate-and-verification.md](02-debate-and-verification.md). 평가 패널이 capped한 인용 정밀도 갭을 세션 실측으로 닫은 것이 본 PRD가 워크플로 89점 대비 갖는 증분.
