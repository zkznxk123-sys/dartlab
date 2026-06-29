# 왓처·알림 — 다음 할 일 (resume point)

마지막 작업: 2026-06-29. 브랜치 `feat/watcher-notify-p1` (포크 origin 푸시됨). 상태는 [05-progress-ledger.md](05-progress-ledger.md).

## 지금까지 (DONE)
- P1 코드 전체 구현 + 자동검증(pytest 8/8 · vitest 59/59 · svelte-check 0err · ruff).
- Worker 배포 라이브: `https://dartlab-push-hub.zkznxk123.workers.dev` (Cloudflare zkznxk123@gmail.com, D1 `8893927a-...`).
- **end-to-end 실배달 검증(Chrome/localhost)**: 구독→/send→VAPID+aes128gcm→FCM(sent:1)→SW→macOS 알림 표시 성공.

## 라이브 워커 메모 (재개 시 참고)
- 공개키(VAPID_PUBLIC_KEY): `BAVOeCEd...` — wrangler.toml 에 기입됨. 개인키·SEND_TOKEN 은 Worker secret.
- 워커 ALLOW_ORIGIN: 커밋본 = `eddmpython.github.io`만. (로컬테스트 시 `wrangler deploy --var ALLOW_ORIGIN:"...,http://127.0.0.1:5173"` 로 임시 추가)
- 로컬 e2e: `landing/.env.local`(gitignore) + `npm run dev -w landing` + scratchpad `testSend.mjs`.

---

## A. P1 SHIP 잔여 게이트 (비차단)
- [ ] **iOS 16.4+ standalone 실기기 실배달** — Chrome 통과 ≠ Apple 수락(별 leg). 실기기에서 홈화면 추가 후 구독→발송.
- [ ] **Worker 테스트 하네스 스캐폴드** — `infra/workers/pushHub/TEST_SCAFFOLD.md` 절차(`npm create cloudflare` → vitest-pool-workers 버전핀 → 첫 green → `package-lock.json` 커밋). 커밋되면 `pushhub-test.yml` worker 잡 자동 활성.
- [ ] **운영자 눈검수** — NotifyOptIn/InstallPrompt 하단 바 겹침 스크린샷 확인.

## B. 공개 배포 — 방향 결정 필요 (포크만 제어 중)
- **옵션 A: upstream(eddmpython) PR** — 브랜치를 PR → 머지 + GitHub vars/secret 등록:
  - var `VITE_VAPID_PUBLIC_KEY` = `BAVOeCEd...`
  - var `VITE_PUSHHUB_URL` = `https://dartlab-push-hub.zkznxk123.workers.dev`
  - secret `PUSHHUB_SEND_TOKEN` = (워커와 동일 openssl 토큰)
- **옵션 B: 포크 self-host** (`zkznxk123.github.io/dartlab`):
  - [ ] 워커 `wrangler.toml` ALLOW_ORIGIN 을 포크 Pages origin 으로 변경 + 재배포
  - [ ] 포크 GitHub Pages 활성 + 위 vars/secret 등록
  - [ ] 포크 Actions 선택적 재활성 — `deploy-landing.yml`·`notify-publish.yml`·`pushhub-test.yml`만, **데이터 cron(govPrice·edgar·naver 등)은 비활성 유지**(secret 없어 실패 스팸)

## C. 이후 단계 (P2~P4)
- [ ] **P2 공개 왓처 토픽** — '신규수주' = `scan('orders')` book-to-bill≥1 threshold_cross diff → 브로드캐스트. 러너 `.github/scripts/notify/` (발행 러너와 별개), last-seen 커서 dedup.
- [ ] **P3 개인 왓처** — `tests/_attempts/watcherEval/` 졸업 → `src/dartlab/synth/watch/` + `WATCHER_REGISTRY`. `~/.dartlab/watch.json` 로컬 config. PNA 브리지 미들웨어.
- [ ] **P4** — 모드B(gist) + 소비자 패키징. 운영자 결정 게이트.

## 열린 결정
- [ ] **발송 트리거(#2)** — 수동 POST vs `blog/PIPELINE.md` 발행 cron 1줄. (현재 P1 워크플로는 push 트리거로 동작 — cron 은 선택)

---
*기타 dartlab 전반 다음거리(thesis/report 꼬리, UI 이주 map/scan 등)는 [../ARCHITECTURE.md](../ARCHITECTURE.md) 참고.*
