# 06 — 진행 원장

## 상태

- **2026-06-19**: PRD v0.1 작성(13인 토론 `wf_c20526bc-bed`) → 확장 v0.2(07, 11인 `wf_c62ab765-ea5`) → **경화 v0.3(08, 4인 `wf_c451d741-93f`)**. 착수 대기(운영자 go).
- **구현 코드 1건(perf 버그 수정, commit `e801f42f0`)**: 정기보고서 팩트 패널 멈춤 = DuckDB→hyparquet 이관(실측 수십초→4.3초·svelte-check 0err·시각변화 없음). 나머지 feature 구현 0.
- **경화 평결**: "조건부 강함 — 강한 제품, 약한 기반". SHIP 전 정정 필수 6갭(08 §2): F2 도달불가(→NEEDS-PARSING)·F5 경로·grep가드 신규·lossPct lift·공개로컬 패리티·−1 4팩트 드롭. **Phase-0 사전점검 probe**(체이닝 1.4x·6%·shard0 대표성 측정)가 새 SHIP 게이트.

## NEXT (재개 포인터)

> 운영자 go 시 **Phase-0 사전점검 probe(08 §4.1) 먼저** — 체이닝 1.4x·cost-by-nature 6%·shard0 대표성을 전 유니버스 측정해 SHIP 숫자 확정. 그 뒤 Phase 0 스파인. 08 §2 정정 6갭 + §3 UI/UX 상태기계 반영.

1. **Phase 0 (스파인, 단독 ship 가능)**: `companyLive.ts` 6 SELECT 에 `rcept_no`+`stlm_dt` 추가 (⚠ reportFacts는 이미 hyparquet 이관됨 — `e801f42f0`, 라인 L286-322·DuckDB 아님) → `LiveCompanyReportFact` contract → 도시에 헤더 리본 → 평면 팩트 패널 흡수. svelte-check 0 + 헤더 회귀 가드 + 공개/로컬 동일.
2. **Phase 1 (zero-fetch 리프레임)**: 환원흐름 문장+RETURN 막대 / lossPct+control-shift / 인력 자기이력+`상세보기` / CARD_GUIDE 리프레임. NEVER-CLAIM grep + 3-케이스 소형주 데모 → 운영자 push 승인.
3. **Phase 2 (엔진 bake)**: 인적자본 분위 배열 + rndIntensity CI parquet. slip 허용.
4. **Phase 3 (선택)**: 가동률 원문 발췌(zero 추출 한정).

## 열린 결정 (착수 전 확인 가능)

1. **R&D 스파크라인 vs 텍스트 추세**: 적대검증 합의=텍스트(↑/↓/→ + 전년 Δ), 레일 그래프 금지. 인라인 스파크라인 primitive 도입 안 함 확인.
2. **R&D 소스 태그 의미**: IS라인(정규화 비용) vs SG&A주석(총지출, 자본화 포함) = 다른 개념 → UI 가 회사별 소스 표시(절대 혼합 금지).
3. **Phase 2 slip 시**: Phase 1 단독 ship(R&D 행·백분위 축 부재로 우아하게 degrade, 깨진 빈 행 아님) 확인.
4. **`controlShiftSummary` 기간 선택**: earliest-vs-latest(큰 지배 이야기) vs latest-two(최신). 명시 YYYYqQ→YYYYqQ 라벨 어느 쪽이든.
5. **pctOfParentCap self-gate 임계**: 'material' listed 커버리지 기준(listed ≥1 AND listedStakeSum ≥ bookTotal 의 일정 비율)? 독립 소형주에 오해소지 작은 % 대신 자기 suppress 하도록 구체 cutoff.
6. **가동률 원문 블록(P3)**: 뷰어가 이미 rawMaterial 섹션 텍스트 렌더하는지(=anchor+label ship) vs 새 추출 필요(=컷) — feasibility 체크.

## 메모리 포인터

`MEMORY.md` §6.2 에 `[[project_terminal_periodic_report_dossier]]` 등록(포인터만, SSOT=본 폴더).
