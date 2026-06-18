# 06. Progress Ledger

상태: PRD v1.1

## 2026-06-19

### v1.0 — Current-code grounded PRD 승격

배경:

- 원문 `C:\Users\MSI\.claude\plans\graceful-yawning-valley.md`는 방향과 화면 자산은 강했지만, 일부 계약이 현재 코드/데이터보다 넓고 테스트 명령이 불명확했다.
- 사용자는 전문 관점 토론을 거쳐 PRD를 완성하라고 지시했다.

완료:

- PRD를 `mainPlan/macro-lens/` SSOT로 승격했다.
- 현재 코드 근거를 `LeftRail.svelte`, `TerminalSurface.svelte`, `engine.ts`, `macroLens.ts`, `types.ts`, `landing/static/dashboards/macro.json` 기준으로 검증했다.
- 현행 v19 `macro.json`의 실제 sector key set, all-sector edge, phase/quadrant/transition, all-positive blended 상태를 문서에 고정했다.
- `HEADWIND/역풍` 정직 버그가 `engine.ts`, `LeftRail.svelte`, `TerminalSurface.svelte` 세 표면에 걸쳐 있음을 반영했다.
- `ui/packages/surfaces`에 test script가 없다는 점을 반영해 Vitest 실행 방식을 명시했다.
- 전문 관점 토론 결과를 제품/UX, 매크로, UI, 데이터계약, 구현 레드팀으로 분해했다.

검증:

- 문서 작업 단계에서는 코드 실행 변경 없음.
- Current state audit은 로컬 파일 읽기와 `node` JSON inspection으로 수행했다.

NEXT:

1. 완료: v1.1에서 에이전트 3인의 검토 결과를 통합했다.
2. 구현 착수 시 P0 `positive blended -> no headwind` 버그 수정부터 독립 commit으로 진행한다.

### v1.1 — Expert review integration and visual research

배경:

- Product/UX, macro/data, implementation red-team 리뷰가 모두 같은 약점을 지적했다: 회사 미선택 뷰, 실제 v19 sector key 계약, P0 영향 표면, 테스트 명령, 롤백 범위가 더 명확해야 했다.
- 사용자는 매크로 분석 대시보드 시각화 방식을 조사하라고 요구했다.

완료:

- `MacroGlanceView`와 `CompanyMacroLensSnapshot`을 분리했다. 회사 미선택 상태에서도 macro drill이 열리는 계약을 추가했다.
- 실제 LeftRail 폭 300/284/270px와 `RegimeQuadrant` 높이 138px 예산을 수용 기준으로 추가했다.
- `sectorFilter`와 `bottomTab`의 단일 owner를 `TerminalSurface`로 고정했다.
- `EDGE_TO_TAILWIND` 중복 금지와 공유 mapper 원칙을 추가했다.
- `logistics`, `utility`는 임의로 `it_software`/`energy`에 붙이지 않고 `tailwind 미산출`로 렌더하도록 수정했다.
- freshness와 evidence 시각 채널을 분리했다.
- P0 범위에 `engine.ts`, `LeftRail.svelte`, `TerminalSurface.svelte`를 모두 명시했다.
- 테스트 명령에 `uv run python -X utf8 tests/audit/dartlabGuard.py quick`와 Vitest 실행 조건을 추가했다.
- 공식 매크로 대시보드 조사 결과를 `07-visual-research.md`로 추가했다.

검증:

- 문서 보강 단계에서는 코드 실행 변경 없음.
- 전문가 리뷰 3건의 모든 구현 차단 지적을 PRD/계획/검증 매트릭스 중 하나에 반영했다.

NEXT:

1. 외부 원문 PRD `C:\Users\MSI\.claude\plans\graceful-yawning-valley.md`에 SSOT 승격 상태를 표시한다.
2. 문서 링크/미해결 토큰 검사를 통과시킨 뒤 explicit-path commit을 만든다.
