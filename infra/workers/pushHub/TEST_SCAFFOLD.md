# pushHub 테스트 하네스 (스캐폴드 완료)

`@cloudflare/vitest-pool-workers` 로 Miniflare/workerd 안에서 워커를 실제 실행해 테스트한다. 2026-06-30 스캐폴드 완료.

## 실행

```bash
cd infra/workers/pushHub
npm ci
npm test          # vitest run — 현재 15 passed, 1 todo
```

`pushhub-test.yml` 의 worker 잡이 `package-lock.json` 존재를 감지해 CI 게이트로 활성화돼 있다.

## 버전 (핀 — lockfile 커밋됨)

- `@cloudflare/vitest-pool-workers` ^0.16.20 · `vitest` ^4.1.9 · `wrangler` ^4.105.0 (node 22).
- ⚠ 0.16.x 에서 config API 가 바뀌었다(`defineWorkersConfig`/`./config` 서브패스 폐지 → `cloudflareTest()` **플러그인**).
  업그레이드 시 `npm view @cloudflare/vitest-pool-workers peerDependencies` 로 vitest 짝을 맞추고 config 형태를 재확인할 것.

## 구성

- `vitest.config.js` — `cloudflareTest({ wrangler: { configPath }, miniflare: { bindings } })` 플러그인.
  wrangler.toml 에서 `[[d1_databases]] PUSHHUB_DB`·`[vars]` 자동 발견. secret(`PUSHHUB_SEND_TOKEN='test-send-token'`)·
  `TEST_MIGRATIONS`(migrations 배열)는 miniflare.bindings 로 주입.
- `test/applyMigrations.js` (setupFiles) — `applyD1Migrations(env.PUSHHUB_DB, env.TEST_MIGRATIONS)` 1회. 멀티라인 `exec(schema)` 금지(migrations/ 경유).
- 각 테스트 `beforeEach` 3테이블 DELETE 리셋(파일단위 격리 — isolatedStorage 없음).
- VAPID 키는 테스트 env 에 불필요 — 워커가 대상 0이면 키 import 를 건너뜀(무구독 발송 = 정상 no-op).

## 커버 (15 passed)

- `subscribe.test.js` — SSRF host allowlist·topic 필터·UPSERT 멱등·DELETE 전체(CASCADE)/부분.
- `send.test.js` — Bearer 누락/오류 401·nonce 누락 400·ts 윈도 401·replay 409·notification/target 누락 422·무구독 no-op(sent:0).

## 남은 것

- `send.test.js` 의 `it.todo('410 endpoint purge / 201 sent 집계')` — push 엔드포인트 outbound 를 fetchMock 으로 가로채는
  fan-out/purge 검증. 설치된 vitest-pool-workers 의 fetchMock(`cloudflare:test`) API 로 구현.
