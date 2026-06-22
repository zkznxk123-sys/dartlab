# Terminal Chart Suite — 차트 중심 터미널 PRD Index

> ✅ **DONE · _done 이관 (2026-06-16)**: 01 주가/지수 차트(subject 토글·IndexPort)·02 공시 이벤트 레일(discRail)·04 지표 팔레트(econOverlay·SUB_GROUPS) **전부 구현·출시 완료**. 03 백테스팅은 `mainPlan/terminal-strategy-lab/`로 **재기획·분리**(차트=시간기계 다전략, SUPERSEDED — 본 폴더의 03은 이력 보존). 미래 Play 연속은 `../../scenario-simulator/05`가 본 suite를 단방향 소비. 신규 백테스팅 작업 = `terminal-strategy-lab/`.

상태: v0.2 (2026-06-14 — scenario-simulator 에서 분리 신설 후 **4 문서 전부 공통배선(포트/어댑터) 이후 현재기준 정합 완료**. 01·04 는 이미 ui/packages 기준; 02·03 은 v0.3 정합 섹션(02 §1.5 / 03 §0.5)으로 경로·아키텍처·스코프 확정. 전문 4-렌즈 토론 + ground-truth 실측. **착수 = 운영자 go 대기**(코딩 아님 — 본 트랙은 *플랜 완성*까지))
범위: 메인 주가 차트 위에서 동작하는 **현재/과거** 터미널 기능 — 주가/지수 차트·공시 위치 타임라인·EOD 백테스팅. 미래 방향(Play 시뮬레이션)은 `../../scenario-simulator/`가 소유한다.

---

## 한 줄 결정

이 suite는 차트의 **현재/과거**를 그리는 세 터미널 기능이다(주가/지수·공시 레일·백테스팅). 셋은 *독립적으로 출시 가능*하며 시뮬레이터 없이도 단독 가치를 가진다. 시뮬레이터(`scenario-simulator/`)의 **Play 미래 리플레이는 같은 차트의 *미래* 방향 대칭 확장**으로, 이 suite를 **단방향으로 소비**한다 — 절단면은 임의가 아니라 **시간축**이다(현재/과거 = suite, 미래 = 시뮬).

---

## 왜 분리했나 (scenario-simulator 에서 추출)

- **원래 별도 PRD였다**: 02(레일)·03(백테스팅)은 메모리 `project_terminal_disclosure_event_rail_prd`·`project_terminal_backtesting_prd` 였다가 시뮬 PRD에 컴포넌트로 흡수됐던 것. 분리는 over-coupling 되돌리기.
- **인질 해소**: 시뮬레이터는 "될 설계지 증명 아님"(검증 루프 write-end·admission·lens 미빌드). 이 셋이 시뮬 PRD에 묶이면 *시뮬의 미완 게이트 뒤에 인질로 잡힌다*. 분리 → 구체적·즉시 출시 가능한 셋을 먼저, 시뮬은 천천히.
- **실행 순서 = 분리선**: 통합 로드맵(시뮬 07)이 이미 `지수→레일→백테스팅→시뮬+Play`로 시퀀싱 중. 앞 셋이 본 suite, 마지막이 시뮬.

---

## ★단방향 의존 규칙 (불가침)

```
terminal-chart-suite (현재/과거)  ──(소비)──▶  scenario-simulator/05 Play (미래)
       ▲ suite는 시뮬을 모른다(역참조 0)
```

- **suite ⟶ 시뮬 역참조 금지**: 본 suite 3문서는 시뮬레이터를 *상류 의존으로 선언하지 않는다*. 시뮬 Play(05)가 suite를 소비한다(차트 미래 캔버스는 01 차트 재사용·미래 공시 마커는 02 레일의 `DisclosureEvent` 계약 재사용·look-ahead/RunSpec DNA는 03 백테스팅 SSOT 재사용).
- **시뮬-앵커 사상과 동형**: leaf→simulate 단방향(`test_simulate_leaf_ssot`)과 같은 결 — 미래층이 현재/과거층을 호출만 하고, 현재/과거층은 미래를 모른다.
- **미래 마커 이관**: 02 레일은 *과거 공시 위치*만 완결. 미래 정기공시 점선은 표시할 캔버스(시뮬 05 §3)가 있어야 생기므로 **시뮬 트랙으로 이관**(02는 `DisclosureEvent` 데이터 계약만 준비).
- **DSR/PBO·RunSpec SSOT = 03 백테스팅**, 시뮬이 *재사용*(중복 신설 금지).

---

## ★로컬/퍼블릭 공동배선 (suite 공통 불가침)

세 기능 모두 **공유 surface**(`ui/packages/surfaces/src/terminal/`)에 살고, 데이터는 **포트/어댑터 런타임**으로 흐른다. 따라서 **퍼블릭 floor 에 설계, 로컬은 bonus**(메모리 `project_terminal_improvement` 2타깃 원칙).

- **퍼블릭(landing, adapter-static·서버 0·브라우저)** = floor. 세 기능 전부 브라우저에서 완결돼야 한다 — 01 지수=브라우저 parquet 직독, 02 공시=`rt.filing.*`(브라우저 parquet), 03 백테스트=브라우저 TS 엔진(`rt.price.loaded` 캔들).
- **로컬(:8400 백엔드·포트 배선됨)** = bonus(빠름·장기이력·Python). floor 기능을 *대체하지 않고 보강*만.
- **불변**: 어느 기능도 `env.kind` 로 분기해 floor 에서 사라지면 안 된다. 포트가 같은 형(01=IndexPort·02=FilingPort·03=PricePort) 을 public/local/fake 3 어댑터에서 동시 만족(01 §3.5 가 IndexPort 3어댑터 conformance 의 *예시 정본*).
- **신규 어댑터 작업**: 01=IndexPort 3어댑터 신규(govIndex/fredIndex/fake) · 02=어댑터 변경 0(fake nonRegular fixture 1건만) · 03=어댑터 변경 0(엔진 순수·캔들 패리티만). Python(03 Robustness)은 별도 PRD·parity-gate 뒤 local 전용.

---

## 문서 지도

1. [01-price-index-chart.md](01-price-index-chart.md) — 주가/지수 차트(center subject-swap, IndexPort catalog/search/series, KR gov OHLCV 캔들 + US FRED 종가 라인 평행 subject, candleStyle='area' degenerate, 종가전용 지표 3분기, subject 소유권 seam).
2. [02-disclosure-event-rail.md](02-disclosure-event-rail.md) — 공시 위치 찾기 레일(x축 아래 과거 공시 위치, `rceptNo` 중심 `DisclosureEvent` 정규화, 호버 메타·클릭→우측 행 스크롤. 미래 마커는 시뮬로 이관). **v0.3 정합(§1.5 SSOT): 마커 ~70% 기빌드 실측 → 하단 레일 채택 + disclosure 캔들고가 경로 제거(one-system)·rt.filing.\* 포트 소비(어댑터 변경 0)·형제 펄스 스토어 sync·타입 18→6 필드.**
3. [03-backtesting-strategy-tester.md](03-backtesting-strategy-tester.md) — 차트 중심 EOD 백테스팅 Strategy Tester(look-ahead 차단·t종가→t+1시가 체결·비용 기본 ON·RunSpec/ledger/provenance·DSR/PBO 과최적화 가드. 리포트 도크 스크롤). **v0.3 정합(§0.5 SSOT): 엔진 정확성 척추 이미 라이브 실측 → v1 CORE=리포트 도크 4탭+계약 경화(~4파일·2원장+reconcile)·Sensitivity/Robustness/Builder/Python parity 는 별도 PRD DEFER·빈 Robustness 탭 금지.** **v0.4(§0.5.9+§0.6, 4-렌즈 토론): 엔진 SSOT=TS(터미널 floor 실행)+Python(robustness 정본)·겹치는 표면은 golden parity fixture 중재. floor 경계=OOS train/test 분할 시각+2열은 floor 승격(표본이 받침)·DSR/PBO/CPCV 수치는 folk-stat이라 단일종목 floor 금지(로컬 정밀 모드·게이트). BtConfig→전략 콘솔 CORE(버튼 약함 직격). 엔진 갭 3종(Python reconcile·벤치마크상대·parity fixture)=배선/정합. 레드팀 §0.6 가드 5종(통계천장·문구봉인·탐색=과적합경고·벤치편향고지·G1/G2 엔진개선게이트).**
4. [04-indicator-overlay-palette.md](04-indicator-overlay-palette.md) — 경제·보조지표 오버레이 + 팔레트 조직(2026-06-14, F1). **신규 능력 0** — econOverlay·MACRO_SERIES·ChartMenus/ChartRibbon 전수 팔레트·SUB_GROUPS 이미 라이브. 작업 3건 = SUB_GROUPS 조직 이식·ECON 우선 순서·마퀴 클릭→toggleEcon 배선(명시 분기).

> **참조 규약**: suite 내부 = 01/02/03/04. **시뮬 PRD 바 번호(05 Play·07 통합로드맵·08 valuation·09 정합화 등) = `../../scenario-simulator/NN`.** 통합 시퀀싱은 시뮬 07(브리지 문서)이 소유.

---

## 경계 (불가침)

- **시뮬레이터(미래 Play·드라이버 DAG·valuation·신용·정합화)** = `../../scenario-simulator/`. 본 suite는 미래를 그리지 않는다.
- **`terminal-improvement`**(블룸버그식 수평 직조·워치리스트·커맨드바) = 별개. 그 PRD가 ceding 하던 "지수/이벤트레일"은 이제 본 suite 소유(terminal-improvement 경계 노트 정정 동반).
- **UI 토폴로지**: 본문의 `landing/src/lib/terminal/<rest>` 경로는 stale — 새 SSOT = `ui/packages/surfaces/src/terminal/<rest>`(터미널 전체 이동 ff9099ba0). 각 문서 헤더의 기계적 매핑 규약대로 읽는다.

---

## 착수 게이트

mainPlan(터미널 ui/packages 정착) 완료 + 운영자 go 후 착수. 단 **01 주가/지수 차트·04 지표 팔레트(F1)는 mainPlan 무관 선행 가능**(01=IndexPort 충돌 1회 확인 / 04=기존 자산 배선). 넷은 시뮬 미완과 무관하게 독립 진행 가능 — 그것이 분리의 핵심 이득.

- **이 트랙(플랜 완성)은 코딩이 아니다** — 4 문서를 *재조사 없이 구현 가능한 완전 설계*로 확정하는 것이 범위. 구현 착수는 운영자 go.
- **UI 변경이므로 push 는 운영자 명시 승인 후에만**(`feedback_ui_rules`: 스크린샷 전수 눈검수 + 공개 터미널 무중단 + 완결 단위만). 본 트랙은 *문서만* 변경하므로 commit 자율·push 보류는 운영자 지시.
- **구현 순서**(시뮬 07 통합로드맵): 01 지수 → 02 레일 → 03 백테스팅. 04 는 차트 크롬 개선이라 어디든 선행 가능.
