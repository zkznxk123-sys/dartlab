# 매크로 렌즈 다이얼로그 시각 재설계

> 상태: **PRD 확정 (2026-06-19) · 기획점수 96/100** (분석가·사용자 에이전트 적대 평가 통과, min 96 ≥ 95). 착수 = 운영자 go (UI 변경이므로 push는 명시 승인 후).
> 거처: `ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte` (기존 다이얼로그 EXTEND, 새 라우트·상주 패널·차트 복제 0).

---

## 한 줄 결론

터미널 좌측상단 "마켓 펄스·매크로"(Macro Lens) 다이얼로그의 무게중심을 **"판정 엔진(verdict·score·100)"에서 "정직한 매크로 계기판(dashboard)"으로 역전**한다. v0.1→v1.12까지 12번 개선하며 한 탭에 *쌓인* 13개 섹션·전문용어 벽(kill-chain·flip test·direction contest·evidence cockpit)을 **깎아내고**, 4블록 IA — 무엇이 움직였나(Phase·Pulse) → 어느 채널에 닿나(Exposure Map) → 증거가 무엇인가(Gate) → 언제 다시 보나(Release) — 로 되돌린다. 새 fetch 0·새 패널 0·코드 ~600줄 순삭감.

핵심 시각 결정: 첫 화면 **시각 주역은 단 하나 — Exposure Map**(유일 테두리 패널·면적 ≈53%·내부 읽기 1→2 위계: 초점 전파사슬 → 채널 열 클러스터 닷그리드), 증거 칩은 **CSS 도형**(글리프 폰트 의존 0·색맹 무손실).

---

## 문서 지도

1. [01-redesign-prd.md](01-redesign-prd.md) — **완전 PRD** (비전·현상진단·IA·ASCII 목업·시각 토큰/CSS 도형 칩·데이터 계약·정직 가드·영향 파일/함수·테스트/롤백·Phase·이중 평가·성공/실패 기준). 자기충족적 — 이 문서만 보고 재조사 없이 구현 가능.
2. [00-eval-ledger.md](00-eval-ledger.md) — 전문가 공조·적대 평가 과정과 점수 이력(88→93→96), ground-truth 교정 기록.

---

## 기존 `macro-lens-dialog/` 트랙과의 관계

본 재설계는 [`mainPlan/macro-lens-dialog/`](../macro-lens-dialog/) 트랙을 **대체하지 않고 일부를 폐기·계승**한다.

- **폐기 (재설계가 뒤집음):** verdict-first IA(판정 13섹션·`buildMacroVerdict`·단일 macro score). 이 누적 레이어가 사용자 평가 "심각해"의 근원이며, 프로젝트 "단일 macro score·판정 금지" 가드와도 충돌했다.
- **계승 (여전히 유효):** 엔진 강화 트랙([07-macro-engine-upgrade.md](../macro-lens-dialog/07-macro-engine-upgrade.md))·데이터 계약([02-data-contract.md](../macro-lens-dialog/02-data-contract.md))·시각화 조사([08-dashboard-visual-patterns.md](../macro-lens-dialog/08-dashboard-visual-patterns.md))·정직 상태 라벨(OBS/PRIOR/TPL/LOCK). 재설계는 이 자산을 그대로 소비한다.

즉 macro-lens-dialog = "분석 엔진·데이터·정직 원칙" SSOT, macro-lens-redesign = "그 자산을 시각적으로 직관적인 계기판으로 재배치하는 UI 재설계" SSOT.
