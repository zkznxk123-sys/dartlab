# 04 — 진행 원장

## 상태
- **2026-06-27 기획 박제**: panel spine taxonomy 실측 인벤토리 + 7에이전트 토론(wf_138893c3) → PRD 6문서 작성. **미착수**(설계 완료, 구현 0).

## 선행 사실 (착수 전 확인됨)
- Tier B 17종 `reportSource.ts` 런타임 직독 배선 완료(surface만 남음).
- noteSeries(비용·부문) live + NotesDashboardDialog 시계열 스택 막대+테이블(이번 세션 커밋 `06a8ed4df`·`5263445ac`·`145d0e906`, UI push 보류).
- `xbrlCellsFromContent` 범용 acode 리더 — Tier A 무빌드 확장 경로 확인.
- 코드에 `notesDispatch` 레지스트리(borrowings·lease·provisions·affiliates·receivables·inventory) 일부 존재(신용 렌즈 발견 — 착수 시 실재 재확인 필요).
- 수주 flow = [[project_order_flow_scan]] _attempts(810사·≥90%·book-to-bill), 본진 미투입.

## NEXT (재개 포인터)
1. **운영자 결정 3종**(`03` open questions): 통합 패널 적층 3블록 확정 / 수주 flow scan 빌드 승인 / Tier A 횡단 scan 승인.
2. **P0 착수**(승인 시): RightStack WORKFORCE·SHAREHOLDER·REPORT NOTES → 「사업보고서 한눈」 적층 블록 병합. `reportSelfHistory`·기존 시리즈 재사용, 신규 fetch 0. 블록별 ⤢ → FinFullscreen PEOPLE/RETURN + NotesDashboardDialog.
   - 게이트: svelte-check 0 · Playwright 실측 스크린샷 · 눈검수 → 운영자 승인 후 push(UI 게이트).
3. **P1**: `notesDispatch` 실재 재확인 후 acode 필터로 리스·차입금·충당부채·관계기업·매출채권·재고 → NotesDashboardDialog 섹션(우측 글랜스 금지).
4. **P2**(승인 후): 수주 flow 졸업·scan('orders') / Tier A 횡단 scan.

## 검증 게이트 (착수 시)
- 무빌드 P0/P1: 런타임-SSOT 강행규칙 준수(빌드 0). 공개 surface = 눈검수·운영자 승인 후 push.
- 빌드 P2: 사전 토론·실측 입증·명시 승인 후에만(CLAUDE.md 런타임-SSOT 강행규칙).
- 점수 인플레·미빌드 가치 과장 0([[feedback_plan_score_not_signature]]).
