# 00. 제품 PRD — 산업 분석 심화 랩

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: 판정·제품 비전·차별 명제·제품 원칙·핵심 화면·성공 기준을 한 문서로. 나머지 문서가 이 판정을 펼친다.

---

## 1. 판정 (왜 하는가 / 무엇이 진짜 문제인가)

**문제 재정의**: "산업 분석이 약하다"는 통념은 코드실측 후 틀린 것으로 드러났다. 진짜 문제는 셋이다.

1. **묻어둔 *함수***: industry 엔진엔 세계 수준 기계가 이미 들어있다 — `calcHHI`/`calcTopNRatio`/`calcIndustryConcentration`([insights.py](../../src/dartlab/industry/build/insights.py))은 DOJ 척도(1500/2500)로, `computeHop2`([hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32))는 2-hop 공급망을, `calcSupplyInsights`([insights.py:201](../../src/dartlab/industry/build/insights.py#L201))는 공급 다양성을 산출한다. 그런데 **이 함수들이 빌드 산출물(`enrichCompany` → JSON)에만 baked되고 Industry verb DataFrame·화면 어디서도 질의로 호출되지 않는다.** 만들고 (화면에) 묻은 부채다. ★단 산업 분석 *능력* 전체가 orphan은 아니다 — `recipes.industry/` 8 curated·validated(industryStagePhase·marginCompressionScan·supplyChainConcentration·peerCapexWave·rdIntensityTrend 등)가 RunPython 런타임 분석을 이미 제공한다(중복 신설 금지, [03 §5.1](03-architecture-and-reuse.md)).

2. **노출 안 된 핵심 능력**: `industry(id, summary=True)`(공정별 매출·영업이익 집계)·`timeline=True`(연도별 추이)는 live인데 **어느 화면에도 안 뜬다.** 퍼블릭 `/industry/[id]`는 라이브 엔진을 부르지 않고 사전빌드 static JSON([+page.ts](../../landing/src/routes/industry/%5Bid%5D/+page.ts): `/map/industries/{id}.json` 외 3종)만 렌더하며, 거기서도 산업 평균 영업이익률 스칼라 1개만 보여준다. 로컬 터미널은 진짜 industry 엔진을 아예 소비하지 않는다(RightStack 산업 패널 4종은 모두 ecosystem-nodes 회사중심 cut). (★`lifecycle`은 예외 — `industryBadge.phase`로 단일 종목 응답에 자동 부착돼 이미 live, backend 4-phase + 재도약 합성 = surface 5-phase.)

3. **분기·stale**: 산업 백분위가 3갈래(RightStack ecosystem pctRank / compare panel 분포 / industryStats 분포)로 분기해 정합성 위험. `industry/README.md`가 유령 *verb/모듈*(`dartlab.industry.sectorMomentumLeadership(...)` 등 구현 0)을 카탈로그까지 전파했다(단 동명 recipe는 실재). edges.json은 구버전 코드 산출물(precise 642 docstring vs 실제 132·source 라벨 불일치).

**판정**: 따라서 이 작업은 *세계 메커니즘을 새로 쌓는 일*이 아니라 **묻어둔 함수를 화면·verb에 배선하고, 핵심 능력을 화면에 노출하고, 분기를 통일하고, stale을 정리하는 일**이다. 그 위에 단 하나의 진짜 신규 가치(profit-pool 격자)를 얹는다.

---

## 2. 제품 비전 — 산업 분석가의 질문

산업을 보는 사람이 실제로 묻는 것:

- **이 산업에서 돈은 어느 단계가 버나?** (매출이 큰 단계가 아니라 — McKinsey profit pool의 핵심 통찰: 이익집중 ≠ 매출집중)
- **이 공급사가 어느 매출처에 매출 몇 %를 의존하나?** (매출처 의존도 = 교섭력의 한 측면, Porter 5힘 — 현대모비스→기아 91.4%처럼, ★type=supplier 측 데이터. customer 측 ratio는 0건)
- **이 회사가 산업 분포의 어디에 서 있나?** (절대값이 아니라 백분위 — 마진/ROE/성장)
- **이 산업은 사이클 어디인가?** (surface 5-phase: 도입/성장/성숙/재도약/쇠퇴 — 이미 industryBadge.phase로 live, 단 산업별 정상성장률 차이는 한계)
- **이 산업이 어느 산업에 2-hop 노출됐나?** (공급망 전파 — "내 공급사의 공급사")

세계 제품은 이걸 컨센서스·추정·시장점유율 raw로 답한다 — 우리는 그 데이터가 없다. 그러나 **born-structured 격자(taxonomy/nodes/edges)와 공시인용 거래관계는 세계 제품이 추정으로 하는 일을 우리는 인용으로 한다.** 그게 차별이다.

---

## 3. 차별 명제 (한 문장)

> **세계 제품은 산업의 모양을 그려주고 멈춘다. DartLab은 같은 자산 위에서 "이 산업의 이익은 어느 공정 단계가 버나"를 born-structured 셀로 증명하고, 그 단계의 거래의존도를 공시인용 evidence로 보여준다 — 추정이 아니라 인용으로, 결손은 0으로 채우지 않고, 시장점유율이 없으면 "상장사 매출 기준"이라고 라벨하며, 등급을 단정하지 않는다.**

상세 killer 3종 = [02-differentiation-killer-features.md](02-differentiation-killer-features.md).

---

## 4. 제품 원칙 (정직 룰 전체 SSOT = [04 §3](04-data-readiness-kill-list.md))

1. **배선이 먼저, 신규가 다음.** 묻어둔 *함수*(HHI·hop2·summary·timeline)를 Industry verb·화면에 꽂는 게 1순위(lifecycle·recipe 층은 이미 live). 새 메커니즘은 그 위에 최소한으로.
2. **하나의 킬러.** profit-pool 격자 하나에 집중한다. Porter 5힘 전체를 점수표로 박지 않는다(정성 force를 가짜 정량으로 만드는 fake precision).
3. **추정 아닌 인용.** 공급망 evidence는 사업보고서 본문 추출. 추정 알고리즘·학술 권위 라벨(SPLC·Leontief 승수) 도입 금지.
4. **데이터 없으면 카드 없음.** 시장점유율·컨센서스·TAM·operational KPI·대체재·S-curve·platform KPI·Capital Cycle 순수CAPEX = 차단(04 문서).
5. **결손은 0 대체 금지.** opMargin 결손 노드 격자 제외 + coverageRatio, ratio 없는 엣지 굵기 균일.
6. **라벨 사칭 금지.** HHI→DOJ 독점라벨, moat→wide/narrow, hop2→IO 승수 단정 금지. 측정값만.
7. **경계 불가침.** peer N사 비교 = `compare()`, 횡단 스크리닝 = `scan`, 산업맵 전체뷰 = `/map`, 조합 = `story`(L3), Damodaran 자본효율 = `synth`·fin-stmt-lab. industry 패널은 이들을 재구현하지 않고 고유 4능력(공정 이익분포·edges amount/ratio·lifecycle phase·summary 집계)만.

---

## 5. 핵심 화면

| 화면 | 무엇 | 거처 |
|---|---|---|
| **Profit-pool 격자** | 공정 단계별 (매출규모 × 영업이익률) 2D. "돈 버는 단계"가 매출 큰 단계와 다름을 시각화 | 퍼블릭 `/industry/[id]` stage 섹션 축 확장(브라우저) + 로컬 CenterStack 인터랙티브 버블 |
| **공급망 evidence** | edges의 ratio(거래의존도%)·amount + confidence/source 칩. hop2 전파(count 기반) | 퍼블릭 `/industry/[id]` 공급망 섹션(이미 amount top20 有) + 로컬 RightStack hop walk |
| **산업 분포 밴드** | 회사값을 industryStats p10~p90 분포 위 마커로(읽기). compare로 funnel | 퍼블릭 `/industry/[id]` + 로컬(ecosystem pctRank 통일) |
| **회사 → 산업 점프** | industryBadge 클릭 → 산업뷰(밸류체인·lifecycle), 섹터 필터 클릭이 산업뷰도 띄움 | 로컬 nav(현재 `/map?focus=`로만 이탈) |

---

## 6. 범위·성공 기준 요약

- **범위**: Phase A(profit-pool) → B(공급망 evidence) → C(백분위 통일). 각 Phase는 선결조건순(05 문서). 위생 작업(유령 API 청소·edges.json 재빌드)은 해당 Phase 선결.
- **성공 기준**: "이 산업의 이익은 어느 단계가 버나"가 한 화면에서 답해진다 + 묻어둔 능력이 런타임에서 질의된다 + 백분위가 단일 정의로 수렴한다 + 모든 숫자가 정직 라벨(상장사 기준·coverageRatio·source/confidence)을 단다. **헤드라인 지표가 "세계 메커니즘 N종 구현"이면 이미 실패.**
- **비-목표**: Porter 5힘 종합 스코어카드, moat 등급, TAM/SAM/SOM, 시장점유율, operational KPI 대시보드, 컨센서스. (04·05 킬리스트)
