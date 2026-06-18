# 05. Universe Backtester — 전종목 크로스섹셔널 랭킹 백테스트

상태: v0.1 (2026-06-16, 전문에이전트 4렌즈 토론 + 적대검증). 거처 = `ui/packages/surfaces/src/scan/universe/`(신규).

> ① 단일종목 다전략 캔버스(00~04)와 **별도 객체**다. "이 규칙으로 매 분기 상위 종목을 사면?"을 17년 survivorship-clean 유니버스 위에서 정직하게 회계한다. ①의 단일종목 가드는 *비상속* — 유니버스 특유 거짓말(생존 청산가·자유도 폭발·턴오버·벤치 조작)을 겨냥한 신규 가드가 필요.

---

## 0. 왜 별도 객체인가 (토론 합의)

`①`은 한 종목 candles 위 N전략 equity 곡선이다. `runPortfolioBacktest`의 `equity:(number|null)[]`는 candles 길이에 묶이고(`portfolio.ts:73`), combo는 *손으로 고른 N≤3 전략의 equity 가중합*이다. 유니버스는 **전종목(~2000+)을 매 리밸런싱마다 팩터로 랭킹 → 상위 K 보유 → 재랭킹**하는 *크로스섹셔널 포트폴리오 회계*다. 멤버십 교체·체결·턴오버 회계가 필요해 `runPass`(long/flat 단일종목 캐시 회계)를 **버린다**. 공유는 순수 equity 헬퍼 6종(`mdd`·`mddWindowOf`·`riskRatios`·`benchmarkStats`·`endRet`·`cagr`)뿐.

→ **04 §2 가드를 그대로 상속하면 "단일종목 가드로 유니버스를 검사했다"는 거짓 안전감**이 생긴다. 04 §2.8·2.9 신설로 막는다.

## 1. 거처 · 재사용 (실측 근거)

- **거처 = `ui/packages/surfaces/src/scan/universe/`** (terminal charts 아님). 근거: scan이 이미 `gov/prices/date/{year}.parquet`(67만행 long-form, 17년 survivorship-clean)를 DuckDB-wasm 뷰 `krxPricesAll`로 등록(`scan/tableSources.ts`) + ScreenBuilder(유니버스 정의) 보유. 백테스터 = scan의 자연 종착("스크린→랭킹→walk").
- **reject**: terminal `btLayer.ts`/`portfolio.ts` 확장 = candles-aligned 단일종목 계약(`portfolio.ts:73`)이라 N종목 holdings 못 받음. DataExplorer 탭 = 테이블 뷰어라 시계열 루프 부적합.
```
scan/universe/
  UniverseBacktester.svelte   풀스크린 모달 (DataExplorer 형제, scan LeftRail [유니버스 백테스트▸])
  engine.ts                   N종목 holdings 회계 루프 (신규 — 순수 헬퍼 6종만 재사용)
  ranking.ts                  랭킹 신호 (모멘텀·저변동성·52주신고가·유동성·단기반전)
  types.ts                    UniverseSpec·RebalanceSnapshot·UniverseBtResult
  viz/{NavCurves,QuantileSpread,RebalanceWalk,HoldingsTurnover}.svelte
```
- **재사용**: `terminal/lib/backtest/engine.ts`(헬퍼 6종)·`charts/btLayer.ts` 공유 절대축 draw 패턴(공통 lo/hi 픽셀 매핑)·OOS 분할선 draw·`scan/duckSql.ts`(`DartDb`·`krxPricesAll`)·`scan/ScreenBuilder`·`origin.ts`(HF SSOT)·`quant/alphas`(local 재무, P1 미사용).
- **동선**: 유니버스 walk → Q5 보유 행 클릭 → `/terminal?symbol=` 단일종목 차트(단방향 drill-down). **역방향 금지**(단일종목→유니버스 = cherry-pick 유인).

## 2. 엔진 계약 (신규 `universe.ts`)

```ts
interface UniverseSpec {
  rebalance: 'M' | 'Q' | 'W';                 // 거래일 캘린더 위 첫 거래일
  rankSignal: RankSignalKey;                   // 'mom12_1'|'lowVol60'|'high52w'|'turnover'|'reversal1m' (가격/기술만 P1)
  selection: { kind:'topN'; n:number } | { kind:'quantile'; buckets:number; pick:number };
  weight: 'equal';                             // P1 동일가중만 (cap/inv-vol = 후속)
  longShort: false;                            // P1 long-only (공매도·차입비용 folk)
  universe: 'all' | { market:'KOSPI'|'KOSDAQ' };
  minLiquidity?: number;                       // ADV 컷 (그 리밸 시점 데이터로만 — PIT)
  costBp: BtCostsBp;                           // 기존 타입 재사용 (턴오버 기반 적용)
  windowFrom: string; windowTo: string;
}
type DelistReason = 'none' | 'merger' | 'unknown' | 'codeChange';  // §3.1 F1 — bool 격상
interface RebalanceSnapshot {
  t: string; decisionT: string; fillT: string; // decisionT < fillT 불변 (look-ahead 차단)
  selected: { code; rankValue; weight; delistReason?: DelistReason }[];
  turnover: number; nHeld: number; nEligible: number;
  mergerExits: number; unknownExits: number; advBreaches: number;  // 정직 카운터 (합병/unknown 분리)
}
interface UniverseRun {                          // 한 청산가정의 1회 실행 (unknown 폐지만 분기)
  navByBucket: Record<number, number[]>;         // 분위별 NAV (시작 100). 합병=last-close 고정(밴드 무관)
  ewBench: number[]; indexBench: number[];       // 동일가중 전체 + 지수 (둘 다)
  metrics: UniverseMetrics;                      // equity 헬퍼 재사용 + 턴오버·집중도
  cashDragPct: number;
}
interface UniverseBtResult {
  optimistic: UniverseRun;                       // ⓐ unknown 폐지=0손실(마지막 종가) · 합병=last-close
  conservative: UniverseRun;                     // ⓑ unknown 폐지=−100손실 · 합병=last-close — 헤드라인 기준
  unknownDependence: number;                     // 두 실행 종착 차이(%p) = 밴드 폭 = *진짜 unknown* 의존도(U-G1)
  headlineSuppressed: boolean;                   // 밴드 폭>30%p → hero 숫자 차단(U-G1 ④)
  rebalances: RebalanceSnapshot[];               // 청산가정 무관(선정·턴오버 동일)
  status: 'ok' | 'invalid';
}
// 엔진은 동일 랭킹·체결 경로를 청산가정 2값으로 2회 — 선정/턴오버·합병 청산은 공유, unknown 청산만 분기(저비용).
```
- **회계 루프**(일별 마킹 + 리밸일 execute): `nav = cash + Σ shares·close(code,t)`. 리밸일 = 신호는 `decisionT`(직전 거래일) 종가까지로 랭킹 → `fillT`(t+1) 시가 청산·매수, 비용 = `turnover × costBp`. 정지(v=0)·결측 = 체결 이연 + cashDrag(forward-fill 금지).
- **재사용 vs 신규**: 헬퍼 6종 그대로 / 랭킹·eligibility·분위 버킷·holdings 루프·턴오버·이중 벤치 전부 신규.

## 3. 데이터 경로 — floor vs local (실측 성능)

- **date 샤드 실측**: 연도당 12.5~16.6MB, 17파일 ≈ 230MB, 일별 전체 ≈ 1,200만행. **라이브 일별 17파일 쿼리 = floor 불가**(iOS WASM 힙 200~512MB 즉사, scan이 2년 윈도에도 30/60초 타임아웃 — `duckSql.ts`).
- **floor(퍼블릭 서버0) = prebuilt 월말 리샘플 패널**. 신규 `.github/scripts/prebuild/buildUniversePanel.py`(offline only, `buildPricesSnapshot.py` 템플릿·`enforceOffline()`):
  - 산출물 `gov/prices/universe-monthly.parquet` (long-form, 월말 1행/종목/월). **실측 스키마**: `ym·stockCode·close·mktcap·turnover·momMonthly·volMonthly6m·high52wProx·retFwd1m·retFwd3m·delistReason`. **실측 443,422행 = 11.91MB 단일 파일**(가격/기술 팩터만, 재무 EXCLUDE).
  - 브라우저는 1파일 로드 → DuckDB-wasm `NTILE` 크로스섹셔널 랭킹 + forward port return 루프.
  - **월말 = `MAX(BAS_DD) per (ym,stockCode)`**(캘린더 월말 아닌 그 월 마지막 거래봉).
- **local(:8400 bonus) = Python 일별 full-resolution**(date 샤드 17파일 직독, t+1 시가 체결·정지 이연 정밀). floor 월말 근사를 일별 정밀로 격상.
- **선결 의존**: ① `buildUniversePanel.py` 산출물 — ⚠ **스크립트는 이미 존재**(`.github/scripts/prebuild/buildUniversePanel.py`, 8157B, Jun 16). 따라서 게이트는 "작성"이 아니라 **"측정·결함수정·실행"**(§3.1). ② OPFS 캐시 재활성(`duckdb.ts` 현재 비활성 — 재방문 0다운로드).

## 3.1 ★데이터층 결함 수정 (적대검증 발견 — U1 출시 필요조건, 측정으로 닫음)

> **★실측 완료 (2026-06-18, commit `34dde130c`)**: F1·F2 수정 + 로컬 17샤드 전체 build.
> - **G-M1 PASS**: 443,422행 · 3,693종목 · ym 201001~202606 · **11.91MB(<20MB)** → floor 단일파일 로드 OK.
> - **폐지 886종목** · **F2 reindex 적용**(정지월 stitching 차단, 합성+실데이터 로직검증 PASS).
> - ⚠ **F1 merger=0 (중요 한계)**: 검출윈도(last ym≥202406) 폐지 151종목이 **allFilings recent에 0 출현** — `recent.parquet`(2024-09+)은 *활성기업* 수시공시라 *폐지기업 공시를 안 담음*. 즉 F1 merger 검출은 *코드는 정상(합성검증 PASS)이나 현 데이터로 실질 no-op* → **밴드가 전부 conservative(886 unknown)**. 정직-degradation 설계대로(거짓 제외 0)지만, 진짜 merger 제외 = **정밀 폐지사유 데이터 소스(KRX 상폐사유)가 별도 트랙**(U4와 함께). 현재는 밴드 폭이 진짜보다 넓을 수 있음을 라벨(보수 안전).

`buildUniversePanel.py`가 *존재하나* 데이터층에 U-G1·수익률을 깨는 결함 2종이 박혀 있다(아래 = 수정 전 진단). **코딩 착수 첫 스텝 = `--skip-upload`로 측정 + 아래 수정.**

- **🔴 F1 `delisted` 오염**(`:128` `(_lastYm < globalMaxYm)`): "최근 2개월 미출현"을 폐지로 보나 **합병·정지·코드변경·실폐지를 한 bool로 뭉갬**. U-G1 양극단 밴드가 이 bool 위에 서므로 → 합병(주주 인수가+프리미엄)을 −100% 처리 → 보수 헤드라인 *허구 과소평가* = 밴드가 분류버그 증폭기(04 §2.8 U-G1).
  - **측정**: 이 bool로 잡힌 "폐지" 중 합병/정지/코드변경 비율(allFilings mna 공시 + gov 재상장 코드 cross).
  - **★수정 방법 (재사용 자산 명시 — 텍스트 완벽판정 불가라 정직 휴리스틱)**:
    1. **합병 추정**: `quant/signal/event.py:18 _EVENT_RULES`의 mna 분류(`["합병","인수","분할","영업양수","영업양도"]`)를 allFilings `report_nm`에 적용 → **폐지일 직전 ±3개월 윈도에 mna 공시 있는 종목 = `delistReason='merger'`(추정)**. ⚠ 방향(소멸/존속)·종목귀속은 report_nm 텍스트로 완벽판정 불가 → **"합병 추정" 라벨**(확정 아님). `gather/transforms/corporateAction.py`의 `action_type='merger'` SSOT는 *수동 입력 원장*이라 보강 cross(있으면 우선).
    2. **코드변경**: gov 재상장 코드 cross(같은 corp 다른 ISU_CD) = `delistReason='codeChange'` → 가격 연결(폐지 아님).
    3. **나머지 폐지** = `delistReason='unknown'`(상폐·정지 혼재) → 양극단 밴드.
    4. `delisted: bool` → `delistReason: str(none/merger/unknown/codeChange)` 컬럼 격상. **휴리스틱 자체가 근사라 "사유=추정" 라벨 상존**(완벽 분류 주장 금지 — never-claim 정신).
- **🔴 F2 forward-return stitching**(`:118-119` `shift(-1).over("stockCode")`, "ym 정렬 전제"): 정지로 월 빠진 종목의 `retFwd1m`이 *건너뛴 다음 존재월*을 가리켜 실제 2~3개월 → 조용한 구간왜곡/look-ahead.
  - **측정**: 월 간격이 1이 아닌 (stockCode,ym) 쌍 비율.
  - **수정**: **완전 월 그리드 reindex**(전 종목×전 월 outer join) 후 shift → 결측월은 명시 null(forward-fill 금지). `momMonthly`·`volMonthly6m`도 동일 reindex 위에서.
- **산출 스키마 변경**: `delisted: bool` → `delistReason: str`(none/merger/unknown/codeChange). 합병 식별 join이 prebuild의 신규 의존(offline 가드 유지 — allFilings도 HF 다운로드).

## 4. 팩터 — 가격 P1 / 재무 랭킹 금지

- **✅ P1 (가격/기술, 17년 clean)**: 모멘텀(12-1·6-1)·저변동성(60/120봉)·52주 신고가 근접·유동성(거래대금)·단기반전(1개월). OHLCV만 쓰고 상폐사도 폐지일까지 후보 → survivorship-clean.
- **❌ 재무 팩터 *랭킹* = P1 금지(배너로도 불가)**: panel은 사라진 코드의 **13.9%(86/618)만** 재무 보유 → 망한 회사 86% 후보 누락 = 분모 자체가 생존자 편향(저PBR·고배당 등이 실제보다 좋아 보임). **배너는 *해석*을 가릴 뿐 *생성된 수치의 상향 편향*은 못 가림.** G6(held-out·zero-train 게이트) = 상폐사 재무 미수집이라 통과 *불가능* → 금지가 정공법. 정밀 재무 유니버스 = 상폐사 재무 재수집(별도 트랙) 선결.
- **✅ 단일종목 재무 *게이트*(04 §4.10)는 허용** — 한 종목 진입 조건이라 분모 문제 없음(생존편향 무관). **칼 = 랭킹 금지 / 게이트 허용.**

## 5. 벤치마크 — 이중 강제

- **(a) 동일가중 전체 유니버스(primary)** + **(b) 시총가중 지수(KOSPI/KOSDAQ, gov indices 샤드)** — **둘 다 동시 표시 의무(택일 금지)**.
- 동일가중 = 그 자체가 소형주 size 틸트 → "초과수익은 size 프리미엄 포함" 라벨. 지수만 쓰면 size·비용 차이가 알파로 오인. **둘 다 + 라벨 = 정직 필요조건(충분조건 아님 — size·유동성·생존 잔차 미통제 명시).**

## 6. 킬러뷰 + UX

킬러뷰 = **"N분위 NAV 곡선 + 분위 스프레드(Q5−Q1)"**. "분위가 단조롭게 벌어지는가"가 한 자에 읽히는 게 전부. 보유 회전 테이블은 *증거*(walk 다이얼로그 격리).
```
┌─ 유니버스 백테스터 ─────────────────────[월말 근사 ⓘ]──[✕]─┐
│ KOSPI+KOSDAQ 전종목(상폐포함) · 리밸 분기 · 12-1 모멘텀 · 5분위 · 동일가중 │
│ ┌─ NAV (공유 절대축, 시작 100) ──────────────────────────┐  │
│ │ Q5(상위) ━━━━━━ +148   Q4 ─── +121                      │  │ ★분위 끝만 라벨
│ │ EW전체 ▒▒▒▒ +110 (primary 벤치)  KOSPI - - +88 (보조)   │  │
│ │ Q1(하위) ─ ─ +71   ░EW MDD -34%(월말표본)░  ⚖⚖⚖ 리밸    │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌ 분위 스프레드 Q5−Q1 +77%p ┐ ┌ 턴오버 38%/분기 ┐            │
│ │ ⚠ 단조성=눈으로(t-stat 아님)│ │ ⚠ ADV초과 4% 빨강│            │
│ └────────────────────────────┘ └─────────────────┘            │
│ Q5 +148·EW +110·α +38%p │ ⚠ 사후선택 1신호·표본=리밸24회 [walk▸]│
└────────────────────────────────────────────────────────────────┘
```
- NAV = klinecharts 아닌 경량 SVG(NavCurves), `btLayer` 공유 절대축 draw 이식. floor 곡선은 **계단**(직선 보간 금지 — 월말만 평가 시각화). 분위 끝만 라벨, 중간 dim.
- **리밸 walk = 읽기전용 점프 스크럽**(이산 리밸 시점, ①의 연속 재생 아님). 편입▲/편출▼/유지● + "→다음분기 수익"(사후 라벨). 행 클릭 → 단일종목 drill-down("구성원이지 추천 아님" 툴팁).

## 7. 정직 가드 (04 §2.8·2.9 신설 — 떼어낼 수 없음)

| 가드 | 내용 |
|---|---|
| **U-G1 생존 = 합병식별 + 양극단 이중실행 밴드** | 폐지 청산가는 사유 미구분이라 *알 수 없다* → **임의 숫자(−30% 등) 금지**(folk-stat). ★v0.2 정정(적대검증): "사유 미구분"을 미덕으로 두면 **합병(주주 인수가+프리미엄)이 −100%에 들어가 보수 헤드라인 허구 과소평가** → 밴드가 분류버그 증폭기. **4단계**: ① **합병 식별**(§3.1 F1: allFilings mna 분류 폐지일 근접 휴리스틱) → 합병 추정 = last-close 청산(**밴드에서 제외**), ② **unknown 폐지만** 두 극단 2회 실행 ⓐ 0손실(낙관) ⓑ −100%(보수) → **밴드 폭 = *진짜 unknown 폐지 의존도***(폐지명 없으면 폭 0), ③ 상한은 last-close(0손실)에 고정 + "합병 프리미엄은 이 위 — 낙관 끝도 보수적일 수 있음" 라벨(*비대칭 무지의 방향 정직*: 밴드 전체가 진실의 하방), ④ 밴드 폭>30%p면 **hero 숫자 차단**(라벨 아닌 차단). 헤드라인 정렬·비교는 보수(−100%) 끝 기준. |
| **U-G2 PIT 멤버십** | 유니버스·필터(시총/거래대금 컷)는 *그 리밸 시점 그날 date 샤드*로만(코드 assert: 필터 입력 ts ≤ rebalanceT). IPO = 상장+룩백 충족 후만. forward-fill 금지. |
| **U-G3 턴오버·ADV P1 승격** | 단일종목 P4 아님 — **턴오버율·추정비용·ADV 초과 주문비율 KPI 동급 상시 노출**. 주문>ADV X% = "실거래 불가능" 빨강. bp 고정=소형주 비용 과소 경고. |
| **U-G4 이중 벤치** | EW 유니버스 + 지수 둘 다 표시 의무. size 틸트 라벨. 필요조건이지 충분조건 아님 명시. |
| **U-G5 리밸 타이밍 운** | "리밸일 ±N일 흔들면 결과 달라짐 — 한 타이밍 운 포함" 라벨. (지터 밴드 = local bonus.) |
| **U-G6 floor/local 근사(§2.9)** | floor NAV에 *(근사·월말)* 접미. "월중 손절·갭·정지 미반영, MDD 과소평가" 라벨. env.kind 분기로 라벨 증발 금지. local에서 괴리 오버레이 비교. |
| **U-G7 selection 차단** | argmax 금지만으론 부족 → **시도 조합 카운터**(팩터×분위×K×주기×필터 누적, "N조합 탐색=자유도 N") + **OOS 강제(끌 수 없음, 2010~19 train/2020~26 test)** + 사전규칙 1종 P1 + 중립 렌더(수익순 정렬 금지). |
| **U-G8 어휘 봉인** | "이 팩터가 시장/KOSPI를 이긴다"·"검증된 팩터"·"유효한 전략" = 투자자문(CLAUDE) grep 0. IC·팩터 t-stat·분위 단조성 **수치** 금지(표본=리밸 ~72회). 표면 = "과거 [기간] 이 유니버스·규칙 회계 결과, 추천 아님". |

## 8. 단계

- **U1 (최소·정직)**: 단일 가격 팩터(모멘텀 12-1) · 5분위 · 분기 리밸 · 동일가중 · long-only · 이중 벤치 · 보수 청산 · 시도 카운터 · OOS 강제. floor 월말 패널(prebuild) + DuckDB-wasm 루프. 킬러뷰(NAV 분위 + 스프레드 + 턴오버).
- **U2**: 가격/기술 팩터 다양화(저변동성·52주·유동성·반전) · 리밸 walk · 보유 회전 테이블 · ① drill-down.
- **U3 (local bonus)**: Python 일별 정밀 · ADV 비선형 충격 · 리밸일 지터 밴드 · floor/local 오버레이 비교.
- **U4 (별도 트랙·미착수)**: 재무 팩터 유니버스 = 상폐사 재무 재수집 선결(G6 게이트). 그 전 영구 금지.

## 9. 위험 · 선결 의존

1. **floor 라이브 일별 유혹 = iOS 즉사** → prebuilt 월말 패널이 **U1 진짜 선결**. `buildUniversePanel.py`는 *이미 작성됨* → 착수 전 1순위 = **결함수정(§3.1 F1·F2) + 측정(G-M1·M2) + 실행·HF push**. (문서 v0.1의 "미작성" 단언은 실태와 불일치였음 — 설계가 자기 산출물을 몰랐던 함정.)
2. **생존 청산가 미지**(U2 적대 발견 — 00 §4.11 "사유 미구분=무관"은 크로스섹셔널에서 거짓) → 임의 숫자 대신 U-G1 **양극단 이중실행 밴드**(0손실/−100%)로 불확실성 자체를 노출. 밴드가 비현실적으로 넓은 전략 = "폐지명 의존 과다" 경고(G-M4).
3. **자유도 폭발**(팩터×분위×K×주기×필터 = 수천 조합) → U-G7 카운터+OOS+사전규칙.
4. **OPFS 비활성** → 재방문 재다운로드. 월말 패널 작아 견디나 재활성이 헤드룸.
5. **floor 월말 vs local 일별 괴리** → U-G6 근사 라벨·계단 곡선·오버레이.

## 11. ★실측 게이트 (코딩 착수 = 측정으로 닫음 — 추측 금지)

설계는 확정이나 *현실 수치 전제*는 미측정이다. 구현 1단계 = 아래 게이트를 실측으로 닫고, FAIL이면 *설계에 미리 박힌 분기*로 간다(재토론 없음).

| 게이트 | 측정 | PASS 기준 | FAIL 분기 (사전 명시) |
|---|---|---|---|
| **G-M1 prebuild 패널** | `buildUniversePanel.py` 실행 → 행수·parquet MB·DuckDB-wasm 콜드로드 ms (데스크톱+iOS) | <20MB · 콜드로드 <5s · iOS 미충돌 | ① 팩터 컬럼 축소(파생 줄임) → ② 유니버스 시총컷(소형주 제외) → ③ floor=KOSPI만 |
| **G-M2 floor/local 괴리** | 동일 전략 월말 vs 일별 종착 수익률·MDD 차이 | 종착 괴리 ≤ ~5%p (가독 임계) | floor = "단순 가격전략만(괴리 큼 라벨 강화)" / 정밀은 local 전용 격리 |
| **G-M3 OPFS 재활성** | `duckdb.ts` OPFS 캐시 검증 | 재방문 0다운로드 | in-memory only 수용(월말 패널 작아 재다운 견딤) |
| **G-M4 폐지 밴드 폭** | 0손실/−100% 이중실행 밴드 폭 분포(전 전략) | — (관측) | 밴드 >~30%p 전략 = "폐지명 의존 과다" 빨강 경고(차단 아닌 라벨) |

→ **G-M1 = 코딩 착수 첫 스텝**(없으면 floor 67만행 클라 로드로 죽음). G-M1·M2 결과가 floor 범위를 확정한다.

## 12. U1 수용기준 (AC) · 테스트 매트릭스 · 롤백

**U1 AC (전부 충족해야 출시):**
- N분위 NAV가 *공유 절대축*(공통 lo/hi)에 렌더 — per-series 정규화 0(`btLayer` draw 패턴 회귀 테스트).
- 이중 벤치(EW+지수) 동시 표시, 택일 불가. 폐지 밴드(0/−100%) 표시, 폐지명 보유 시 단일 hero 숫자 0.
- 시도 조합 카운터 상존, OOS 분할 끌 수 없음, 정직 라벨(근사·월말·size틸트·추천아님) 상존.
- `decisionT < fillT` 코드 assert. PIT 필터 입력 ts ≤ rebalanceT assert. 재무 팩터 신호 = 비활성(회색).

**테스트 매트릭스:**
- **엔진 단위(`universe.engine.test`)**: holdings 회계 보존(Σ가중=1·NAV 연속)·턴오버 산식·`decisionT<fillT`·이중실행이 선정/턴오버 공유하고 청산만 분기·OOS 분할 리밸 단위·헬퍼 6종 재호출 일치.
- **DuckDB 쿼리**: `NTILE` 크로스섹셔널 랭킹 결정론(동일 입력=동일 분위)·월말 = `MAX(BAS_DD) per (ym,code)`·PIT 필터 미래 행 미접근.
- **Playwright(`scan/universe`)**: 분위 곡선 N개+이중벤치 렌더·밴드 표시·리밸 walk 점프·Q5행→단일종목 drill·시도카운터 증가·콘솔 0.
- **정직 회귀(grep)**: "전문가급"·"추천"·"검증된 팩터"·"시장 초과" 0건·IC/팩터 t-stat/분위 단조성 수치 0·시도카운터·이중벤치·폐지밴드 존재.

**롤백**: `scan/universe/` 전체가 신규 폴더 + scan LeftRail 진입 버튼 1개 → 폴더 삭제 + 버튼 제거로 완전 가역. `terminal/lib/backtest`(① 엔진)·기존 scan 무수정이라 회귀 0. prebuild 산출물은 HF 별도 파일(기존 데이터 무영향).

## 13. 평가 (전문 개발자 · PM 이중)

- **개발자**: 위험 집중점 = (a) `buildUniversePanel.py` 산출물 크기/성능(G-M1) (b) DuckDB-wasm 크로스섹셔널 루프 + holdings 회계 신규. 완화 = scan `krxPricesAll`·`btLayer` 공유축 draw·헬퍼 6종 재사용으로 신규 표면 최소화, 회귀는 별 폴더 격리. 이중실행은 월말 패널이 작아(저비용) 부담 없음.
- **PM**: 킬러 = "분위가 단조롭게 벌어지나"가 한 자에 읽힘 + 폐지 밴드로 *불확실성까지* 정직. 차별 = 가격 백테스터(TradingView 등) 단일종목 한계를 17년 survivorship-clean 유니버스로 넘음 — 단 재무 랭킹 금지를 *제품이 먼저 정직히 답함*(13.9% 회색 비활성)이 신뢰. 위험 = floor/local 괴리(G-M2)가 크면 floor 신뢰 저하 → 범위 축소 분기 대비.

## 14. 경계 (claim 금지)

- JUDGE(reverseDCF·compare) = financial-statement-lab. 시뮬/지수/이벤트레일 = scenario-simulator. egress = table-export. 본 랩 = *전종목 규칙 회계*만.
- 종목 추천·목표주가·"검증된 팩터"·"시장 초과" 일반화 = 금지(CLAUDE 투자자문 규약).
