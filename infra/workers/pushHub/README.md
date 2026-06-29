# 푸시 허브 Worker

웹푸시 구독을 Cloudflare D1에 저장하고, 발행 알림 러너의 `/send` 호출을 받아 구독 기기로 발송하는 Worker다.
허브는 **저장 + 발송만** 한다(크롤·판정·요약 0). 상세설계: `mainPlan/watcher-notify-platform/06-p1-hub-worker.md`.

## 저장 원칙

- D1 = 2테이블(`subscriptions` · `topicSubs`) + `sentNonce`. **user_id · 종목 · 개인조건 컬럼 영구 0**(재식별 회피).
- 개인화는 로컬 소유(P3) — 허브는 토픽 브로드캐스트만.

## 라우트

| method · path | 인증 | 용도 |
|---|---|---|
| `POST /subscribe` | 무인증(SSRF host allowlist) | 구독 등록·갱신(endpoint UPSERT + 토픽 교체) |
| `DELETE /subscribe` | 무인증 | 해지(부분=토픽 지정, 전체=토픽 생략 → CASCADE) |
| `POST /send` | Bearer + nonce(CORS 없음) | 러너 전용 발송 |

`/subscribe` body: `{endpoint, keys:{p256dh, auth}, topics:[]}` — endpoint host ∈ {fcm.googleapis.com, web.push.apple.com, *.push.services.mozilla.com}, topics ⊆ {blogPublish, cardPublish}.

`/send` body: `{topic, notification:{title,body,url,tag}}` 또는 `{endpoints:[], notification}`. 헤더: `Authorization: Bearer <PUSHHUB_SEND_TOKEN>`, `X-DL-Nonce: sha1(topic:slug)`, `X-DL-Ts: <unix>`. 응답 `{sent, pruned, failed}`.

## 암호화

- 페이로드 = **aes128gcm**(RFC 8291 §3.4 2단계 HKDF) — 제목·본문 실제 표시 + iOS 표준경로. VAPID JWT = ES256 순수 WebCrypto(npm 0).
- ece 바이트 프레이밍 졸업 게이트: `tests/_attempts/pushHub/` 실브라우저(Chrome + iOS 16.4+) — **P1 SHIP 필수**.

## 배포 절차

```bash
cd infra/workers/pushHub
wrangler d1 create dartlab-push-hub                 # → database_id 를 wrangler.toml 기입
wrangler d1 execute dartlab-push-hub --remote --file schema.sql
wrangler secret put VAPID_PRIVATE_KEY               # pkcs8 DER 의 base64url
wrangler secret put PUSHHUB_SEND_TOKEN              # GitHub Actions secret 과 동일값 필수(다르면 전 발송 401)
# wrangler.toml [vars] VAPID_PUBLIC_KEY · VAPID_SUBJECT 기입
wrangler deploy
```

VAPID 키쌍 생성(1회): ECDSA P-256 → `exportKey('pkcs8')`(개인키, base64url) · `exportKey('raw')`(공개키 65B, base64url).
공개키는 `wrangler.toml VAPID_PUBLIC_KEY` + GitHub `VITE_VAPID_PUBLIC_KEY`(양쪽 공개값), 개인키는 Worker secret only.

## secret 짝맞춤 (회전 시 함정)

`PUSHHUB_SEND_TOKEN` 은 **Cloudflare Worker secret ↔ GitHub Actions secret 동일값**. 회전 시 양쪽 동시 갱신.
나머지: VAPID 비밀키 = Worker only, 공개키 = 양쪽 공개값.

## 테스트

`test/` (vitest-pool-workers) — 401/409/nonce/purge/JWT/fan-out. 그린필드 하네스라 **버전 고정 스캐폴드 필요**:
`npm create cloudflare` 의 Worker+Vitest 템플릿에서 설치한 버전으로 `package.json` 핀 + 첫 `npm test` green 게이트.
불변 요구사항: 스키마는 `migrations/` + `applyD1Migrations`(멀티라인 `exec` 금지), `beforeEach` 3테이블 DELETE 리셋,
원격 batch 의미 비의존(기능 정확성만).
