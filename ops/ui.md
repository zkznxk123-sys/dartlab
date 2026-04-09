# UI 엔진 (L4 표현 계층)

> dartlab의 모든 시각 인터페이스를 관리한다.

## 한 눈에 보기

| 항목 | 설명 |
|------|------|
| **레이어** | L4 — 표현 (L3 AI 위) |
| **Surface** | Svelte SPA (`ui/web/`) + VSCode 확장 (`ui/vscode/`) |
| **패리티 원칙** | VSCode 확장이 선행, Svelte가 따라감 |
| **SPA 서빙** | `dartlab share` → FastAPI가 `ui/build/` 정적 서빙 |
| **확장 배포** | VS Marketplace (독립 패키지) |
| **공유 코드** | markdown renderer, SSE handler, contentSplitter (TS↔JS 분기) |
| **외부 소비자** | [dartlab-desktop](https://github.com/eddmpython/dartlab-desktop) v0.3.13+ — pip 설치된 본체를 실행. UI 구조 변경 시 영향 필수 확인 |
| **UI 패키징** | PyPI wheel에 UI 빌드 포함 (`publish.yml` npm build → `src/dartlab/ui/build/`) |

## 디렉토리 구조

```
ui/
├── web/                   ← Svelte SPA
│   ├── src/               ← Svelte 컴포넌트 + 라이브러리
│   ├── build/             ← 빌드 출력 (gitignore)
│   └── package.json
├── vscode/                ← VSCode 확장 (확장 본체 + webview)
│   ├── src/               ← TypeScript 확장 코드
│   ├── webview/           ← 사이드바 Svelte UI
│   │   └── src/lib/       ← markdown/, api/, components/
│   ├── dist/              ← 빌드 출력 (gitignore)
│   └── package.json       ← marketplace manifest
└── shared/                ← web/vscode 공유 코드 (chart, api, markdown)
```

## 빌드

```bash
# Svelte SPA
cd ui/web && npm install && npm run build

# VSCode 확장
cd ui/vscode && npm install && npm run build

# Webview
cd ui/vscode/webview && npm install && npm run build
```

## 서버 연동

`src/dartlab/server/web.py`가 UI 빌드 디렉토리를 정적 서빙한다.
- `/assets/*` → `{UI_BUILD}/assets/`
- 나머지 → `{UI_BUILD}/index.html` (SPA fallback)

### UI 빌드 경로 해석 (`server/_ui_path.py`)

`resolve_ui_build_dir()` 단일 함수가 `web.py`와 `cli/commands/ai.py` 양쪽에서 사용된다.

| 우선순위 | 경로 | 환경 |
|---------|------|------|
| 1 | `DARTLAB_UI_DIR` 환경변수 | dartlab-desktop 등 외부 소비자 |
| 2 | `site-packages/dartlab/ui/build/` | pip install (패키지 내부) |
| 3 | `<project_root>/ui/web/build/` | editable install (개발) |

## 패리티 규칙

> **원칙: Svelte UI는 VSCode 확장을 따라간다.**
> VSCode 확장에 있는 기능은 Svelte에도 있어야 하고, VSCode에 없는 기능은 Svelte에서 숨긴다.

## 기능 대조표

| 기능 | VSCode 확장 | Svelte UI | 상태 |
|------|------------|-----------|------|
| AI 채팅 | chat panel | Chat 뷰 | **동기** |
| 대화 관리 (목록/생성/삭제/이름변경) | sidebar | Sidebar | **동기** |
| 대화 검색 | sidebar 필터 | SearchModal | **동기** |
| 스트리밍 응답 | SSE | SSE | **동기** |
| Provider/Model 선택 | 드롭다운 | 설정 패널 | **동기** |
| Slash 명령어 | /new, /clear, /model 등 | — | Svelte 미구현 |
| 상태표시줄 | 하단 서버 상태 | 상단 연결 상태 | **동기** |
| 공시뷰어 (Viewer) | — | 숨김 | VSCode 미구현 |
| 대시보드 (Dashboard) | — | 숨김 | VSCode 미구현 |
| Room 협업 | — | 활성 | Svelte 전용 (서버 기능) |
| Data Explorer (우측 패널) | — | 활성 | Svelte 전용 (서버 기능) |
| Excel 내보내기 | — | 활성 | Svelte 전용 (서버 기능) |
| 종목 검색 (Ctrl+K) | — | SearchModal | Svelte 전용 |

> Room, Data Explorer, Excel 내보내기는 서버 연동 전용 기능이므로 VSCode에 없어도 유지.
> Viewer/Dashboard는 VSCode에 동일 기능 추가 후 Svelte에서 복원.

## 숨김 처리 위치

| 항목 | 파일 | 처리 |
|------|------|------|
| Viewer/Dashboard 상단 탭 | `App.svelte:535-553` | 주석 |
| 모바일 하단 탭 | `App.svelte:742-756` | 주석 |
| 키보드 단축키 2/3 | `App.svelte:430-431` | 주석 |
| ActivityBar items | `ActivityBar.svelte:25-28` | 주석 |
| SearchModal 액션 | `SearchModal.svelte:30` | 주석 |
| App.svelte 콜백 | `App.svelte:799-800` | 주석 |

> 모든 TODO 주석에 "VSCode 확장에 동일 기능 추가 후 복원" 표기.

## 복원 절차

1. VSCode 확장에 해당 기능(예: Viewer) 구현 완료
2. 위 숨김 처리 위치의 주석 해제
3. 이 대조표 갱신
4. 양쪽 surface 동작 확인

## ⚠️ [최우선] UI 빌드 패키징 + dartlab-desktop 연동

### 구조 (2026-04-09 확정)

**PyPI wheel에 UI 빌드를 포함한다.** `pip install dartlab` 하면 `site-packages/dartlab/ui/build/`가 존재한다.

| 구성요소 | 역할 |
|---------|------|
| `publish.yml` | npm ci + npm run build → `src/dartlab/ui/build/`에 복사 → hatchling이 wheel에 포함 |
| `pyproject.toml` | `artifacts = ["src/dartlab/ui/build/**"]` — 비Python 파일 wheel 포함 |
| `server/_ui_path.py` | `resolve_ui_build_dir()` — env > pkg-relative > dev fallback |
| `web.py` + `ai.py` | `_ui_path.py` 사용 (하드코딩 경로 제거) |

### dartlab-desktop 연동

[dartlab-desktop](https://github.com/eddmpython/dartlab-desktop)은 Rust(tao+wry) 앱으로, pip 설치된 dartlab을 실행한다.

```
dartlab-desktop 시작
  → setup.rs: uv pip install dartlab[ai,llm] → wheel에 UI 포함
  → runner.rs: DARTLAB_UI_DIR=site-packages/dartlab/ui/build/ 환경변수 설정
  → dartlab ai --port 8400 --no-browser 실행
  → _ui_path.py: DARTLAB_UI_DIR 발견 → SPA 정상 서빙 ✅
```

- `ensure_ui_build()`: GitHub ZIP 다운로드 제거. wheel 설치 후 `index.html` 존재만 확인, 없으면 `--force-reinstall`
- `runner.rs`: `DARTLAB_UI_DIR` 환경변수를 서버 프로세스에 주입

### 릴리즈 이력

| 날짜 | dartlab-desktop | 본체 변경 | 내용 |
|------|----------------|----------|------|
| 2026-04-09 | **v0.3.13** | `_ui_path.py`, `publish.yml`, `pyproject.toml` | UI 빌드를 wheel에 포함. ZIP 다운로드 제거. DARTLAB_UI_DIR 환경변수 주입 |

### [강제] 본체 UI 구조 변경 시 dartlab-desktop 영향 체크리스트

본체(`dartlab`)에서 아래 항목 중 하나라도 변경하면 **dartlab-desktop에 영향이 간다**:

| 변경 항목 | dartlab-desktop 영향 | 확인 방법 |
|-----------|---------------------|----------|
| `web.py` 경로 해석 로직 | SPA 서빙 실패 | pip install → `dartlab share` 실행 |
| `DARTLAB_UI_DIR` 환경변수 계약 | 데스크톱 빌드 설정 변경 필요 | 환경변수 미설정 시 동작 확인 |
| `ui/web/` 빌드 출력 구조 | 정적 파일 서빙 경로 깨짐 | `build/assets/`, `build/index.html` 존재 확인 |
| `dartlab share` CLI 인터페이스 | 데스크톱 앱 실행 명령 변경 | CLI help 확인 |
| FastAPI 라우트 (`/api/*`) | 프론트엔드 API 호출 실패 | Svelte SPA E2E 테스트 |
| SSE 프로토콜 (스트리밍) | AI 채팅 깨짐 | SSE 연결 + 메시지 수신 확인 |
| `pyproject.toml` 빌드 설정 | wheel 내용물 변경 | `pip install .` → 파일 목록 확인 |

**규칙:**
- 위 항목 변경 시 커밋 메시지에 `[desktop-impact]` 태그를 붙인다
- dartlab-desktop 레포에 이슈를 열거나, 동시에 대응 PR을 만든다
- "본체만 고치면 끝" 이 아니다 — 외부 소비자(desktop, MCP 클라이언트)까지 확인

## 신규 기능 추가 시

1. **VSCode 확장에 먼저 (또는 동시에) 구현**
2. Svelte UI에 반영
3. 이 대조표에 행 추가
4. **pip 설치 환경에서 동작 확인** — UI 경로/API 변경 시 dartlab-desktop 영향 체크
