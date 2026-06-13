# 06. 진행 원장

상태: 비전 PRD v0.1 (2026-06-13) → **착수 v0.2 (2026-06-14): Phase 1 실측 + 가격↔기초체력 오버레이 구현·검증**
목적: 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터. 재개 시 여기부터.

---

## 0. 착수 기록 (2026-06-14)

### 0.1 Phase 1 MUST 실측 결론 — 대부분 *이미 구현*, parity 추가 거부
운영자 go 후 `financeSource.ts`(785줄)·`finTabs.ts`·`FinFullscreen.svelte`·`CenterStack.svelte`·`RightStack.svelte`·`MiniFinChart.svelte` 전수 실측. PRD §1 steelman("이미 95% 보유 — parity 카드 추가는 차별 아님")이 코드로 확증됨:

| MUST | 실측 상태 |
|---|---|
| 1. 기간모드(분기/연간/TTM) | **이미 구현** — CenterStack(ttm)·RightStack(quarter)·FinFullscreen 3곳 segGroup, `buildMode` per mode. |
| 1. 역순 | **이미 구현** — `RightStack:110-111` 재무제표 **표는 최신순** + 박제 주석 "차트는 오름차순 유지, 표만 reverse" = **운영자 의도적 결정**. 차트 역순 강제는 이 결정 위반이라 기각. |
| 2. 업종 인지 카드 필터 | **대부분 기존 `alive`/null-filter가 처리**(은행=재고·매출원가 null→DIO/GPM 카드 자동 붕괴). 명시 업종→카드-hide 맵은 marginal + `if(bank)` 클러터 위험(PRD §5 위반)이라 보류. |
| 3. 지수 리베이스 | **보편 토글 기각** — 16카드가 목적별 설계(듀얼축·혼합단위, FinSeries에 개별 단위 없음)라 깨끗이 리베이스되는 카드가 사실상 1개(incomeBreakdown)뿐. 보편 토글은 클러터. **→ 리베이스의 진짜 거처 = 0.2 가격↔체력 카드.** |
| 4. 운전자본 회전일수 split | **이미 구현** — `cccCard`(CCC+DSO+DIO+DPO 4선, financeSource:492). CapEx 재투자율은 `capexCycle`(CAPEX/매출·CAPEX/영업CF) 존재; CapEx/감가상각은 감가상각 계정 부재로 blocked. |
| 5. honest-gap | **탭 레벨 이미 구현**(`FinFullscreen` tabEmpty "이 회사는 해당 탭 데이터 없음"). 카드 레벨 "왜 비어있나" placeholder 는 현 hide-empty 설계(빈 카드 노출 금지 룰)와 충돌 + "기본 뷰 더 작게" 성공지표 역행이라 미채택. |

**결론**: Phase 1 MUST 는 성숙한 터미널에 실질 충족돼 있다. PRD 자신의 subtraction-first·"강함은 깎아서" 원칙대로, parity 카드 더 그리기는 거부. 진짜 가치는 Phase 2 신규 능력(가격↔체력·PER/PBR·백분위)이며 거기서 리베이스가 비로소 의미를 가진다.

### 0.2 구현 deliverable — 가격↔기초체력 지수 오버레이 (SHOULD #8, iTooza 시그니처)
- **신규 `ui/packages/surfaces/src/terminal/lib/priceFundamental.ts`** — 순수 `buildPriceFundamentalCard(view, filedDates, candles)`. 주가·매출·자본을 첫 공통 유효기간=100 으로 리베이스해 3선 1차트. ★**look-ahead 차단**: 각 기간 주가 = 그 기간 *공시 접수일* 종가(`priceAtOrBefore`, t≤접수일 마지막 종가). 신규 데이터 0 — 이미 로드된 candles+bundle.filedDates 재사용.
- **`FinFullscreen.svelte`** — `candles` prop 수신, `priceCard` derived, 종합 탭 선두 히어로(`.finFsHero`, amber 보더)로 렌더. `CenterStack` 이 `chartCode===co.code` 소프트스왑 가드 후 candles 주입(전환 중 옛 회사 캔들 차단 → null=비표시).
- **`cardGuide.ts`** `priceVsFundamentals` 해석칩(서술만, "가격이 펀더멘털 위/아래로 벌어짐" — 적정주가 판정 금지, honesty 가드레일 §5.2 준수). **`terminal.css`** `.finFsHero` 5룰.
- **검증**: svelte-check 0 ERROR(3959파일) · `@dartlab/ui-local` 풀빌드 green(terminal.js 213kB) · 순수 로직 합성테스트 PASS(look-ahead 2500 미사용·=100 인덱싱·null 가드 3종[candles 부재/단일점/행부재]). ⏳라이브 스크린샷(FinFullscreen 종합 탭)은 /api(:8400 dartlab ai 서버) 구동 필요 — 별도 verify 패스.

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
| 06-progress-ledger | ✅ v0.2 (본 문서 — §0 착수 기록) |

## 4. 워크스페이스 변동

- 본 PRD 작성 = `mainPlan/financial-statement-lab/` 신설(문서만). 코드 변경 0.
- 의존 인접 PRD: `mainPlan/scenario-simulator/`(미래 리플레이 — reverseDCF·valuation 경계 공유), `mainPlan/`(UI 플랫폼 리팩토링 — 터미널 ui/packages 거처).
- 메모리 정본: `reference_itooza_vchart_system`(iTooza 50차트 census), `reference_financial_graph_ssot`(렌더 정본), `project_segment_rnd_extraction`·`project_gov_price_migration`·`project_gather_dataportal_customs_pension`·`project_terminal_chart_audit`(데이터 경계).

## 5. NEXT (착수 시 닫을 체크리스트)

✅ **Phase 1 — 완료(2026-06-14)**: MUST 1/4/5 = 이미 구현 실측 확인(§0.1), MUST 2/3 = parity 거부, 진짜 신규 가치 = 가격↔기초체력 오버레이 구현·검증(§0.2). 브라우저 전용·신규데이터 0.

다음(Phase 2부터):
1. **PER/PBR 시계열** — Phase 2 진입 전 **주식수 정합 census**(분기 stockTotal × 자사주 vintage). clean 안 되면 스냅샷 유지(카드 미생성). 가격↔체력과 같은 (gov/prices × reportSource.stockTotal × panel) 조인 패턴 재사용.
2. **가격↔체력 라이브 스크린샷 검증** — /api(:8400) 구동 후 FinFullscreen 종합 탭 실데이터 눈검수(삼성·카카오·중소형사 각 1). 현 상태=빌드·타입·로직 green, 라이브 미확인.
3. Phase 3 진입 전: 동종 universe 정의(업종 코드·시총 밴드) + 분포 prebuild 스키마 → 백분위 밴딩(SHOULD #6).
4. `tests/_attempts/financialStatementLab/` 카테고리 생성(Python 의존 능력 졸업 게이트 — reverseDCF 함축기대·forensic 사전계산·세그먼트/R&D).

미작성/후속:
- 컴포넌트 spec 상세(FinCard `band`/`flags` 필드 계약 확정) = 착수 시 03 §4 기준 구현 문서로.
- 공시 큐레이션(11) ↔ scenario-simulator disclosure-event-rail 경계 합의 = 두 PRD 교차 세션.

## 6. 메모리 포인터

신규 메모리 1줄(MEMORY.md §6.2): `project_financial_statement_lab` — 본 폴더 SSOT 포인터(내용 복제 금지). 착수 = 운영자 go.
