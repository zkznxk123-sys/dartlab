# 02. 차별의 핵 — killer features

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: ★이 PRD의 심장. 세계 제품이 답하지 못하는(또는 컨센서스/점유율 raw로만 답하는) 질문을 우리 자산으로 답하는 killer 3종. 각 가치 + 데이터 지원(file:line) + 가드레일.
정직 룰 SSOT는 [04 §3](04-data-readiness-kill-list.md) (본 문서는 killer별 *고유* 가드만).

> real upgrade vs reskin 테스트: *"이 능력이 우리가 이미 신뢰하는 데이터로, 전에 답 못하던 질문을 답하게 하나?"* 아니오면 기각.

---

## Killer #1 — Profit-pool 격자 ("이 산업에서 돈은 어느 단계가 버나") · Phase A

**질문**: 반도체 산업에서 매출이 가장 큰 공정 단계가 이익도 가장 큰가? (McKinsey의 통찰: 거의 항상 아니다 — 매출집중과 이익집중은 다른 단계에 있다.)

**세계 천장**: McKinsey/Bain은 이걸 컨설팅 deck으로 수작업한다. Bloomberg BI는 컨센서스로 추정한다. 회사별 사일로 제품(iTooza·Koyfin)은 *산업 전체를 한 격자로* 못 봐서 구조적으로 약하다.

**우리 우위**: born-structured 격자. `buildIndustrySummary`([financials.py:303-313](../../src/dartlab/industry/build/financials.py#L303))가 이미 stage별 `매출(조)`·`영업이익(조)`·`기업수`를 group_by(stage)로 산출한다. profit-pool 격자 = 여기에 **stage 영업이익률(= 영업이익 합 / 매출 합, revenue-weighted)**과 **coverageRatio**를 파생으로 더해 2D(x=매출규모, y=영업이익률)로 그리는 것. 신규 fetch·계정·컨센서스 0.

**학술 근거(prose만 — 정량 0)**: McKinsey Profit Pools(이익집중≠매출집중)에 더해 Slywotzky의 *Value Migration*(profit zone·"market share is dead")과 Christensen의 *이익 보존이동*(Conservation of Attractive Profits), BCG의 *Stack Fracturing/Deconstruction*(1998)이 born-structured 이익격자가 회사별 사일로 제품보다 우월한 이유의 학술 토대다. 단 이 인용은 *정적 통찰 강화*(SEO/AI 인용)용이며 **시간축 측정으로 끌면 [04 BLOCKED](04-data-readiness-kill-list.md)(migration) kill 회귀**.

**데이터 지원**:
- 엔진: `buildIndustrySummary` 출력에 `영업이익률(%)`(파생) + `coverageRatio`(opIncome 보유 노드 / 전체 노드) 2컬럼 추가. ★반환 첫 컬럼은 실명 `stage`(docstring `공정`은 오기 — 구현 시 KeyError 주의).
- 퍼블릭: `/industry/[id]`가 fetch하는 `/map/industries/{id}.json`의 `stages[].nodes[]`가 이미 `revenue`(2561노드 100%) + `opMargin`(82.4%) 보유 → **브라우저에서 stage 롤업 = 신규 fetch 0**. 현재 페이지는 산업 평균 영업이익률 스칼라 1개만 렌더([+page.svelte](../../landing/src/routes/industry/%5Bid%5D/+page.svelte)) — 2D cross 부재.
- 로컬: 같은 static JSON으로 CenterStack 인터랙티브 버블(호버=stage companyCount·coverageRatio).
- ★dual-source SSOT: 엔진 파생(panel `opIncome.sum()/revenue.sum()`)과 브라우저 롤업(prebuild JSON per-node `revenue×opMargin` Σ/Σ, opMargin 82.4% 커버리지)은 소스·커버리지가 달라 같은 stage 마진이 갈릴 수 있다 → **엔진 파생=캐논, 브라우저=표시만**, coverageRatio 분모도 경로별 고정 + 불일치 회귀테스트(상세 [03 §4](03-architecture-and-reuse.md)).
- ★집중도 3차원 인코딩 금지: "이익 큰 단계 = 집중/파편 단계인가"(Stack Fracturing)는 흥미롭지만 stage 버블에 집중도를 색/테두리 *3번째 차원*으로 얹는 것은 축 누적(가드레일 #4 위반) — 집중도는 Phase B/C의 라벨 뗀 CR4 evidence가 소유, Killer #1은 2D 유지.

**가드레일 (3게이트 — cosmetic 아닌 필수)**:
1. **revenue-weighted 롤업 강제.** stage opMargin은 단순평균 금지(소형사 극단 마진이 왜곡). `timeline`의 비가중 avgOpm을 그대로 빌리면 안 됨.
2. **coverageRatio 노출 + null 노드 격자 제외.** opMargin 18% 결손이 핵심 distortion. stage마다 "opMargin 보유 N/전체 M" 표기, 결손 노드는 0이 아니라 격자에서 빠짐.
3. **'listed-only' 라벨 + companyCount 동반 + 음수 풀 그대로.** 비상장 단계 결손 명시, 영업적자 stage는 음수 풀 깊이 그대로(fake smoothing 금지).
- **신규 패널 신설 금지** — 퍼블릭은 기존 stage 섹션 축 1개 확장, 로컬은 CenterStack 기존 시각화 zone. (적대렌즈가 "셀 1줄 변환을 새 패널로 부풀리는 것"을 migration kill의 이유로 지목.)

---

## Killer #2 — 공시인용 교섭력·공급망 전파 ("이 거래선에 매출 몇 %") · Phase B

**질문**: 이 공급사가 어느 *매출처*에 매출 몇 %를 의존하나(매출처 의존도)? 이 산업이 어느 산업에 2-hop 노출됐나?

**세계 천장**: Bloomberg SPLC·Interos는 100k사 공급망을 *추정 알고리즘*으로 엮는다. 우리는 규모는 발끝에도 못 미치지만 **추정이 아니라 사업보고서 「주요 매출처/매입처」 본문 인용**이다 — 현대모비스→기아 91.4%, 현대글로비스→기아 96.9%가 그 예. ★단 이 ratio들은 `type=supplier`·`source=docs_table`, 즉 *공급사가 신고한 매출처 의존도*다(구매자 교섭력의 한 측면이지 customer 측 데이터가 아님). `type=customer` 엣지는 7건 전원 `ratio=None`이라 인용할 구매자측 ratio는 0건 — 우리가 정직하게 답하는 건 "supplier 매출처 의존도"까지다.

**우리 우위**: edges.json이 ratio(매출처 의존도%, 전부 type=supplier 19건)·amount를 confidence/source와 함께 보유. `IndustryEdge` 객체는 amount/ratio를 들고 있는데 **`Industry.edges()` DataFrame이 두 컬럼을 select에서 누락**([__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359)) — 노출이 select 2줄 추가가 전부. 묻어둔 `computeHop2`([hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32))·`calcSupplyInsights`([insights.py:201](../../src/dartlab/industry/build/insights.py#L201)) *함수*를 런타임 인자로 배선(★단 산업 분석 *능력* 자체는 orphan 아님 — `recipes.industry.supplyChainConcentration`가 이미 RunPython으로 HHI 교섭력을 답한다, [03 §5.1](03-architecture-and-reuse.md)). 중복 신설 금지.

**데이터 지원**:
- 엔진: `Industry.edges()` DataFrame에 `의존도(%)`(ratio)·`거래액`(amount) 2컬럼 추가. `Industry().edges(hop=2, insights=True)` 인자 확장으로 hop2/다양성 노출(별 verb 금지). ★필드명: 디스크 edges.json은 `type`(supplier 3191·affiliate 12980·investor 2240·customer 7), in-memory `IndustryEdge`만 `edgeType`.
- 퍼블릭: `/industry/[id]` 공급망 섹션이 이미 amount top20 표시 → ratio %·confidence/source 칩 추가.
- 로컬: RightStack hop walk.

**가드레일 (★빈곤을 화면 1급시민으로 — 과대포장 한 번이면 확신오정렬)**:
1. **선결: edges.json 재빌드.** docstring precise 642 vs 실제 132·source 라벨(코드 panel_text/panel_table vs 디스크 docs/docs_table) 불일치 = 구버전 산출물. 재빌드 없이 surface하면 거짓 숫자. 별도 "정리: edges 재빌드" commit.
2. **커버리지 빈곤 노출**: amount 132/18,418(0.7%)·customer 7건·ratio 19개. affiliate 70.5% 압도 → supplier/customer 필터 강제. ratio 없는 엣지 0채움/굵기 균일.
3. **confidence/source 칩 의무**: docs_table(강한 단정)·network(출자)·docs(언급, 텍스트매칭 0.5~0.7 약). 2-hop은 confidence 곱셈 감쇠. ratio 캡션은 **"사업보고서 「주요 매출처/매입처」 공시 추출(supplier 의존도)"까지만** — US ASC 275 등 회계기준 권위 인용 금지(KR supplier 의존도에 갖다붙이면 규제척도 사칭). provenance 칩 자체가 "왜 추정 아닌 인용인가"를 정직히 수행한다.
4. **amount 단위 억원 + "추출 누락분 존재" 캡션.** amount-가중 전파는 비활성/명시(amount 132/3191=4.1%만, count 기반만 honest).
5. **인과·미래예측 프레이밍 금지.** static 다양성/hop만(scenario-simulator 경계).

> ⚠ 이 killer는 데이터 천장이 낮다(02 §빈곤). 임팩트가 작을 수 있고, 그게 정직한 평가다. "Bloomberg SPLC식"이라는 단어를 화면·문서에 쓰지 않는다.

---

## Killer #3 — 산업 분포 위 1점 읽기 + 백분위 통일 · Phase C

**질문**: 이 회사가 산업 분포의 어디인가? (그리고 — 지금 3갈래로 분기된 백분위 정의를 하나로.)

**문제**: 산업 컨텍스트가 3갈래다 — RightStack ecosystem pctRank([engine.ts:301-312](../../ui/packages/surfaces/src/terminal/lib/engine.ts#L301)) / compare panel 분포 / industryStats.json 분포. 유니버스가 달라 같은 "업종 백분위"가 화면마다 다른 값을 줄 수 있다. 부수적으로 engine.ts:312의 `점유율(Mkt share)` 메트릭은 `node.marketShare`(types.ts:120 옵셔널, 채우는 producer 없음)가 전무해 line 313 `.filter((m)=>m.p!=null)`에서 드롭 → **절대 렌더 안 되는 inert dead 컬럼**이다(현재 user harm 0, 미래 활성화 대비 선제 청소 가치만 — "노출 중 정직버그"가 아니라 inert dead code 제거).

**우리 우위**: industryStats.json이 34산업 roe/opMargin/revCagr 각각 p10/p25/median/p75/p90/mean/std/n 분포를 이미 보유(monotone 확인). `/industry/[id]`의 [+page.ts](../../landing/src/routes/industry/%5Bid%5D/+page.ts)가 이미 fetch하나 avgRoe/avgOpMargin/avgCagr만 렌더 — 분포 미사용. **신규 분포 계산 0, 표시층 통일.**

**데이터 지원**:
- 퍼블릭: 회사값을 industryStats p10~p90 밴드 위 마커로(읽기). compare로 funnel 링크.
- 로컬: engine.ts industryPercentile를 industryStats 분포로 통일(또는 정의 일치) + `점유율` 컬럼 제거.

**가드레일 (4선결)**:
1. **percentile band만** — mean±std 박스 금지(std가 roe 86.44·opMargin 34.71 heavy outlier까지 = fake precision). mean 마커도 밴드 밖 자주 벗어나므로 percentile만.
2. **n<10 *분포(metric)* 숨김 + "n=N" 노출.** (industryStats는 산업당 metric별 roe/opMargin/revCagr 독립 distribution이고 각자 n을 가짐 — 산업 단위 아님.)
3. **'분포출처=industryStats(KSIC섹터·동일가중·상장 primary사, n=N) ≠ KRX 시총가중 업종지수' 라벨 + inert `marketShare` 컬럼 선제 제거**(engine.ts:312). 공식 업종지표는 외부 link-only(미러·reconcile 금지, [04 §3 #8](04-data-readiness-kill-list.md)).
4. **SSOT 경계 명문화 선결**: industry = 섹터 분포 위 1점 읽기/깔때기, compare + financial-statement-lab = 큐레이션 peer 정밀 SSOT. 이 경계를 mainPlan 문서로 박기 전 코딩 금지(fin-stmt-lab PRD와 충돌이 아니라 de-risk).

> 적대렌즈가 "또 하나의 백분위 패널 신설"을 kill했다. 이 killer가 생존한 유일한 이유는 **신규 계산이 아니라 표시층 통일 + inert dead 정리**이기 때문. 새 백분위 엔진을 만들면 그 순간 kill 대상으로 회귀한다.

---

## 세 killer의 합

A(이익은 어디서 버나) → B(그 단계의 거래의존도) → C(그 회사가 분포 어디인가)는 한 내러티브로 이어진다. 그러나 **동시에 짓지 않는다** — A는 선결 없는 깨끗한 킬러, B는 edges 재빌드 선결·천장 낮음, C는 경계 문서화 선결. 순서 = [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md).
