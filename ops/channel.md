# Channel

**주체**: 사용자 · Channel 엔진 (`dartlab channel`).
**현재**: Microsoft DevTunnels 자동화 파이프라인 (Phase A~G) · GitHub OAuth 1회 · anonymous access entry · 영구 URL 재사용.
**방향**: `--auth-github` access control · VSCode 확장 통합 · HF Space 이관 옵션.

PC dartlab 을 폰·외부 어디서나 그대로 쓰게 하는 공유 엔진.

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

## 모바일 호환 진단 가이드

Svelte 5 SPA 의 모바일 전용 hydration 실패 유형을 진단할 때 유용한 패턴.

### 대표 증상

- 데스크탑 Chrome 정상, 모바일 Chrome 에서 화면은 렌더되지만 상호작용 전체가 멎음 (버튼 무반응, 스피너 영원).
- 서버 로그 상 모든 API 200 응답.
- 같은 폰에서 다른 SPA (예: 정적 블로그) 는 정상 동작.

### 일반적 근본 원인

- 외부 패키지의 deprecated export 가 번들에 남아 런타임 `ReferenceError` 발생 → 모듈 평가 단계 throw → SPA 전체 hydration 실패.
- 데스크탑 V8 은 dead-code 에 관용적이라 우회되나, 모바일 V8 은 stricter 하게 reject 하는 경향.

### 진단법

1. **폰 콘솔 접근이 어렵다 → 진단 페이지를 별도로 제공**. 단순 HTML + `window.addEventListener('error', ...)` 핸들러로 화면에 에러 메시지 직접 표시.
2. **`document.title` 을 진단 정보로 활용**. `document.title = "[" + step + "]"` 로 단계 표기 → 폰 탭 제목에서 즉시 확인.
3. **블로그/정적 페이지 비교**. 같은 폰에서 다른 SPA 가 동작하면 환경 문제가 아닌 코드 문제로 좁힘.
4. **lucide-svelte 등 외부 패키지의 deprecated export 의심**. 메이저 업데이트 후 이전에 잘 됐던 게 깨지면 import 일괄 grep.
5. **데스크탑 ↔ 모바일 차이가 명확 → syntax/runtime 에러 의심**. 빌드 번들에서 deprecated symbol grep.

### 기본 설정

안정적 모바일 호환을 위해 다음 기본 조합을 유지한다:

- `svelte ^5.55` + `@sveltejs/vite-plugin-svelte ^6.2`.
- `@vitejs/plugin-legacy` (es2020 target + nomodule fallback).
- `getUiStore()` 모듈 싱글톤 패턴 (createUiStore factory + getter export).
- `_core` 단일 `$state` 객체로 핵심 reactive state 묶기.
- `AppShell.isMobile` 은 `$effect` 대신 `matchMedia` listener + module-level 즉시 평가.
- 모바일 반응형: EmptyState/ChatArea 풀너비, 우상단 검색 숨김, 하단 nav `position: fixed`.

## 설계 원칙

- **진입점 1개** — `dartlab channel`
- **백엔드 1개** — Microsoft DevTunnels
- **자동화 파이프라인** — 사람 손은 GitHub OAuth 1번
- **dead-code 0** — 모든 path 실사용 확인

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

## 검증된 경로

- Windows 11 + winget devtunnel 자동 설치.
- GitHub OAuth 1회 인증 후 tunnel ID 재사용 (재실행 시 같은 URL).
- Conflict 자동 해결 (`devtunnel list` fallback).
- Anonymous access entry 자동 등록.
- Android Chrome (LTE) 에서 dartlab UI 렌더 · ProviderDropdown · AI 질문 스트리밍 · 모바일 반응형 정상.

## 비범위 (Phase 2)

- GitHub access control 자동화 (`--auth-github`)
- VSCode 확장에서 channel 토글
- HF Space로 옮겨 PC 끄기 옵션
- 메시징 봇과 channel URL 자동 연동
