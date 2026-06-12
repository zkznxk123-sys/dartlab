# 사이트 신호 Worker

공개 문서 사이트의 사용성 신호를 Cloudflare D1에 **집계 counter로만** 누적하는 Worker다.

## 저장 원칙

- 원시 이벤트 row를 append 저장하지 않는다.
- 원시 IP, User-Agent 원문, 세션 ID, 검색어 원문, 입력값, 세션 리플레이를 저장하지 않는다.
- D1에는 `signalDate × path × eventName × bucket × target` counter만 남긴다.
- 공개 사이트가 읽는 값은 별도 집계 JSON(`landing/static/site-signals/*.json`)이다.

## 이벤트 allowlist

| eventName | bucket | target |
|---|---|---|
| `pageView` | 없음 | 없음 |
| `dwell` | `0-10s`, `10-30s`, `30-120s`, `120s+` | 없음 |
| `scrollDepth` | `25`, `50`, `75`, `100` | 없음 |
| `ctaClick` | 없음 | 버튼/링크 id |
| `viewerOpen` | 없음 | route family |
| `dataDownload` | 없음 | 파일 종류 |

## 배포 절차

```bash
cd infra/workers/siteSignals
wrangler d1 create dartlab-site-signals
```

생성된 `database_id`를 `wrangler.toml`에 넣은 뒤:

```bash
wrangler d1 execute dartlab-site-signals --remote --file schema.sql
wrangler deploy
```

프로덕션 사이트 배선은 별도 변경에서 `VITE_SITE_SIGNALS_URL`로 Worker URL을 주입한다. 이 값이 없으면 프론트 수집 코드는 호출하지 않는다.

## 요청 예시

```bash
curl -X POST https://dartlab-site-signals.<subdomain>.workers.dev \
  -H "Content-Type: application/json" \
  -d '{"eventName":"pageView","path":"/viewer/company/005930"}'
```

성공 응답은 `ok`다.

## 공개 집계

공개 화면(`/site-signals`)은 원시 D1을 직접 읽지 않는다. 별도 집계 작업이 D1에서 표본 기준을 통과한 값만 JSON으로 내보낸 뒤 `landing/static/site-signals/rolling.json`에 둔다.
