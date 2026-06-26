# 전문 리포트 엔진 — story 갈아엎기 + 능력 엔진 격상

> **비전**: dartlab 의 `story` 엔진을 *진짜 전문 애널리스트 리포트*를 내러티브로 조립하는 SSOT 로 갈아엎고, 랜딩 `/report` 가 그것을 **동일 계약으로 소비**한다. 옛 "6막·11 reportType·sixAct 레이더" 군더더기는 폐기. 리포트가 빨아들이는 **능력 엔진들(밸류에이션·전망·세그먼트·moat·신용·매크로민감도)** 은 아마추어 수준이므로, *정직 스킵으로 도망치지 않고* 각 SSOT 를 찾아 프로 수준으로 끌어올린다.

## 사상 (operator 확정)

1. **정직 ≠ 차별. 정직 스킵 = 능력부족.** "공시에 없으니 평가 불가"는 전문성이 아니다. 애널리스트가 하는 일은 *근거 있는 모델링*(DCF·전망·세그먼트 마진 배분은 전부 방법 있는 추정). 부족한 능력은 **개선해서 끌어올린다.**
2. **단, 날조는 금지.** 게으른 스킵 ❌ · 근거 0 날조 ❌ · *방법·가정·검증을 갖춘 모델* ✅. 차이는 "방법의 엄밀성 + 검증"이지 "추정을 피하느냐"가 아니다.
3. **능력부족은 SSOT 를 찾아 거기서 개선.** 병렬 빌드·사본 신설 금지(`feedback_common_workbench_ssot`). 밸류에이션은 `analysis/valuation/`, 전망은 forecast SSOT 등 — 정본 모듈을 강화한다.
4. **검증 게이트는 방어 스캐폴딩이 아니라 졸업 조건.** "약하게 추정하고 단정"은 operator 가 가장 싫어하는 형태(`feedback_plan_score_not_signature`). 능력 향상 = 모델 빌드 + 백테스트/민감도로 *증명* → 그제서야 리포트에 올린다.

## 2 층 구조

```
[리포트 엔진 (story)]  ← 갈아엎는 본체. 전문 내러티브 조립 + SSOT.
        ↑ 빨아들임
[능력 엔진들]          ← 바닥에서 끌어올림. 밸류에이션·전망·세그먼트·moat·신용·매크로.
```

리포트 엔진 혼자 멋져도 입력이 아마추어면 아마추어 리포트. **둘 다 손대되 순서는 능력 먼저.**

## Phase 순서 (operator 확정 — 능력 먼저)

- **P0. 현상태 publish** — 라이브러리 안정화 단계. 현 안정본 publish 후 착수.
- **P1. 능력 엔진 격상 (SSOT 강화)** — 밸류에이션 → 전망 → 세그먼트 → moat → 신용 라이브배선 → 매크로민감도. 각 엔진 *졸업 게이트*(백테스트/민감도 검증) 통과해야 다음.
- **P2. 리포트 엔진 갈아엎기** — story 군더더기 폐기 → 강화된 능력을 thesis-led 인과 아크로 조립하는 ReportModel emitter. 서사 문법 계약(`ui/packages/contracts`).
- **P3. 랜딩 동일 소비** — `/report` TS 가 같은 계약에 conform(베이크 0, 런타임 직독). drift 상수 parity 테스트.

## 강행 가드레일

- ⛔ **런타임-SSOT**: 베이크·별도배선 금지. 정적 사이트는 브라우저 직독, Python 못 돎 → SSOT 는 *문법 계약*, Python·TS 둘 다 conform.
- ⛔ **no-graph-regression**: "통일"을 빌미로 고정 다단 파이프라인·companyStory MCP 부활 금지. `checkAgentBoundary.py`.
- ⛔ **find-SSOT-improve**: 능력 개선은 정본 모듈에서. 병렬 빌드 금지.
- ⛔ **날조 금지 / 검증 게이트**: 모든 추정은 방법·가정 노출 + 백테스트·민감도 검증. 미검증 확신 금지.
- ⛔ **master only · 변경단위 commit · UI push 눈검수**.

## 문서 맵

| # | 문서 | 내용 |
|---|---|---|
| 00 | [product-prd](00-product-prd.md) | 전문 리포트가 *무엇인가* — 인과 아크·thesis 규율·섹션·밸류·리스크·서사 문법 |
| 01 | [current-state-audit](01-current-state-audit.md) | 두 시스템 매핑·story 군더더기 폐기목록·능력 원장(아마추어 실측) |
| 02 | capability-uplift | 능력 엔진별 SSOT·아마추어 격차·프로 표준·빌드·검증 (전문 에이전트 조사) |
| 03 | report-engine-architecture | story 갈아엎기·ReportModel emitter·서사 문법 계약·랜딩 소비 |
| 04 | scope-phasing-guardrails | Phase 분해·졸업 게이트·리스크·롤백 |
| 06 | progress-ledger | 진행 추적 |

## 상태

- **2026-06-26 기획 완료** — 6문서 박제(00 PRD·01 현상태·02 능력종합+02a~02e 상세·03 아키텍처·04 phasing·06 원장). 전문 에이전트 6 SSOT 조사 완료.
- **핵심 발견**: 능력부족 = 능력 부재 아닌 *조립 아마추어*. 프로 기계(bottom-up WACC·reverse-DCF·재투자성장·dCR 20등급·정량 moat 기질) 대부분 *이미 존재*하나 게이트로 꺼졌거나·묻혔거나·미배선. 격상 = de-gate+배선+검증.
- **착수 대기 = 운영자 결정 1개**: 신용 prebuild-publish 승인(04 §결정1). 이후 P0 publish → P1a 밸류에이션부터.
