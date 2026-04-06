# Channel

dartlab의 외부 접근 인프라. 로컬에서 도는 dartlab 서버를 외부 사용자가 안전하게 사용할 수 있게 한다.
"한 줄 명령으로 영구 URL이 뜨고, PC 재부팅해도 살아있는" 1인 SaaS 표준 스택.

| 항목 | 내용 |
|------|------|
| 레이어 | L4 (표현/접근) |
| 진입점 | `dartlab channel`, `dartlab channel --persistent` |
| 소비 | server (FastAPI), guide (안내), security (인증/감사) |
| 생산 | 외부 공개 URL + 메시징 어댑터(telegram/slack/discord) |
| 백엔드 | cloudflare(quick) / **cloudflare-named**(영구) / tailscale / ngrok / ssh |

## 채널의 정의

`channel/`은 두 가지를 묶은 개념이다:
1. **터널 백엔드** (`channel/tunnel.py`) — 로컬 포트를 외부 URL로 노출
2. **메시징 어댑터** (`channel/adapters/`) — telegram/slack/discord 봇으로 dartlab을 호출

`dartlab channel` CLI는 채널의 얼굴. 채널 자체를 강화하면 share가 자동으로 강해진다.

## 3-모드 체계

| 모드 | 백엔드 | URL | 사용처 | 보안 |
|------|--------|-----|--------|------|
| Quick | `cloudflare` | 매번 변경 (`*.trycloudflare.com`) | 30초 데모, 임시 공유 | 토큰 |
| **Persistent** | `cloudflare-named` | **영구** (`dartlab.<your-zone>` 또는 `<id>.cfargotunnel.com`) | **실제 운영, 1인 SaaS 표준** | 토큰 + (옵션) Zero Trust + WAF/DDoS |
| Tailscale | `tailscale` | `*.<tailnet>.ts.net` | 본인/지인 한정 (5명 내) | Tailnet 인증 |

선택 기준:
- 데모/스크린샷 1회 → **Quick**
- 외부 사용자에게 안정적으로 공개 → **Persistent** (디폴트 권장)
- 본인이나 가까운 지인 몇 명만 → **Tailscale**

## 사용자 약속 — "한 줄이면 끝"

### 최초 실행

```
$ dartlab channel --persistent
[guide] cloudflared 미설치 → winget으로 자동 설치 중...  ✓
[guide] CF 인증 필요 → 브라우저를 엽니다. Authorize 버튼 클릭하세요.  ✓
[guide] tunnel 생성: dartlab-msi-pc  ✓
[guide] DNS route 등록: dartlab.<your-zone>  ✓
[guide] 부팅 시 자동 시작 등록 (Windows 서비스)  ✓

  https://dartlab.your-zone.com   ← 영구 URL
  TTL: 무제한 / Tunnel: cloudflare-named / Auth: token + (선택) Zero Trust

Ctrl+C 로 종료
```

사람이 손대는 건 **최초 1회 브라우저 Authorize 클릭 1번**. 그 외는 dartlab이 전부 자동.

### 2회차 이후

```
$ dartlab channel --persistent
[guide] 저장된 tunnel 재사용: dartlab.your-zone.com  ✓
```

URL 동일. 메시징 봇/임베드 코드/북마크 그대로 살아있음.

## 자동화 플로우 (Phase A~H)

`channel/tunnel.py::CloudflareNamedTunnel`이 다음 8단계를 순차 실행한다.

| Phase | 메서드 | 역할 | 실패 시 guide 분기 |
|-------|--------|------|-------------------|
| A | `_ensure_binary` | cloudflared 자동 설치 (winget/brew/직접 다운로드 → `~/.dartlab/bin/`) | `onCloudflaredMissing(os)` |
| B | `_ensure_login` | `cert.pem` 확인 → 없으면 `cloudflared tunnel login` (브라우저 자동 오픈) | `onCloudflareLoginRequired()` |
| C | `_ensure_tunnel` | `tunnel_id` 재사용 또는 `tunnel create dartlab-<host>` | RuntimeError → `handleError(feature="share")` |
| D | `_ensure_route` | `--domain` 우선, 없으면 `*.cfargotunnel.com` fallback | 경고만 출력 후 진행 |
| E | `_write_config` | `~/.cloudflared/config-dartlab.yml` 작성 (SSE 보장: `disableChunkedEncoding: false`) | OSError → handleError |
| F | `_maybe_install_service` | `--install-service` 시 `cloudflared service install` (Windows/launchd/systemd) | 경고만 출력 후 포그라운드 진행 |
| G | `start` | `cloudflared tunnel run <id>` subprocess, stdout 폴링 | `onTunnelStartFailed(stderr)` |
| H | `stop` | 포그라운드 subprocess terminate (서비스는 끄지 않음) | — |

상태 저장: `~/.dartlab/tunnel-state.json` (`tunnel_id`, `tunnel_name`, `hostname`, `service_installed`).

### dry-run / no-service / yes 플래그

| 플래그 | 효과 |
|--------|------|
| `--dry-run` | 모든 phase가 명령 출력만, 실제 실행 X. 사용자 셀프 테스트 Stage 1의 첫 단계 |
| `--no-service` | Phase F 건너뜀. 포그라운드만 |
| `--yes` | 모든 사용자 확인 자동 승인 (CI/배치용) |
| `--install-service` | Phase F 강제 실행 |
| `--domain dartlab.foo.com` | Phase D에서 명시 도메인 사용 |

## 보안 모델

외부 노출 기능이라 다층 방어로 설계. 모든 계층이 동시 적용된다.

### 위협 모델
1. 링크 유출 — URL이 우연히 공유돼 제3자가 접근
2. 링크 추측 — 무작위 스캔/사전 공격
3. 악성 페이로드 — POST /api/ask로 LLM 키 소진/비용 폭탄
4. DDoS / 봇 트래픽 — 무차별 요청으로 PC 자원 고갈
5. 로컬 데이터 유출 — 외부 사용자가 의도치 않은 파일/엔드포인트 접근
6. CF 계정 탈취 — credentials 파일 유출 시 tunnel 도용

### 방어 계층

| 계층 | 메커니즘 | 위협 | 구현 |
|------|---------|------|------|
| L0 네트워크 | Cloudflare Tunnel **인바운드 포트 0**, 아웃바운드만 | 1, 2 | `cloudflared` 자체 |
| L1 엣지 | Cloudflare WAF/DDoS/Bot Fight (무료) | 4 | CF 자동 |
| L2 신원(옵션) | Cloudflare Zero Trust Access — Google/GitHub OAuth 게이트 | 1, 2 | Phase 2 (수동 등록) |
| L3 토큰 | `TokenManager` full / readonly 2종, HMAC 파생 | 1 | `server/security.py:101` |
| L4 권한 | `_POST_WHITELIST` 미들웨어 — POST 화이트리스트, readonly는 room read만 | 3 | `security.py:73` |
| L5 레이트리밋 | `SlidingWindowLimiter` — ask 10/min, company 30/min, global 100/min, SSE 동시 3 | 4 | `security.py:164` |
| L6 화이트리스트 | `_WHITELIST_PATTERNS` — 노출 라우트만 통과, 그 외 403 | 5 | `security.py:38` |
| L7 감사 로그 | `_write_audit` JSONL → `~/.dartlab/audit.jsonl` (ts/method/path/token_hash/status/duration/ip) | 사후 추적 | `security.py:302` |
| L8 이상 탐지 | `AnomalyDetector` — burst, 스크래핑, 에러율 → kill_switch 자동 발동 | 2, 4 | `security.py:230` |
| L9 TTL 킬스위치 | `TunnelKillSwitch` — `--ttl` 만료 시 자동 차단 | 잊고 켜둠 | `security.py:130` |
| L10 시크릿 | `~/.cloudflared/*.pem`/credentials JSON 권한 0600, .gitignore | 6 | tunnel.py phase B/C |
| L11 환경 격리 | tunnel 모드 시 `DARTLAB_TUNNEL=1` env → 위험 라우트 자동 비활성 | 5 | `is_tunnel_mode()` |

### 보안 기본값
- 화이트리스트는 **default deny**. 새 라우트는 명시적으로 추가해야 함.
- POST 허용 라우트는 `_POST_WHITELIST` + `_POST_PATTERNS` 명시적 매칭만.
- Readonly 토큰은 room read 5종(join/leave/heartbeat/chat/react)만 POST 허용.
- 첫 실행 시 `onShareSecurityWarning` 패널이 모드/호스트/권한/감사로그/종료법을 출력.

### 사고 발생 시 회수 절차
1. `Ctrl+C` 즉시 종료 (포그라운드 모드)
2. 서비스 모드라면: `cloudflared service uninstall`
3. tunnel 자체 폐기: `cloudflared tunnel delete <id>`
4. 토큰 회수: 서버 재시작 시 `TokenManager`가 새 토큰 발급
5. 감사 로그 분석: `~/.dartlab/audit.jsonl` grep으로 의심 IP/path 추적
6. 필요 시 `~/.dartlab/tunnel-state.json` 삭제 후 새 tunnel 재생성

## guide 통합

guide는 안내의 축. 모든 share 흐름은 guide를 거친다.

### checkReady
```python
from dartlab.guide import guide
guide.checkReady("share")                        # 기본
guide.checkReady("share", persistent=True)       # cloudflared/cert.pem 추가 점검
```
구현: `guide/readiness.py::_checkShare`. 서버 의존성(error) + persistent 시 cloudflared/cert.pem(warning).

### hint 함수
| 함수 | 호출 시점 | 출력 |
|------|----------|------|
| `onCloudflaredMissing(os_name)` | Phase A 실패 | OS별 설치 명령 + GitHub release 링크 |
| `onCloudflareLoginRequired()` | Phase B 진입 전 | 브라우저 인증 안내 + 무료 도메인 가입 안내 |
| `onTunnelStartFailed(stderr)` | Phase G 실패 | stderr 분석 → 1033/1034/530/502/cert/permission 매핑 |
| `onShareSecurityWarning(mode, hostname, readonly)` | start 직후 | 보안 요약 패널 (계층/감사로그/종료법) |

### handleError 통합
`guide.handleError(exc, feature="share")` — `guide/desk.py:handleError`에 share 분기 추가. cloudflared/tunnel/cert/login 키워드 자동 매칭. CLI 병목 1곳에서 모든 share 에러를 안내.

## 메시징 어댑터

기존 `channel/adapters/`의 telegram/slack/discord는 그대로 유지. share CLI 플래그로 백그라운드 시작:
```
dartlab channel --persistent --telegram <BOT_TOKEN>
```
어댑터는 별도 스레드 + asyncio 이벤트 루프로 실행. persistent URL과의 연동(봇이 URL을 사용자에게 안내)은 Phase 2.

## 운영 체크리스트

### 시작 전
- [ ] `dartlab status` — 데이터 준비 확인
- [ ] `dartlab channel --persistent --dry-run` — 실행될 단계 미리 확인
- [ ] CF 계정 + 도메인 1개 (없으면 fallback URL 사용)
- [ ] PC가 실제로 24시간 켜져 있는가?

### 운영 중
- [ ] 주 1회 `~/.dartlab/audit.jsonl` 검토 (이상 IP/path)
- [ ] 토큰을 우연히 채팅/스크린샷에 노출하지 않았는가?
- [ ] cloudflared 자동 업데이트 확인 (winget upgrade 또는 brew upgrade)

### 사고 대응
- [ ] Ctrl+C 또는 `cloudflared service uninstall`
- [ ] `cloudflared tunnel delete <id>`
- [ ] tunnel-state.json 삭제 → 재발급
- [ ] audit 로그로 영향 범위 확인

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `cloudflared not found` | PATH/로컬 경로 모두 없음 | `dartlab channel --persistent` 재실행 (자동 설치) 또는 `onCloudflaredMissing` 안내 따라 수동 설치 |
| Error 1033 | DNS 전파 대기 | 1~2분 후 재시도 |
| Error 1034 | Argo 비활성 | `cloudflared service start` 또는 재실행 |
| Error 530 | DNS route 미연결 | `cloudflared tunnel route dns <id> <hostname>` 수동 |
| Error 502 | 로컬 서버 다운 | dartlab 서버 켜졌는지 확인 (`dartlab status`) |
| SSE 끊김 | Quick Tunnel 사용 중 | `--persistent`로 전환 (config에 `disableChunkedEncoding: false`) |
| `cert.pem missing` | CF 미인증 | `dartlab channel --persistent` 재실행 → 브라우저 로그인 |
| Windows 서비스 등록 실패 | 관리자 권한 부족 | PowerShell을 관리자 권한으로 실행 후 `--install-service` |

## 테스트 게이트 (사용자 셀프 테스트)

> 코드 작성 ≠ 머지. 사용자 셀프 테스트가 끝난 후에만 머지한다.

### Stage 0 — 구현 + unit test (완료 시점에 머지 X)
- `tests/test_channel_named_tunnel.py` — subprocess 모킹 단위 테스트
- `tests/test_guide_share.py` — checkShare/hint 함수 단위 테스트

### Stage 1 — 사용자 로컬 dry-run
1. `dartlab channel` (Quick 회귀)
2. `dartlab channel --persistent --dry-run` — 단계 미리보기
3. `dartlab channel --persistent --no-service` — 포그라운드 시작
4. 발급 URL을 외부망(폰 LTE)에서 접근
5. SSE: `/api/ask` 스트리밍 끊김 없음
6. POST 차단(readonly default), `--write` 풀고 다시 차단 확인
7. 레이트리밋: curl 루프로 429 발생
8. 화이트리스트: 비허용 경로 403 확인
9. 감사 로그 `~/.dartlab/audit.jsonl` 항목 확인

### Stage 2 — 서비스 등록 후 재부팅
- `dartlab channel --persistent --install-service`
- PC 재부팅 → URL 그대로 살아있음 확인
- `cloudflared tunnel delete <id>` 회수 절차 1회 연습

### Stage 3 — 머지
- Stage 1, 2 모두 OK 보고 후
- ops/channel.md 확정 게시
- README 한 줄 추가

## 비범위 (Phase 2 이후)

- Cloudflare Zero Trust Access OAuth 게이트 자동화 (1단계는 문서만)
- VSCode 확장에서 share 토글 UI
- 메시징 봇과 persistent URL 연동 자동화
- HF Space로 옮겨 PC 끄기 옵션 (별도 아키텍처)
- 사용자 계정/멀티테넌시

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/channel/tunnel.py` | TunnelProvider ABC + 5개 백엔드 (Quick/Named/Tailscale/Ngrok/SSH) |
| `src/dartlab/channel/__init__.py` | export |
| `src/dartlab/channel/adapters/` | telegram/slack/discord 메시징 봇 |
| `src/dartlab/cli/commands/share.py` | `dartlab channel` CLI 진입점, persistent 플래그, guide 호출 |
| `src/dartlab/server/security.py` | TokenManager, KillSwitch, SlidingWindowLimiter, AnomalyDetector, TunnelSecurityMiddleware, AuditLog |
| `src/dartlab/server/__init__.py` | 미들웨어 등록 (DARTLAB_TUNNEL=1일 때) |
| `src/dartlab/guide/readiness.py::_checkShare` | share 사전 점검 |
| `src/dartlab/guide/hints.py` | onCloudflaredMissing/onCloudflareLoginRequired/onTunnelStartFailed/onShareSecurityWarning |
| `src/dartlab/guide/desk.py::handleError` | share 에러 라우팅 |
| `tests/test_channel_named_tunnel.py` | 단위 테스트 |
| `tests/test_guide_share.py` | 단위 테스트 |
