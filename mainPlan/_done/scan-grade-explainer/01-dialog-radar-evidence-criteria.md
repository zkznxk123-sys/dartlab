# 01. 설명 다이얼로그 (OQ5) — 레이더 + 근거 + 기준 3분할

상태: PRD v0.1 (2026-06-14, 코드 실측 + 적대검증 #4 survives=true)
범위: 스캔등급 헤더 클릭 → 다이얼로그. 좌 = 스파이더(레이더), 우 = "왜 이 등급"(근거), 아래 = 등급 기준(주석).

---

## 1. 한 줄 결정

데이터·컴포넌트·셸이 **90% 이미 라이브** — 신설은 *다이얼로그 셸 1개 + 큐레이션/정렬 맵 2개 + 어댑터 1개*뿐. 좌측 레이더는 **터미널 orphan `Radar.svelte` 부활 금지**, *살아있는* map `RadarChart.svelte`를 재사용한다.

---

## 2. 재사용 자산 (실측) — 데이터·컴포넌트·셸 3종 라이브

| 자산 | 위치 | 용도 |
|---|---|---|
| 레이더 데이터 | `engine.ts:524-531` `co.radar` | 6축 `{kr,en,s(0~1)}`(수익성·성장성·안정성·이익질·유동성·거버넌스). live 빌드되나 **어떤 패널도 미소비**(orphan 데이터) |
| 근거 데이터 | `engine.ts:268-300` `co.verdict` | `{composite, band(5밴드), strengths[], concerns[], riskRed/Yellow}` — *이미 합성됨* |
| 축별 셀 | `engine.ts:505-507` `verdict.cells` | 6셀(prof/growth/stab/cf/val) 원수치 텍스트(부채비율%·영업CF조·PER x) |
| 등급 기준 | `engine.ts:44-53` `GRADE_SCALE` + `:100-101` `gradeTone` 임계 | 축별 letter 스케일 + 색 임계 |
| **레이더 컴포넌트** | `ui/.../map/components/RadarChart.svelte` | ★살아있는 SVG 레이더(map CompanyCard·ChartRenderer 3곳 소비 중). prop = `axes:{label, value(0~100), benchmark?}`, `N` 동적 |
| 다이얼로그 셸 패턴 | `ScreenerModal.svelte:146-151` | `scrimWrap→role=dialog→aria-modal→stopPropagation→✕+Escape` |
| 큐레이션 선례 | `cardGuide.ts` `CARD_GUIDE{what/good/bad}` | 사람 작성 환각0 주석 패턴 |

> **★`terminal/charts/Radar.svelte`(orphan) 부활 금지**: `grep <Radar` 0건 死자산(mainPlan/08 삭제후보). 살아있는 map `RadarChart.svelte` 재사용이 정공법(`feedback_check_internal_assets_first`).

---

## 3. 좌측 — 스파이더(레이더)

- **어댑터(소형)**: `co.radar.map(r => ({ label: r.kr, value: (r.s ?? 0) * 100 }))` — 0~1→0~100 스케일 + kr 라벨. map `RadarChart`에 그대로 주입.
- **benchmark(선택)**: `co.radar`에 업종중앙값이 있으면 `benchmark`로(Snowflake 영역), 없으면 생략(map `RadarChart`는 benchmark null이면 영역 미렌더).
- **★축 정합 함정 — 정직 라벨 필수**: 3개 축 집합이 *불일치*한다 — radar=**6축**(audit 누락)·grades=**7축**(+감사위험)·verdict.cells=**또 다른 6축**(prof/growth/stab/cf/val). 결정: 스파이더는 `co.radar` 6축 그대로 **"6축"으로 정직 라벨**(audit는 3단이라 0~1 정규화 시 해상도 거짓 → 스파이더 제외, 우측 근거 칩에서 audit 등급 별도 표시). **"등급 구성 팩터 전부"라 주장 금지**(audit 빠짐).

---

## 4. 우측 — "왜 이 등급" 근거

- `co.verdict.strengths` / `concerns`(이미 합성, `engine.ts:287-298`) + `co.verdict.cells` 축별 텍스트(**원수치 표기** 부채비율%·영업CF조·PER x — 환각 0) + `riskRed/Yellow` 플래그 재사용.
- **★키 정렬 맵 신설**: verdict 축(prof/growth/stab/cf/val 5)·grades 축(prof/growth/gov/qual/liq/audit/stab 7)·radar 축(6)이 1:1 아님 → 다이얼로그가 "축별 근거"를 grades 기준으로 정렬하려면 **키 정렬 맵**이 필요(섞어 표시 = 사용자 오독, KILL). 신설 작음(상수 맵).
- **등급 수 노출**: 종합 = 5밴드 + 연속 `composite` 0~100 숫자(00 §4). 신용 dCR-14 합류 표시.

---

## 5. 아래 — 등급 기준 (주석)

- `GRADE_SCALE` 라벨 + `gradeTone` 임계(예: `f≤0.18 up`, `engine.ts:100-101`) + **결정론 원수치 노출**(roe/debtRatio가 *어느 단계*인지).
- **큐레이션 텍스트 = `GRADE_GUIDE` 맵 신설**(사람 작성). `cardGuide.ts` `CARD_GUIDE{what/good/bad}`가 정확한 선례(환각 0)지만 grade-key별 맵은 미존재 → 신설. **자동생성 금지**(`feedback_no_docstring_auto_sweep` 가드 정합 — providers docstring auto-sweep과 동류).

---

## 6. 셸 · 진입점

- **셸**: `ScreenerModal.svelte:146-151` scrim 패턴 재사용(scrimWrap→role=dialog→aria-modal→stopPropagation→✕+`svelte:window` Escape). 신규 패턴 0.
- **진입점**: `CenterStack.svelte:340` "스캔 등급" Panel은 header onclick 부재. `Panel.svelte`(`terminal/ui/Panel.svelte`) 실측: `panelHead`에 `title`(정적 span)·`right`(Snippet)·`sub`만 — 헤더 클릭 슬롯 없음. **결정**: `right()` 스니펫에 **"⊕ 기준" 버튼**(VERDICT 패널 right snippet 선례 `:394`) → Panel **무수정**, 신설 작음. (대안 `Panel`에 `onTitleClick?` 옵션 prop 추가는 다른 패널 영향 0이나 후자가 더 작음.)

---

## 7. OQ7 정직 척추

- **매수/매도 신호·목표주가·"좋은 주식"·인과(선행지표가 주가 예측) 금지**(`00 kill-list` 정합). 등급 = fact 아닌 **판정** → 근거+기준 동반은 요구와 정합(이미 정직).
- **결손 축 `.filter(v존재)` 유지**: 다이얼로그/스파이더에서 0점 채우면 "취약" 오독 → 결손은 축 자체를 빼고 그린다(0대체 금지).

---

## 8. 영향 파일·함수 · 재사용 원장 (재조사 없이 구현 가능)

| 신설/변경 | 위치 | 내용 |
|---|---|---|
| 신설 | `terminal/panels/GradeExplainDialog.svelte`(신규) | scrim 셸(ScreenerModal 패턴) + 좌 RadarChart + 우 verdict 근거 + 아래 기준 |
| 신설 | grade-key 정렬 맵 + `GRADE_GUIDE` 큐레이션 맵(상수, 사람 작성) | 축 정합·기준 주석 |
| 변경 | `panels/CenterStack.svelte:339-351` | 스캔등급 Panel `right()` 스니펫에 "⊕ 기준" 버튼 → 다이얼로그 open |
| 재사용 | `map/components/RadarChart.svelte` | 좌측 스파이더(어댑터 0~1→0~100) |
| 재사용 | `co.radar`·`co.verdict`·`GRADE_SCALE`·`gradeTone` | 데이터 전량 라이브(신설 0) |

**신설 총량**: 다이얼로그 셸 1 + 큐레이션 맵 + 키 정렬 맵 + Panel right 버튼 + 0~1→0~100 어댑터. **scan 엔진·등급 산식 불변**.

---

## 9. 착수 게이트

운영자 go 후. 다이얼로그는 기존 자산 조합이라 경량·선행 가능. `feedback_ui_rules`(스크린샷 눈검수·무중단·완결 단위) 준수.
