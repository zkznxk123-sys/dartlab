# Channel

dartlab의 외부 공유 엔진. PC dartlab을 폰/외부 어디서나 그대로 쓰게 한다.
**dartlab의 5번째 정식 엔진** (Company / Scan / Analysis / Macro / Quant + Credit + Review + **Channel**).

| 항목 | 내용 |
|------|------|
| 레이어 | L4 (표현/접근) |
| 진입점 | `dartlab channel` |
| 기술 백엔드 | Microsoft DevTunnels (VS Code Remote Tunnels와 동일 인프라) |
| 폰 호환 | Android Chrome / iOS Safari 검증 (2026-04-07) |
| 영구 URL | `https://<id>-<port>.<region>.devtunnels.ms` |
| 요구 조건 | GitHub 계정 (1회 OAuth) |

## 한 줄 사용

```
dartlab channel
```

흐름:
1. winget으로 devtunnel CLI 자동 설치 (1~2분, 최초 1회)
2. GitHub OAuth (브라우저 자동 오픈, 최초 1회)
3. tunnel 자동 생성 + anonymous access + host 시작
4. URL + QR 출력
5. 폰 Chrome에 URL 입력 (또는 QR 스캔)

## 기술 스택

| 컴포넌트 | 선택 이유 |
|---|---|
| **Microsoft DevTunnels** | VS Code Remote Tunnels의 기반 인프라. MS 공식, **모바일 호환성 검증됨**. winget 자동 설치 가능 |
| **anonymous access entry** | 토큰 시스템 없이 URL만으로 접근 가능. dartlab CLI 자체로 인증 모델 단순화 |
| **devtunnel host** background process | 백그라운드 실행, atexit cleanup |

### 폐기된 백엔드 (왜 안 썼는가)

| 백엔드 | 폐기 이유 |
|---|---|
| Cloudflare Quick Tunnel (`*.trycloudflare.com`) | **모바일에서 fetch 응답 hang 버그.** 데스크탑은 OK인데 폰 LTE에서 응답 본문이 안 옴. [cloudflared#1385](https://github.com/cloudflare/cloudflared/issues/1385) |
| Cloudflare Named Tunnel | 도메인 필수 (사용자 거부) |
| Tailscale | 폰에 Tailscale 앱 설치 필요 (사용자 거부) |
| ngrok | 무료 1GB/월 제한 + 상업 이용 제약 |
| ssh (localhost.run) | 안정성 떨어짐, URL 매번 바뀜 |

## 자동화 파이프라인 (Phase A~G)

`src/dartlab/channel/devtunnel.py`

```
A. find_devtunnel_binary()
   PATH → ~/.dartlab/bin → Program Files → winget package dir 직접 스캔
   ↓ (없으면)
B. install_devtunnel(auto_yes)
   Windows: winget install Microsoft.devtunnel
            실패 시 https://aka.ms/TunnelsCliDownload/win-x64 직접 다운로드
   macOS  : brew install --cask devtunnel → fallback zip
   Linux  : curl https://aka.ms/DevTunnelCliInstall | bash
   ↓
C. ensure_logged_in(bin_path, auto_yes)
   devtunnel user show → "logged in" 검증
   미인증 → devtunnel user login -g (브라우저 자동 오픈, GitHub OAuth)
   ↓
D. ensure_tunnel(bin_path, port)
   ~/.dartlab/devtunnel-state.json 에서 tunnel_id 재사용
   없거나 검증 실패 → devtunnel create dartlab-<hostname> --allow-anonymous
   conflict → devtunnel list 에서 base_label 매칭으로 기존 ID 발견
   여전히 conflict → timestamp suffix 라벨로 재시도 (최대 3회)
   ↓
E. _ensure_port_mapping(bin_path, tunnel_id, port)
   devtunnel port create <id> -p <port> --protocol http
   "already exists" → 멱등 통과
   ↓
F. _ensure_anonymous_access(bin_path, tunnel_id)
   ★ 핵심: --allow-anonymous는 tunnel 생성 옵션일 뿐, 실제 접근은 access entry로 통제됨.
   devtunnel access create <id> --anonymous 를 명시 호출해야 폰 등 미인증 클라이언트가 통과.
   ↓
G. start_host(bin_path, tunnel_id, port)
   devtunnel host <id> Popen 백그라운드
   stdout 별도 thread로 폴링, [dt] 접두 콘솔 출력
   "Connect via browser: https://..." 정규식 매칭 → URL 추출
   atexit로 process terminate 등록
```

## 보안 모델

dartlab channel은 **anonymous reader 기본**. URL을 알면 누구나 접근 가능.

| 계층 | 메커니즘 |
|---|---|
| L0 네트워크 | DevTunnels — 인바운드 포트 0, outbound only. 공유기/방화벽 손 안 댐 |
| L1 인프라 | Microsoft 백엔드 — anti-phishing confirmation page, DDoS 방어 |
| L2 access entry | anonymous reader 명시 등록 (Phase F) |
| L3 (옵션) | 추후 `--auth-github` 옵션으로 GitHub access control 가능 |

**주의:**
- URL이 새면 접근 = 누구나 가능. 회수: `devtunnel tunnel delete <id>` → 다음 실행 시 새 URL
- dartlab 미들웨어(토큰/화이트리스트/레이트리밋)는 비활성. 단순한 모델 우선
- 운영용 공개 SaaS에는 부적합. **개인 PC를 자기 폰에서 쓰는 게 주 시나리오**

## 사용자 약속 — "한 줄이면 끝"

### 최초 실행

```
$ dartlab channel

  Channel 시작 — Microsoft DevTunnels
  devtunnel 미설치. 자동 설치하시겠습니까? [Y/n] y
  winget으로 devtunnel 설치 중... (1~2분)
  ✓ devtunnel 설치 완료
  GitHub 인증 필요. 브라우저가 자동으로 열립니다.
  ✓ devtunnel 인증 완료
  tunnel 생성: dartlab-msi-pc
  ✓ tunnel ID: dartlab-msi-pc.jpe1
  포트 매핑: 8400 → http
  ✓ anonymous 접근 허용
  devtunnel host 시작: dartlab-msi-pc.jpe1
  [dt] Hosting port: 8400
  [dt] Connect via browser: https://09t4mqdh-8400.jpe1.devtunnels.ms
  [dt] Ready to accept connections

  ✓ Channel 활성: https://09t4mqdh-8400.jpe1.devtunnels.ms/

╭──── DartLab Channel ────╮
│ ▓▓▓▓ QR ▓▓▓▓            │
│ URL  https://...        │
╰─────────────────────────╯
```

사람이 손대는 건 **최초 1회 GitHub OAuth 클릭**. 이후는 모두 자동.

### 2회차 이후

```
$ dartlab channel
  ✓ devtunnel 이미 인증됨
  기존 tunnel 재사용: dartlab-msi-pc.jpe1
  ✓ anonymous 접근 허용
  ✓ Channel 활성: https://09t4mqdh-8400.jpe1.devtunnels.ms/  ← 매번 같은 URL
```

영구 URL이라 폰 북마크 그대로 동작.

## 메시징 봇 (옵션 기능)

```
dartlab channel --telegram <BOT_TOKEN>
dartlab channel --slack <BOT_TOKEN> --slack-app-token <APP_TOKEN>
dartlab channel --discord <BOT_TOKEN>
```

`src/dartlab/channel/adapters/`의 어댑터 백그라운드 실행. 메시징 앱에서 dartlab AI에 직접 질문 가능.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `winget 실패 (rc=2316632084)` | winget 패키지 충돌 | MSI 직접 다운로드 fallback (자동) |
| `MSI 설치 실패 rc=1603` | admin 권한 부족 | PowerShell `Start-Process -Verb RunAs` (자동) |
| `Tunnel not found in jpe1` | tunnel ID 파싱 미스 | `~/.dartlab/devtunnel-state.json` 삭제 후 재실행 또는 `dartlab channel --reset` |
| `Conflict with existing entity` | 같은 라벨 중복 | `devtunnel list`에서 자동 발견 또는 timestamp suffix |
| 폰에서 anti-phishing 페이지 | 첫 접속 confirmation | "Continue" 1번 클릭 (이후 쿠키) |
| 폰에서 화면 안 뜸 | dartlab UI 모바일 깨짐 | dartlab 0.x 빌드 확인. legacy plugin 적용된 빌드인지 |

## 검증된 진단 사례 — 우리가 개고생한 이유 (2026-04-06 ~ 04-07)

> **이건 dartlab 특유의 문제가 아니라 일반 Svelte 5 SPA에서 누구나 부딪칠 수 있는 함정이다. 다음에 비슷한 증상이 보이면 여기 먼저 확인할 것.**

### 사건 개요

- **데스크탑 Chrome OK / Android Chrome NG.**
- 서버 로그(PowerShell) 모든 API 200 응답.
- 폰 Chrome에서 dartlab UI는 로드되는데 우상단 ProviderDropdown이 영원히 "확인 중..." 스피너만 돔.
- 버튼 클릭도 무반응.
- 같은 폰에서 다른 페이지(블로그)는 정상 동작.
- 8시간 이상 추적.

### 추적 단서들 (모두 잘못된 가설이었음)

| 시도한 가설 | 결과 |
|---|---|
| Cloudflare Quick Tunnel의 fetch hang | 부분적으로 맞음. 모바일 LTE에서 Quick Tunnel은 fetch 응답이 지연되거나 손실되는 경향 있음. 그러나 진짜 원인은 아니었음 |
| 토큰 시스템(`token.js` + `authedFetch`) 누락 | 도입했지만 무관 |
| `_WHITELIST_PATTERNS` 화이트리스트 좁음 | 확장했지만 무관 |
| `share.py` import 순서 → TokenManager 두 인스턴스 | 진짜 버그였지만 모바일 스피너와는 별개 |
| Svelte 5 `$state` getter 패턴 reactivity 끊김 | 부분적. _core 객체로 통합했지만 진짜 원인은 아님 |
| `$effect`/`onMount` 모바일 미발화 | 가설일 뿐, 실제로는 발화함 |
| `$state` proxy → 폰 Chrome 옛 버전 호환성 | 가설. legacy plugin + es2020 target 적용. 부분 효과 |
| Svelte 5.0.0 → 5.55.1 + vite-plugin-svelte 5 → 6.2.4 업그레이드 | 안정성 향상은 됐지만 직접 원인 아님 |
| `stopPropagation()` + Svelte 5 body delegation 충돌 | 일부 케이스 영향. 제거했지만 직접 원인 아님 |

### 진짜 원인 — `<Settings>` 아이콘 ReferenceError

**lucide-svelte 0.575+ 에서 `Settings` 아이콘이 deprecated → 완전 제거됨.**

dartlab 코드에 다음 사용처가 남아있었음:
- `App.svelte` `<Settings size={18}>`
- `CompanyContextBar.svelte` import 잔재
- `SearchModal.svelte` 의 quick action 데이터: `{ id: "openSettings", icon: Settings, ... }`

**데스크탑 Chrome**: tree-shaking + dead-code 관용으로 어떻게든 동작
**모바일 Chrome**: 빌드된 번들에서 `Settings`가 미정의 → **`Uncaught ReferenceError: Settings is not defined`** → 모듈 평가 단계에서 throw → **SPA 전체 hydration 실패** → DOM은 그려지지만 모든 reactivity/이벤트 핸들러가 안 붙음 → "스피너 영원, 버튼 무반응"

### 결정적 단서 (사용자가 던진 두 마디)

1. **"블로그(landing/)는 모바일에서 잘 됨"**
   - 같은 Svelte, 같은 폰. dartlab만 깨짐 → dartlab 코드 자체에 모바일 특이 문제가 있다 확정
   - dartlab `vite-plugin-svelte 5.0.0` vs 블로그 `6.2.4` 차이 발견 → 업그레이드 (도움은 됐지만 결정타 아님)

2. **"test 페이지는 데스크탑 viewport일 땐 됐었음"**
   - test3.html 만들어서 `window.addEventListener('error', ...)` 핸들러 박음
   - 폰에서 열어보니 진단 패널에 **`ERR: Uncaught ReferenceError: Settings is not defined @ index-XXX.js:2026`** 출력
   - 8시간 만에 진짜 원인 확정

### 진단법 (다음에 비슷한 증상 만나면)

1. **폰 콘솔 직접 보기 어려움 → 진단 페이지를 따로 만들어라**
   - `build/test.html` 같이 단순 HTML + `window.addEventListener('error', ...)` 핸들러
   - 화면에 직접 에러 메시지 표시
2. **`document.title`을 진단 정보로 활용**
   - `document.title = "[" + step + "]"` 식으로 단계 박으면 폰 탭 제목으로 즉시 확인
3. **블로그/정적 페이지 비교**
   - 같은 폰에서 다른 SPA가 동작하면 → 코드 문제, 환경 문제 아님
4. **lucide-svelte 같은 외부 패키지의 deprecated export 의심**
   - 패키지 메이저 업데이트 후 이전엔 잘 됐던 게 깨지면 → import 일괄 grep
5. **데스크탑 ↔ 모바일 차이가 명확하면 syntax/runtime 에러 의심**
   - 데스크탑 V8은 dead-code 관용이 큼, 모바일 V8은 stricter
   - 빌드된 번들에서 `grep` 으로 deprecated symbol 찾기

### 부수적 fix들 (정상 정착 시 같이 적용된 것)

- `vite-plugin-svelte 5 → 6` + `svelte 5.0 → 5.55`
- `@vitejs/plugin-legacy` 도입 (es2020 target + nomodule fallback)
- `<Settings>` → `<Cog>` 일괄 교체
- ProviderDropdown 의 `stopPropagation()` 제거 (Svelte 5 body delegation 호환)
- `handleClickOutside`를 `<div onclick>` 대신 `document.addEventListener('click', ...)` 로 직접
- `getUiStore()` 모듈 싱글톤 패턴 (createUiStore factory + getter export)
- `_core` 단일 $state 객체로 핵심 reactive state 묶기
- AppShell `isMobile` 을 `$effect` 대신 `matchMedia` listener + module-level 즉시 평가
- 모바일 반응형: EmptyState/ChatArea 풀너비, 우상단 검색 숨김, 하단 nav `position: fixed`

### 한 줄 요약

> **lucide-svelte의 `Settings` 아이콘이 사라진 걸 모르고 코드에 남겨둔 게 진짜 원인이었다.**
> 8시간을 fetch/CORS/token/Svelte reactivity로 헛수고. 진단 패널에 onerror 한 줄이 전부였다.

## ops 문서 사상

- **진입점 1개** — `dartlab channel`
- **백엔드 1개** — Microsoft DevTunnels (다른 백엔드는 폐기 검증됨)
- **자동화 파이프라인** — 사람 손은 GitHub OAuth 1번
- **dead-code 0** — 모든 path가 진짜 사용됨

## 관련 코드

| 파일 | 역할 |
|---|---|
| `src/dartlab/cli/commands/channel.py` | CLI 진입점 (`dartlab channel`) |
| `src/dartlab/channel/devtunnel.py` | Phase A~G 자동화 |
| `src/dartlab/channel/__init__.py` | `setup_devtunnel` re-export |
| `src/dartlab/channel/adapters/` | 메시징 봇 (telegram/slack/discord) — 옵션 |
| `ui/web/src/lib/components/ProviderDropdown.svelte` | 모바일 호환 검증된 reactive 패턴 |
| `ui/web/src/lib/stores/ui.svelte.js` | `_core` $state 단일 객체 + `getUiStore()` 모듈 싱글톤 |
| `ui/web/vite.config.js` | `@vitejs/plugin-legacy` + es2020 target |
| `ui/web/package.json` | `svelte ^5.55.1`, `@sveltejs/vite-plugin-svelte ^6.2.4` (블로그와 동일) |

## 검증 (사용자 셀프 테스트 통과 — 2026-04-07)

- ✅ Windows 11 + winget devtunnel 자동 설치
- ✅ GitHub OAuth 1회 인증
- ✅ 영구 tunnel ID 재사용 (재실행 시 같은 URL)
- ✅ Conflict 자동 해결 (`devtunnel list` fallback)
- ✅ Anonymous access entry 자동 등록
- ✅ Android Chrome (KT LTE) 정상 동작
  - dartlab UI 렌더
  - ProviderDropdown 정상 표시 (`oauth-codex`)
  - AI 질문 → 스트리밍 응답 OK (POST /api/ask 200)
  - 모바일 반응형 (EmptyState/ChatArea 풀너비, 하단 탭바 fixed)

## 비범위 (Phase 2)

- GitHub access control 자동화 (`--auth-github`)
- VSCode 확장에서 channel 토글
- HF Space로 옮겨 PC 끄기 옵션
- 메시징 봇과 channel URL 자동 연동
