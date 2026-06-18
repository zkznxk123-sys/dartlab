# 05 — 범위·단계·가드레일

## 1. Phase 계획 (브라우저 우선 → Python/CI)

### Phase 0 — 스파인 배선 (P0, 단독 ship, 브라우저 only)
- `rcept_no`+`stlm_dt` 를 6 SELECT(`companyLive.ts` L281-322) + `LiveCompanyReportFact` contract 추가.
- 도시에 헤더 리본: "사업보고서 {stlm_dt} · 접수 {rceptDate} · N/6 공시 · 약 N개월 전 · ↗원문" (↗ = `viewerUrl(marketForCode(code), rceptNo)`+`openFiling`).
- 평면 `DART 정기보고서 팩트` 패널 → 리본 흡수(−1 패널).
- **게이트**: svelte-check 0; 삭제 전 모든 reportFacts 키 재표현 확인(헤더 회귀 가드); 공개+로컬 동일 렌더. 엔진/Python 0.

### Phase 1 — killer 리프레임 (P0/P1, 전부 메모리 배열에서 새 fetch 0)
- 환원 흐름 문장 + RETURN 탭 막대 + 빈상태 first-class.
- 타법인출자 lossPct(항상) + `controlShiftSummary` helper.
- 인력 자기이력 문장 + 누락 `상세보기` 추가.
- CARD_GUIDE 글로서리 리프레임(올라가면/내려가면).
- **게이트**: NEVER-CLAIM grep green; **3/6 커버리지 소형주 + 무배당 소형주 + 첫배당 케이스 전부 데모**(삼성 아님) 후에야 push 요청.

### Phase 2 — 엔진 배선 축 (Python/CI + 브라우저)
- 인적자본 분위 배열{N,asOfYear,gate} bake → 단일시점 백분위 1행(`scanValueAdded`/`computeSalaryVsRevenue` 배선).
- rndIntensity HF parquet bake (`calcRndExpense` 는 **완성 엔진 — 재graduate 금지**; 진짜 일=CI consolidation bake + reportSource 5번째 read + `report.rndIntensity(code)` 포트, 로컬 fallback).
- **게이트**: baked 배열이 실제 교집합 N(글로벌 N 아님); 공통배선 공개+로컬 동일; **bake 지연 시 R&D 없이 Phase 1 ship**.

### Phase 3 — narrative honest-gap (P3, 선택)
- 가동률 원문 발췌 블록 — **zero 추출일 때만**(뷰어가 이미 섹션 텍스트 렌더 → anchor+label). 새 파싱 필요 = 컷.

> **UI push 는 모든 Phase 에서 운영자 게이트**(CLAUDE.md ⛔ public/local 프론트). commit 자율, push 는 명시 승인.

## 2. 경계 (다른 PRD 소유권 — 소비만, 재소유 금지)

| 경계 PRD | 소유 | 이 PRD 의 선 |
|---|---|---|
| **financial-statement-lab** | 재무 5종(peer 백분위·reverseDCF·이익품질·tie-out·TTM) | 백분위 머신 *재사용*은 정당. peer-relative 백분위·payout-vs-CFO 지속가능성 비율은 fin-stmt-lab(인적자본 유니버스-rank 축 1개만 예외). 급여매출괴리는 accruals 프레임 금지 |
| **terminal-improvement** | 워치리스트 + since-last-visit 델타 + freshness 티어 | control-shift·배당 streak 은 *filing-period* 자기이력(YYYY→YYYY). "마지막 본 이후 변화" 알림 금지(=watchlist) |
| **industry-analysis-lab** | 섹터 profit-pool · 공급망 엣지 · HHI · `recipes.industry.rdIntensityTrend` | R&D 는 회사 자기 숫자+자기 추세만. 섹터 밴드 *소비*(재계산 fork 금지). 출자를 섹터/HHI 로 집계 금지 |
| **scenario-simulator** | 미래 replay · what-if · forward 가정 | 전부 backward(실현 흐름·과거 기간). dilution-net 은 과거 이벤트 reconciliation, projection 금지. 백분위=단일시점(궤적 금지) |
| **table-export** | egress · 다운로드 · xlsx | ↗ = DART 공시 새 탭(navigation, egress 아님). "도시에 xlsx 다운로드" 버튼 금지 |
| **cross-universe-percentile (_done)** | 유니버스 교차 백분위 머신·다이얼로그 | 인적자본 축 1개 추가(패턴 정본), 단일시점 lock 준수 |

## 3. 가드레일 (CLAUDE.md ⛔ 정합)

- **데이터 SSOT**: HF=공개 truth, 공통배선(공개+로컬 동일), 로컬전용 금지. 전부 HF-parquet read.
- **안티클러터**: 순 패널 DOWN. 새 패널·새 다이얼로그·레이더·종합점수 = red flag. 강함=빼기.
- **전상장사 커버**: ~2,800 침묵 top-N cap 금지. 표본 절단 시 명시 라벨. 데모 소형주 포함.
- **정직갭**: 모든 숫자 ref-trace + as-of. 결측=first-class `—`/미공시, 0-fill·impute 금지. 종합점수·buy/sell 톤 금지.
- **레이아웃법**: center=차트, right=표/텍스트/메트릭(그래프 금지), left=내비. 흐름막대=center-stack only.
- **commit 자율 / push 운영자 게이트**(UI surface).

## 4. 영향 파일 (구현 착수 시)

**브라우저(Phase 0/1)**:
- `landing/src/lib/browser/companyLive.ts` (6 SELECT + rcept_no/stlm_dt)
- `ui/packages/contracts/src/company.ts` (`LiveCompanyReportFact` + rceptNo/stlmDt), `report.ts`(필요 시)
- `ui/packages/surfaces/src/terminal/panels/RightStack.svelte` (리본·섹션 문장·`상세보기`·lossPct/control-shift 헤더)
- `ui/packages/surfaces/src/terminal/lib/holdings.ts` (`controlShiftSummary(periods)` 순수 helper)
- `ui/packages/surfaces/src/terminal/panels/FinFullscreen.svelte` + `lib/finTabs.ts` (RETURN/PEOPLE 탭 확장 + 환원흐름 막대)
- `ui/packages/surfaces/src/terminal/lib/cardGuide.ts` (신규 키 7 + convention 주석)
- `ui/packages/surfaces/src/terminal/charts/MiniFinChart.svelte` (소각vs금고 stacked+hatch — 필요 시)
- `ui/packages/surfaces/src/viewer/lib/dartUrl.ts` (`viewerUrl` 재사용, 신규 0)

**엔진/CI(Phase 2)**:
- `src/dartlab/scan/builders/kr/snapshot.py:159-161` (인적자본 분위 배열 bake — `scanValueAdded`/`computeSalaryVsRevenue`; ⚠ `scan/workforce/snapshot.py` 아님, 08 G2)
- R&D consolidation: rndIntensity parquet bake(`calcRndExpense` 소비) + `reportSource.ts` 5번째 read + `report.rndIntensity` 포트
- `ui/packages/surfaces/src/terminal/lib/engine.ts` (인적자본 백분위 축 `mk()`/`pctRank` 1행)

**테스트/가드**:
- NEVER-CLAIM grep 가드 확장(신규 토큰), `node tests/audit/checkUiDataWiring.mjs`, `npx svelte-check`, baked 배열 N/asOf/gate 단위검증.

## 5. 영향 함수

`loadLiveCompanyReportFacts`(SELECT+contract) · `viewerUrl`/`openFiling`(↗ 재사용) · `buildShareholderReturn`(소각 표면화) · `controlShiftSummary`(신설) · `buildHoldingsModel`(lossPct/pctOfParentCap 인라인) · `calcRndExpense`(소비, 불변) · `scanValueAdded`/`computeSalaryVsRevenue`(bake) · `mk`/`pctRank`(인적자본 축) · CARD_GUIDE(7키) · FinFullscreen RETURN/PEOPLE 빌더.

## 6. 평가 (개발자 + PM 렌즈)

**개발자**: 최대 위험 = ① `rcept_no` 배선(유일 신규 의존, 순수 additive 컬럼 → Phase 0 단독·svelte-check 선). ② 딥링크 mis-wire(`urlForCompany`=null → `viewerUrl`). ③ R&D 공개배선(엔진 재구축 함정 — CI bake 1 task 로). ④ 누적 소각 비율(same-year undefined). ⑤ contribShare 가짜 분모(보고순익 재배선/삭제). ⑥ 교집합 N(글로벌 N=top-cap 침묵). ⑦ 레이아웃법 누출(그래프=center, 백분위=단일시점, grep 게이트). 재사용 지도 정밀(새 셸 0).

**PM**: 사용자 명령("강력한 정보 못 씀") 정확 진단. ROI 탁월 — P0/P1 거의 전부 *빼기*(중복 패널 제거 + 메모리 배열 리프레임, 새 fetch 0), 순 패널 DOWN 하며 최고신호 KR-equity read(소각vs금고·lossPct·control-shift·인적자본) 표면화. '강함'과 '단순함'이 일치하는 드문 기능. **컷라인**: Phase 0(스파인) + Phase 1(zero-fetch 리프레임) = MVP. Phase 2(엔진 R&D/백분위)는 고가치이나 CI-bake 비용 → blocking 없이 slip 허용. Phase 3 = 선택, 새 파싱 필요 시 컷. 데모 게이트=3-케이스 소형주(삼성 아님)가 PM 강제 정직 계약. 경계는 소비만(재소유 금지). UI push 운영자 게이트.
