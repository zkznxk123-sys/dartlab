# pushHub 테스트 하네스 — 스캐폴드 필요 (착수 1회)

`infra/workers/pushHub/` 는 repo 최초 `package.json` 보유 Worker(형제 4종은 raw `wrangler deploy`).
`vitest-pool-workers`·`vitest`·`wrangler` 의 config API 는 **버전마다 깨진다**(`d1Databases`·`exec(schema)`·
`defineWorkersConfig` vs `cloudflareTest()`·`cloudflare:test` vs `cloudflare:workers` env). 따라서 config 를
손코딩하지 않고 **설치한 버전의 공식 템플릿**에서 스캐폴드한다([08] §4).

## 절차

```bash
cd infra/workers/pushHub
npm create cloudflare@latest -- --type=hello-world --ts=false   # 또는 Worker+Vitest 템플릿
#  → 생성된 vitest.config.js · test/setup 의 버전 정합 config 만 차용
npm install   # @cloudflare/vitest-pool-workers·vitest(peer 핀)·wrangler 설치 → package.json "*" 를 설치 버전으로 핀
npm test      # 첫 green 을 게이트로
```

생성/핀 후 `package.json` devDependencies 의 `"*"` 를 **설치된 정확한 버전**으로 교체하고 `package-lock.json` 을 커밋한다.
→ `pushhub-test.yml` 의 worker 잡이 `package-lock.json` 존재를 감지해 그때부터 CI 게이트로 활성화된다.

## 불변 요구사항 (버전 무관 — 손대지 말 것)

- 스키마는 `migrations/0001_init.sql` + `readD1Migrations`/`applyD1Migrations` 로 적용(멀티라인 `exec(schema)` 금지).
- D1 바인딩 = `wrangler.toml [[d1_databases]]` 자동발견.
- `beforeEach` 에서 3테이블(`subscriptions`·`topicSubs`·`sentNonce`) DELETE 리셋(파일단위 격리 — 시나리오간 상태 누수 가드).
- 원격 D1 batch 의미 비의존: 테스트는 *기능 정확성*만(멱등 설계라 원자성 불요, [06] §6). 원격 1회 스모크는 배포 후 수동.

## 닫아야 할 시나리오 (test/send.test.js · test/subscribe.test.js 에 기술)

- `/send` Bearer 누락/오류 → 401, nonce replay → 409, 404/410 endpoint → purge, JWT 서명, fan-out.
- `/subscribe` SSRF host allowlist, topics ⊆ allowlist, UPSERT 멱등, DELETE 부분/전체(CASCADE).
