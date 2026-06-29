# 05 — 진행 원장

## 상태: P1 구현 완료(코드) · SHIP 게이트(실브라우저·배포) 대기

| 날짜 | 항목 | 상태 |
|---|---|---|
| 2026-06-28 | 설계 브리프 작성([00-design-brief.md](00-design-brief.md)) — 3계층·퍼블릭↔개인 통일·로컬 브리지·P1~P4 | ✅ |
| 2026-06-28 | 로컬 런타임 브리지 일반화 + 로컬 GPU 방향 노트([00b](00b-local-runtime-bridge-and-gpu.md)) | ✅ |
| 2026-06-28 | 6 분야 전문 패널 토론 + 통합(라이브러리·인프라/WebPush·프로덕트/UX·보안·로컬브리지·클러터비평) | ✅ |
| 2026-06-28 | PRD 문서 세트 합성(00~04 + README) | ✅ |
| 2026-06-29 | **P1 구현(코드)** — 허브 Worker(`infra/workers/pushHub/` worker.js·schema·wrangler)·수신단(service-worker 3리스너·NotifyOptIn·notify/subscription·url·pwa/platform)·발행 러너(`.github/scripts/notify/` + notify-publish.yml)·CI 배선(deploy-landing env+vitest, pushhub-test.yml) | ✅ |
| 2026-06-29 | P1 자동검증 — 발행 러너 pytest 8/8 · landing vitest(sink/직렬화) 59/59 · svelte-check 0 err · ruff pass | ✅ |
| 2026-06-29 | **pushHub Worker 배포** — `dartlab-push-hub.zkznxk123.workers.dev` (Cloudflare zkznxk123@gmail.com). D1 생성·스키마·VAPID/SEND secret 등록. 인증401·SSRF422·구독/삭제 CASCADE 검증 | ✅ |
| — | 운영자 결정 잔여 — #2 발송 트리거(수동 vs cron) | ⏳ |
| — | **P1 SHIP 게이트** — ece 실브라우저 졸업(`tests/_attempts/pushHub/`)·iOS 16.4+ 실배달·Worker 하네스 스캐폴드(TEST_SCAFFOLD.md)·SW 키 치환 확인·운영자 스크린샷 눈검수 | ⏳ 대기 |
| — | P2 공개 토픽(신규수주 첫 레퍼런스) | ⬜ |
| — | P3 개인 왓처(로컬 소유·브리지) | ⬜ |
| — | P4 모드B·패키징 | ⬜ 운영자 결정 게이트 |

## 패널 산출 핵심 (통합자 확정)

- **수신 스택은 0부터** — `service-worker.ts` 셸캐시만, push 핸들러·pushManager·VAPID 전무(grep 0건).
- **왓처 ≠ 새 L2 엔진** — P1-P2 러너 plain 함수(게이트 비대상), P3 에서 synth/watch 발견적 추출.
- **`scan.orders` 이미 본진 졸업** — '신규수주' 토픽 새 데이터 0줄. 메모리 stale 정정 필요.
- **D1 = 2테이블·개인조건 0** — 개인화는 로컬 소유(재식별 회피).
- **`/send` 인증** — Bearer SEND_TOKEN + 결정적 nonce(품질점검서 HMAC 층 절단=독립 신뢰축 0). 발신자 인증 없으면 스팸/피싱 발사대.
- **PNA 미들웨어 신규 필수** — Starlette CORSMiddleware 는 PNA 헤더 미발급. pure-ASGI 추가.
- **capability 토큰** — 로컬 `/api` 무인증 + CORS 개방 = 악성 사이트 CSRF 면. 쓰기/ai/export 토큰 강제.

## 미해결 분기 → [04](04-phasing-scope-guardrails.md) §4 (운영자 결정)

## 비용 메모
- 패널 토론: 7 에이전트 · 531k 토큰 · 7분 24초.

## 다음 액션 (P1 코드 완료 후)
1. **VAPID 키쌍 생성** + Cloudflare/GitHub secret 등록(결정 #4) — `wrangler secret put VAPID_PRIVATE_KEY·PUSHHUB_SEND_TOKEN`, `[vars] VAPID_PUBLIC_KEY`, GitHub `vars VITE_VAPID_PUBLIC_KEY·VITE_PUSHHUB_URL` + `secret PUSHHUB_SEND_TOKEN`(Worker↔GHA 동일값).
2. **Worker 하네스 스캐폴드**(`infra/workers/pushHub/TEST_SCAFFOLD.md`) — `npm create cloudflare` 로 vitest-pool-workers config 버전핀 + 첫 green + lockfile 커밋(→ pushhub-test.yml worker 잡 활성).
3. **ece 실브라우저 졸업**(`tests/_attempts/pushHub/`) — Chrome + iOS 16.4+ standalone aes128gcm 수신. P1 SHIP 선행.
4. d1 create + schema 적용 + `wrangler deploy` → 운영자 눈검수(NotifyOptIn/InstallPrompt 겹침 스크린샷) 후 발간.
