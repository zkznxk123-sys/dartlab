# 질문 수집 Worker (questionCollector)

공시 Q&A 코파일럿의 **opt-in 사용자 질문**을 HF 데이터셋 raw 샤드로 모으는 Cloudflare Worker.
정적사이트(GitHub Pages)는 런타임 쓰기가 불가해 이 작은 수신단이 유일한 백엔드다.

## 왜 필요한가

질문 수집 = 모델 라우팅을 *실사용 어휘*로 키우는 원천. 단 검증으로 입증된 사실:
**볼륨은 포화 — 효과는 "새 패턴/어휘" 커버에서만 난다.** 그래서 전량이 아니라 *불확실 쿼리*만 모으고,
운영자 review 게이트로 신규성만 `curatedQuestions.json` 에 승격한다(노이즈 자동유입 0). 자세한 설계: `.github/scripts/queries/PIPELINE.md`.

## 1회 배포 (운영자)

```bash
cd infra/workers/questionCollector
npm i @huggingface/hub
npx wrangler login
npx wrangler secret put HF_TOKEN     # write 권한 HF 토큰 — Worker secret 에만(클라이언트 노출 0)
npx wrangler deploy
```

배포 후 출력된 Worker URL 을 프론트에 알려준다:
- `landing/.env` 에 `VITE_FEEDBACK_URL=https://dartlab-question-collector.<account>.workers.dev` 추가 후 재빌드.
- 이 값이 없으면 프론트의 "질문 익명 기여" 토글은 **숨김**(수집 완전 비활성, prod 영향 0).

`wrangler.toml` 의 `ALLOW_ORIGIN` 을 실제 사이트 origin 으로 좁히면 CORS 남용을 막는다.

## 수집물

- 경로: `dart/queries/raw/{YYYY-MM-DD}/{uuid}.json` (질문당 1파일 = append 레이스 0)
- 내용: `{ q, intent, ts }` — **PII 0**(회사코드/식별자 미수집), 질문 본문 + 예측 intent 만.

## 재학습 루프

1. Worker → HF raw 적재 (사용자 opt-in 시에만).
2. `.github/scripts/queries/reviewRawQueries.py` → 미라우팅(route score 0)·신규 군집을 추려 운영자 review 용으로 출력(+소비분 정리).
3. 운영자가 의미있는 신규 질문만 `curatedQuestions.json` 에 intent 라벨 달아 추가.
4. push → `Intent Model Pipeline` 워크플로가 build+회귀게이트+HF 업로드 자동 → 프론트가 라이브 fetch.

→ 운영자 손은 3번(신규 군집 빠른 review)뿐. 나머지는 자동.
