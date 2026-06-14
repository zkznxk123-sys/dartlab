# Scan Grade Explainer — 스캔등급 설명 다이얼로그 PRD Index

상태: v0.1 (2026-06-14, 4-ground 코드 실측 + 4렌즈 토론 + 적대검증 5)
범위: 터미널 per-company **스캔 등급 패널**의 설명 다이얼로그 — 헤더 클릭 → 좌 스파이더(레이더) / 우 "왜 이 등급"(근거) / 아래 등급 기준(주석). + 등급 수 정직 판정.

---

## 한 줄 결정

스캔등급 설명 다이얼로그(레이더+근거+기준)는 **dartlab 정직/provenance 사상 그 자체** — 강력 진행. 단 데이터·컴포넌트·셸이 **90% 이미 라이브**(`co.radar`·`co.verdict`·`GRADE_SCALE`·map `RadarChart.svelte`·`ScreenerModal` scrim)라 신설은 *다이얼로그 셸 1개 + 큐레이션/정렬 맵*뿐이다. 그리고 운영자가 말한 **"스캔등급 12단계 확장"은 reject(허위정밀)** — 그런 단일 12단 등급은 코드에 부재하고, composite는 진짜 해상도가 5~7밴드이며 가격 오염을 포함한다(상세 = 00).

> **★전제 정정 2건(운영자에 보고):**
> 1. **"12단계 스캔등급으로 확장"** — 현재 그런 단일 12단 등급이 *부재*하다. 실재 = ① 7축 각자 categorical 5~6단(`engine.ts:44-53 GRADE_SCALE`) ② 종합 verdict **5밴드**(STRONG/SOLID/NEUTRAL/CAUTION/WEAK, `:268-300`) ③ *별개* 신용 dCR **14밴드**. 12밴드 신설은 허위정밀 → reject. 대안 = 5밴드 유지 + 연속 composite 0~100 숫자 노출 + dCR-14 합류(00).
> 2. **거처** — 스캔등급은 "메인 주가차트 위"가 아니라 *scan 엔진 산물*이라 `terminal-chart-suite` 범위와 불일치, fin-stmt-lab도 합성 등급을 KILL → **독립 최소 트랙**으로 둔다(아래 거처 판정).

---

## 거처 판정 — 3중 확증 (OQ6)

어느 기존 PRD도 F2를 소유하지 않는다 → 신규 최소 트랙.

1. **`terminal-chart-suite` 아님**: `grep profGrade|govGrade|grades`를 `terminal/charts/`에 돌리면 **0건** — 등급 로직은 차트가 아니라 scan 엔진 산물. suite README §범위 = "메인 주가차트 위 현재/과거"(01 주가지수·02 공시레일·03 백테스팅), 등급/레이더/verdict 트랙 0건.
2. **`fin-statement-lab` 아님**: 그 PRD `02-differentiation`이 "종합 1위·A등급(합성 판정)"을 *명시 KILL*(분포 사실만 허용) → F2를 거기 넣으면 그 PRD 가드 위반.
3. **본진 화면은 이동 0**: 스캔등급 패널은 `CenterStack.svelte:339-351`(per-company 터미널 뷰)에 그대로. 다이얼로그 컴포넌트만 `terminal/panels/`에 신설.

---

## 경계 (불가침)

- **JUDGE(reverseDCF·compare·동종 백분위)** = `fin-statement-lab` (합성 등급 KILL).
- **시뮬/Play(미래)** = `scenario-simulator`. **차트 오버레이/지표** = `terminal-chart-suite/04`.
- **수직 분석 깊이** = 손대지 않음(`terminal-improvement`는 *연결만*).
- **본 트랙** = 스캔등급 *설명 UI*만(등급 산식 신설 0, scan 엔진 불변).

---

## 문서 지도

1. [00-grade-count-honesty.md](00-grade-count-honesty.md) — 등급 수 정직 판정(OQ4): "12밴드" 허위정밀 reject, 실측 3층 구조, 정직 권고(5밴드+연속 숫자+dCR-14 합류).
2. [01-dialog-radar-evidence-criteria.md](01-dialog-radar-evidence-criteria.md) — 설명 다이얼로그(OQ5): 좌 스파이더(`co.radar` 6축·map RadarChart 재사용)/우 근거(`co.verdict` 원수치)/아래 기준(`GRADE_SCALE`+`GRADE_GUIDE`)·셸·진입점.

---

## 정직 척추

등급 = fact 아닌 **판정** → 근거+기준 동반은 운영자 요구와 정합(이미 정직). 다이얼로그 어디에도 **매수/매도 신호·목표주가·"좋은 주식"·인과(선행지표가 주가 예측)** 금지(`00 kill-list` 정합). 결손 축 `.filter(v존재)` 제거 유지(0대체 금지 — 0점 채우면 "취약" 오독). UI 경로 = `ui/packages/surfaces/src/terminal/`(landing 死경로).

## 착수 게이트

운영자 go 후 착수. 다이얼로그는 기존 자산 조합이라 경량·선행 가능.
