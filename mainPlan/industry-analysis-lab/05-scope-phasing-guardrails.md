# 05. 범위·단계·가드레일

상태: 비전 PRD v0.1 (2026-06-14)
목적: 적대검증(skeptic PM lens)을 박제한다. MUST/SHOULD/WON'T 단두대, 선결조건순 Phase A→B→C, honesty 가드레일, 성공지표·실패모드·단일 최대 리스크.

---

## 1. "안 해도 되는가" — steelman과 생존 조건

**반론(steelman)**: industry 엔진은 이미 lifecycle·summary·edges·HHI·hop2를 다 가졌다. "강화"는 대부분 *이미 있는 걸 화면에 꺼내는 배선*이지 새 능력이 아니다. 한계 노력은 데이터가 진짜 빈약한 곳(공급망 amount 0.7%·세그먼트 2/10·가동률 미추출)을 메우는 데 가야 한다. profit-pool도 "셀 1줄 변환"으로 보이면 덕지덕지다.

**생존 조건**: 이 업그레이드는 *세계 메커니즘 매칭*이 아니라 **(a) 못 풀던 질문 1개를 답하거나 (b) 묻어둔 능력을 배선하거나 (c) 정직 버그·분기를 고치는 곳**에서만 산다.
- (a) profit-pool 격자 = 회사별 사일로 제품이 구조적으로 못 푸는 "이익은 어느 단계가 버나". 신규 데이터 0이라 싸고, born-structured 격자라 우리만.
- (b) hop2·summary·lifecycle·HHI를 런타임/화면에 꺼내는 배선 = "만들고 묻은 부채" 상환.
- (c) 백분위 3분기 통일 + engine.ts:311 marketShare 정직 버그 제거 = 회귀 차단.

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
3. **engine.ts marketShare 정직 버그 제거**(Phase C 일부, 단독으로도 가치).

### SHOULD (MUST 후 — 데이터 천장 인지하고)
4. **공급망 evidence(Phase B)**: `Industry.edges()` ratio/amount 2컬럼 + hop2/insights 인자 배선 + confidence/source 칩. edges.json 재빌드 선결. *천장 낮음 인지.*
5. **백분위 통일(Phase C)**: industryStats 분포 밴드 + compare funnel. SSOT 경계 문서화 선결.
6. **회사→산업 점프**: industryBadge/섹터필터 클릭이 산업뷰 띄움(`/map` 이탈 해소).

### WON'T (본 PRD, 기록)
- 시장점유율·컨센서스·TAM/SAM/SOM·operational KPI(소스 부재 — 영구).
- Porter 5힘 종합 스코어카드·moat wide/narrow 라벨·HHI DOJ 독점라벨·진입장벽 점수(정직성 위반).
- profit-pool 이동 시계열(migration — 코호트 노이즈 확신오정렬).
- 대체재 정량화·driver DAG(scenario-simulator 소유)·peer N사 비교 재구현(compare 소유).
- 가동률·세그먼트·US 산업(데이터 추출 선결 — 별도 게이트).

---

## 4. 선결조건순 Phase

- **Phase 0 — 비전 문서화(현재).** 본 PRD. 메모리엔 경로만.
- **Phase A — profit-pool(선결 없음, 신규 데이터 0).** ① 위생 commit(유령 API 청소). ② `buildIndustrySummary` 파생 컬럼(영업이익률·coverageRatio). ③ 퍼블릭 `/industry/[id]` stage 2D 격자(브라우저 롤업). ④ 로컬 CenterStack 버블. 즉시 출시·사용 관측. 다른 mainPlan과 무관하게 선행 가능.
- **Phase B — 공급망 evidence(edges.json 재빌드 선결).** ① "정리: edges 재빌드" commit. ② `Industry.edges()` ratio/amount 컬럼 + hop=2/insights 인자. ③ 퍼블릭 공급망 섹션 ratio/confidence 칩. ④ 로컬 RightStack hop walk. *빈곤을 1급시민으로.*
- **Phase C — 백분위 통일(경계 문서화 선결).** ① 백분위 SSOT 경계를 본 PRD/엔진 docstring에 확정(industry=섹터분포 / compare+fin-stmt-lab=peer 정밀). ② engine.ts:311 `marketShare` 제거 + industryPercentile 정의 통일. ③ 퍼블릭 industryStats 분포 밴드 + compare funnel. ④ 회사→산업 점프.
- **Phase D — 차단(착수 금지·재방문 게이트).** 적응형 lifecycle 임계(`_attempts` 졸업) · 가동률 셀 추출 · 세그먼트 · US 산업.

각 Phase는 *이미 가진 데이터*로 출시하고 막힌 것을 *연기*한다. "세계 메커니즘 N종"이 아니라 "못 풀던 질문 1개 + 묻어둔 능력 배선 + 정직 라벨"이 합격선.

---

## 5. honesty / credibility 가드레일

1. **자동 verdict 금지.** profit-pool 격자는 "이 단계가 이익을 가장 많이 번다"(사실)는 OK, "이 산업은 좋다/매력적이다"(판정) 금지.
2. **추정 아닌 인용.** 공급망 ratio/amount는 공시 추출. 추정 알고리즘 도입 = 회귀.
3. **빈곤 과대포장 금지.** "Bloomberg SPLC식"·"전수 공급망" 단어 사용 금지. amount 0.7% 노출.
4. **라벨 사칭 금지.** HHI→DOJ 독점, moat→wide/narrow, 상장사 매출→시장점유율 = 전부 금지.
5. **결손 0 대체 금지.** coverageRatio·n=N·"추출 누락분" 캡션.
6. **백분위 ≠ 종합등급.** 지표별 분포 위치(사실) OK, 합성 단일 점수(판정) 금지.
7. **경계 인용.** valuation/moat 측정값은 financial-statement-lab, driver/시뮬은 scenario-simulator로 교차참조(중복 구현 금지).

---

## 6. 성공 지표 · 실패 모드 · 단일 최대 리스크

**성공 지표**: "이 산업의 이익은 어느 단계가 버나"가 한 화면에서 답해진다 + 묻어둔 능력(hop2·summary·lifecycle·CR4)이 런타임 질의로 나온다 + 백분위가 단일 정의로 수렴한다 + 모든 숫자가 정직 라벨(상장사 기준·coverageRatio·source/confidence). 헤드라인 지표가 "세계 메커니즘 구현 개수"면 이미 실패.

**실패 모드**: 세계 제품 parity를 짓다가 born-structured 격자의 진짜 차별(profit-pool)이 Porter 5힘 점수표·HHI 독점라벨·가짜 TAM 같은 *우리에게 없는 데이터의 흉내* 더미에 희석되고, 정직성을 깎아 신뢰를 잃는다 — 사용자가 옮겨오는 이유는 *세계 제품이 추정으로 하는 걸 우리가 인용으로 하기 때문*이지 그들 화면 재현이 아니므로.

**단일 최대 리스크 / 반드시 맞출 것**: **profit-pool 하나를 깨끗이(신규 패널 금지·3게이트) 박고, 나머지는 "신규 메커니즘"이 아니라 "묻어둔 능력 배선 + 정직 버그 정리"로 프레임한다.** 승리 조건 = *못 풀던 질문 1개를 born-structured로 답하고, 없는 데이터는 EXCLUDED로 박는다.* 강함은 빼기에서.

---

## 7. _attempts 졸업 게이트 적용

Python 의존 신규 계산(적응형 lifecycle 임계·가동률 셀 추출·세그먼트)은 `tests/_attempts/industryAnalysisLab/`에서 ① 카테고리 ② 개념확립(데모 실측) ③ 모듈화 ④ 데모(docstring+README) ⑤ 덕지덕지 제거 ⑥ 클린코드 ⑦ 9섹션 docstring **확정 후** ⑧ 본진. 검증 전 `src/` 직행 금지. Phase A/B/C의 EXTEND(파생 컬럼·select 추가·표시층)는 기존 함수·화면 확장이라 본진 무관 — 단, edges.json 재빌드·유령 API 청소는 회귀 가드(테스트 동행) 필수.
