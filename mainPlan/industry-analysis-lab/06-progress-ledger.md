# 06. 진행 원장 (Progress Ledger)

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터. 세션 간 재개 단일 진입점.

---

## 1. 현재 결정 (2026-06-14)

- **방향 확정**: A(profit-pool) → B(공급망 evidence) → C(백분위 통일) **3단계 전부**, 선결조건순 순차. 운영자 승인(2026-06-14): "3개 다 하되 순서 지켜서".
- **핵심 재구성(v0.2 정정)**: industry 엔진은 약한 게 아니라 *만들어 묻어둔* 엔진 — 단 "묻어둔"은 **함수·화면·DataFrame 노출**에 한정한다(orphan은 build/insights.py 함수가 verb/화면에 안 나옴 + /industry static JSON이 격자/밴드 미렌더 + edges() 컬럼 누락 + engine.ts marketShare inert dead). 산업 분석 *능력* 자체는 `recipes.industry/` 9 curated·validated가 이미 RunPython 런타임 가동 → 중복 신설 금지. lifecycle도 orphan 아님(industryBadge.phase 자동 부착 live). 1순위 = 묻어둔 *함수* 배선 + 정직 라벨 + 분기 통일. 신규는 profit-pool 격자 하나.
- **킬 확정**: 시장점유율·컨센서스·TAM·operational KPI·대체재·S-curve·경험곡선·platform KPI(EXCLUDED) / Porter 5힘 점수·HHI DOJ 라벨·moat 라벨·진입장벽 점수·GE 9box·7 Powers·Leontief 명명(REJECT) / profit-pool migration(코호트 노이즈 kill) / Capital Cycle·Damodaran 자본효율(OWNED-ELSEWHERE).
- **거처**: 엔진 EXTEND + 퍼블릭 `/industry/[id]` EXTEND + 로컬 터미널 CenterStack/RightStack 배선. 새 파일·verb·패널 0(집중도 함수는 calcs/concentration.py 승격이지 새 능력 아님). 엔진 리팩토링 = **design-only**([03 §8](03-architecture-and-reuse.md)).

---

## 2. 토론 출처

- 1차 워크플로(2026-06-14): 조사 4건(세계 프레임워크 11종 + 세계 제품 + industry 엔진 코드실측 + 양 터미널 코드실측) → 4렌즈 토론(엔진강화·퍼블릭·로컬·덕지덕지 적대) → 후보 병합 → 적대검증 → 수렴 → PRD v0.1.
- 2차 워크플로(2026-06-14): PRD 적대검증 + 엔진 클린코드/리팩토링 감사 + 세계개념 *대대적* 재조사(전략매트릭스·산업경제학·데이터제품/한국) → 흡수설계 → 적대검증 → 개정 spec → PRD v0.2. **산물 = 기능 추가보다 사실오류 정정 + 부정 카탈로그**(강함은 깎아서).
- 코드실측 확정 사실(이 PRD의 근거):
  - `buildIndustrySummary` stage 집계 live, 반환 첫 컬럼 `stage`(docstring `공정`은 오기) ([financials.py:219](../../src/dartlab/industry/build/financials.py#L219))
  - `Industry.edges()` DataFrame amount/ratio 누락 ([__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359)). 디스크 필드 `type`(supplier 3191·affiliate 12980·investor 2240·customer 7), in-memory만 `edgeType`
  - `computeHop2`/`calcSupplyInsights`/`calcHHI`/`calcTopNRatio`/`calcIndustryConcentration` *함수*는 enrichCompany 빌드+테스트만 호출(Industry verb DataFrame·화면 미노출) ([insights.py](../../src/dartlab/industry/build/insights.py)·[hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32)). ★단 산업 분석 *능력*은 `recipes.industry/` 9 curated(industryStagePhase·marginCompressionScan·supplyChainConcentration·peerCapexWave·rdIntensityTrend 등, validated 2026-05-27)로 RunPython 런타임 live — orphan은 함수/화면/컬럼 한정
  - lifecycle은 orphan 아님 — `ai/tools/industryContext.py` getIndustryBadge로 모든 Company.panel/EngineCall 응답에 자동 부착 live. backend 4-phase + 재도약 합성 = surface 5-phase
  - 퍼블릭 `/industry/[id]`는 라이브 엔진 아닌 static JSON 소비 ([+page.ts](../../landing/src/routes/industry/%5Bid%5D/+page.ts))
  - engine.ts:312 `marketShare`는 producer 없어 :313 filter 드롭 → 절대 렌더 안 되는 inert dead 컬럼(정직버그 아님, 선제 청소만)
  - Damodaran 자본효율(sales-to-capital·reinvestment·ROC)은 [synth/damodaranL15.py](../../src/dartlab/synth/damodaranL15.py):390-416에 이미 curated 구현
  - 데이터 빈곤: amount 132/18,418(0.7%)·customer 7(전원 ratio=None)·ratio 19(전부 supplier)·opMargin 82.4%·industryStats p10~p90 monotone
  - 유령 *verb/모듈*: `dartlab.industry.sectorMomentumLeadership(...)`·sectorMomentum.py 등 구현 0(README·카탈로그 전파). 단 `recipes.industry.sectorMomentumLeadership.md`는 라이브 recipe(삭제 금지)
- 적대검증 생존: profit-pool grid(conditional·overlap 없음)·edges ratio/amount(conditional·천장 낮음)·hop2(conditional)·percentile band(conditional·표시층 통일로만). kill: migration·BCG stack-fracturing 3차원·ASC275 인용·Capital Cycle·Damodaran 산업분포·Leontief 명명.

---

## 3. 문서 상태

| 문서 | 상태 |
|---|---|
| README.md | ✅ v0.2 |
| 00-product-prd.md | ✅ v0.2 |
| 01-reference-teardown.md | ✅ v0.2 (+§4 부정 카탈로그) |
| 02-differentiation-killer-features.md | ✅ v0.2 (사실오류 정정) |
| 03-architecture-and-reuse.md | ✅ v0.2 (+§5.1 recipe·§8 리팩토링) |
| 04-data-readiness-kill-list.md | ✅ v0.2 (정직 룰 SSOT) |
| 05-scope-phasing-guardrails.md | ✅ v0.2 (정직 룰 SSOT 포인터화) |
| 06-progress-ledger.md | ✅ v0.2 (본 문서) |

---

## 4. NEXT (재개 포인터)

- **착수 = 운영자 go.** 코딩 아님(현재 = 비전 PRD 정착).
- **첫 구현 단위(Phase A)**: ① 위생 commit(유령 API 청소 — README 재작성 + scan/README·skills 카탈로그 정리, `generateSkills` 동기화) → ② `buildIndustrySummary` 파생 컬럼(영업이익률 revenue-weighted·coverageRatio) + 회귀 테스트 → ③ 퍼블릭 `/industry/[id]` stage 2D 격자(브라우저 롤업, svelte-check·build) → ④ 로컬 CenterStack 버블.
- **Phase B 선결**: edges.json 재빌드(별도 "정리: edges 재빌드" commit) — 목적은 source 라벨·docstring(642 vs 132) 정합(커버리지 증가 아님), 642 vs 132 격차 원인 1회 진단 선행. + `build/insights.py` 순수계산 → `calcs/concentration.py` 승격([03 §8](03-architecture-and-reuse.md)).
- **Phase C 선결**: 백분위 SSOT 경계를 엔진 docstring·fin-stmt-lab PRD에 교차 확정.
- **Phase D ledger 후보(본문 승격 금지)**: operating leverage(DOL) 산업 cross-section(panel 다년 회귀, _attempts 졸업·R²/N 동반·marginCompressionScan recipe와 직교 확인 선결). 다축 동시 추가=덕지덕지 → 1축 우선·ledger에만.
- **★흡수 거부 박제(재제안 차단)**: Capital Cycle 순수CAPEX·Damodaran 산업분포(damodaranL15 OWNED)·BCG stack-fracturing 3차원 인코딩·ASC275 customer 인용(supplier 사칭)·Leontief 명명 — [01 §4](01-reference-teardown.md) 부정 카탈로그 참조.
- **검증 게이트**: Python 변경 시 `uv run python -X utf8 tests/run.py preflight` + 단일 파일 `bash tests/test-lock.sh`. svelte 변경 시 svelte-check + build. 푸시 전 ci-fast-local.

---

## 5. 메모리 포인터

- 정본 = `mainPlan/industry-analysis-lab/` (README + 00~06). 메모리는 포인터만(내용 복제 금지).
- 관련 프로젝트: [[project_financial_statement_lab]](백분위 SSOT 경계·reverseDCF·moat 측정값 소유) · [[project_terminal_simulation_prd]](driver DAG·인과·시뮬 소유) · [[project_ui_platform_refactor]](터미널 거처) · [[feedback_always_check_clutter]](덕지덕지 self-check) · [[core_boundary]](L2 단방향).
- 엔진 근본 문서: `engines.industry`(SKILL.md) · `operation.architecture`.
