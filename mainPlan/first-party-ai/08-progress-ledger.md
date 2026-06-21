# 08. 진행 원장 — 결정·세션 간 재개·NEXT

상태: 원장. 세션 간 재개 포인터 + 결정 기록.

---

## 결정 원장

| # | 결정 | 근거 | 문서 |
|---|---|---|---|
| D1 | 인바운드 first-party AI(DartLab 이 직접 생성) — 커넥터(아웃바운드)와 별도 | 운영자 "터미널/리포트/캐러셀/블로그에 AI 가 대신 써줌" | 00 §7 |
| D2 | 4 티어 사다리 `deterministic→onDevice→edge→advanced`, advanced 는 사다리 밖 | tool-calling 추상 누수 회피 | 01 §2·§5 |
| D3 | edge = Cloudflare Workers AI 무료티어(우리 워커·키 0) — 운영자 "우리 서버 OK·CF 무료티어" | 02 §1·§2 |
| D4 | WebGPU 폴백·"이미 켜졌으면 그대로"·자동설치 — 운영자 directive 그대로 | 02 §4 |
| D5 | Grounding SSOT = 전 티어 공통 근거(숫자 결정론·서술만 모델) | "ask 처럼 일원화"·환각 0 | 03 |
| D6 | `ask`/`compose` 2 동사, `generate()` 단일 코어, 템플릿 열림 | 일원화 + 확장성 | 01 §3·§5 |
| D7 | budget = Durable Object 원자 + CF 429 ground-truth + spend cap | 과금 사고 0 | 02 §6 |
| D8 | 정적 카피 = baked(CI·문장캐시·asOf 무효화), 인터랙티브 = live | 비용 0·검수·신선도 | 04 |
| D9 | 02-runtime-ai-services §4 "public secret 0·gateway 없음" 개정(edge 추가) | 운영자 CF 승인 | 01 §1 |

---

## 평가 라운드 (07 상세)

- R1: 72/71/71/82/71 (평균 73.4) — 실코드 미대조 척추 결함.
- R2: 89/86/88/90/87 (평균 88.0) — census 실측 박고 BLOCKER 대량 해소.
- **R3: 93/91/95/90/92 (평균 92.2) — ✅ 게이트 통과(전원 ≥90). 잔여 전부 MINOR·census 흡수.**

---

## NEXT

1. **R3 패널 확인** — 5 분야 재채점, 전원 ≥90·평균 ≥90 확인(07 §2 표 채움).
2. **착수 = 운영자 go.** 비-UI 선행 가능: Phase 0a(census 문서)→0b(계약+Grounding 추출, 자동 push 가능). UI(Phase 1·3)·워커(Phase 2)·baked(Phase 4)는 06 게이트.
3. **운영자 트리거 필요**: 워커 배포(CF `CLOUDFLARE_API_TOKEN` GitHub secret 주입) · UI push 승인 · spend cap 설정.
4. **선결 census**(06 Phase 0a): 계약·심볼·search 모호성·build.ts findings 매핑.

---

## 세션 간 충돌 회피

본 PRD 작업은 mainPlan 문서만 건드림(코드 0). 동시 세션의 surface/runtime 작업과 무충돌. 구현 착수 시 runtime/data·contracts 계층만 → terminal/macro surface 작업(현재 워킹트리 MacroLensDialog·RegimeQuadrant)과 분리.
