# 산업 분석 심화 랩 (Industry Analysis Lab) PRD Index

상태: 비전 PRD v0.1 (2026-06-14, 전문 에이전트 4 lens 조사·설계·적대검증 후 작성)
범위: industry 엔진(L2) + 퍼블릭 터미널(landing) + 로컬 터미널(ui/packages/surfaces) 의 산업 분석 능력을 세계 수준으로 끌어올린다. 세계 프레임워크(Porter Five Forces · McKinsey Profit Pools · Industry Life Cycle)와 제품(Bloomberg Intelligence · Morningstar Moat · GICS/RBICS · Bloomberg SPLC)을 **그대로 복제하지 않고**, DartLab 고유 자산(taxonomy/nodes/edges born-structured 격자 · 공시인용 거래관계 · panel 분포)으로 흡수해 "한 단계 위"의 산업 분석을 만든다.

---

## 한 줄 결정

이 업그레이드의 출발점은 코드실측이 깬 전제다 — **industry 엔진은 "약한" 게 아니라 "만들어 묻어둔" 엔진이다.** HHI·CR3·2-hop 공급망·공급다양성([build/insights.py](../../src/dartlab/industry/build/insights.py)·[build/hop2.py](../../src/dartlab/industry/build/hop2.py))은 live·정확한데 **빌드 산출물(JSON)에만 baked되고 런타임 질의로 못 꺼낸다.** `summary`(공정별 이익집계)·`timeline`·`lifecycle`(Vernon phase) 3대 능력은 **어느 화면에도 안 뜬다.** 퍼블릭 `/industry/[id]`는 라이브 엔진이 아니라 사전빌드 static JSON만 렌더하고, 로컬 터미널은 진짜 industry 엔진을 아예 소비하지 않는다.

> 따라서 목표는 "세계 메커니즘 무더기 추가"가 **아니다.** 1순위는 *이미 만든 능력을 런타임·터미널에 배선하고, 정직 라벨을 붙이고, 분기된 경계를 통일하는 것*이다. 강함은 쌓아서가 아니라 깎아서.

핵심 명제: **세계 제품은 "이 산업의 모양"을 그려주고 멈춘다. DartLab은 같은 자산 위에서 못 풀던 한 질문을 답한다 — "이 산업에서 *돈은 어느 단계가 버나*"(매출 큰 단계가 아니다, McKinsey profit pool). 그리고 그 답은 추정 알고리즘이 아니라 공시로 역추적되고(공급망 ratio/amount는 인용이지 추정이 아니다), 결손은 0으로 채우지 않으며, 시장점유율 raw가 없으면 "상장사 매출 기준"이라고 정직하게 라벨한다.**

---

## 핵심 결정 요약 (4 lens 토론 수렴 + 적대검증 후)

- **거처 = 기존 industry 엔진 + 양 터미널 surface 확장.** 새 엔진·새 verb·새 패널 더미 금지. 엔진은 `src/dartlab/industry/`(`buildIndustrySummary`·`Industry.edges()`·`computeHop2`/`calcSupplyInsights`)를 EXTEND, 퍼블릭은 `landing /industry/[id]`의 기존 stage/공급망 섹션을 EXTEND, 로컬은 `ui/packages/surfaces/terminal`의 CenterStack(시각화)·RightStack(테이블) 슬롯에 배선. 상세 = [03-architecture-and-reuse.md](03-architecture-and-reuse.md).
- **차별의 핵 = profit-pool 격자 + 공시인용 공급망 evidence.** "공정별 매출규모 × 영업이익률" 2D 격자로 *이익집중 ≠ 매출집중*을 우리만의 born-structured 셀로 증명한다(세계 제품은 회사별 사일로라 구조적으로 약하거나 컨센서스 의존). 그 위에 edges의 ratio(거래의존도=교섭력)·amount가 공시인용 evidence로 얹힌다. 상세 = [02-differentiation-killer-features.md](02-differentiation-killer-features.md).
- **3단계 = A(profit-pool) → B(공급망 evidence) → C(백분위 통일).** A는 선결 없는 깨끗한 킬러(신규 데이터 0), B는 edges.json 재빌드가 선결(현재 stale)·데이터 천장이 낮음, C는 백분위 SSOT 경계 문서화가 선결·표시층 통일로만(새 백분위 엔진 금지). 순서·게이트 상세 = [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md).
- **데이터 없으면 카드 없음.** 시장점유율 raw(없음)·애널리스트 컨센서스(EXCLUDED)·TAM/SAM/SOM(상장사 매출합은 체계적 과소)·operational KPI(ASM/SSS 등 비재무 표준 미보유)·대체재 교차탄력성(산업 외부 도메인)은 차단. HHI는 DOJ 독점/경쟁 라벨 단정 금지(시장점유율 사칭) — 라벨 뗀 CR4/top1 비중 + "상장사 매출 기준" 캡션만 조건부. 상세 = [04-data-readiness-kill-list.md](04-data-readiness-kill-list.md).
- **위생 작업 동반.** README가 광고하는 `sectorMomentumLeadership`·`concentration.py`·`peerMatrix.py`·`map.py`는 **구현 0인 유령 API**인데 scan/README·skills `*.json` 카탈로그까지 전파됐다. edges.json은 stale(docstring precise 642 vs 실제 132·source 라벨 불일치). 이 둘은 본 작업의 선결 위생 commit으로 정리한다.
- **착수 = 운영자 go.** Phase A(브라우저 전용 + 엔진 파생 컬럼, 신규 데이터 0)는 다른 mainPlan과 무관하게 선행 가능. 상세 = [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md).

---

## 문서 지도

1. [00-product-prd.md](00-product-prd.md) — 판정, 제품 비전(산업 분석가의 질문), "묻어둔 엔진" 재구성, 차별 명제, 제품 원칙, 핵심 화면, 범위·성공기준.
2. [01-reference-teardown.md](01-reference-teardown.md) — 세계 메커니즘 11종(Porter·Profit Pools·HHI·Life Cycle·SCP) + 제품(Bloomberg BI·Morningstar Moat·GICS/RBICS·SPLC) teardown. 우리가 이미 가진 것 / 묻어둔 것 / 못하는 것. TAKE·REJECT·DEFER.
3. [02-differentiation-killer-features.md](02-differentiation-killer-features.md) — ★차별의 핵. 산업 분석가의 실제 질문, 세계 제품의 천장, killer 3종(profit-pool 격자·공시인용 교섭력/공급망 전파·산업 분포 위 1점 읽기) 각 가치+데이터지원+가드레일.
4. [03-architecture-and-reuse.md](03-architecture-and-reuse.md) — 자산 인벤토리 판정(REUSE/EXTEND/NEW), 거처(engine·public·local), 코드 touchpoint(file:line), 경계(compare/scan/map/story), orphan 능력 배선, stale 정리.
5. [04-data-readiness-kill-list.md](04-data-readiness-kill-list.md) — 데이터 가용성 매트릭스, EXCLUDED/BLOCKED/CONDITIONAL 킬리스트, edges.json stale·amount 0.7% 빈곤·시장점유율 부재 honest-gap 규칙.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — MUST/SHOULD/WON'T 단두대, Phase A→B→C(선결조건순), honesty 가드레일, 성공지표·실패모드·단일 최대 리스크.
7. [06-progress-ledger.md](06-progress-ledger.md) — 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터.

---

## 정직 척추 (전 문서 관통)

1. **클론 아님.** 세계 메커니즘 매칭 개수가 성공지표면 이미 실패. 목표는 *못 풀던 질문 1개*(이익은 어느 단계가 버나)지 Porter 5힘 점수표·Bloomberg 화면 재현이 아니다.
2. **배선 우선 > 신규.** 1순위는 묻어둔 능력(HHI·hop2·summary·timeline·lifecycle)을 런타임·화면에 *꽂는 것*. 새 메커니즘은 그 다음.
3. **데이터 없으면 카드 없음.** 시장점유율·컨센서스·TAM·operational KPI·대체재 = 차단. "나중에 Phase N"으로 흐리지 말고 EXCLUDED/BLOCKED로 박는다.
4. **결손은 0 대체 금지.** opMargin 결손 노드는 격자 제외 + coverageRatio 노출, ratio 없는 엣지는 굵기 균일·0채움 금지. missing/blocked/partial 라벨.
5. **추정 아닌 인용.** 공급망 ratio/amount는 사업보고서 본문 추출(공시인용)이지 추정 알고리즘 아님 — 그러나 커버리지 빈곤(amount 0.7%)을 "Bloomberg SPLC식"으로 과대포장하면 확신오정렬. 빈곤을 화면 1급시민으로.
6. **라벨 사칭 금지.** HHI를 DOJ 독점/경쟁 라벨로, moat를 wide/narrow로 단정 금지. 측정값(CR4 비중·ROIC-WACC 스프레드 지속성)은 OK, 등급 단정은 금지.
7. **본진 0줄(검증 전).** Python 의존 신규 능력은 `tests/_attempts/industryAnalysisLab/` 졸업 게이트(개념확립→모듈화→데모→덕지덕지제거→클린코드→docstring) 후에만 `src/dartlab`. 브라우저 계산·기존 함수 파생 컬럼은 EXTEND.
