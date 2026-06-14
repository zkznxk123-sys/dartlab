# 06. 진행 원장 (Progress Ledger)

상태: 비전 PRD v0.1 (2026-06-14)
목적: 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터. 세션 간 재개 단일 진입점.

---

## 1. 현재 결정 (2026-06-14)

- **방향 확정**: A(profit-pool) → B(공급망 evidence) → C(백분위 통일) **3단계 전부**, 선결조건순 순차. 운영자 승인(2026-06-14): "3개 다 하되 순서 지켜서".
- **핵심 재구성**: industry 엔진은 약한 게 아니라 *만들어 묻어둔* 엔진. 1순위 = 묻어둔 능력(hop2·summary·lifecycle·HHI) 배선 + 정직 라벨 + 분기 통일. 신규는 profit-pool 격자 하나.
- **킬 확정**: 시장점유율·컨센서스·TAM·operational KPI·대체재(EXCLUDED) / Porter 5힘 점수·HHI DOJ 라벨·moat 라벨·진입장벽 점수(REJECT) / profit-pool migration(코호트 노이즈 kill).
- **거처**: 엔진 EXTEND + 퍼블릭 `/industry/[id]` EXTEND + 로컬 터미널 CenterStack/RightStack 배선. 새 파일·verb·패널 0(파일 단위).

---

## 2. 토론 출처

- 전문 에이전트 워크플로(2026-06-14): 조사 4건(세계 프레임워크 11종 + 세계 제품 + industry 엔진 코드실측 + 양 터미널 코드실측) → 4렌즈 토론(엔진강화·퍼블릭·로컬·덕지덕지 적대) → 후보 병합 → 적대검증(데이터 실재·정직·중복 3축) → 수렴.
- 코드실측 확정 사실(이 PRD의 근거):
  - `buildIndustrySummary` stage 집계 live ([financials.py:219](../../src/dartlab/industry/build/financials.py#L219))
  - `Industry.edges()` DataFrame amount/ratio 누락 ([__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359))
  - `computeHop2`/`calcSupplyInsights`/`calcHHI` 런타임 orphan ([insights.py](../../src/dartlab/industry/build/insights.py)·[hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32))
  - 퍼블릭 `/industry/[id]`는 라이브 엔진 아닌 static JSON 소비 ([+page.ts](../../landing/src/routes/industry/%5Bid%5D/+page.ts))
  - engine.ts:311 `marketShare` pctRank 정직 버그 ([engine.ts:301-312](../../ui/packages/surfaces/src/terminal/lib/engine.ts#L301))
  - 데이터 빈곤: amount 132/18,418(0.7%)·customer 7·ratio 19·opMargin 82.4%·industryStats p10~p90 monotone
  - 유령 API: `sectorMomentumLeadership` 등 구현 0, README·skills 카탈로그 전파
- 적대검증 생존: profit-pool grid(conditional·overlap 없음)·edges ratio/amount(conditional·천장 낮음)·hop2(conditional)·percentile band(conditional·표시층 통일로만). kill: migration.

---

## 3. 문서 상태

| 문서 | 상태 |
|---|---|
| README.md | ✅ v0.1 |
| 00-product-prd.md | ✅ v0.1 |
| 01-reference-teardown.md | ✅ v0.1 |
| 02-differentiation-killer-features.md | ✅ v0.1 |
| 03-architecture-and-reuse.md | ✅ v0.1 |
| 04-data-readiness-kill-list.md | ✅ v0.1 |
| 05-scope-phasing-guardrails.md | ✅ v0.1 |
| 06-progress-ledger.md | ✅ v0.1 (본 문서) |

---

## 4. NEXT (재개 포인터)

- **착수 = 운영자 go.** 코딩 아님(현재 = 비전 PRD 정착).
- **첫 구현 단위(Phase A)**: ① 위생 commit(유령 API 청소 — README 재작성 + scan/README·skills 카탈로그 정리, `generateSkills` 동기화) → ② `buildIndustrySummary` 파생 컬럼(영업이익률 revenue-weighted·coverageRatio) + 회귀 테스트 → ③ 퍼블릭 `/industry/[id]` stage 2D 격자(브라우저 롤업, svelte-check·build) → ④ 로컬 CenterStack 버블.
- **Phase B 선결**: edges.json 재빌드(별도 "정리: edges 재빌드" commit) — 착수 전 stale 해소.
- **Phase C 선결**: 백분위 SSOT 경계를 엔진 docstring·fin-stmt-lab PRD에 교차 확정.
- **검증 게이트**: Python 변경 시 `uv run python -X utf8 tests/run.py preflight` + 단일 파일 `bash tests/test-lock.sh`. svelte 변경 시 svelte-check + build. 푸시 전 ci-fast-local.

---

## 5. 메모리 포인터

- 정본 = `mainPlan/industry-analysis-lab/` (README + 00~06). 메모리는 포인터만(내용 복제 금지).
- 관련 프로젝트: [[project_financial_statement_lab]](백분위 SSOT 경계·reverseDCF·moat 측정값 소유) · [[project_terminal_simulation_prd]](driver DAG·인과·시뮬 소유) · [[project_ui_platform_refactor]](터미널 거처) · [[feedback_always_check_clutter]](덕지덕지 self-check) · [[core_boundary]](L2 단방향).
- 엔진 근본 문서: `engines.industry`(SKILL.md) · `operation.architecture`.
