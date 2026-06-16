# dartlab-hf-proxy — HF parquet 레인지 프록시 Worker

정적 프런트(GitHub Pages, `landing/`)가 HuggingFace `eddmpython/dartlab-data` 의 parquet 을
HTTP Range 로 직독할 때, 콜드 HF CDN 의 간헐 403/429/5xx 를 엣지에서 재시도로 흡수하고
HF URL 을 단일 SSOT 로 묶는 경량 프록시.

## 무엇을 하나
- `GET /hf/<dataset-path>` → `https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main/<dataset-path>` 로 프록시.
- `Range`/`If-Range`/`If-None-Match` 전달, `Content-Range`/`Accept-Ranges`/`Content-Length`/`x-linked-size`/`206`/`304` 보존·재발급 (hyparquet 의존 헤더).
- 403/429/5xx 시 서버측 재시도(최대 4회, 지수 백오프).
- CORS + `Access-Control-Expose-Headers`(range 헤더) 부착.
- `GET /naver?code=XXXXXX` → 네이버 fchart 일별 OHLCV(가격 fresh-tail). 키 불필요(공개 차트 API).
- `GET /news?code=XXXXXX` → 종목 뉴스 헤드라인(제목+스니펫+원문링크). private 데이터셋
  (`dartlab-news-private`)을 read-only 토큰으로 서버사이드 read 해 반환(라이브 표시 = 의도된 용도,
  공개 벌크 재배포 아님). 가드: code 형식검증(영숫자 ≤12) + 10분 엣지 캐시 + 토큰 미설정 시 빈배열 noop.

### /news 시크릿 (private 데이터셋 read)
```bash
cd infra/workers/hfProxy
CLOUDFLARE_API_TOKEN=*** CLOUDFLARE_ACCOUNT_ID=*** npx wrangler secret put HF_NEWS_TOKEN
# → dartlab-news-private 에 대한 read-only 토큰 입력 (피해 범위 최소화)
```
시크릿 없이 배포해도 `/news` 는 빈배열 noop 으로 안전(배선 먼저, 토큰은 나중). 프런트 전환 env:
```
VITE_DARTLAB_NEWS_PROXY=https://dartlab-hf-proxy.<subdomain>.workers.dev/news
```

## 무엇을 안 하나 (의도적)
- 부분응답(206)을 CF Cache API 에 직접 put 하지 않는다 — 잘못된 바이트 위험. 레인지 캐시는 브라우저(URL+Range 키, 정확)에 맡긴다.
- R2/KV 미사용 (무료 티어 Workers + 브라우저 캐시로 충분). 후속: 작은 인덱스 parquet(corpList·valuation·changes·finance-lite)만 R2 미러 검토.

## 배포 (1회)
저장소 루트 `.env` 의 `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` 사용 (대화형 로그인 불필요):

```bash
cd infra/workers/hfProxy
CLOUDFLARE_API_TOKEN=*** CLOUDFLARE_ACCOUNT_ID=*** npx wrangler deploy
```

배포되면 `https://dartlab-hf-proxy.<subdomain>.workers.dev` 가 뜬다.

## 프런트 전환 (단일 스위치)
`landing/.env` (및 `.github/workflows/docs.yml` 빌드 env) 에:

```
VITE_DARTLAB_HF_RESOLVE=https://dartlab-hf-proxy.<subdomain>.workers.dev/hf
```

`landing/src/lib/data/hfRange.ts`(및 동일 base URL 을 쓰는 로더들)가 이 env 를 읽으므로 한 줄로 전체 전환된다.
문제 시 env 를 비워 즉시 HF 직결로 롤백 — 가역적. (URL SSOT 통합 = workbench origin.ts 후속 작업.)

## 한도 (무료 티어)
- Workers 10만 req/day. parquet 1개 열 때 footer+청크로 수 회 range → 무거운 스캔 세션은 빠르게 소진 가능.
  소진 시 env 비워 HF 직결로 폴백. 모니터 후 필요하면 R2 미러로 req 수 감축.
