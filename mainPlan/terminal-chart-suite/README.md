# Terminal Chart Suite — 차트 중심 터미널 PRD Index

상태: v0.1 (2026-06-14 scenario-simulator 에서 분리 신설 — 차트의 *현재/과거* 3 컴포넌트를 독립 트랙으로)
범위: 메인 주가 차트 위에서 동작하는 **현재/과거** 터미널 기능 — 주가/지수 차트·공시 위치 타임라인·EOD 백테스팅. 미래 방향(Play 시뮬레이션)은 `../scenario-simulator/`가 소유한다.

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

## 문서 지도

1. [01-price-index-chart.md](01-price-index-chart.md) — 주가/지수 차트(center subject-swap, IndexPort catalog/search/series, KR gov OHLCV 캔들 + US FRED 종가 라인 평행 subject, candleStyle='area' degenerate, 종가전용 지표 3분기, subject 소유권 seam).
2. [02-disclosure-event-rail.md](02-disclosure-event-rail.md) — 공시 위치 찾기 레일(x축 아래 과거 공시 위치, `rceptNo` 중심 `DisclosureEvent` 정규화, 호버 메타·클릭→우측 행 스크롤. 미래 마커는 시뮬로 이관).
3. [03-backtesting-strategy-tester.md](03-backtesting-strategy-tester.md) — 차트 중심 EOD 백테스팅 Strategy Tester(look-ahead 차단·t종가→t+1시가 체결·비용 기본 ON·RunSpec/ledger/provenance·DSR/PBO 과최적화 가드. 리포트 도크 스크롤).

> **참조 규약**: suite 내부 = 01/02/03. **시뮬 PRD 바 번호(05 Play·07 통합로드맵·08 valuation·09 정합화 등) = `../scenario-simulator/NN`.** 통합 시퀀싱은 시뮬 07(브리지 문서)이 소유.

---

## 경계 (불가침)

- **시뮬레이터(미래 Play·드라이버 DAG·valuation·신용·정합화)** = `../scenario-simulator/`. 본 suite는 미래를 그리지 않는다.
- **`terminal-improvement`**(블룸버그식 수평 직조·워치리스트·커맨드바) = 별개. 그 PRD가 ceding 하던 "지수/이벤트레일"은 이제 본 suite 소유(terminal-improvement 경계 노트 정정 동반).
- **UI 토폴로지**: 본문의 `landing/src/lib/terminal/<rest>` 경로는 stale — 새 SSOT = `ui/packages/surfaces/src/terminal/<rest>`(터미널 전체 이동 ff9099ba0). 각 문서 헤더의 기계적 매핑 규약대로 읽는다.

---

## 착수 게이트

mainPlan(터미널 ui/packages 정착) 완료 + 운영자 go 후 착수. 단 **01 주가/지수 차트는 mainPlan 무관 선행 가능**(IndexPort 충돌 1회 확인). 셋은 시뮬 미완과 무관하게 독립 진행 가능 — 그것이 분리의 핵심 이득.
