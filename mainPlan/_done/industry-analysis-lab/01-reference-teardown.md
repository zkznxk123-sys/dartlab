# 01. 레퍼런스 분해 — 세계 메커니즘·제품 teardown

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: 세계 수준 산업 분석 프레임워크(학술/실무)와 제품을 분해해 *우리가 이미 가진 것 / 묻어둔 것 / 못하는 것*으로 나눈다. 각 항목 TAKE·REJECT·DEFER. §4 = 2차 조사가 검토했으나 흡수 거부한 부정 카탈로그(재제안 차단).

> 출처는 WebSearch로 확인한 실제 레퍼런스(Porter HBR 1979/1985, Gadiesh·Gilbert HBR 1998, Vernon 1966, Gort·Klepper 1982, CFA 커리큘럼, DOJ HHI 척도, Bloomberg Intelligence/SPLC, Morningstar Economic Moat, MSCI GICS, FactSet RBICS, Damodaran industry datasets). dartlabFit 판정은 코드실측 기반.

---

## 1. 프레임워크 teardown (학술/실무)

| 메커니즘 | 핵심 | 우리 데이터로 | 판정 |
|---|---|---|---|
| **Profit Pools** (McKinsey / Gadiesh·Gilbert HBR 1998) | 밸류체인 전 구간 총이익을 풀로, 이익이 어느 단계에 집중되는지. x=단계 매출규모, y=단계 이익률. **이익집중 ≠ 매출집중** | **HIGHEST.** `buildIndustrySummary`가 이미 stage별 매출·영업이익·기업수 산출([financials.py:303-313](../../../src/dartlab/industry/build/financials.py#L303)). 격자는 정규화 파생일 뿐 신규 fetch/계정/컨센서스/share/TAM 의존 0. 학술 근거 보강: Slywotzky *Value Migration*(profit zone)·Christensen *이익 보존이동*·BCG *Stack Fracturing*(1998)은 prose 인용만(정량화=§4 migration kill 회귀) | **TAKE — killer #1** |
| **Stack Fracturing / Deconstruction** (BCG Stern 1998) | profit-pool의 "왜" — 어느 단계가 규모민감·집중으로 이익을 독식하나 | **TAKE(프레임명만, 신규 계산 0).** Killer #1 격자의 *해석 프레임*. 산업 단위 CR3는 `calcIndustryConcentration`이 이미 계산 — ★stage 단위 새 grouping/3차원 인코딩은 금지(축 누적=덕지덕지) | **TAKE(02 Killer#1 내러티브)** |
| **Value Chain** (Porter 1985) | 산업을 upstream→midstream→downstream 분해, 단계별 부가가치 | **YES.** nodes.json에 stage·stream·role 이미 매핑. 우리 핵심자산과 정확 일치 | **TAKE(기반)** — profit-pool의 x축 |
| **교섭력 — 공급자/구매자** (Porter 5힘) | 거래선 매출의존도(ratio %)가 핵심 측정 | **HIGH but DATA-POOR.** edges.json이 ratio+amount 보유(공시인용). 단 amount 132/18,418·ratio 19·customer 7건 | **TAKE — killer #2(한계 가드 엄격)** |
| **Industry Life Cycle** (Vernon 1966 / Gort·Klepper 1982) | 도입→성장→shakeout→성숙→쇠퇴 | **LIVE (자동 부착).** backend `classifyLifecycle`은 4-phase emit(도입·성장·성숙·쇠퇴, [lifecycle.py](../../../src/dartlab/industry/calcs/lifecycle.py)) + `ai/tools/industryContext.py`가 재도약(resurgence) 합성 → **surface 5-phase**(engines.industry.lifecycle SKILL이 SSOT). `industryBadge.phase`로 단일 종목 응답에 런타임 자동 부착 — 화면 미노출 아님. thin=전산업 공통 임계 | **LIVE / 적응형 임계만 DEFER(_attempts, build 내부)** |
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
| **Bloomberg SPLC / FactSet supply chain** | 100k사·500k관계 center-node 공급망, amount 가중 | edges + `/industry/[id]` amount top20 이미 有. 단 한국 DART 본문 위주라 스케일·amount 조밀도가 SPLC 발끝에도 못 미침(amount 0.7%) | **TAKE(인용 우위) but 빈곤 명시 — 과대포장 금지** |
| **Morningstar Economic Moat** | wide/narrow/none (ROIC>WACC + 5소스 정성) | ROIC-WACC 스프레드 지속성은 측정 가능(fin-stmt-lab reverseDCF 영역), wide/narrow 단정은 정성판단 | **REJECT(라벨) / 측정값은 fin-stmt-lab 소유** |
| **Koyfin COMP / Capital IQ / Damodaran averages** | peer 벤치마킹 + 산업평균 분포 | `compare()`가 이미 소유. industryStats.json이 p10~p90 분포 보유(Damodaran 동적버전). forward 멀티플은 컨센서스 EXCLUDED라 trailing만 | **OWNED-ELSEWHERE — industry는 "분포 위 1점 읽기"로 funnel** |
| **MSCI GICS / FactSet RBICS** | 전수·표준화 분류 SSOT, 연1회 리뷰 | KSIC + taxonomy.json(운영자 큐레이션 34산업)이 GICS 역할. 단 선별·수동(freshness 라벨 필수), RBICS식 revenue-% 세그먼트는 panel 2/10만 clean | **PARTIAL/DIFFERENT — taxonomy 유지, 전수 표준화는 비-목표** |
| **AlphaSense+Tegus / CFRA Surveys / Statista** | 전문가 transcript·정성 리서치·시장규모 | 데이터 아닌 큐레이션 콘텐츠라 재현 불가. story(L3)가 공시근거 내러티브로 '데이터주도 절반'에 대응 | **NO — target price·buy/sell 의도적 미구현** |
| **Visible Alpha** | operational KPI 컨센서스(ASM/RPM·SSS·subscribers) | 컨센서스 line item EXCLUDED, 비재무 표준 미보유 | **NO** |

---

## 3. 취사 요약

- **TAKE (본 PRD 핵)**: Profit Pools(killer #1, Phase A) · Value Chain(기반) · 교섭력 ratio/amount(killer #2, Phase B, 한계 가드) · 묻어둔 hop2/공급다양성 배선(Phase B) · 산업 분포 밴드 통일(killer #3, Phase C).
- **REJECT (만들지 않음)**: Porter 5힘 종합 스코어카드 · HHI DOJ 라벨 · 진입장벽 점수화 · 대체재 정량화 · 정식 TAM/SAM/SOM · moat wide/narrow 라벨 · operational KPI 대시보드.
- **DEFER (다른 곳 소유 / 후속)**: SCP 인과·수요공급 driver(scenario-simulator) · unit economics 재무부분(analysis/compare) · 가동률(셀 추출 후) · 적응형 lifecycle 임계(build 내부 후속) · peer COMP(compare).

세부 데이터 가용성·킬리스트 = [04-data-readiness-kill-list.md](04-data-readiness-kill-list.md).

---

## 4. 조사 너머 — 재제안 차단 (REJECT, 본문 흡수 0)

2차 대대적 조사가 검토했으나 흡수하지 않은 것. *닫기 자산* — "나중에 Phase N"으로 흐리지 말고 여기서 영구 차단(데이터 매트릭스는 [04](04-data-readiness-kill-list.md)).

- **Capital Cycle / 자산증가율 이상현상** (Marathon Capital Returns · Cooper-Gulen-Schill 2008 = FF CMA): KR은 프리빌드 parquet에서 순수 CAPEX 분리 불가([scan/financial/cashflow.py](../../../src/dartlab/scan/financial/cashflow.py):3-5 — ICF에 증권 취득/처분 혼입) → Marathon 정의 측정 불가, ΔPP&E·자산증가율 프록시만. 게다가 **`recipes.industry.peerCapexWave`(curated, validated 2026-05-27)가 이미 capex/매출 wave lead-lag 구현** + scenario-simulator(driver DAG)·quant(투자팩터) 경계 + 신규 다년 집계=덕지덕지.
- **GE 9-box · BCG 매트릭스 · ADL 성숙도 · Hamilton Helmer 7 Powers · Wardley · McKinsey 3 Horizons · Profit-from-the-Core**: 점유율 raw 부재(핵심축 막힘) 또는 정성·회사내부 전략(산업분석 범위 밖) 또는 종합점수=vanity(Porter 5힘 스코어카드와 동일 fake precision).
- **iTooza ROE&PBR 매트릭스 · 팩터/섹터 로테이션**: Killer #3 + compare 재탕(가격축 추가=덕지덕지) 또는 L2↔L2 위반(quant+macro→story·scenario-simulator 소유).
- **Damodaran 자본효율** (sales-to-capital · reinvestment rate · NOPAT · ROC): ★이미 [synth/damodaranL15.py](../../../src/dartlab/synth/damodaranL15.py):390-416에 curated 구현 + `damodaranAnalysisSystem.json` gapLedger/plannedSkills(salesToCapitalBenchmark·incrementalRoc) 소유. §2가 Damodaran을 compare+fin-stmt-lab OWNED-ELSEWHERE로 판정 — 산업분포 추가=또 하나의 백분위(vanity) 회귀.
- **S-curve · 경험곡선 · MES cost curve · Christensen 파괴 라벨 · 플랫폼 network-effect**(MAU/GMV/take rate): 수량·단위원가·세그먼트·operational KPI 부재(EXCLUDED 동일 사유).
- **Leontief Input-Output "승수" 명명**: `computeHop2`는 그래프 인접 count BFS(amount 가중조차 4.1%)일 뿐 — 진짜 Rasmussen/Hirschman 연쇄는 산업연관표(한국은행) 기술계수 행렬 필요(부재). "Leontief 경량판" 명명은 SPLC보다 강한 학술 권위 라벨이라 확신오정렬 더 큼. *disclaimer만* 흡수([04 BLOCKED](04-data-readiness-kill-list.md)), 명명은 거부.
