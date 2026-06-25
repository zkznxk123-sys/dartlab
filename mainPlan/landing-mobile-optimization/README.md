# 랜딩 전체 모바일 최적화

> ★활성 — 기획 박제 완료, 운영자 승인 후 구현. 작성 2026-06-25.
> 핵심 요구(운영자): **/report 쓸데없는 여백 없게 + 모바일 가독, /cards 동일, 랜딩 전체.**

## 문서
- [00-prd-and-principles.md](00-prd-and-principles.md) — 목적·범위·현재상태 실측·설계 원칙(엣지투엣지·유체타이포)·수용기준.
- [01-report-and-cards-design.md](01-report-and-cards-design.md) — Phase1(/report)·Phase2(/cards) **구체 CSS 명세**(자기충족)·검증 매트릭스.
- [02-sweep-impact-tests-rollback-eval.md](02-sweep-impact-tests-rollback-eval.md) — Phase4 스윕 + plan-deep 5섹션(영향 파일/함수/테스트/롤백/평가).

## 한 줄 요지
폰에서 report 의 "떠있는 A4 용지 카드"(좌우 회색 거터·radius·shadow·과대 패딩)를 해제해 콘텐츠를 뷰포트 폭으로 꽉 채우고, cards 피드·PostModal 을 풀스크린·고밀도화한다. **전부 `max-width:640px` media query 추가 = 데스크톱 무회귀.** UI 변경이라 운영자 스크린샷 눈검수 후 push.

## Phase 순서
1. /report 엣지투엣지 + 유체 타이포 + 표/그리드 붕괴 (최고 ROI)
2. /cards 피드 밀도 + PostModal 풀스크린
3. 공통 헤더(terminal.css) 모바일 — **조건부**(overflow 실측 시)
4. 나머지 surface 스윕(홈·blog·viewer·scan·map·skills) — 스크린샷 매트릭스 기반
