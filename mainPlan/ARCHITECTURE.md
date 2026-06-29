# DartLab 아키텍처 설계도

> **한 줄:** 한국 DART + 미국 SEC EDGAR 공시를 구조화 데이터로 바꿔, "종목코드 하나로 회사 전체 스토리"를
> AI·Python·CLI·웹으로 보여주는 오픈소스 금융분석 플랫폼. (v0.10.7 기준)

상태 범례: ✅ 안정/운영 · 🔶 진행중 · ⏳ 대기/미배선

마지막 갱신: 2026-06-29 (왓처·알림 P1 코드 완료 시점)

---

## 1. 전체 레이어 (데이터 → 엔진 → 공유 UI → 소비자 → 엣지)

```
┌─ 데이터 소스 ────────────────────────────────────────────────────────────┐
│  DART(한국)   EDGAR(미국)   gov(KRX 가격·지수)   HuggingFace parquet(사전빌드)   │
│                                          Naver(최신 시세)  GDELT/Naver(뉴스)    │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ providers/ · gather/ (자격증명·소스 단일진입)
                               ▼
┌─ ② Python 코어  src/dartlab/  ★ 두뇌 ─────────────────────────── ✅ ─────┐
│  core(Company·panel) · frame(재무 28표준계정 정규화) · credit(dCR 등급)        │
│  analysis · macro · quant · scan · industry · simulate                      │
│  story/ ─ buildStory · thesis.py(ROIC−WACC 인과) · report.py(ReportModel) 🔶 │
│  pipeline/(L4 오케스트레이션) · skills/(Skill OS) · synth/(P3 왓처 자리 ⏳)    │
│                                                                            │
│  ├─ mcp/   MCP 서버 (ask·EngineCall·RunPython…) ─ Claude/Cursor 연결  ✅     │
│  ├─ cli/   `dartlab ai` 등 CLI                                       ✅     │
│  └─ server/ FastAPI ─ SPA 서빙 + /api(panel·export·AI SSE)           ✅     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ 같은 데이터를 "포트 계약"으로 추상화
                               ▼
┌─ ③ 공유 UI  ui/packages/ ─ 공개·로컬이 같은 코드 ────────────────── 🔶 ───┐
│  contracts/  DartLabRuntime 포트 타입 SSOT(company·price·finance·ai…)  ✅   │
│  runtime/    어댑터 ─ local(/api+HF) · public(HF직독) · test            ✅   │
│  surfaces/   terminal ✅  |  viewer 🔶  scan 🔶  map ⏳ (단계적 추출)        │
│  design/ format/  토큰·포맷                                            ✅   │
└───────────────┬───────────────────────────────────┬───────────────────────┘
                ▼                                   ▼
┌─ ④a 공개 사이트 landing/ ─ GitHub Pages ─ ✅ ┐   ┌─ ④b pip 터미널 ui/apps/local/ ─ 🔶 ┐
│  blog·cards(카드뉴스)·report·terminal·scan │   │  `dartlab ai` 가 서빙(SvelteKit SPA) │
│  ·map·screener·search·compare…             │   │  React ui/web 회수(legacy) ⏳         │
│  런타임 = public(HF 직독)                  │   │  런타임 = local(/api + HF)            │
└────────────────────────────────────────────┘   └──────────────────────────────────────┘
                │ (공개 사이트는 Cloudflare 엣지 워커로 데이터 보강)
                ▼
┌─ ⑤ 엣지 워커  infra/workers/ (Cloudflare) ───────────────────────────────┐
│  hfProxy ✅ (HF range+뉴스·시세 오버레이)  siteSignals ✅  cardShare ✅       │
│  questionCollector ✅            pushHub ★신규 (P1 알림 허브) 🔶              │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 핵심 설계 원리

- **포트 계약 SSOT** — `ui/packages/contracts/DartLabRuntime` 가 모든 데이터 접근을 인터페이스로 정의.
  공개(landing)·로컬(pip)은 같은 surface 코드를 쓰고, 어댑터(`runtime/adapters/{local,public,test}`)만 갈아끼운다.
- **하이브리드 데이터 전략** — 공개 자산(price·finance·macro·report)은 HF parquet 직독, 로컬 전용(panel viewer·export·AI streaming)만 `/api`.
- **런타임-SSOT** — gather/scan 직독, 베이크 0. 데이터 사본을 만들지 않는다.
- **단계적 추출** — UI 이주는 surface 단위로(terminal→viewer→scan→map) 점진 진행. 미배선은 `notWiredYet` 으로 정직 표기.

---

## 3. 왓처·알림 P1 — 새로 깔린 줄기 (2026-06-29)

발행 → 알림 발송 → 폰 수신의 한 줄기. 상세설계: `mainPlan/watcher-notify-platform/`.

```
  글/카드 발행(git push: blog/**/index.md · _issues/**/cards.plan.json)
        ▼
  GitHub Actions  notify-publish.yml          🔶 코드 ✅ / 배포 대기
     .github/scripts/notify/  detect→payload→/send (Bearer + 결정적 nonce)
        ▼
  pushHub Worker  /send                        🔶 코드 ✅ / 미배포
     VAPID JWT ES256 서명 + aes128gcm(RFC 8291) 암호화 → FCM/Apple/Mozilla
        ▼
  브라우저  service-worker.ts (push 리스너)     🔶 코드 ✅
     showNotification → 클릭 → /dartlab/blog/{slug}
        ▲ 구독: NotifyOptIn.svelte → /subscribe → D1(subscriptions·topicSubs)
  사용자 "알림 켜기"
```

**P1 자동검증:** 발행 러너 pytest 8/8 · landing vitest 59/59 · svelte-check 0err · ruff pass.
**남은 SHIP 게이트(코드 밖):** VAPID 키 생성·secret 등록 → Worker 하네스 스캐폴드 → ece 실브라우저(Chrome+iOS) 졸업 → 배포 → 운영자 눈검수.
P1~P4 단계: P1=발행알림(현재) · P2=공개 토픽(신규수주) · P3=개인 왓처(로컬) · P4=모드B·패키징.

---

## 4. 디렉터리 빠른 지도

| 경로 | 역할 |
|---|---|
| `src/dartlab/` | Python 코어 엔진(providers·core·story·credit·scan·mcp·cli·server) |
| `ui/packages/contracts` | DartLabRuntime 포트 타입 SSOT |
| `ui/packages/runtime` | 어댑터(local·public·test) |
| `ui/packages/surfaces` | 공유 Svelte surface(terminal…) |
| `ui/apps/local` | pip `dartlab ai` 가 서빙하는 SvelteKit 앱 |
| `landing/` | 공개 사이트(GitHub Pages, BASE_PATH=/dartlab) |
| `infra/workers/` | Cloudflare 엣지(hfProxy·siteSignals·cardShare·questionCollector·pushHub) |
| `blog/` | 블로그·카드뉴스 콘텐츠(frontmatter + carousel) |
| `mainPlan/` | 설계 문서(이 파일 + watcher-notify-platform 등) |

---

## 5. 현재 상태 한 장 요약

1. **엔진(Python)은 성숙** — 안정 운영 중(v0.10.7).
2. **UI는 "공개+로컬 한 코드 통일" 대공사 중간** — terminal 끝, viewer·scan 진행, map 남음.
3. **알림(P1)은 새 줄기** — 코드 완성, 켜는 건(배포) 다음 단계.
