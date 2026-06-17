# 05. 범위·단계·가드레일

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: 적대검증(skeptic PM lens)을 박제한다. MUST/SHOULD/WON'T 단두대, 선결조건순 Phase A→B→C, 성공지표·실패모드·단일 최대 리스크. (정직 룰 SSOT는 [04 §3](04-data-readiness-kill-list.md) — 본 §5는 *Phase 적용 가드* 고유분만.)

---

## 1. "안 해도 되는가" — steelman과 생존 조건

**반론(steelman)**: industry 엔진은 이미 lifecycle·summary·edges·HHI·hop2를 다 가졌다. "강화"는 대부분 *이미 있는 걸 화면에 꺼내는 배선*이지 새 능력이 아니다. 한계 노력은 데이터가 진짜 빈약한 곳(세그먼트 2/10·가동률 미추출·익명 매출처)을 메우는 데 가야 한다. (★공급망 amount 0.7%는 "진짜 빈약"이 아니라 *추출 천장* — [_attempts 레버A](../../tests/_attempts/industryAnalysisLab/README.md)로 제조업 한정 7.9x 상향 확인, 보강 ROI 있음.) profit-pool도 "셀 1줄 변환"으로 보이면 덕지덕지다.

**생존 조건**: 이 업그레이드는 *세계 메커니즘 매칭*이 아니라 **(a) 못 풀던 질문 1개를 답하거나 (b) 묻어둔 함수를 배선하거나 (c) 분기 통일·inert dead 정리를 하는 곳**에서만 산다.
- (a) profit-pool 격자 = 회사별 사일로 제품이 구조적으로 못 푸는 "이익은 어느 단계가 버나". 신규 데이터 0이라 싸고, born-structured 격자라 우리만.
- (b) hop2·summary·HHI/CR4 *함수*를 Industry verb DataFrame·화면에 꺼내는 배선 + summary/timeline 화면 노출 = "함수는 만들고 화면엔 안 꺼낸 부채" 상환. (★lifecycle은 industryBadge.phase로 이미 런타임 자동 부착·live이라 "화면 노출"만 — orphan 아님. recipe 층 8 curated도 이미 RunPython 런타임 분석 제공 → 중복 신설 금지, [03 §5.1](03-architecture-and-reuse.md).)
- (c) 백분위 경계 통일(★실측 정정: "3분기 분기"가 아니라 단일 pctRank+모집단 파라미터화, cross-universe-percentile이 이미 통일 — [07 §구멍5](07-implementation-plan.md)) + `marketShare` 정직 재라벨(전 소비처 '점유율'→'상장사매출비중', 키·metric·preset 보존 — 로컬 100만 값 제거. "inert dead·producer 전무"·"표시 제거"는 사실오류 — [07 §구멍5](07-implementation-plan.md) 토론 정정) = 회귀 차단.

이게 없으면 "세계 제품 흉내"라 안 하느니만 못하다.

---

## 2. 클론 트랩 — parity-as-spec 금지

"Porter/Bloomberg 추가"가 feature-pile이 되는 순간 = PRD가 *답할 질문*이 아니라 *매칭할 프레임워크*를 나열할 때. Porter 5힘을 5점수표로, Bloomberg BI 1200 KPI를 격자로 타겟하면 그들의 덕지덕지(또는 우리에게 없는 컨센서스 의존)를 통째 수입한 것.

**real upgrade vs reskin 테스트**: *"우리가 이미 신뢰하는 데이터로 전에 답 못하던 질문을 답하나?"* 아니오("같은 산업 모양 더 예쁘게"·"세계 제품 스크린샷 매칭") → 기각. 2차: **30일 후 제거하면 항의 나오나?**

**vanity(좋아보이나 저사용/위험)**: Porter 5힘 종합 점수 · moat 등급 배지 · HHI 독점 라벨 · TAM 숫자 · operational KPI 대시보드 · "또 하나의" 백분위 패널.

---

## 3. 범위 단두대 (MUST / SHOULD / WON'T)

### MUST (작고 진짜인 것 — 먼저)
1. **profit-pool 격자(Phase A)**: `buildIndustrySummary` 파생 2컬럼 + 퍼블릭 stage 섹션 2D + 로컬 CenterStack 버블. revenue-weighted·coverageRatio·listed-only 3게이트.
2. **stale 정리(선결 위생)**: 유령 API 청소(README 재작성 + 카탈로그 정리) + edges.json 재빌드.
3. **`marketShare` 표시 컬럼 선제 제거**(표시층 한정 CenterStack.svelte:194/198·ScreenerModal.svelte:42, `EcoNode.marketShare` 필드는 types.ts:120 보존 — landing map:236·compare:82 공유. engine.ts에선 이미 제거됨. Phase C 일부·단독 가치 — ★사유는 "producer 전무 청소"[사실오류]가 아니라 *라벨 사칭(buildIndustryMap.py:816/868 상장사 상대비중을 "점유율"로) + 로컬 marketShare:100 날조(localTerminalData.ts:348) 시정*, [07 §구멍5](07-implementation-plan.md)).

### SHOULD (MUST 후 — 데이터 천장 인지하고)
4. **공급망 evidence(Phase B)**: `Industry.edges()` ratio/amount 2컬럼 + hop2/insights 인자 배선 + confidence/source 칩. edges.json 재빌드 선결. *천장은 "낮음"이 아니라 "제조업 한정·추출 보강 여지"* — [_attempts 레버A](../../tests/_attempts/industryAnalysisLab/README.md) 실측: amount 0.7%는 상장필터 드롭+취약헤더 인공물, buyer-centric 미드롭으로 amount 행 7.9x. 단 원재료 매입처 표 보유사 ~21%(제조업 편중)는 진짜 잔존천장.
5. **백분위 경계(Phase C)**: industryStats 분포 밴드. SSOT 경계 문서화 선결. ★산식은 이미 단일(pctRank+모집단)이라 "통일" 작업은 대부분 문서. compare는 percentile 토큰 0건(셀 정렬)이라 백분위 항목서 분리 → fin-stmt-lab/compare 교차참조로만([07 §구멍5](07-implementation-plan.md)).
6. **회사→산업 점프**: industryBadge/섹터필터 클릭이 산업뷰 띄움(`/map` 이탈 해소).

### WON'T (본 PRD, 기록)
- 시장점유율·컨센서스·TAM/SAM/SOM·operational KPI(소스 부재 — 영구).
- Porter 5힘 종합 스코어카드·moat wide/narrow 라벨·HHI DOJ 독점라벨·진입장벽 점수(정직성 위반).
- profit-pool 이동 시계열(migration — 코호트 노이즈 확신오정렬).
- 대체재 정량화·driver DAG(scenario-simulator 소유)·peer N사 비교 재구현(compare 소유).
- 가동률·세그먼트·US 산업(데이터 추출 선결 — 별도 게이트).
- Capital Cycle 순수 CAPEX 비율(KR ICF 분리불가)·Damodaran 산업 sales-to-capital 분포(damodaranL15 OWNED-ELSEWHERE)·DOL cross-section 본문 승격(신규 회귀=덕지덕지, Phase D ledger 후보로만)·GE 9-box/7 Powers 종합점수(vanity)·iTooza ROE&PBR 가격축(compare 재탕)·Leontief 승수 명명(라벨 사칭). 상세 [01 §4](01-reference-teardown.md).

---

## 4. 선결조건순 Phase

- **Phase 0 — 비전 문서화(현재).** 본 PRD. 메모리엔 경로만.
- **Phase A — profit-pool(선결 없음, 신규 데이터 0).** ① 위생 commit(유령 API 청소). ② `buildIndustrySummary` 파생 컬럼(영업이익률·coverageRatio). ③ 퍼블릭 `/industry/[id]` stage 2D 격자(브라우저 롤업). ④ 로컬 CenterStack 버블. 즉시 출시·사용 관측. 다른 mainPlan과 무관하게 선행 가능.
- **Phase B — 공급망 evidence(추출 보강 + edges.json 재빌드 선결).** ① **레버 A — `extractRawMaterialEdges` 추출 보강**: (a) 비상장 매입처 미드롭 → buyer별 leaf supply fact + 공급집중도(HHI/CR3, `calcHHI`는 이미 상장무관) (b) 헤더 퍼지화(`매입액`/`비중` exact → `주요매입처`/`비율`/`제NN기매입액(비율)`/합쳐진셀 대응). _attempts 졸업 게이트 후 본진(테스트 동행·edges.json 재빌드). ② `Industry.edges()` ratio/amount 컬럼 + hop=2/insights 인자. ③ 퍼블릭 공급망 섹션 ratio/confidence 칩 + "제조업 매입집중도, 상장사 그래프 아님" 라벨. ④ 로컬 RightStack hop walk. ⑤ **레버 C(선택)** — 매출처 표 동일 기계 재사용으로 customer ratio 채움. *제조업은 두껍게, 비제조업(표 부재)은 honest-gap으로 1급시민.*
- **Phase C — 백분위 경계 문서화(산식은 이미 단일).** ① 백분위 SSOT 경계를 본 PRD/엔진 SKILL.md에 확정(industry=섹터분포 / compare+fin-stmt-lab=peer 정밀) + band 소스 이원화(public industryStats prebuilt / local quantileBand 라이브)는 의도된 설계로 박제. ② `marketShare` 표시 제거(표시층 한정 CenterStack.svelte·ScreenerModal.svelte, EcoNode 필드 보존) — 제거 전 ecosystem.json·routeLoad.ts:46·landing map/compare 미회귀 1회 실측. ③ 퍼블릭 industryStats 분포 밴드(compare는 교차참조로만 분리). ④ 회사→산업 점프. 상세 [07 §구멍5](07-implementation-plan.md).
- **Phase D — 차단(착수 금지·재방문 게이트).** 적응형 lifecycle 임계(`_attempts` 졸업) · 가동률 셀 추출 · 세그먼트 · US 산업.

각 Phase는 *이미 가진 데이터*로 출시하고 막힌 것을 *연기*한다. "세계 메커니즘 N종"이 아니라 "못 풀던 질문 1개 + 묻어둔 능력 배선 + 정직 라벨"이 합격선.

---

## 5. honesty / credibility 가드레일

★**정직 룰 전체 SSOT = [04 §3 honest-gap 규칙](04-data-readiness-kill-list.md)**(결손 0금지·빈곤 1급시민·라벨 사칭 금지·분포≠공식지수·산업집계≠migration 등 9항). 여기 중복 박제하지 않는다(동기화 부채 방지). 본 §5는 *Phase 적용* 고유 가드만:

1. **자동 verdict 금지.** profit-pool 격자는 "이 단계가 이익을 가장 많이 번다"(사실)는 OK, "이 산업은 좋다/매력적이다"(판정) 금지.
2. **경계 인용(중복 구현 금지).** valuation/moat 측정값은 financial-statement-lab, driver/시뮬은 scenario-simulator, peer N사=compare, 횡단=scan으로 교차참조.
3. **백테스트 게이트.** lifecycle/사이클/수익률 예측 주장은 `quant.walkForward`가 backtest SSOT — 본 PRD 산출물은 advisory·관측 서술까지만.

---

## 6. 성공 지표 · 실패 모드 · 단일 최대 리스크

**성공 지표**: "이 산업의 이익은 어느 단계가 버나"가 한 화면에서 답해진다 + 묻어둔 *함수*(hop2·summary·CR4)가 Industry verb·화면으로 나온다 + 백분위가 단일 정의로 수렴한다 + 모든 숫자가 정직 라벨(상장사 기준·coverageRatio·source/confidence). 헤드라인 지표가 "세계 메커니즘 구현 개수"면 이미 실패.

**실패 모드**: 세계 제품 parity를 짓다가 born-structured 격자의 진짜 차별(profit-pool)이 Porter 5힘 점수표·HHI 독점라벨·가짜 TAM 같은 *우리에게 없는 데이터의 흉내* 더미에 희석되고, 정직성을 깎아 신뢰를 잃는다 — 사용자가 옮겨오는 이유는 *세계 제품이 추정으로 하는 걸 우리가 인용으로 하기 때문*이지 그들 화면 재현이 아니므로.

**단일 최대 리스크 / 반드시 맞출 것**: **profit-pool 하나를 깨끗이(신규 패널 금지·3게이트) 박고, 나머지는 "신규 메커니즘"이 아니라 "묻어둔 함수 배선 + 분기 통일 + inert dead 정리"로 프레임한다.** 승리 조건 = *못 풀던 질문 1개를 born-structured로 답하고, 없는 데이터는 EXCLUDED로 박는다.* 강함은 빼기에서.

---

## 7. _attempts 졸업 게이트 적용

Python 의존 신규 계산(적응형 lifecycle 임계·가동률 셀 추출·세그먼트·Capital Cycle 자산증가율·DOL cross-section·Damodaran reinvestment 산업분포)은 `tests/_attempts/industryAnalysisLab/`에서 ① 카테고리 ② 개념확립(데모 실측) ③ 모듈화 ④ 데모(docstring+README) ⑤ 덕지덕지 제거 ⑥ 클린코드 ⑦ 9섹션 docstring **확정 후** ⑧ 본진. 검증 전 `src/` 직행 금지. ★industry build가 `buildIndustrySummary(year=)` 단일·`_extractYearly` 단일연도 snapshot이라 *다년 확장 자체가 신규 계산 = Phase A EXTEND 아님*. **착수 전 recipes.industry(peerCapexWave·marginCompressionScan 등)와 중복 여부 확인 의무.** Phase A/B/C의 EXTEND(파생 컬럼·select 추가·표시층)는 기존 함수·화면 확장이라 본진 무관 — 단, edges.json 재빌드·유령 verb 청소·calcs/concentration.py 승격은 회귀 가드(테스트 동행) 필수.
