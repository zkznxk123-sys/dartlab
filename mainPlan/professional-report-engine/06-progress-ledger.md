# 06 · 진행 원장

> 표기: ☐ 대기 · ◐ 진행 · ✅ 완료 · ⚠ 차단(결정 대기). 완료 시 게이트 결과 한 줄 동행.

## 기획 (조사·플랜)

- ✅ 현상태 매핑 (두 시스템·story 군더더기·소비 그래프) — `01`
- ✅ 전문 리포트 PRD (인과 아크·thesis 규율·밸류·신용·서사 문법) — `00`
- ✅ 능력 엔진 6 SSOT 조사 (de-gate 발견) — `02a~02e`
- ✅ 리포트 엔진 아키텍처 (계약 SSOT·delete ~2,834·emitter) — `03`
- ✅ Phase 분해·게이트·가드 — `04`
- ☐ 운영자 결정: 신용 prebuild-publish 승인 (§04 결정1)

## P0 · publish
- ☐ 현 안정본 publish

## P1 · 능력 격상 (순서: 02a 선행)
- ☐ P1a 밸류에이션 de-gate + WACC/성장/fade/reverse — 게이트 G1·G2(백테스트)·G3·G5
- ☐ P1b 전망 driver + `_revenueBacktest.py` — 게이트 MAPE·방향·밴드·skill
- ☐ P1c 세그먼트 마진 도출 + SOTP — 게이트 MAE≤5%p·커버·ρ
- ☐ P1d 정량 moat(`_attempts/quantMoat` → `moat.py`) — 게이트 cohort 평균회귀
- ☐ P1e 신용 라이브배선 + 매크로 강화 — 게이트 parity·79사·β-stability ⚠(결정1)

## P2 · 리포트 엔진
- ☐ 삭제 ~2,834 LOC (`story/macro`·publisher·sixAct·dashboard·sections)
- ☐ `reportModel.ts` 계약 + 18블록
- ☐ `story/report.py::buildReportModel` emitter
- ☐ 소비자 마이그레이션 (CLI·테스트·storyTemplate)

## P3 · 랜딩 동일소비
- ☐ `build.ts` → ReportModel emit (베이크 0)
- ☐ `model.ts` re-export shim
- ☐ 6상수 golden-parity (N=5, ~20셀)
- ☐ UI 스크린샷 눈검수 + 운영자 승인 push

## 결정·이벤트 로그
- 2026-06-26 착수. operator 사상 확정: 정직-스킵=무능, 능력부족은 SSOT 찾아 개선, 날조만 금지. 순서 = 능력 먼저. 기획 6문서 박제.
