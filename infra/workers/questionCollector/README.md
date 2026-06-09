# 질문 수집 Worker (questionCollector)

공시 Q&A 코파일럿의 **opt-in 사용자 질문**을 HF 데이터셋 raw 샤드로 모으는 Cloudflare Worker.
정적사이트(GitHub Pages)는 런타임 쓰기가 불가해 이 작은 수신단이 유일한 백엔드다.

## 배포 상태 (2026-06-09)

- **라이브**: `https://dartlab-question-collector.eddmpython.workers.dev`
- HF_TOKEN secret 등록 완료 · `nodejs_compat` 플래그(wrangler.toml) 적용 · 엔드투엔드 검증(POST→`ok`, 노이즈/길이 거절 422) 통과.
- 프론트 연결: `VITE_FEEDBACK_URL` 이 **landing/.env(로컬) · docs.yml Build env(프로덕션)** 양쪽에 설정됨 → opt-in 토글 라이브(기본 OFF).
- Cloudflare 자격증명은 repo 루트 `.env` 의 `CLOUDFLARE_API_TOKEN`·`CLOUDFLARE_ACCOUNT_ID`(로컬 전용). 재배포는 아래 절차로 묻지 말고 직접.

## 왜 필요한가

질문 수집 = 모델 라우팅을 *실사용 어휘*로 키우는 원천. 단 검증으로 입증된 사실:
**볼륨은 포화 — 효과는 "새 패턴/어휘" 커버에서만 난다.** 그래서 전량이 아니라 *불확실 쿼리*만 모으고,
운영자 review 게이트로 신규성만 `curatedQuestions.json` 에 승격한다(노이즈 자동유입 0). 자세한 설계: `.github/scripts/queries/PIPELINE.md`.

## 재배포 / 업데이트 (운영자)

자격증명이 repo 루트 `.env` 에 있으므로(`CLOUDFLARE_API_TOKEN` write-Workers · `CLOUDFLARE_ACCOUNT_ID`),
대화형 `wrangler login` 없이 토큰 방식으로 배포한다. worker.js 또는 wrangler.toml 수정 후:

```bash
cd infra/workers/questionCollector
npm i @huggingface/hub
export CLOUDFLARE_API_TOKEN=$(grep -E '^CLOUDFLARE_API_TOKEN=' ../../../.env | cut -d= -f2-)
export CLOUDFLARE_ACCOUNT_ID=$(grep -E '^CLOUDFLARE_ACCOUNT_ID=' ../../../.env | cut -d= -f2-)
npx wrangler deploy
```

- **HF_TOKEN secret** 은 이미 등록됨(1회). 회전 시: `printf '%s' "$HF" | npx wrangler secret put HF_TOKEN` (`$HF`=.env 의 HF_TOKEN write 토큰).
- **`nodejs_compat`**: `@huggingface/hub` 가 node 빌트인(`fs/promises`·`url`)을 import → wrangler.toml 에 `compatibility_flags = ["nodejs_compat"]` 필수(이미 적용). 빼면 deploy 가 "Could not resolve" 로 실패.
- **CORS**: `wrangler.toml` 의 `ALLOW_ORIGIN`(현 `https://eddmpython.github.io`)을 실제 사이트 origin 으로 유지/조정.

> 토큰 부재로 막혔다는 보고 금지 — 자격증명은 .env 에 있다(memory `feedback_secrets_available_no_ask`).

### 처음부터 (자격증명 없을 때, 대안)

대시보드 `profile/api-tokens` → "Edit Cloudflare Workers" 템플릿으로 토큰 발급(Account Resources=본인 계정) + Account ID(Workers & Pages 우측) →
`.env` 에 `CLOUDFLARE_API_TOKEN`·`CLOUDFLARE_ACCOUNT_ID` 두 키 추가 → 위 토큰 방식 그대로.
대화형이 편하면 `npx wrangler login`(브라우저 OAuth) → `secret put HF_TOKEN` → `deploy`.

### 프론트 연결 (이미 완료)

- 로컬: `landing/.env` 의 `VITE_FEEDBACK_URL=<Worker URL>` (dev 서버 재시작해야 반영).
- 프로덕션: `.github/workflows/docs.yml` Build site 단계 env 에 동일 값(공개 URL, secret 아님).
- 이 값이 없으면 프론트 "질문 익명 기여" 토글은 **숨김**(수집 완전 비활성, prod 영향 0).

## 수집물

- 경로: `dart/queries/raw/{YYYY-MM-DD}/{uuid}.json` (질문당 1파일 = append 레이스 0)
- 내용: `{ q, intent, ts }` — **PII 0**(회사코드/식별자 미수집), 질문 본문 + 예측 intent 만.

## 재학습 루프

1. Worker → HF raw 적재 (사용자 opt-in 시에만).
2. `.github/scripts/queries/reviewRawQueries.py` → 미라우팅(route score 0)·신규 군집을 추려 운영자 review 용으로 출력(+소비분 정리).
3. 운영자가 의미있는 신규 질문만 `curatedQuestions.json` 에 intent 라벨 달아 추가.
4. push → `Intent Model Pipeline` 워크플로가 build+회귀게이트+HF 업로드 자동 → 프론트가 라이브 fetch.

→ 운영자 손은 3번(신규 군집 빠른 review)뿐. 나머지는 자동.
