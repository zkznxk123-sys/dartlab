# Cross-Universe Percentile — 유니버스 교차 백분위 다이얼로그 PRD Index

상태: v0.1 (2026-06-14, 4-ground 코드 실측 + 4렌즈 토론 + 적대검증)
범위: 터미널 우측 **"업종 내 백분위" 패널 헤더 → "상세 보기" 버튼 → 다이얼로그**. 한 회사의 분야별 백분위를 **여러 유니버스(업종 / 소속시장 KOSPI·KOSDAQ / 전체상장사 / 소속지수)에서 한 좌표로** 본다. scan 엔진의 프리빌드 계정/지표가 원천.

---

## 한 줄 결정

이 다이얼로그는 **"강점의 상대성"** — 같은 분야 점수가 *보는 잣대(유니버스)에 따라 어떻게 뒤집히는가* 를 한 화면에 노출한다. 업종 1등이 전체로 넓히면 중위로 내려앉거나, 거버넌스만 모든 잣대에서 일관 상위인 식의 **유니버스-민감도**는 기존 어느 화면도 못 준다. 신설 비용은 작다 — 백분위 산식 `pctRank`(engine.ts:88)와 분포곡선 `DistCurve.svelte`, 모달 셸이 **이미 라이브**이고, 브라우저 engine 이 받는 `EcoNode` 에 **전 종목 13축 raw 값 + market 필드가 이미 들어있다**(types.ts:111-152). 신설 = `industryPercentile` 을 `percentileIn(code, universe)` 로 일반화(모집단 필터만 분기) + 다이얼로그 1개.

> **★운영자 확정 (2026-06-14):** scan-grade-explainer 는 **종합평가 방식(큰그림·판정)** 으로 독립 개선한다. 본 화면은 그것과 *다르게* 간다 — **단순 업종내 백분위를 넘어선 유니버스 교차 분포**이되, **분포 사실만 / 판정 0**. 두 다이얼로그는 사이블링(percentileIn 공유), 중복 아님.

---

## 거처 판정 — 별도 트랙 (흡수 거부)

| 후보 | 판정 | 근거 |
|---|---|---|
| scan-grade-explainer 에 흡수 | **거부** | 운영자 명시: scan-grade = 종합평가(판정), 본 화면 = 분포 사실(판정 0). 진입 헤더도 다름(스캔등급 패널 = CenterStack vs 업종내 백분위 = RightStack). |
| 별도 mainPlan 카테고리 | **채택** | 진입점·개념·정직 레인(MAP vs JUDGE)이 분리. 단 **공유 SSOT 강제**로 중복 차단(아래 경계). |

본진 화면 이동 0 — 업종내 백분위 패널은 [RightStack.svelte:234-244](../../ui/packages/surfaces/src/terminal/panels/RightStack.svelte) 그대로. 다이얼로그 컴포넌트만 `terminal/panels/` 신설.

---

## 경계 (불가침)

- **종합평가·verdict·composite·"왜 이 등급"** = `scan-grade-explainer` (종합평가 레인). 본 화면은 **판정 금지 — 분포 사실(상위 N%)만**.
- **JUDGE(reverseDCF·정합성 forensic)** = `financial-statement-lab`. **N사 비교(compare)** = `financial-statement-lab` — 본 화면은 *1사*만, "유니버스 상위 N사와 비교" 는 `compare` verb 로 점프만.
- **회사→산업 점프** = `industry-analysis-lab`. **워치리스트** = `terminal-improvement`. **시뮬/미래·차트 오버레이** = `scenario-simulator`/`terminal-chart-suite`.
- **공유 SSOT 계약**: 백분위 산식은 단일 함수 `percentileIn` — scan-grade-explainer 와 *같은 pctRank* 를 쓰고 로직 복제 0. 새 백분위 *엔진/집계 파이프라인* 신설은 KILL(02).

---

## 문서 지도

1. [00-feasibility-and-universe-verdict.md](00-feasibility-and-universe-verdict.md) — 유니버스 4종 실현가능성 판정(업종 ✅이미라이브 / 시장 ✅라이브 / 전체 ✅라이브+cross-sector caveat / 지수 ❌BLOCKED), 코드 증거, 비용, 재사용 헬퍼.
2. [01-mechanism-decision.md](01-mechanism-decision.md) — 시각화 메커니즘 결정: 히트맵 reject → **축별 행 × 유니버스 열 백분위 띠 + 행클릭 DistCurve 드릴다운**. 정성 처리. ASCII 목업.
3. [02-honesty-kill-list.md](02-honesty-kill-list.md) — KILL 목록 + 필수 정직 가드(가격격리·범주형 가짜백분위·허위정밀·cross-sector·판정금지·n<10·분포출처).
4. [03-architecture-and-reuse.md](03-architecture-and-reuse.md) — 영향 파일/함수/테스트/롤백. `percentileIn` 일반화, 다이얼로그 컴포넌트, 셸/DistCurve 재사용, 공유 SSOT.
5. [04-scope-phasing-boundaries.md](04-scope-phasing-boundaries.md) — **완성 범위(한 빌드)** + 단일 정직 제외(소속지수, 데이터 게이트), 경계 연결 맵(재구현 0), 정직 성공지표, 인접 PRD 침범 KILL.
6. [05-progress-ledger.md](05-progress-ledger.md) — 상태·결정 로그·NEXT 포인터.

---

## 이중 평가

- **전문 개발자**: 위험은 낮다. 백분위는 `EcoNode` 클라이언트 배열 재필터(새 데이터 0), 분포곡선·셸·띠 마크업 전부 라이브. 유일 신설 = 일반화 함수(~30줄) + 다이얼로그 1개. **완성형이 한 빌드에 다 들어간다** — 시장/전체 분포곡선도 같은 모집단 배열에서 라이브 5분위로 뽑아 prebuild 불필요. 유일 제외 = 소속지수, 그러나 이건 단계가 아니라 **멤버십 데이터 부재로 물리적으로 막힌 것**(우회 위조 금지) — 데이터 확보 시 같은 격자에 열 자동 추가.
- **PM**: 킬러는 "유니버스를 바꾸니 순위가 뒤집힌다" 한 통찰. 성공지표는 셀 개수가 아니라 *뒤집힘 발견 빈도 + 연결 클릭률*. scan-grade 와 레인이 갈렸으므로(MAP vs JUDGE) 중복 우려 해소. 과욕(컨센서스·목표주가·멀티심볼보드)은 인접 PRD 소유 → KILL.

---

## 정직 척추

이 화면은 **판정이 아니라 좌표** — "상위 N%" 라는 분포 사실만 낸다. 매수/매도·목표주가·"좋은 주식"·종합 1위·composite 금지(그건 scan-grade 레인). 결손 축은 `.filter(존재)` 제거(0대체 금지). 분포 출처(KSIC섹터·동일가중·상장 primary ≠ KRX 시총가중)와 표본수 n 을 셀마다 노출. 전체상장사 유니버스는 섹터 혼재(금융·제조) caveat 강제. UI 경로 = `ui/packages/surfaces/src/terminal/`(landing 死경로). UI 변경이라 **자동 push 금지 — 운영자 눈검수 후 명시 승인**.

## 착수 게이트

운영자 go 후 착수. 다이얼로그는 기존 자산 조합이라 경량·선행 가능. **완성형 = 한 빌드** — 업종+시장+전체 백분위 + 전 유니버스 분포곡선(라이브) + 정성 칩비중 + 가격 격리. 소속지수만 데이터 게이트로 정직 제외.
