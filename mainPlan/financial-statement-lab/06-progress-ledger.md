# 06. 진행 원장

상태: 비전 PRD v0.1 (2026-06-13)
목적: 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터. 재개 시 여기부터.

---

## 1. 현재 결정 (확정)

- **정체성**: 터미널 재무제표 분석 surface 업그레이드. iTooza V차트 + Butler 레퍼런스를 *복제 아님*, panel cell-grid·`compare`·reverseDCF·honesty spine으로 흡수. 성공 지표 = 차트 수 아님, "기본 뷰 더 작게 + 카드마다 별개 질문".
- **거처**: 기존 `ui/packages/surfaces/src/terminal/` 확장(finTabs·MiniFinChart·financeSource). 새 엔진·패널·탭 더미 금지. Python 의존은 `tests/_attempts/financialStatementLab/` 졸업 후 → prebuild parquet.
- **렌더러**: `MiniFinChart.svelte` EXTEND, `ChartRenderer`(풀사이즈 디스패처) 도입 금지.
- **차별 핵**: 동종 백분위(`compare`) + 가격 함축 기대(reverseDCF) + 이익품질 forensic + 정합성. 전부 ref-추적.
- **데이터 킬리스트**: 컨센서스·수출 회사매핑 = EXCLUDED. 수주잔고 = BLOCKED. 세그먼트(2/10)·PER/PBR 시계열(post-2020) = CONDITIONAL. 금융업 set = WON'T(필터는 MUST).
- **가드레일**: 추천·단정·종합등급·목표주가 0. reverseDCF = 함축 기대 읽기지 적정주가 아님(scenario-simulator 미래 what-if과 경계).
- **착수**: 운영자 go 대기. Phase 1(브라우저 전용)은 mainPlan UI 플랫폼 완료 무관 선행 가능.

## 2. 토론 출처 (provenance)

2026-06-13 전문 에이전트 4 lens 조사·설계·적대검증:
- **lens 1 (제품 reverse-engineering)**: iTooza/Butler 갭 분해 → 고가치 4(가격↔체력 지수·밸류에이션 탭·공시 큐레이션·운전자본 split) vs 덕지덕지 구분.
- **lens 2 (아키텍처 재사용)**: 코드 실측(Read/Grep 31회) → REUSE/EXTEND/NEW 판정, MiniFinChart EXTEND·ChartRenderer 금지, 데이터 준비도순 Phase.
- **lens 3 (가치투자 도메인 "why")**: 투자자 5 질문 + killer 5종 + 차별 명제 교정 3.
- **lens 4 (적대 PM)**: 클론 트랩·데이터 킬리스트·MUST/SHOULD/WON'T 단두대·honesty 가드레일·실패 모드.

수렴: 4 lens 모두 "이미 70% — 클론 금지, 깎아서 강하게, 데이터 없으면 카드 없음, 추천 금지"에 동의. 잔여 긴장(도메인 lens의 야심찬 moat vs 적대 lens의 ship-narrow) = **비전은 차별 명제(백분위·함축기대·품질), 실행은 subtraction-first 단계화**로 해소. reverseDCF는 scenario-simulator honesty 패턴 차용해 목표주가 함정 회피.

## 3. 문서 상태

| 문서 | 상태 |
|---|---|
| README | ✅ v0.1 |
| 00-product-prd | ✅ v0.1 |
| 01-reference-teardown | ✅ v0.1 |
| 02-differentiation-killer-features | ✅ v0.1 |
| 03-architecture-and-reuse | ✅ v0.1 (코드 경로 실측) |
| 04-data-readiness-kill-list | ✅ v0.1 |
| 05-scope-phasing-guardrails | ✅ v0.1 |
| 06-progress-ledger | ✅ (본 문서) |

## 4. 워크스페이스 변동

- 본 PRD 작성 = `mainPlan/financial-statement-lab/` 신설(문서만). 코드 변경 0.
- 의존 인접 PRD: `mainPlan/scenario-simulator/`(미래 리플레이 — reverseDCF·valuation 경계 공유), `mainPlan/`(UI 플랫폼 리팩토링 — 터미널 ui/packages 거처).
- 메모리 정본: `reference_itooza_vchart_system`(iTooza 50차트 census), `reference_financial_graph_ssot`(렌더 정본), `project_segment_rnd_extraction`·`project_gov_price_migration`·`project_gather_dataportal_customs_pension`·`project_terminal_chart_audit`(데이터 경계).

## 5. NEXT (착수 시 닫을 체크리스트)

운영자 go 후 Phase 1부터:
1. **기간모드·업종 필터·지수 리베이스·honest-gap** — `financeSource.ts`/`finTabs.ts`/`MiniFinChart.svelte` 실측 재확인 후 브라우저 구현. 신규 데이터 0.
2. **운전자본 split + 신뢰 데이터 1~3 카드** — 기존 CCC 카드 상위호환, cardGuide 동행.
3. Phase 2 진입 전: PER/PBR 시계열 **주식수 정합 census**(분기 stockTotal × 자사주 vintage) — clean 안 되면 스냅샷 유지(카드 미생성).
4. Phase 3 진입 전: 동종 universe 정의(업종 코드·시총 밴드) + 분포 prebuild 스키마.
5. `tests/_attempts/financialStatementLab/` 카테고리 생성(Python 의존 능력 졸업 게이트).

미작성/후속:
- 컴포넌트 spec 상세(FinCard `band`/`flags` 필드 계약 확정) = 착수 시 03 §4 기준 구현 문서로.
- 공시 큐레이션(11) ↔ scenario-simulator disclosure-event-rail 경계 합의 = 두 PRD 교차 세션.

## 6. 메모리 포인터

신규 메모리 1줄(MEMORY.md §6.2): `project_financial_statement_lab` — 본 폴더 SSOT 포인터(내용 복제 금지). 착수 = 운영자 go.
