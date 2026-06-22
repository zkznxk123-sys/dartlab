# 03. Staging Roadmap — 무게중심 역전 (기반·W·S·D)

상태: v0.2 (2026-06-18). 거처 = `ui/packages/surfaces/src/terminal/` + `ui/packages/surfaces/src/scan/universe/`.

> 단계는 *기능을 깎은 MVP가 아니라* 회귀위험을 격리한 진입 경로. 각 단계 = 독립 출시 + 단방향 적층. moat(간판 W) 우선, commodity(살 S)는 세계급 마감, 위험·의존 미충족은 이연(D).

---

## 기반 — persistent dock + 정직 3단 tiering (UX 토대, 현 엔진 무수정)

> 깨진 드롭다운 루프(02 §0)를 먼저 닫는다. 전 탭(단일·유니버스·게이트)의 토대 — 이게 없으면 무엇도 못 쌓음.

### AC
1. `[BT]` 드롭다운 → **persistent docked 레일**(리사이즈·28px spine 접힘, 자동닫힘 0). config·result·chart 동시 가시.
2. `BtConfig`(룰빌더 포함)를 dock에 무손실 흡수. 차트 클릭해도 빌더 안 사라짐.
3. 정직 = `HonestyFooter`(11px·3단 tiering: spec 중립/caution slate/active amber + `ⓘ 방법론` 원장). 9.5px 위반 전수 교정.
4. 진입 side-effect 명시(`[BT]`→tf 강제 전환에 라벨/empty-state).

### 영향 파일/함수
- **신규** `StrategyDock.svelte`(BtConfig 흡수+자동닫힘 제거), `HonestyFooter.svelte`(tiering+원장).
- **교체** `ChartMenus.svelte`(`:214` 드롭다운 마운트→dock 토글), `BacktestStrip.svelte`(→HonestyFooter+헤드라인). `PriceChart.svelte`(`:1268` dock 레이아웃).
- **재사용** `BtConfig` 룰빌더 내부 무수정(컨테이너만 dropdown→dock).

### 테스트 / 롤백 / 위험
svelte-check 0. Playwright: dock 열고 차트 클릭→빌더 잔존·spine 접힘·정직 11px 측정·empty-state. 위험: 레이아웃 회귀(중) — 차트 폭/리사이즈. 가역(dock→드롭다운 복원). **엔진 0 변경.**

---

## W1 — 유니버스 U1 (간판① · 별도 폴더 · 완전 가역)

> 17년 가격보존 횡단면 분위 백테스트. dartlab만 가진 A− moat. 단일종목 가드 비상속(05 §2.8 신규 가드). **코딩 첫 스텝 = 데이터 게이트 측정·수정(아래 선결).**

### 🔴 선결 (코딩 전 측정으로 닫음 — 추측 금지)
`buildUniversePanel.py`는 *이미 존재*(Jun 16). 단 데이터층 결함 2종 + 측정 미실행:
- **🔴 F1 `delisted` 오염**(`:128` `_lastYm < globalMaxYm`): 폐지/정지/합병/코드변경 혼재 → U-G1 밴드 위에 거짓 표본. **수정 = allFilings 합병공시로 합병 식별 → 합병은 last-close 처리(밴드 제외), unknown 폐지만 양극단**(05 §3.1·§7 U-G1).
- **🔴 F2 forward-return stitching**(`:118-119` `shift(-1).over("stockCode")`, 캘린더 reindex 없음): 정지로 월 빠진 종목의 "1개월 수익"이 2~3개월 → 조용한 구간왜곡. **수정 = 완전 월 그리드 reindex 후 shift**(05 §3.1).
- **G-M1/M2 측정**: `buildUniversePanel.py --skip-upload` → 행수·MB·iOS 콜드로드·floor/local 괴리. FAIL 분기(05 §11).

### AC
1. 단일 가격 팩터(모멘텀 12-1) · 5분위 · 분기 리밸 · 동일가중 · long-only.
2. NAV 분위 곡선 *공유 절대축*(공통 lo/hi·계단). 이중 벤치(EW+지수) 동시·택일불가.
3. **폐지 양극단 밴드**(0손실/−100%, 합병 식별 후 unknown만)·폭>30%p면 hero 숫자 차단.
4. 시도 조합 카운터 상존·OOS 강제(2010~19/2020~26, 끌 수 없음)·정직 라벨(근사·월말·size틸트·추천아님).
5. `decisionT<fillT` assert·PIT 필터 ts≤rebalanceT assert. 재무 팩터 신호 = 비활성(회색).
6. 킬러뷰: NAV 분위 + 스프레드(Q5−Q1) + 턴오버. 현 종목 앵커 백분위. 행클릭→단일종목 drill.

### 영향 파일/함수
- **신규 폴더** `scan/universe/`: `UniverseBacktester.svelte`·`engine.ts`(N종목 holdings 회계)·`ranking.ts`·`types.ts`·`viz/{NavCurves,QuantileSpread,RebalanceWalk,HoldingsTurnover}.svelte`.
- **수정** `.github/scripts/prebuild/buildUniversePanel.py`(F1·F2). **신규 산출** `gov/prices/universe-monthly.parquet`.
- **재사용** 헬퍼 6종(`terminal/lib/backtest/engine.ts`)·`btLayer` 공유축 draw 패턴·`scan/duckSql.ts`·`origin.ts`.

### 테스트 / 롤백 / 위험
엔진 단위(holdings 보존·턴오버·decisionT<fillT·이중실행 청산만 분기)·DuckDB NTILE 결정론·PIT 미래행 미접근·정직 grep. 위험: F1/F2 미측정 착수=밴드 거짓(높) → 선결로 차단. 가역(폴더+버튼 삭제, 기존 무수정). 상세 = 05.

---

## S1 — 다전략 캔버스 (살A · 엔진 배선됨 · dock 흡수)

### AC
1. dock에서 전략 ≤3개, 각 색칩(ID 해시 고정). 포커스 전략 마커(N≥2 클러터 LOD).
2. 에쿼티 N전략+조합+B&H **공유 절대축**(시작 100, per-series 정규화 회귀 0).
3. 조합=동일가중 가중합. MDD 음영 개별보다 얕으면 분산효과 노출.
4. 리플레이 N전략 동시 절단(look-ahead 상속). combo 거래 KPI=명시 "—". 곡선마다 OOS 2열·vs B&H·selection 경고·단일종목 분산 라벨.

### 영향 파일/함수
- **배선됨**: `runPortfolioBacktest`([portfolio.ts](../../ui/packages/surfaces/src/terminal/lib/backtest/portfolio.ts))가 [PriceChart.svelte:808](../../ui/packages/surfaces/src/terminal/charts/PriceChart.svelte) 동작 중 + btLayer N슬롯 공유축. **S1 = dock UX 흡수 + btViz 세계급 마감**(`btViz/EquityCurve` 공유축).
- 마감: 승자강조 0·정렬 입력순·분산효과 미니라벨·헤드라인 11px footer.

### 테스트 / 롤백 / 위험
N=1 byte 동일(회귀)·공유축 정규화 함정·LOD. Playwright: 2전략 2색+에쿼티+combo 동시·MDD<개별·리플레이 동시절단. 위험: dock 흡수 레이아웃(중). 가역.

---

## W2 — 펀더게이트 + 조건빌더 + 시간레인 (간판② · panel 칼날)

> TradingView `request.financial()`이 한국 재무를 엮으므로 차별은 "재무 쓴다"가 아니라 **DART 계정 정규화 + 학술팩터 9 사전구현 + PIT 근사 정직 라벨**. 단일종목이라 생존편향 무관.

### AC
1. **펀더게이트**: `quant/alphas` 9개(Piotroski·Altman Z·Beneish 등)를 진입 게이트로. **PIT = `rcept_dt` 이후 봉만 채움**(공시 전 봉 null=진입차단, 코드 assert). 정정공시 별도 rcept면 정정일 이후 적용·아니면 "공시일 근사" 라벨. 계단·매끈한 선 금지.
2. **조건빌더**(배선됨, [conditions.ts](../../ui/packages/surfaces/src/terminal/lib/backtest/conditions.ts)·`evalRule`·`runBacktestRule`): dock 노출. AND/OR, 각 조건=지표비교 또는 펀더게이트. best/optimal/추천 금지·OOS 강제·거래<10 수치 숨김.
3. **조건 레인 시각화**(02 §3.1, opt-in): 핀한 조건 on/off 스트립 서브페인 + 펀더게이트 배경음영(한 겹) + AND 합성↔진입 마커 수직정렬. 리플레이 동시절단.
4. 출력 boolean 음영만 — 점수·등급·"저평가" 라벨 0(JUDGE 경계).

### ★PIT 빌더 명세 (구현됨 — red-team "calc*Factor(year=Y)" 가정 정정)
> ⚠ **정정**: red-team이 "calc*Factor(year=Y)가 이미 연도 필터"라 했으나 **틀림** — `calcPiotroskiFactor(*, market, stockCode, **kwargs)`는 `year` 인자가 없고 `_latestYear` 로 *최신 1기만* 낸다. 시계열은 신규 public **`calcPiotroskiSeries(market)`**(piotroski.py, `_scoreOne` 전 연도 루프 = 단일 SSOT)로 해결. 실측 9,751행·2,311종목·2020~2025.
- **공시일 소스**: finance.parquet `rcept_no`(14자리 YYYYMMDD+seq) **첫 8자리 = 접수일 = PIT 앵커**(별도 rcept_dt 컬럼 없음). 연간 사업보고서(`reprt_code='11011'`) (stockCode,bsnsYear)별 min rcept_no[:8] = 최초 공시일. 정정공시 = 나중 rcept(min이라 원공시일 채택).
- **alphas 시계열화**: `calcPiotroskiSeries`(구현·검증). Altman·Beneish 등은 동일 패턴 series 함수 후속(각 모듈 `_scoreOne` 류 재사용).
- **신규 빌더**: `.github/scripts/prebuild/buildFundamentalGate.py`(offline·`enforceOffline()`) → `gov/fundamental-gate.parquet`(long-form: `stockCode·bsnsYear·rceptDt·piotroski`). 브라우저 floor 1파일 로드 → `rceptDt` 이후 봉부터 계단. ⚠커버리지 **2020+**(finance 한계, 그 이전 게이트 null=진입 미평가). local=라이브 `calcPiotroskiSeries`.

### 영향 파일/함수
- **데이터**: 위 PIT 빌더(`buildFundamentalGate.py` 신설) + finance `rcept_dt` 앵커. floor=prebuilt parquet, local=라이브.
- **레이어**: `btLayer` 조건 레인 draw(opt-in 핀) + 가격페인 게이트 배경음영. **UI**: `StrategyDock` 조건빌더 섹션 + 펀더 선택 + `◉` 차트핀.

### 테스트 / 롤백 / 위험
조건 평가 단위(AND/OR·PIT 계단)·**PIT assert(공시 전 봉 미적용)**·레인↔진입 정렬. 위험: PIT 조인 데이터 배선(중)·레인 LOD(중). 가역(게이트·레인 제거→프리셋 복원).

---

## S2 — 거래 정밀 + 한국 비용·체결 모델 (살B · `runPass` 확장)

### AC
1. 전략별 손절%·익절%·트레일%·N봉 청산. 손절 마커 색구분(✖ 적), `exitReason:'stop'|'gapStop'`. **봉내 우선순위 고정**(갭→손절→신호, look-ahead 0, "당일 인트라바 가정" 라벨).
2. **한국 비용·체결 모델**(01 §3.5): 호가단위 스냅·상하한가 클램프(갇힘=이연, deferredBars 재사용)·**유동성 비례 슬리피지를 *밴드*로**(점추정 `k` 금지 — folk-stat). 비용 4성분 워터폴(세금/수수료/슬리피지/충격).
3. 거래 분석: MAE/MFE·expectancy·R-multiple·연속승패·보유분포·수익 히스토그램. Calmar·MAR·Ulcer·롤링 Sharpe·월별 히트맵·underwater.
4. 포지션 사이징 fixed-frac·vol-target. **Kelly 수치 금지**(개념만).

### 영향 파일/함수
- **`engine.ts` `runPass`**: stop 체크(high/low 봉내)·`exitReason`·`maePct/mfePct`·사이징. **`btStop=null`이면 현 동작(N=1 byte 동일 회귀)**. `types.ts` 한국 비용 함수(`KrFillModel`)·`BtStopConfig`.
- **`btViz/`**: `MaeMfeScatter`·`ReturnHistogram`·`MonthlyHeatmap`·`RollingSharpe`·`Underwater`·비용 워터폴. `BacktestDialog` Diagnose 탭 확장.

### 테스트 / 롤백 / 위험
손절 trade 비용 정합·equity↔trades reconcile·MAE/MFE∈[worst,best]·N=1 stop=null byte 동일·비용밴드 양끝 실행. 위험: runPass 확장(중~높). 가역(stop/sizing/비용함수 분기 제거).

---

## W3 — 유니버스 U2 + drill-down 동선 (깔때기 완성 · 서사 검증)

### AC
1. 가격/기술 팩터 다양화(저변동성·52주·유동성·반전)·리밸 walk(읽기전용 점프)·보유 회전 테이블.
2. **drill-down**: Q5 행→`/terminal?symbol=` 단일종목(단방향, 역방향 금지). "구성원이지 추천 아님" 툴팁.
3. **★통합 서사 검증**: drill-down 전환율 측정 → "panel 두 방향 절단=한 제품" 가설 증명. 낮으면 통합 OS 서사 조용히 내림(코드 이미 격리).

### 영향 / 위험
`scan/universe/` 확장 + 단일종목 진입 파라미터. 위험: 동선 측정(저). 가역.

---

## 이연 — D1 리밸런싱 / D2 강건성 / D3 미래·재무유니버스

- **D1 P3 리밸런싱**: `runComboBacktest` 별도 패스(부분노출 일반화, 단일전략 무손상). 커서바인딩·append-only·반복재생 카운터(04 §2.1). 위험 高·ROI 재검 후.
- **D2 P4 강건성 / U3 local**: 퍼블릭 민감도(argmax 금지·**색=분산**, 04 §6)·MC 거래 재배열·multi-split anchored OOS(floor 정직 가능). 로컬 walk-forward(refit)·CPCV·DSR/PBO 수치는 04 §1 G2 게이트(영구 DEFER). `_backtestAdvanced.py` 이미 보유.
- **D3 P5 미래연속 / U4 재무유니버스**: mode 토글·asOf→시뮬 초기조건(시뮬 코어 졸업 후). 재무 팩터 랭킹=상폐사 재무 재수집 선결(영구 금지까지).

---

## 순서·게이트
기반(dock) → W1(유니버스, 데이터게이트 선결) ∥ S1(캔버스) → W2(펀더게이트) → S2(거래정밀) → W3(drill-down) → D1~D3. 각 단계 commit 자율·**push 운영자 명시 승인 후**(UI 시각 회귀·공개 무중단). 운영자 go로 기반 착수.
