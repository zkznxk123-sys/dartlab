# 02. 차별의 핵 — killer features

상태: 비전 PRD v0.1 (2026-06-14)
목적: ★이 PRD의 심장. 세계 제품이 답하지 못하는(또는 컨센서스/점유율 raw로만 답하는) 질문을 우리 자산으로 답하는 killer 3종. 각 가치 + 데이터 지원(file:line) + 가드레일.

> real upgrade vs reskin 테스트: *"이 능력이 우리가 이미 신뢰하는 데이터로, 전에 답 못하던 질문을 답하게 하나?"* 아니오면 기각.

---

## Killer #1 — Profit-pool 격자 ("이 산업에서 돈은 어느 단계가 버나") · Phase A

**질문**: 반도체 산업에서 매출이 가장 큰 공정 단계가 이익도 가장 큰가? (McKinsey의 통찰: 거의 항상 아니다 — 매출집중과 이익집중은 다른 단계에 있다.)

**세계 천장**: McKinsey/Bain은 이걸 컨설팅 deck으로 수작업한다. Bloomberg BI는 컨센서스로 추정한다. 회사별 사일로 제품(iTooza·Koyfin)은 *산업 전체를 한 격자로* 못 봐서 구조적으로 약하다.

**우리 우위**: born-structured 격자. `buildIndustrySummary`([financials.py:303-313](../../src/dartlab/industry/build/financials.py#L303))가 이미 stage별 `매출(조)`·`영업이익(조)`·`기업수`를 group_by(stage)로 산출한다. profit-pool 격자 = 여기에 **stage 영업이익률(= 영업이익 합 / 매출 합, revenue-weighted)**과 **coverageRatio**를 파생으로 더해 2D(x=매출규모, y=영업이익률)로 그리는 것. 신규 fetch·계정·컨센서스 0.

**데이터 지원**:
- 엔진: `buildIndustrySummary` 출력에 `영업이익률(%)`(파생) + `coverageRatio`(opIncome 보유 노드 / 전체 노드) 2컬럼 추가.
- 퍼블릭: `/industry/[id]`가 fetch하는 `/map/industries/{id}.json`의 `stages[].nodes[]`가 이미 `revenue`(2561노드 100%) + `opMargin`(82.4%) 보유 → **브라우저에서 stage 롤업 = 신규 fetch 0**. 현재 페이지는 산업 평균 영업이익률 스칼라 1개만 렌더([+page.svelte](../../landing/src/routes/industry/%5Bid%5D/+page.svelte)) — 2D cross 부재.
- 로컬: 같은 static JSON으로 CenterStack 인터랙티브 버블(호버=stage companyCount·coverageRatio).

**가드레일 (3게이트 — cosmetic 아닌 필수)**:
1. **revenue-weighted 롤업 강제.** stage opMargin은 단순평균 금지(소형사 극단 마진이 왜곡). `timeline`의 비가중 avgOpm을 그대로 빌리면 안 됨.
2. **coverageRatio 노출 + null 노드 격자 제외.** opMargin 18% 결손이 핵심 distortion. stage마다 "opMargin 보유 N/전체 M" 표기, 결손 노드는 0이 아니라 격자에서 빠짐.
3. **'listed-only' 라벨 + companyCount 동반 + 음수 풀 그대로.** 비상장 단계 결손 명시, 영업적자 stage는 음수 풀 깊이 그대로(fake smoothing 금지).
- **신규 패널 신설 금지** — 퍼블릭은 기존 stage 섹션 축 1개 확장, 로컬은 CenterStack 기존 시각화 zone. (적대렌즈가 "셀 1줄 변환을 새 패널로 부풀리는 것"을 migration kill의 이유로 지목.)

---

## Killer #2 — 공시인용 교섭력·공급망 전파 ("이 거래선에 매출 몇 %") · Phase B

**질문**: 이 회사는 어느 고객에 매출 몇 %를 의존하나(구매자 교섭력)? 이 산업이 어느 산업에 2-hop 노출됐나?

**세계 천장**: Bloomberg SPLC·Interos는 100k사 공급망을 *추정 알고리즘*으로 엮는다. 우리는 규모는 발끝에도 못 미치지만 **추정이 아니라 사업보고서 본문 인용**이다 — 현대모비스→기아 91.4%, 현대글로비스→기아 96.9%는 공시에서 나온 실측 ratio다.

**우리 우위**: edges.json이 ratio(거래의존도%)·amount를 confidence/source와 함께 보유. `IndustryEdge` 객체는 amount/ratio를 들고 있는데 **`Industry.edges()` DataFrame이 두 컬럼을 select에서 누락**([__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359)) — 노출이 select 2줄 추가가 전부. 묻어둔 `computeHop2`([hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32))·`calcSupplyInsights`([insights.py:201](../../src/dartlab/industry/build/insights.py#L201))를 런타임 인자로 배선.

**데이터 지원**:
- 엔진: `Industry.edges()` DataFrame에 `의존도(%)`(ratio)·`거래액`(amount) 2컬럼 추가. `Industry().edges(hop=2, insights=True)` 인자 확장으로 hop2/다양성 노출(별 verb 금지).
- 퍼블릭: `/industry/[id]` 공급망 섹션이 이미 amount top20 표시 → ratio %·confidence/source 칩 추가.
- 로컬: RightStack hop walk.

**가드레일 (★빈곤을 화면 1급시민으로 — 과대포장 한 번이면 확신오정렬)**:
1. **선결: edges.json 재빌드.** docstring precise 642 vs 실제 132·source 라벨(코드 panel_text/panel_table vs 디스크 docs/docs_table) 불일치 = 구버전 산출물. 재빌드 없이 surface하면 거짓 숫자. 별도 "정리: edges 재빌드" commit.
2. **커버리지 빈곤 노출**: amount 132/18,418(0.7%)·customer 7건·ratio 19개. affiliate 70.5% 압도 → supplier/customer 필터 강제. ratio 없는 엣지 0채움/굵기 균일.
3. **confidence/source 칩 의무**: docs_table(강한 단정)·network(출자)·docs(언급, 텍스트매칭 0.5~0.7 약). 2-hop은 confidence 곱셈 감쇠.
4. **amount 단위 억원 + "추출 누락분 존재" 캡션.** amount-가중 전파는 비활성/명시(amount 132/3191=4.1%만, count 기반만 honest).
5. **인과·미래예측 프레이밍 금지.** static 다양성/hop만(scenario-simulator 경계).

> ⚠ 이 killer는 데이터 천장이 낮다(02 §빈곤). 임팩트가 작을 수 있고, 그게 정직한 평가다. "Bloomberg SPLC식"이라는 단어를 화면·문서에 쓰지 않는다.

---

## Killer #3 — 산업 분포 위 1점 읽기 + 백분위 통일 · Phase C

**질문**: 이 회사가 산업 분포의 어디인가? (그리고 — 지금 3갈래로 분기된 백분위 정의를 하나로.)

**문제**: 산업 컨텍스트가 3갈래다 — RightStack ecosystem pctRank([engine.ts:301-312](../../ui/packages/surfaces/src/terminal/lib/engine.ts#L301)) / compare panel 분포 / industryStats.json 분포. 유니버스가 달라 같은 "업종 백분위"가 화면마다 다른 값을 줄 수 있다. 게다가 engine.ts:311이 `점유율(Mkt share)`을 `node.marketShare`로 pctRank 노출 중인데 **시장점유율 raw가 없어 이건 기존 정직 버그**다.

**우리 우위**: industryStats.json이 34산업 roe/opMargin/revCagr 각각 p10/p25/median/p75/p90/mean/std/n 분포를 이미 보유(monotone 확인). `/industry/[id]`의 [+page.ts](../../landing/src/routes/industry/%5Bid%5D/+page.ts)가 이미 fetch하나 avgRoe/avgOpMargin/avgCagr만 렌더 — 분포 미사용. **신규 분포 계산 0, 표시층 통일.**

**데이터 지원**:
- 퍼블릭: 회사값을 industryStats p10~p90 밴드 위 마커로(읽기). compare로 funnel 링크.
- 로컬: engine.ts industryPercentile를 industryStats 분포로 통일(또는 정의 일치) + `점유율` 컬럼 제거.

**가드레일 (4선결)**:
1. **percentile band만** — mean±std 박스 금지(std가 roe 86.44·opMargin 34.71까지 = fake precision).
2. **n<10 산업 숨김 + "n=N" 노출.**
3. **'분포출처=industryStats(KSIC섹터 전체, n=N)' 라벨 + `marketShare` 컬럼 제거**(engine.ts:311 정직 버그 정리).
4. **SSOT 경계 명문화 선결**: industry = 섹터 분포 위 1점 읽기/깔때기, compare + financial-statement-lab = 큐레이션 peer 정밀 SSOT. 이 경계를 mainPlan 문서로 박기 전 코딩 금지(fin-stmt-lab PRD와 충돌이 아니라 de-risk).

> 적대렌즈가 "또 하나의 백분위 패널 신설"을 kill했다. 이 killer가 생존한 유일한 이유는 **신규 계산이 아니라 표시층 통일 + 정직 버그 정리**이기 때문. 새 백분위 엔진을 만들면 그 순간 kill 대상으로 회귀한다.

---

## 세 killer의 합

A(이익은 어디서 버나) → B(그 단계의 거래의존도) → C(그 회사가 분포 어디인가)는 한 내러티브로 이어진다. 그러나 **동시에 짓지 않는다** — A는 선결 없는 깨끗한 킬러, B는 edges 재빌드 선결·천장 낮음, C는 경계 문서화 선결. 순서 = [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md).
