# pushHub 배포 런북 (P1 SHIP)

순서대로. 사전: `wrangler login` (Cloudflare 계정), repo push 권한, GitHub repo Settings 접근.
secret/공개값 구분이 핵심 — 아래 표가 SSOT.

| 값 | 종류 | Worker | GitHub |
|---|---|---|---|
| `VAPID_PRIVATE_KEY` | 🔒 비밀 | `wrangler secret put` | — (Worker 만) |
| `PUSHHUB_SEND_TOKEN` | 🔒 비밀 | `wrangler secret put` | repo **secret** (동일값!) |
| `VAPID_PUBLIC_KEY` | 공개 | `wrangler.toml [vars]` | — |
| `VITE_VAPID_PUBLIC_KEY` | 공개 | — | repo **variable** (= VAPID_PUBLIC_KEY 값) |
| `VITE_PUSHHUB_URL` | 공개 | — | repo **variable** (배포된 Worker URL) |

---

## 1. VAPID 키쌍 생성 (본인 터미널에서 — `!`/공유 세션 금지)

```bash
node infra/workers/pushHub/scripts/genVapid.mjs
```
출력 2개를 안전히 보관: `VAPID_PRIVATE_KEY`(비밀) · `VAPID_PUBLIC_KEY`(공개).

## 2. 발송 토큰 생성

```bash
openssl rand -base64 32        # 이 값이 PUSHHUB_SEND_TOKEN (Worker·GitHub 동일하게 등록)
```

## 3. D1 생성 + 스키마

```bash
cd infra/workers/pushHub
wrangler d1 create dartlab-push-hub
#  → 출력된 database_id 를 wrangler.toml [[d1_databases]] database_id 에 기입
wrangler d1 execute dartlab-push-hub --remote --file schema.sql
```

## 4. Worker 비밀 + 공개값

```bash
wrangler secret put VAPID_PRIVATE_KEY      # 1단계 개인키 붙여넣기
wrangler secret put PUSHHUB_SEND_TOKEN     # 2단계 토큰 붙여넣기
#  wrangler.toml 편집: VAPID_PUBLIC_KEY(1단계 공개키) · VAPID_SUBJECT(mailto:운영자메일) 기입
wrangler deploy
#  → 배포 URL 확인: https://dartlab-push-hub.<sub>.workers.dev
```

## 5. GitHub repo 등록 (Settings → Secrets and variables → Actions)

- **secret** `PUSHHUB_SEND_TOKEN` = 2단계 토큰 (Worker 와 **동일값** — 다르면 전 발송 401)
- **variable** `VITE_VAPID_PUBLIC_KEY` = 1단계 공개키
- **variable** `VITE_PUSHHUB_URL` = 4단계 배포 URL

## 6. 검증

```bash
# 무인증 발송 차단 (401 기대)
curl -i -X POST https://dartlab-push-hub.<sub>.workers.dev/send -d '{}'
# 구독 무효 endpoint 거부 (422 기대)
curl -i -X POST https://dartlab-push-hub.<sub>.workers.dev/subscribe \
  -H 'Content-Type: application/json' -d '{"endpoint":"https://evil.com/x","keys":{"p256dh":"x","auth":"y"},"topics":["blogPublish"]}'
```
이후 landing 재배포(`deploy-landing.yml`) → NotifyOptIn 바 노출 확인 → 본인 폰/브라우저 구독 → blog 글 1편 push → 알림 수신.

## 회전·롤백

- `PUSHHUB_SEND_TOKEN` 회전 = Worker secret + GitHub secret **양쪽 동시** 갱신.
- Worker 문제 → `VITE_PUSHHUB_URL` variable 제거 시 NotifyOptIn 자동 hidden(landing 무영향).
- 발송 사고 → `wrangler secret put PUSHHUB_SEND_TOKEN` 재실행으로 즉시 발송 차단.

## 남은 SHIP 게이트 (배포와 별개)

- Worker 테스트 하네스 스캐폴드 — `TEST_SCAFFOLD.md`.
- aes128gcm ece 실브라우저 졸업 — `tests/_attempts/pushHub/` (Chrome + iOS 16.4+ standalone).
- SW 빌드 산출물에 `VITE_VAPID_PUBLIC_KEY` 정적 치환 확인.
- 운영자 눈검수(NotifyOptIn/InstallPrompt 겹침 스크린샷) 후 발간.
