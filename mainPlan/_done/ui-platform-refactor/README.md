# UI Platform Refactor — ✅ 완료 (2026-06-13)

> **상태: 완료·격리.** 단계 1~10 전부 완료 — GitHub Pages 공개(public)와 pip 로컬 앱(local)이
> `ui/packages/*`(contracts·runtime·surfaces·design) 단일 자산을 공유하고, 각자의 composition
> root(`createPublicRuntime`/`createLocalRuntime`)에서 basePath·자산·데이터 포트만 다르게 주입.
> "터미널이 공표·로컬 단일 공유자산" 목표 달성(진행원장 [36], 커밋 `dd19aff60`).

## 문서

| 파일 | 성격 |
|---|---|
| `ui-platform-refactor-prd.md` | 기준 PRD (v2 확정) — 설계 SSOT |
| `00-product-prd.md` ~ `06-inventory-and-freeze-template.md` | 설계/실행 단계 문서 — **완료(불변)** |
| `07-progress-ledger.md` | 진행 원장 (append-only, 단계 1~10 완료 기록) |
| **`08-shared-wiring-parity-maintenance.md`** | ⚠ **살아있는 유지보수 런북** — public/local 공유 배선을 손대기 전 반드시 읽는 SSOT(장애 런북·드리프트 레지스트리·변경 위치 결정 트리). 프로젝트는 완료됐지만 이 문서는 *배포된 시스템의 현역 정비 문서*다. |

## 잔여 (운영자 판단 · 비차단)

- 재무 35카드 bento·퀀트 대시보드 surface 이관(현재 React `ui/web` = `DARTLAB_UI_LEGACY`, pip 기본은 터미널 자체 재무뷰)
- Skill OS `operation/{dashboardDesign,ui,aiProductReplatform}.md` 의 `ui/web` 경로 서술 정정
- `embed.js` 위젯은 이미 dormant(범위 밖)
