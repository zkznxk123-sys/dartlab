# 01. 레퍼런스 분해 — 세계 메커니즘·제품 teardown

상태: 비전 PRD v0.1 (2026-06-14)
목적: 세계 수준 산업 분석 프레임워크(학술/실무)와 제품을 분해해 *우리가 이미 가진 것 / 묻어둔 것 / 못하는 것*으로 나눈다. 각 항목 TAKE·REJECT·DEFER.

> 출처는 WebSearch로 확인한 실제 레퍼런스(Porter HBR 1979/1985, Gadiesh·Gilbert HBR 1998, Vernon 1966, Gort·Klepper 1982, CFA 커리큘럼, DOJ HHI 척도, Bloomberg Intelligence/SPLC, Morningstar Economic Moat, MSCI GICS, FactSet RBICS, Damodaran industry datasets). dartlabFit 판정은 코드실측 기반.

---

## 1. 프레임워크 teardown (학술/실무)

| 메커니즘 | 핵심 | 우리 데이터로 | 판정 |
|---|---|---|---|
| **Profit Pools** (McKinsey / Gadiesh·Gilbert HBR 1998) | 밸류체인 전 구간 총이익을 풀로, 이익이 어느 단계에 집중되는지. x=단계 매출규모, y=단계 이익률. **이익집중 ≠ 매출집중** | **HIGHEST.** `buildIndustrySummary`가 이미 stage별 매출·영업이익·기업수 산출([financials.py:303-313](../../src/dartlab/industry/build/financials.py#L303)). 격자는 정규화 파생일 뿐 신규 fetch/계정/컨센서스/share/TAM 의존 0 | **TAKE — killer #1** |
| **Value Chain** (Porter 1985) | 산업을 upstream→midstream→downstream 분해, 단계별 부가가치 | **YES.** nodes.json에 stage·stream·role 이미 매핑. 우리 핵심자산과 정확 일치 | **TAKE(기반)** — profit-pool의 x축 |
| **교섭력 — 공급자/구매자** (Porter 5힘) | 거래선 매출의존도(ratio %)가 핵심 측정 | **HIGH but DATA-POOR.** edges.json이 ratio+amount 보유(공시인용). 단 amount 132/18,418·ratio 19·customer 7건 | **TAKE — killer #2(정직 가드 엄격)** |
| **Industry Life Cycle** (Vernon 1966 / Gort·Klepper 1982) | 도입→성장→shakeout→성숙→쇠퇴 | **LIVE but THIN.** `classifyLifecycle`이 매출 YoY로 4-phase 산출([lifecycle.py](../../src/dartlab/industry/calcs/lifecycle.py)). 전산업 공통 하드코딩 임계가 한계 | **DEFER(적응형 임계는 Phase 후속, build 내부)** |
| **집중도 HHI / CRn** (Bain IO / DOJ) | HHI=Σ(점유율²), CR4=상위4사 합 | **LOW (raw 부재).** `calcHHI`/`calcIndustryConcentration` 정확히 구현됐으나 런타임 소비처 0. 결정적: 시장점유율 raw 부재 → "상장사 매출=시장규모" 근사 = 체계적 과대 | **REJECT(DOJ 라벨) / 조건부(라벨 뗀 CR4 evidence)** |
| **SCP** (Bain/Mason) | 구조(집중도)→행동→성과(이익률) 인과 | **PARTIAL.** 구조·성과 상관은 가능하나 인과는 L3 story 조합 영역, conduct 데이터 없음 | **DEFER** |
| **진입장벽** | 자본집약도·R&D집약도·규모의경제 프록시 | **PARTIAL.** panel로 개별 프록시 가능, '진입장벽 점수' 단일화는 over-claim | **REJECT(점수화) / 개별 프록시는 analysis 영역** |
| **대체재 위협** | 교차탄력성·기술전환 | **NO.** 산업 외부 도메인 지식, taxonomy edges는 공급관계만(대체관계 없음) | **REJECT** |
| **Unit Economics** | 단위당 기여마진·CAC/LTV | **PARTIAL.** 재무 기반(매출원가율·자본회전율·ROIC)은 가능, per-unit(대당/톤당)·CAC/LTV는 수량 데이터 부재 | **DEFER(재무 부분은 analysis/compare 소유)** |
| **TAM/SAM/SOM** | 시장규모·침투율 | **PARTIAL→NO.** 상장사 매출합은 비상장+수입+미래수요 누락으로 체계적 과소. SAM/SOM은 점유율 raw 필요 | **REJECT(정식 삼각) — 산업 매출규모 제공은 summary가 이미 함** |
| **수요/공급 Driver** | 거시·전방산업·증설·재고 | **PARTIAL.** macro(L2)·customs(수출)·panel CAPEX/재고로 가능하나 L2↔L2 직접 import 금지 → L3 story 조합. scenario-simulator driver DAG와 경계 | **DEFER(scenario-simulator 소유)** |
| **산업 Cycle / Capacity·Utilization** | 가동률 % | **PARTIAL.** 재무 프록시 사이클(`calcSectorCycle`)은 단일연도 conf 0.5. 진짜 가동률은 DART '생산능력·가동률' 항목 파싱 필요(미추출) | **DEFER(가동률 셀 추출 시 승격)** |
| **가격결정력** | 비용전가·프리미엄 | **PARTIAL.** 마진 지속성·spread로 프록시. moat 본질은 정성 | **DEFER** |

---

## 2. 제품 teardown

| 제품 | 산업 뷰 | 우리 재현 | 판정 |
|---|---|---|---|
| **Bloomberg Intelligence (BI)** | 산업 대시보드·BICS·1200 KPI(operational driver) | 재무 KPI 분포는 yes, 비재무 operational KPI(컨센서스 line item)는 EXCLUDED | **REJECT(operational KPI) / TAKE(재무 분포)** |
| **Bloomberg SPLC / FactSet supply chain** | 100k사·500k관계 center-node 공급망, amount 가중 | edges + `/industry/[id]` amount top20 이미 有. 단 한국 DART 본문 위주라 스케일·amount 조밀도가 SPLC 발끝에도 못 미침(amount 0.7%) | **TAKE(인용 우위) but 빈곤 정직 노출 — 과대포장 금지** |
| **Morningstar Economic Moat** | wide/narrow/none (ROIC>WACC + 5소스 정성) | ROIC-WACC 스프레드 지속성은 측정 가능(fin-stmt-lab reverseDCF 영역), wide/narrow 단정은 정성판단 | **REJECT(라벨) / 측정값은 fin-stmt-lab 소유** |
| **Koyfin COMP / Capital IQ / Damodaran averages** | peer 벤치마킹 + 산업평균 분포 | `compare()`가 이미 소유. industryStats.json이 p10~p90 분포 보유(Damodaran 동적버전). forward 멀티플은 컨센서스 EXCLUDED라 trailing만 | **OWNED-ELSEWHERE — industry는 "분포 위 1점 읽기"로 funnel** |
| **MSCI GICS / FactSet RBICS** | 전수·표준화 분류 SSOT, 연1회 리뷰 | KSIC + taxonomy.json(운영자 큐레이션 34산업)이 GICS 역할. 단 선별·수동(freshness 라벨 필수), RBICS식 revenue-% 세그먼트는 panel 2/10만 clean | **PARTIAL/DIFFERENT — taxonomy 유지, 전수 표준화는 비-목표** |
| **AlphaSense+Tegus / CFRA Surveys / Statista** | 전문가 transcript·정성 리서치·시장규모 | 데이터 아닌 큐레이션 콘텐츠라 재현 불가. story(L3)가 공시근거 내러티브로 '데이터주도 절반'에 대응 | **NO — target price·buy/sell 의도적 미구현** |
| **Visible Alpha** | operational KPI 컨센서스(ASM/RPM·SSS·subscribers) | 컨센서스 line item EXCLUDED, 비재무 표준 미보유 | **NO** |

---

## 3. 취사 요약

- **TAKE (본 PRD 핵)**: Profit Pools(killer #1, Phase A) · Value Chain(기반) · 교섭력 ratio/amount(killer #2, Phase B, 정직 가드) · 묻어둔 hop2/공급다양성 배선(Phase B) · 산업 분포 밴드 통일(killer #3, Phase C).
- **REJECT (만들지 않음)**: Porter 5힘 종합 스코어카드 · HHI DOJ 라벨 · 진입장벽 점수화 · 대체재 정량화 · 정식 TAM/SAM/SOM · moat wide/narrow 라벨 · operational KPI 대시보드.
- **DEFER (다른 곳 소유 / 후속)**: SCP 인과·수요공급 driver(scenario-simulator) · unit economics 재무부분(analysis/compare) · 가동률(셀 추출 후) · 적응형 lifecycle 임계(build 내부 후속) · peer COMP(compare).

세부 데이터 가용성·킬리스트 = [04-data-readiness-kill-list.md](04-data-readiness-kill-list.md).
