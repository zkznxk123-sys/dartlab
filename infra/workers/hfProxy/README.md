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
- `GET /news?code=XXXXXX[&q=회사명]` → 종목 뉴스 헤드라인. byCompany 아카이브(private
  `dartlab-news-private`, 네이버 스니펫)를 read-only 토큰으로 서버사이드 read + (q 있으면) 네이버 검색 API
  회사명 라이브 헤드라인(`track:'naver'`, 스니펫 O)을 url-dedup 머지(조회시점 최신). 가드: code 형식검증
  (영숫자 ≤12) + code+q 10분 엣지 캐시. HF_NEWS_TOKEN 없어도 q + 네이버 시크릿 있으면 라이브만으로 동작.
- `GET /market-news?market=KR|US` → 시장 전반 최신 헤드라인 라이브 오버레이. 네이버 검색 API 를 시장
  키워드(증시·코스피·환율 등) fan-out fetch + 파싱(`gather/sources/naverNews.py` 규칙 동일) 해
  `{market, asOf, items:[{date,title,source,url,description}]}` 반환. 프런트(`marketNewsSource`)가 HF
  누적 shard 위에 url-dedup 머지 → cron(일 2회) 사이 갭을 10분급으로 메움. 가드: market 검증(KR/US) +
  10분 엣지 캐시 + 실패 시 빈배열. 네이버 시크릿(아래) 필요.
  ※ Google News RSS 는 CF Workers outbound IP 에서 503(데이터센터 봇 차단)이라 라이브로 못 씀 — 네이버로 전환.
- `GET /market-filings` → 당일 시장 전체 공시 라이브 오버레이. DART list.json(`opendart.fss.or.kr`)을
  corp_code 없이 당일(KST) 호출 = 전체 시장 공시(stock_code 포함, market_recent 와 동일 스키마). page 1·2
  = 최근 200, rceptNo desc. `{asOf, items:[{rceptNo,rceptDate,stockCode,corpName,reportNm,filer}]}` 반환.
  프런트(`nonRegularFilingsSource`)가 HF 누적 위에 rceptNo-dedup 머지 → 시장 피드 + 종목 필터(stockCode) 한 소스.
  가드: 10분 버킷 캐시 + 빈 결과 캐시 안 함. DART_API_KEY 시크릿 필요. **브라우저 UA 필수**(CF 기본 UA 는 DART 가
  error1.html 로 무한 리다이렉트 차단).

### 뉴스·공시 시크릿 (byCompany read + 네이버/DART 라이브)
```bash
cd infra/workers/hfProxy
# byCompany 아카이브(private 데이터셋) read — /news 의 base 레이어
CLOUDFLARE_API_TOKEN=*** CLOUDFLARE_ACCOUNT_ID=*** npx wrangler secret put HF_NEWS_TOKEN
# 네이버 검색 API 라이브(/news?q= · /market-news 오버레이) — id·secret 2개
CLOUDFLARE_API_TOKEN=*** CLOUDFLARE_ACCOUNT_ID=*** npx wrangler secret put NAVER_CLIENT_ID
CLOUDFLARE_API_TOKEN=*** CLOUDFLARE_ACCOUNT_ID=*** npx wrangler secret put NAVER_CLIENT_SECRET
# DART open API 라이브 당일 공시(/market-filings)
CLOUDFLARE_API_TOKEN=*** CLOUDFLARE_ACCOUNT_ID=*** npx wrangler secret put DART_API_KEY
```
모두 graceful — 시크릿 없으면 해당 라이브 생략(프런트는 HF 누적 base 유지). 프런트 전환 env:
```
VITE_DARTLAB_NEWS_PROXY=https://dartlab-hf-proxy.<subdomain>.workers.dev/news
VITE_DARTLAB_MARKET_NEWS_PROXY=https://dartlab-hf-proxy.<subdomain>.workers.dev/market-news
VITE_DARTLAB_MARKET_FILINGS_PROXY=https://dartlab-hf-proxy.<subdomain>.workers.dev/market-filings
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
