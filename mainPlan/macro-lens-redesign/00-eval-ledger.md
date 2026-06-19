# 00. 전문가 공조 · 적대 평가 원장

> 본 PRD는 매크로분석·UX/PM·데이터시각화 전문가 공조로 작성하고, 분석가·사용자 에이전트의 적대 채점이 **95점 이상**에 도달할 때까지 반복 개선했다(운영자 goal). 본 원장은 그 과정과 점수 이력, ground-truth 교정을 기록한다.

---

## 1. 과정

1. **현상 진단** — 현재 `MacroLensDialog.svelte`(1476줄·regime 탭에 13섹션)와 `macroLens.ts` view-model, 기존 `macro-lens-dialog/` 10문서를 정독. 진단: v0.1→v1.12 12번 개선하며 매 라운드 패널·개념을 *추가*해 정보 과부하 + 전문용어 벽이 됨 (anti-clutter 위반).
2. **전문가 공조 (3렌즈)** — 매크로/금융 분석가 · 터미널 UX/PM · 데이터 시각화 전문가가 각자 초안을 정독·비평하고 렌즈별 개선안을 도출.
3. **깨끗한 종합** — 3안의 최고 아이디어를 통합하되, "클러터를 깎자"는 PRD가 라운드별 자기 수정 해명으로 비대해진 자기모순을 제거해 *한 번에 쓴 것처럼* 깨끗하게 재작성.
4. **적대 평가 → 95점까지 반복** — 냉정한 분석가(정직성·데이터 정합·소스 줄번호/값 정확) + 실사용 파워유저(7초 가독성·시각 직관·압도 거부·문서 청결)가 6축 100점 만점으로 엄격 채점. 95점 미만이면 차단 항목을 ground-truth로 정밀 교정 후 재평가.

채점 6축: 시각직관 /25 · 정직 /20 · anti-clutter /15(설계가 깎았나 + 문서 자체 청결) · 구현준비 /20 · 데이터정합 /10 · 사용자가치 /10.

---

## 2. 점수 이력

| 단계 | 분석가 | 사용자 | min | 핵심 차단 → 교정 |
|---|---|---|---|---|
| 초기 평가 라운드 1~4 (종합본) | 88~93 | 88~96 | 88 | 라운드별 메타 해명으로 문서 비대(자기모순) · 소스 사실 오류 누적 |
| **깨끗한 재작성 후 R1** | 92 | 95 | 92 | EDGE_TEMPLATES lag 유령 데이터(4행 null) · tie-break↔ASCII 모순 · quantCandidate 미검증 |
| **R2 (lag·tie-break·실측 교정)** | 88 | 88 | 88 | finance.json "blocked 0" 오기(실제 2645) · "미배선→fallback" 서사가 소스와 반대 |
| **R3 (finance.json 분포·drop 결정성 교정)** | 93 | 93 | 93 | 닷그리드 스프레드시트 잔상 · 전파 게이트 디폴트 부정확 · buildEdges 필터 출처 오기 · 경로 prefix |
| **R4 (채널 클러스터·계산값 게이트·필터명 교정)** | **96** | **96** | **96 ✅** | blocking 0 (통과) |

> 정체 구간(88~93)의 진짜 원인은 "설계 약함"이 아니라 **에이전트가 EDGE_TEMPLATES·finance.json 같은 소스 디테일을 기억으로 쓰다 틀린 사실 오류**였다. 정공법은 또 한 번의 에이전트 라운드(환각 반복)가 아니라 **운영자가 소스 ground-truth를 직접 검증해 정밀 교정**하는 것이었다.

---

## 3. ground-truth 교정 기록 (소스 직접 검증)

각 교정은 추측이 아니라 소스 코드·데이터 실측에 근거한다.

| 항목 | 잘못된 서술 | 소스 ground-truth | 검증 위치 |
|---|---|---|---|
| EDGE_TEMPLATES lag | PPI_SEMI·BAMLH0A0HYM2·DGS10·CPI = null (4행) | 전부 non-null: [0,3]·[0,3]·[0,6]·[1,6] | `macroLens.ts` EDGE_TEMPLATES 594-749 |
| 초점 tie-break | "lag 짧은 순"(ASCII 초점 EXPORT와 모순) | 채널 우선순위(매출>마진>밸류>차입>현금) → OBS 3후보(전부 medium) 중 EXPORT→매출 결정·ASCII 일치 | 설계 결정(change·lag 배제·결정성) |
| 정량 status 분포 | "미배선 → default fallback → blocked 0" | exposureQuality 전 종목(2802사) 배선 · blocked 2645(94.4%·회귀 부재)·qualitativeOnly 157·quantCandidate 0 · fallback=dead branch | `finance.json` 전수 파싱 · `buildExposureQuality` 2336-2355 |
| Map sparsity 렌더 | row=driver×col=channel 격자(24칸 중 6칸=스프레드시트 잔상) | 채널 열 클러스터 렌더(채워진 채널만 열·driver 칩 세로 stack·빈 셀 0) | 시각 설계(데이터 행=driver 유지·렌더만 변경) |
| 전파 게이트 | "고정 디폴트 WATCH/LOCK·OPEN 금지" | macro.json transmission payload 존재 → edgeSourceRef=transmission(template 아님) → 관측 edge 보유 종목 path=ok(OPEN). 게이트는 *계산값* | `buildEvidenceGates` 2383-2415 · `edgeSourceRef` 2625 · `macro.json#transmission` |
| buildEdges 필터 출처 | "SECTOR_DRIVER 매칭" | `e.sectors.includes('all') || e.sectors.includes(co.industry)` (SECTOR_DRIVER는 buildDrivers 전용) | `macroLens.ts` 2173 / SECTOR_DRIVER 573·1998 |
| cap 8→6 | "no-op" | dialog helper `slice(0,8)` + template `slice(0,6)` → 생산단 6 통일 = 실변경(시각·테스트 영향) | `macroLens.ts` 142 · dialog 527/565 |

---

## 4. 최종 판정

- 분석가 96 (시각24·정직20·anti14·구현19·데이터10·가치9) — "데이터정합 10/10, 모든 줄번호·값 실측 일치. 정직 20/20."
- 사용자 96 (시각24·정직20·anti14·구현20·데이터10·가치8) — "남은 사실오류 0건. 95+ 가치 있는 탁월한 PRD."
- 두 평가자 blocking 0건. **min 96 ≥ 95 통과.**
