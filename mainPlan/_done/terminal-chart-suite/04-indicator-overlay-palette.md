# 04. Indicator Overlay + Palette — 경제·보조지표 오버레이 + 팔레트 조직 (발견성·마퀴 배선·조직)

> **참조 규약(분리 후):** 본 문서는 `mainPlan/terminal-chart-suite/`(현재/과거 차트 suite)에 속한다. suite 내부 = 01(차트)/02(레일)/03(백테스팅)/04(본 문서). **시뮬 PRD 참조(05 Play·07 통합로드맵 등 바 번호)는 `../scenario-simulator/NN`을 가리킨다**(단방향: suite ⟶ 시뮬, 역참조 없음).

상태: PRD v0.1 (2026-06-14, 4-ground 코드 실측 + 4렌즈 토론 + 적대검증 5). **2026-06-14 현재기준 재검증** — J~Q claim 전부 TRUE 확인. 미세 정정 2건: `MacroSeriesDef.yoy`·`digits` 는 *optional*(`yoy?`/`digits?`, `macro.ts:8-16`), 마퀴 파생은 *5~6 push*(KR·US 국면·순풍·역풍·시장폭·평균1M, 데이터 부재 시 가변). 본 F1 은 econ 오버레이(`rt.macro.getSeries`)를 소비 — public=`createHfMacroPort`/local 동일 공유라 **로컬/퍼블릭 공동배선 추가 작업 0**(HF 거시 데이터 회사 무관).
범위: 메인 주가차트에 경제지표/보조지표를 오버레이하는 *발견성·배선·조직* 개선. 상단 KPI 마퀴 클릭 → 차트 오버레이.

---

## 1. 한 줄 결정

**이건 신규 기능이 아니다 — 코어(econ 오버레이 엔진·전수 팔레트·`toggleEcon`·`SUB_GROUPS` 조직)는 전부 이미 라이브다.** 운영자 체감 "보조지표 저것만 보이노"의 진짜 원인은 *카탈로그 누락이 아니라* (a) 기본 활성 3종만 차트에 그려짐 + (b) 일반 메뉴가 22종을 평면 나열(조직감 0) + (c) ECON 버튼이 IND 뒤에 옴. 따라서 F1 = **신규 컴포넌트 0, 작업 3건**(조직 이식·순서 swap·마퀴 배선).

> **★전제 정정(운영자에 보고):** "보조지표 소수만 보임"은 부정확하다. `ChartMenus.svelte:42-67`이 이미 `OVERLAY_ALL`(8)+`SUB_ALL`(22)를, `:70-83`이 `MACRO_SERIES`(10)를 *전량 버튼으로 노출*한다. 갭은 카탈로그가 아니라 발견성·조직·디폴트값이다.

---

## 2. 왜 신규 기능이 아닌가 — 이미 구현된 자산 전수 지도 (실측)

| 자산 | 위치 | 상태 |
|---|---|---|
| **econ 오버레이 엔진** | `charts/econOverlay.ts` | ★라이브 — klinecharts `'ECON'` indicator, `figures:[]`로 캔들 y축 무왜곡 + 가시범위 자기정규화 폴리라인 + `ECON_COLORS` 10종 + 원시값 툴팁 |
| econ 차트 배선 | `charts/PriceChart.svelte:705-726` | ★라이브 — `ctl.econ` effect → 로드 → 생성/override |
| 경제지표 카탈로그 SSOT | `ui/packages/contracts/src/macro.ts` `MACRO_SERIES`(10종) | ★라이브 — `MacroSeriesDef{id,src,kr,en,unit,yoy?,digits?}`(yoy·digits optional) + `MACRO_ATTRIBUTION`(`macro.ts:41`, ECOS·FRED) |
| 데이터 로더 | `runtime/.../sources/macroSource.ts` | ★라이브 — observations.parquet HF 직독 |
| **전수 팔레트(일반)** | `charts/ChartMenus.svelte:42-83` | ★라이브 — `OVERLAY_ALL`+`SUB_ALL`+`MACRO_SERIES` 전량 버튼 |
| **전수 팔레트+조직(전체화면)** | `charts/ChartRibbon.svelte:119-198` | ★라이브 — `SUB_GROUPS` 3분류 칩 + `MACRO_SERIES` econ 팝오버 |
| 상태 SSOT | `charts/chartState.svelte.ts` | ★라이브 — `OVERLAY_ALL`(8)·`SUB_ALL`(22)·`SUB_GROUPS`(추세4/모멘텀11/거래량7)·`ECON_MAX=3`·`toggleEcon/toggleOverlay/toggleSub` |
| 커스텀 지표 등록 | `charts/extraIndicators.ts` | ★라이브 — ICHI·ENV·TVAL (klinecharts 미내장 등록 패턴) |

**결론**: 오버레이·카탈로그·팔레트·상태가 전부 있다. 신설은 *마퀴 배선 1건 + 조직 이식 + 순서 swap*뿐.

---

## 3. 작업 1 — ChartMenus IND 메뉴에 `SUB_GROUPS` 조직 이식 (버튼 벽 해소, OQ1)

`ChartRibbon.svelte:188-197`이 이미 `SUB_GROUPS`(추세/모멘텀/거래량, `chartState:18-22`)를 그룹 헤더로 조직해 렌더하는 **살아있는 선례**다. 이 동일 패턴을 `ChartMenus.svelte:54-60`의 평면 `SUB_ALL` 나열에 이식한다(데이터·조직 코드 동일, 신설 0).

- **버튼 벽 처방**: `SUB_GROUPS` 3그룹 헤더 + **활성 칩 그룹 상단 고정**(ON 지표를 위에 모음).
- **검색창·최근사용·고정(pin)은 KILL**: 22+8+10=40개 *닫힌* 카탈로그(klinecharts 내장 거의 소진, 무한 스크롤 아님)에 과설계 = 덕지덕지. `localStorage` 상태 증식만 부르고 발견성 악화.

---

## 4. 작업 2 — 우선순위 재배치: 경제지표 먼저 (OQ3 = UI 발견성 순서)

"경제지표 먼저, 보조지표 뒤"는 **순수 발견성 위계**다(구현/렌더 순서 아님). `econOverlay`는 `candle_pane` 내부 indicator, 보조지표는 별도 pane(`PriceChart.svelte:495` `pane_${k}`) → 그리기 충돌 0·z-order 무관. 따라서 `ChartMenus` 우상 도구 버튼 순서를 **ECON→IND로 교체**(현재 `:42` IND → `:71` ECON 역순). 1줄급 DOM 순서 swap. 구현/렌더 순서 해석은 과잉(불요).

---

## 5. 작업 3 — 마퀴 클릭 → 오버레이 배선 + 정직 분기 (유일한 진짜 신설)

`CenterStack.svelte:288-291`의 `.kpiItem`은 순수 `<span>`, onclick 0. `macroKpis`(`TerminalSurface.svelte:121-141`)는 두 종류 혼합:
- **`MACRO_SERIES` 10종**(시계열 보유 = 오버레이 가능)
- **파생 5종**(KR/US 국면·순풍/역풍·시장폭·평균1M, 시계열 부재 = 오버레이 **수학적 불가**)

**선결 2건**: (i) `macroKpis` 항목 shape `{l,v,t,s}`에 series `id` 필드(`def.id`) 추가 — 현 항목엔 id 부재. (ii) 안정키 — `:290`의 `(i)` index 키 + 중복 concat → label/id 안정키로 교체.

**배선**: id 보유 항목만 `<button>`+`onclick=ctl.toggleEcon(id)`, **파생 5종은 비클릭**(커서 차단·디밍). "마퀴 도는 것 전부 버튼"은 이 5종에 거짓이므로 **정직 분기 필수**(허위 오버레이 금지). `ECON_MAX=3`(`chartState:68`) 4번째 토글의 침묵 무시(`:189 toggleEcon`)는 정직 척추 위반 → **명시 피드백**(토스트 "동시 3개까지"·비활성 표시)으로 교체.

---

## 6. OQ2 축 문제 — 이미 최강 해법, 추가 설계 0

`econOverlay.ts`가 정답 구현이다: `figures:[]`로 캔들 y축 range 0 기여(`calcRange`는 `figures[].key`만 참조 = 캔들 무왜곡) + `draw`에서 **가시범위 시리즈별 min-max 자기정규화 폴리라인**(Bloomberg normalized, 팬/줌 re-fit) + 원시값 툴팁.

- **rebase(`v/v₀`·`close₀`) = KILL**: `T10Y2Y`·YoY 0교차 시리즈 수학 붕괴. `econOverlay.ts:5`에 *코드 주석으로 이미 기각*됨.
- **보조축·sub-pane 신설 = KILL**: 현 자기정규화 폴리라인이 이미 "보이지 않는 독립축". 보조축 신설 = 후퇴.

---

## 7. KILL 리스트

- 신규 지표 팔레트 컴포넌트 신설(중복 팔레트 = 덕지덕지, `feedback_check_internal_assets_first` 위반).
- 팔레트 검색창·최근사용·고정(pin)(40개 닫힌 카탈로그에 과설계).
- 신규 보조지표 무더기 추가(klinecharts 내장 소진 — 미노출 문제 아닌 발견성 문제). 22종 평면 나열도 금지(`SUB_GROUPS` 적용).
- 경제지표 rebase 정규화 / 보조축·sub-pane 오버레이 신설(`econOverlay` 자기정규화가 정답).
- 마퀴 파생 5종 차트 오버레이 클릭 활성(시계열 부재 = 수학적 불가, 허위 오버레이).
- `ECON_MAX=3` 4번째 토글 침묵 무시(명시 피드백으로 교체).
- econ 오버레이 미래 외삽/연장(`../scenario-simulator/05` Play 소유, "현재/과거" 경계 밖).
- 인과/신호 UI 카피(§8).

---

## 8. OQ7 정직 척추 — 상관 ≠ 인과

- 마퀴/오버레이 어디에도 "금리 오르면 주가 하락" 류 **인과 문구**·"매수 타이밍" **신호 문구** 금지. 톤 = "동시 추이 비교"·"상관 참고"만.
- `econOverlay`는 forward-fill로 look-ahead 차단·미래 외삽 0(미래 econ 연장은 `../scenario-simulator/05` 소유).
- `MACRO_ATTRIBUTION`(ECOS·FRED) 출처는 contracts 상수 — 오버레이 활성 시 **노출 강제**.

---

## 9. 영향 파일·함수 (재조사 없이 구현 가능)

| 파일 | 변경 |
|---|---|
| `charts/ChartMenus.svelte:42-67` | IND 메뉴에 `SUB_GROUPS` 조직 이식(ChartRibbon:188-197 패턴) + 활성 칩 상단 고정 |
| `charts/ChartMenus.svelte:42/71` | ECON→IND 버튼 순서 swap(발견성 우선) |
| `panels/CenterStack.svelte:288-291` | `.kpiItem` `<span>`→`<button>`(id 보유 항목)+`onclick=toggleEcon(id)`, 파생 5종 비클릭·디밍, 안정키 |
| `TerminalSurface.svelte:121-141` | `macroKpis` 항목에 `def.id` 필드 추가(클릭 대상 식별) |
| `charts/chartState.svelte.ts:189` | `toggleEcon` `ECON_MAX` 초과 시 명시 피드백 반환(침묵 무시 제거) |

**재사용(신설 최소 증거)**: econOverlay·MACRO_SERIES·macroSource·ChartCtl·ChartMenus/ChartRibbon·extraIndicators 전부 라이브. 신설 = 마퀴 배선 1건 + `macroKpis` id 필드 + `SUB_GROUPS` 이식 + 버튼 순서 swap + `ECON_MAX` 피드백.

---

## 10. 착수 게이트

`terminal-chart-suite`는 mainPlan(터미널 ui/packages 정착) 완료 + 운영자 go 후 착수. 단 F1은 차트 크롬 개선(기존 자산 배선)이라 **선행 가능**. `feedback_ui_rules` 준수(푸시 전 스크린샷 전수 눈검수·공개 터미널 무중단·완결 단위만).
