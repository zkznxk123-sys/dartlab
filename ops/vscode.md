# VSCode Extension

**주체**: VSCode 확장 (`ui/vscode/` — webview + extension host).
**현재**: Svelte webview ↔ postMessage ↔ extension host ↔ stdio JSON Lines ↔ `dartlab chat --stdio` · VS Marketplace 배포.
**방향**: MCP 자동 등록 확장 · 대시보드 통합 · 확장 첫 실행 UX 개선.

dartlab 의 1 순위 UI surface. AI 채팅 + 프로바이더 연결 + MCP 자동 등록. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

| 항목 | 내용 |
|---|---|
| 레이어 | L4 (표현) |
| 경로 | `ui/vscode/` (확장 본체 + webview) |
| 배포 | VS Marketplace (`vsce-*` 태그 → GitHub Actions) |
| 아키텍처 | Svelte webview ↔ postMessage ↔ extension host ↔ stdio JSON Lines ↔ `dartlab chat --stdio` |
| PyPI 의존 | `stdio.py` 변경 시 dartlab PyPI 도 같이 배포해야 다른 PC 에서 동작 |

---

## 1. 버전 — 0.2.x 끝자리만 올린다

- **0.2.x** — 끝자리만 올린다 (0.2.0 → 0.2.1 → 0.2.2 → …).
- `ui/vscode/package.json` 의 `version` 필드가 진실의 원천.
- 태그: `vsce-{버전}` (예: `vsce-0.2.1`).
- CHANGELOG: `ui/vscode/CHANGELOG.md`.

---

## 2. 배포 — 7 단계로 진행한다

1. `ui/vscode/package.json` version 올리기 (끝자리).
2. `ui/vscode/CHANGELOG.md` 작성.
3. 커밋 + 푸시.
4. `git tag vsce-{버전}` + `git push origin vsce-{버전}`.
5. GitHub Actions 가 webview 빌드 → extension 빌드 → `vsce publish`.
6. `stdio.py` 변경이 포함됐으면 dartlab PyPI 도 함께 배포 (`v*` 태그).
7. Actions 결과까지 확인 완료가 배포의 마지막 단계.

**반복 실패** — `stdio.py` 변경하고 VS Marketplace 만 배포하면 다른 PC 에서 프로토콜 불일치로 멈춘다. PyPI 동반 배포 필수.

---

## 3. 아키텍처 — webview ↔ extension host ↔ Python backend 3 층으로 간다

```
┌─ VSCode Extension Host (TS/Node)
│  ├─ extension.ts          활성화, MCP 자동 등록
│  ├─ bridge/
│  │  ├─ stdioProxy.ts      child process 관리, fallback chain, healthcheck
│  │  └─ messageProtocol.ts webview ↔ extension host 메시지 타입
│  ├─ providers/
│  │  ├─ chatWebviewBase.ts webview 셋업 + 메시지 라우팅
│  │  ├─ chatPanelManager.ts 에디터 탭 패널
│  │  └─ sidebarViewProvider.ts 사이드바 세션 목록
│  └─ commands/             커맨드 등록
│
├─ Webview UI (Svelte + TS)
│  ├─ lib/components/
│  │  ├─ ChatPanel.svelte   대화 관리 + 웰컴 화면
│  │  ├─ ChatHeader.svelte  상태 + 프로바이더 드롭다운
│  │  ├─ ChatInput.svelte   입력 + 슬래시 커맨드
│  │  └─ MessageBubble.svelte 메시지 렌더링
│  ├─ lib/api/
│  │  ├─ client.ts          postMessage API
│  │  └─ sseHandler.ts      JSON 이벤트 → 메시지 업데이트
│  └─ lib/chart/            차트 컴포넌트
│
└─ Python Backend (child process)
   └─ src/dartlab/cli/stdio.py  JSON Lines 프로토콜
```

---

## 4. stdio 프로토콜 — 이 메시지 타입으로 주고받는다

```
→ {"type":"ping"}                        ← {"event":"pong","data":{}}
→ {"type":"status"}                      ← {"event":"status","data":{provider, model, ready, providers[]}}
→ {"type":"setProvider","provider":"..."}
   ├─ API 키 있음                         ← {"event":"providerChanged","data":{...}}
   ├─ API 키 없음                         ← {"event":"needCredential","data":{provider, signupUrl}}
   └─ OAuth provider                      ← {"event":"oauthStart","data":{authUrl, provider}}
                                          ← {"event":"providerChanged","data":{...}}  (로그인 완료 후)
→ {"type":"oauthPasteToken","tokenJson":"..."}
                                          ← {"event":"providerChanged","data":{...}}
→ {"id":"1","type":"ask","question":"..."}
   ← {"id":"1","event":"meta","data":{company, stockCode}}
   ← {"id":"1","event":"observe","data":{...}}
   ← {"id":"1","event":"inspect","data":{...}}
   ← {"id":"1","event":"compute","data":{...}}
   ← {"id":"1","event":"verify","data":{...}}
   ← {"id":"1","event":"artifact","data":{...}}
   ← {"id":"1","event":"chart","data":{charts:[...]}}
   ← {"id":"1","event":"chunk","data":{text}} × N
   ← {"id":"1","event":"done","data":{}}
→ {"type":"exit"}
```

workspace-native 이벤트는 장식 로그가 아니다. VSCode webview 는 web UI 와 동일하게 Financial Workspace Agent Trace 로 표시하고, chart 는 `ui/shared/api/visualContract.ts` 를 통과한 spec 만 렌더링한다.

---

## 5. 프로바이더 연결 — 선택하면 바로 연결까지 끝낸다

provider 선택하면 바로 연결까지 끝난다. 추가 설정 페이지 없음.

| provider 종류 | 플로우 |
|---|---|
| API 키 provider | 선택 → signupUrl 브라우저 → InputBox 키 입력 → 저장 → 연결 |
| OAuth provider | 선택 → 브라우저 PKCE 로그인 → callback → 토큰 저장 → 연결 |
| OAuth 토큰 입력 (방화벽) | "토큰 입력" → InputBox 에 JSON 붙여넣기 → 저장 → 연결 |
| 로컬 runtime | 선택 → 바로 연결 |

연결 완료 시 "연결 완료" 메시지 표시.

---

## 6. spawn fallback chain — 이 순서로 dartlab 프로세스를 찾는다

extension 이 dartlab 프로세스를 찾는 순서:

1. `pythonPath` 설정 (있으면).
2. `uv run python -X utf8 -m dartlab chat --stdio`.
3. `python -m dartlab chat --stdio`.
4. `python3 -m dartlab chat --stdio`.
5. `dartlab chat --stdio`.

성공한 후보를 기억해서 다음 재시작 때 먼저 시도.

---

## 7. 빌드·검증

```bash
cd ui/vscode && npm run verify    # esbuild → vite → vitest → tsc → vscode-test
cd ui/vscode && npm run build     # extension만
cd ui/vscode/webview && npm run build  # webview만
```

---

## 8. 에러 메시지 — UI 에서 CLI 명령 안내하지 않는다

- UI 에서 `dartlab.setup(...)` 같은 CLI 명령을 안내하지 않는다.
- `_sanitizeErrorForUi()` 가 stdio 레이어에서 CLI 안내를 제거.
- 인증 에러 시 provider 변경을 UI 에서 직접 제안.

**반복 실패** — 파이썬 예외를 그대로 UI 버블에 노출 → 사용자가 터미널 명령을 이해해야 하는 상황. 항상 `_sanitizeErrorForUi` 로 통과시킨다.

---

## 9. MCP 자동 등록 — extension 활성화 시 자동으로 꽂는다

extension 활성화 시 `.mcp.json` + `.vscode/mcp.json` 에 dartlab MCP 서버 자동 등록.
같은 workspace 를 쓰는 MCP 호환 실행 환경에서 `dartlab` 도구를 바로 사용 가능.

---

## 관련 코드

| 경로 | 역할 |
|---|---|
| `ui/vscode/src/` | TypeScript extension |
| `ui/vscode/webview/src/` | Svelte webview |
| `ui/shared/api/visualContract.ts` | webview 와 web 의 공통 visual 의미 판정 |
| `ui/shared/chart/` | webview 와 web 의 공통 차트 렌더링 |
| `src/dartlab/cli/stdio.py` | Python backend 프로토콜 |
| `src/dartlab/guide/providers.py` | provider 카탈로그 |
| `src/dartlab/guide/credentials.py` | 자격증명 관리 |
| `src/dartlab/ai/providers/support/oauth_token.py` | OAuth 토큰 관리 |

---

## 요약 — 명제 7 줄

1. 버전은 0.2.x 끝자리만 올리고 `ui/vscode/package.json` 이 SSOT.
2. 배포 7 단계 — package.json → CHANGELOG → commit → `vsce-*` tag → GitHub Actions → (stdio 변경이면 PyPI 동반) → Actions 확인.
3. 아키텍처는 Svelte webview ↔ postMessage ↔ extension host ↔ stdio JSON Lines ↔ `dartlab chat --stdio`.
4. stdio 프로토콜은 ping · status · setProvider · ask · exit 메시지로 구성.
5. 프로바이더는 API 키 · OAuth · OAuth 토큰 입력 · 로컬 4 플로우 중 하나로 선택 즉시 연결까지.
6. spawn fallback 5 단계로 `pythonPath` → `uv run` → `python -m` → `python3 -m` → `dartlab` 순서 시도.
7. UI 에러는 `_sanitizeErrorForUi` 통과 (CLI 명령 안내 없음), MCP 는 activation 시 자동 등록.
