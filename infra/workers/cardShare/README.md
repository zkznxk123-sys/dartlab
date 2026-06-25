# dartlab-card-share — 캐러셀 공유/OG 동적 워커

스레드·인스타·카톡·X 에 캐러셀 링크를 공유하면 **첫 슬라이드가 미리보기(OG)** 로 뜨고, 누르면 **그 캐러셀로 바로 이동**하게 하는 엣지 엔드포인트.

## 왜 워커인가 (정공법)
캐러셀 SSOT 는 hfMedia(`carousels/index.json`, 라이브 발행)다. landing 정적 빌드엔 캐러셀 데이터가 없다.
정적 사이트에 캐러셀마다 OG HTML 을 굽는 방식은 라이브 데이터를 정적 빌드에 복사·박제(drift + 캐러셀마다
재배포)라 우회다. 이 워커는 요청 시점에 SSOT 를 라이브로 읽어 OG 만 낸다 — **워커·landing 재배포 0**.
`/cards` 가 브라우저에서 hfMedia 를 읽는 것과 동일 원리를 크롤러용으로 서버사이드에서 하는 것.

## 동작
- `GET /c/<slug>`:
  1. `carousels/index.json` 라이브 read(엣지 캐시 10분 — index 는 가변).
  2. slug 로 캐러셀 → `og:title`(제목) · `og:description`(캡션 첫 문단) · `og:image`(첫 슬라이드 이미지).
     - 이슈 카드: 이미지가 `issues/<slug>/...` hfMedia 경로라 그대로.
     - 회사 카드: `companies/index.json` 으로 semantic 파일명 해석.
  3. 크롤러는 메타만, 사람은 `LANDING_BASE/cards?post=<slug>` 로 즉시 리다이렉트.
- 없는 slug → `/cards` 로 리다이렉트(graceful).

## 배포
```
cd infra/workers/cardShare
wrangler deploy
```
secret 불필요(공개 dartlab-media 만 읽음). 배포 후 워커 URL(`https://dartlab-card-share.<account>.workers.dev`)을
landing 빌드 env `VITE_DARTLAB_CARD_SHARE_BASE` 에 넣으면 /cards 공유 버튼이 `/c/<slug>` 링크를 복사한다
(미설정 시 공유 버튼은 `/cards?post=<slug>` 딥링크로 graceful — OG 미리보기만 일반).

## 한 번 배포 → 영구
워커 1회 deploy + landing env 1회 설정 후, 새 캐러셀은 데이터(carousels/index.json)만 올리면
그 공유 링크가 즉시 작동한다(추가 배포 0).
