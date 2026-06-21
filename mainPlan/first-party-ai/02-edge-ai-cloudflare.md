# 02. Edge AI — Cloudflare Workers AI 무료티어 통합

상태: 구현 계약 PRD v0.2 (R1 운영 BLOCKER 반영: budget=Durable Object+CF 429 ground-truth, 별도 deploy 워크플로, spend cap·Turnstile v0 승격, 관측성 §9 신설, SSE 정산 §10)
범위: `infra/workers/aiEdge` 워커, Workers AI 바인딩, 엔드포인트, 자동 프로비저닝, neuron 예산·남용 방어, 프라이버시, 비용 정직, 관측성.

> ⚠ R1 운영 평가 정정: **기존 워커 라인은 전부 *수동* `wrangler deploy` 이고 KV·rate-limit 이 0** 이다(hfProxy=엣지 캐시만). 따라서 본 PRD 의 CI 자동배포·budget 상태·rate-limit 은 "패턴 계승"이 아니라 **신규 인프라**다. 정직 척추 §1("새 발명 최소화")은 *분석/생성 로직* 에 적용되며, 운영 안전장치(budget·관측·spend cap)는 신규임을 인정한다.

---

## 1. 결정 — 별도 워커 `infra/workers/aiEdge`

`hfProxy` 에 `/ai` 를 얹지 않고 별도 워커. 이유: **비용·남용 격리**(AI 는 neuron metered → `/ai` 남용이 데이터 프록시 rate-limit 을 끌어올려 *전체 fetch* 를 막는 사고 방지), 관측 분리, 독립 배포. `dartlabConnector`(아웃바운드)와도 별도(00 §7).

```text
infra/workers/aiEdge/
  wrangler.toml          # [ai] binding="AI", [[durable_objects]] BUDGET, vars(ALLOW_ORIGIN, MODEL_ID, BUDGET_HARD)
  worker.js              # /ai/compose, /ai/ask(SSE), /ai/health
  budgetDO.js            # Durable Object — 원자 neuron 카운터(§6)
  README.md
  .dev.vars.example
```

---

## 2. Workers AI 사실관계 + 예산 정량 (2026-06)

| 항목 | 값 |
|---|---|
| 무료 할당 | **10,000 Neurons / day / account** (UTC 기준 — §6 에서 CF 429 로 검증) |
| 초과 과금 | $0.011 / 1,000 Neurons (Workers Paid) |
| 8B 소비 | `@cf/meta/llama-3.1-8b-instruct` ≈ 3~5 neurons / 1,000 tokens |
| 바인딩 | `[ai] binding="AI"` — **API 키 불요**(계정 바인딩) |
| 호출 | `env.AI.run('@cf/meta/llama-3.1-8b-instruct', {messages, stream})` |
| 모델 | llama-3.1-8b-instruct(기본·vars 교체 가능), qwen2.5 한국어 비교 후보 |

**예산 정량(R1 데이터 W4·운영 해소)** — 무료 10k/day 가 며칠 버티나 역산:
- 1 질의 grounding ≈ top-K facts(§03 maxFacts=12) + 근거본문 cap → in ~1,500 tok, out ~400 tok ≈ 2,000 tok ≈ **6~10 neurons/질의**.
- 10,000 neurons/day ÷ 8 ≈ **~1,250 질의/day** 무료. 트래픽이 이를 넘으면 `BUDGET_SOFT`(§6)에서 onDevice 강등 → 무료 유지.
- 이 추정을 06 테스트에 fixture 로 박아 모델/프롬프트 변경 시 재계산.

> 정직 척추 §4: 10k/day 는 *계정* 단위. "무제한 무료" 금지. §6 서킷 + CF spend cap 으로 과금 사고 0.

---

## 3. 엔드포인트

```text
POST /ai/compose   body{ template, scope, grounding, tone, maxTokens } → { text }
POST /ai/ask       body{ prompt, scope, grounding } → SSE GenChunk(text) 스트림
GET  /ai/health    → { ok, model, budget:{ remaining:'high'|'low'|'exhausted', resetAt } }   // 정확수 숨김(§9)
```

- **근거는 클라이언트가 만들어 보낸다.** 워커는 무상태 — `grounding`(03 SSOT 가 만든 facts+근거, untrusted-wrap 포함)을 받아 시스템 프롬프트에 끼우고 `env.AI.run` 만. 워커는 DartLab 데이터에 직접 접근 0.
- `/ai/ask` SSE 는 `GenChunk{type:'text'}` 토큰 델타(01 §5 청크 계약과 일치).
- CORS: `ALLOW_ORIGIN`(GitHub Pages + dev).

---

## 4. 자동 프로비저닝 — 별도 워크플로 (R1 운영 B3 해소)

deploy-landing.yml 에 **얹지 않는다**(그건 Pages 전용·`concurrency cancel-in-progress` 라 wrangler 를 중간에 죽임 + 격리 철학 위반).

### 4.1 자동설치 — `deploy-ai-edge.yml` 신설
```yaml
on:
  push: { paths: ['infra/workers/aiEdge/**'] }
  workflow_dispatch:
concurrency: { group: ai-edge-deploy }     # Pages 와 독립
jobs:
  deploy:
    if: ${{ secrets.CLOUDFLARE_API_TOKEN != '' }}   # 토큰 없으면 잡 자체 미실행 → 조용한 폴백
    steps:
      - run: cd infra/workers/aiEdge && npx wrangler deploy
```
landing 빌드의 `VITE_DARTLAB_AI_PROXY` 는 deploy-landing.yml env 에 *상수 URL* 로 추가(워커 존재와 무관하게 박아도, 워커 미배포면 health 실패 → 폴백). 토큰 없으면 워커가 안 떠 있고 health 가 실패 → onDevice. **"자동설치 불가 = 폴백, 에러 아님."**

### 4.2 이미 켜져있으면 그대로
`wrangler deploy` 는 idempotent(diff 없으면 CF no-op). 별도 "켜졌나?" 분기 스크립트 안 만든다. **부분배포 실패 안전**: deploy 실패 시 CF 가 이전 버전 유지(원자 배포) → 반쯤 갱신 없음.

### 4.3 런타임 감지
```text
public 부팅: originConfigured('aiEdge') 거짓 → edge 제외
            참 → GET /ai/health(2s timeout, 1회): ok&budget≠exhausted → edge / else onDevice
```
`originConfigured`(registry.ts:86 게이트) + health 프로브(ollama.ts detectOllama 패턴) 재사용. **단 `aiEdge` origin 항목 자체는 신설**(registry OriginId 에 없음 — 01 §0).

---

## 5. 인증·시크릿

| 무엇 | 어디 | repo |
|---|---|---|
| `[ai] binding`·DO 바인딩 | wrangler.toml | ✅(이름만) |
| Workers AI 인증 | 계정 바인딩 자동 | —(키 0) |
| `CLOUDFLARE_API_TOKEN`/`ACCOUNT_ID` | **GitHub Actions secret 신규 주입** + 로컬 `.env`(gitignore) | ❌ |
| `METRICS_TOKEN`(`/ai/_metrics` 게이트, §9) | wrangler secret + `monitorEdgeAi.yml` 용 GitHub secret | ❌ |
| `ALLOW_ORIGIN`·`MODEL_ID`·`BUDGET_*` | wrangler vars | ✅ |

> R1 정정: "추가 시크릿 0" 은 *런타임 AI 인증* 에만 참. *배포* 엔 `CLOUDFLARE_API_TOKEN` 필요하고 그건 **GitHub secret 으로 신규 주입**(로컬 .env ≠ CI secret). 사용자 API 키는 어디에도 없음(=퍼블릭 무API 의 구현).

---

## 6. 예산·남용 방어 — 4겹 (R1 운영 B1·B4 해소)

KV 의 read-modify-write 비원자성으론 동시성 lost-update 로 샌다. 정공법:

1. **Durable Object 원자 카운터.** `budgetDO.js` 단일 인스턴스가 neuron 소비를 직렬 increment(진짜 원자). KV 아님. `reserve(maxTokens 비관적 예약) → 응답 후 settle(실제 토큰 정산)` 2단계 — 출력 길이 사전 미지를 보수적으로 흡수. **일일 리셋**: DO `alarm()`(UTC 자정) **+ first-request date-rollover 를 항상 백업으로**(AND, 택1 아님) — alarm 미발화 사고 시 budget 이 영구 exhausted 로 굳어 전 트래픽이 조용히 onDevice 강등되는 가용성 열화를 first-request rollover 가 막는다. DO 직렬화가 자정 race 방어.
2. **CF 429 를 ground-truth 1급 신호.** 추정은 틀린다 → 워커가 `env.AI.run` 에서 429/quota 를 받으면 즉시 DO 에 `circuit open until resetAt` 플래그 → 모든 요청이 추정 무관하게 onDevice 강등. 추정 신뢰 안 하고 CF 진실에 항복. `BUDGET_SOFT`(예 8k) 는 *사전* 보호, 429 는 *확정* 차단.
3. **CF native Rate Limiting + Turnstile(v0 승격).** Origin 헤더는 봇이 위조 가능(보안 아님·"정직한 사용자 분류"일 뿐). per-IP 도 IP 로테이션에 무력. 따라서 CF *엣지* Rate Limiting Rules(워커 KV 아님, 우회 난이도↑) + Turnstile 을 **v0 필수**(05 DEFER 에서 승격). 봇/DDoS 과금 공격 차단.
4. **CF Workers Paid spend cap = 운영 전제.** 코드 방어가 다 뚫려도 청구서가 상한에서 멈추게 CF 계정 spend cap 설정을 *배포 전 운영자 체크리스트* 에 명문화. `BUDGET_HARD=0`(wrangler vars 한 줄, 재배포 없이 CF 대시보드 변경)로 즉시 전면 차단 가능.

**DO 운영현실 정직(R2 운영 MAJOR 해소)**: Durable Object 는 공짜가 아니다 — Workers Free 는 **SQLite-backed DO** 만 가용하고 request·duration·storage 가 *별도 과금 축*(neuron 과 다른)이다. 두 가지 트레이드오프를 정량 방어:
- **과금**: DO 호출 = 질의당 reserve+settle 2회. neuron 무료 한도(~1,250 질의/day, §2)에 닿기 한참 전이라 DO 무료 한도는 여유. 단 **DO 도 spend cap 우산 안**에 두고, §2 예산표에 "DO request/duration/storage" 축을 *neuron 과 함께* 모니터(§9).
- **처리량/레이턴시**: DO 단일 인스턴스 = 직렬화 = 처리량 천장 + 단일 리전 RTT. 그러나 **neuron 예산(~1,250 질의/day)이 DO 직렬 처리량보다 훨씬 먼저 닿으므로** DO 병목은 실질 비제약(저 QPS). 유료 확장 시 region-sharded DO + 합산 재검(DEFER).

> 공격 시나리오 차단: `Origin` 위조 + 100 IP 분당 수천 `/ai/ask` → CF Rate Limiting(엣지)에서 1차 차단 + Turnstile 봇 차단 + DO 원자 카운터가 8k 에서 onDevice 강등 + CF 429 확정 + spend cap 최종 상한. 4겹 전부 뚫려도 청구서는 cap. (남용 트래픽이 rate-limit 통과분만 DO 를 때리고, 그것도 무료 처리량 안.)

---

## 7. 프라이버시 분기 + 로깅 가드 (R1 B7)

| 경로 | 디바이스 밖 | 고지 |
|---|---|---|
| deterministic·baked·onDevice | 0 | "이 기기에서 직접 / 빌드 산출물" |
| edge | 프롬프트+근거 → 우리 워커 → CF | "분석을 위해 질문/근거가 DartLab 서버로 전송(개인정보·로그인 없음)" |

edge 로 가는 것은 공개 공시·재무 근거 + 질문 텍스트뿐(PII·워치리스트 0 — 그건 connector 영역). **"로깅 안 함"을 기계 가드로**: wrangler.toml 에 `observability`/logpush off 명시, 에러 응답에 프롬프트 echo 금지를 워커 테스트(06)로 강제. console.log 0 + 플랫폼 로깅 off 둘 다.

---

## 8. 영향 파일

| 파일 | 변경 |
|---|---|
| `infra/workers/aiEdge/{wrangler.toml,worker.js,budgetDO.js,README.md}` | 신규 워커 + Durable Object |
| `.github/workflows/deploy-ai-edge.yml` | 신규(별도) — 조건부 deploy |
| `.github/workflows/deploy-landing.yml` | `VITE_DARTLAB_AI_PROXY` env 만 추가(wrangler step 없음) |
| `…/data/origins/registry.ts` | `aiEdge` origin 신설 |
| `…/runtime/src/ai/backends/edge.ts` | `EdgeBackend`(health·budget 버킷·generate·강등) |
| `.github/scripts/.../monitorPipeline.py` | edge AI 관측 게이트(§9) |

---

## 9. 관측성 — 실배관 (R1 운영 B2 BLOCKER 해소, R2 정정)

vitest 는 배포 전만 본다. *런타임* 운영 루프 신설. **단 R2 정정: `monitorPipeline.py` 는 `gh run list` 로 *워크플로 conclusion* 을 폴링하는 머신이라, 라이브 워커(워크플로 run 이 없음)와 "동형" 이 아니다.** 정확한 배관:

```text
워커 budgetDO 가 누적(neuron·강등·stray 거부율·5xx·env.AI.run 실패율)
  -> GET /ai/_metrics  (운영자 토큰 게이트, /ai/health 와 별도)
  -> 신규 cron 워크플로 monitorEdgeAi.yml (일 1회) 가 fetch → 임계 판정
  -> monitorPipeline 과 *같은 Issue 라벨/싱크* 로 알림 (gather 와 동일 심각도 구분)
```

- **"동형" 이 아니라 "같은 알림 싱크에 붙는 별도 수집 cron".** monitorPipeline 을 확장하는 게 아니라 `monitorEdgeAi.yml` 을 신설해 동일 Issue 라벨을 쓴다.
- **임계.** "최근 7일 강등율 > X%"(무료티어 만성부족 → 운영자 결정) · "5xx > Y" · "stray 거부율 급증"(모델/프롬프트 회귀).
- **수집 저장소 정직.** CF Analytics Engine 은 **write(`writeDataPoint`) 무료이나 read(SQL API)는 플랜 확인 필요**(무료 단정 금지). `siteSignals` 워커는 D1 기반인데 현재 `database_id="replace-with..."` 로 **미프로비저닝** → 이를 쓸 거면 D1 생성을 06 Phase 2 선결 게이트로. v0 1차는 budgetDO → `/ai/_metrics` 직노출(추가 인프라 0)로 시작.
- `/ai/health` 의 `remaining` 은 버킷('high'|'low'|'exhausted')만(B6 정찰 차단). 강등 판단은 health 캐시(60s stale)가 아니라 **실제 429**(§6-2) 1급.

이 관측 없이는 budget 만성소진·환각 급증·워커 장애가 *맹목* 이 된다 — 라이브 워커는 vitest 사각.

---

## 10. SSE 스트림 정산·타임아웃 (R1 운영 B5 해소)

- **시작 시 maxTokens reserve, 종료 시 settle**(§6-1). 스트림 도중 budget 0 이 돼도 *그 스트림은* 예약분 안에서 완주(over-run 0), 다음 요청부터 차단.
- **워커 die 대비**: SSE 가 중간에 끊기면 클라이언트는 *idempotent retry 안 함*(중복답 방지) — "끊김" 표시 후 onDevice 폴백은 명시적 사용자 액션(01 §6-2).
- **전체 타임아웃 예산**(01 §6-3): edge health + 생성이 총 예산 초과면 즉시 deterministic. CF Workers CPU/duration 한계(무료 더 빡빡)에 8B 장문이 부딪히면 maxTokens 로 선제 절단.
