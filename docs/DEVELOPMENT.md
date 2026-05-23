# DEVELOPMENT — 첫 수정 10분 가이드

> 외부 기여자가 clone → 첫 PR commit 까지 10분 안 도달 강제 (T4-1 + T4-6 트랙).
> 문제 발생 시 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → [CONTRIBUTING.md](../CONTRIBUTING.md) → GitHub issue.

---

## 사전 요구

- **Python 3.12+** (3.12 권장)
- **uv** ≥ 0.5.0 (https://docs.astral.sh/uv/)
- **git** ≥ 2.40
- **Windows / macOS / Linux** — 모두 지원. Windows 는 PowerShell 7+ 권장 (UTF-8 정합).

---

## 1단계 — clone + 환경 셋업 (예상 1분)

```bash
git clone https://github.com/eddmpython/dartlab.git
cd dartlab
uv sync
```

`uv sync` 가 .venv 생성 + 의존성 약 80 패키지 설치 (네트워크 변동 ±20%).

---

## 2단계 — 첫 smoke 테스트 (예상 2분)

```bash
# Windows PowerShell
uv run python -X utf8 tests/run.py gate smoke

# 또는 bash/macOS/Linux
uv run python -X utf8 tests/run.py gate smoke
```

`smoke` gate 통과 시 `[run.py] PASSED: smoke` 메시지. 약 30초.

실패 시 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 의 5 시나리오 우선 확인.

---

## 3단계 — 첫 코드 수정 표적 (예상 2분)

예: `src/dartlab/scan/foreignFlow.py` 의 docstring 한 줄 보강.

```bash
# 파일 열기
code src/dartlab/scan/foreignFlow.py

# 수정 후 단일 파일 lint
uv run ruff check src/dartlab/scan/foreignFlow.py
uv run python -X utf8 tests/audit/lint_camelcase_ast.py --changed
```

룰:
- camelCase 강제 (`tests/audit/lint_camelcase_ast.py`)
- ruff format + ruff check 통과
- 변경 함수에 영향받는 호출자 grep 후 확인

---

## 4단계 — commit 단위 룰 (예상 1분)

자기가 한 변경만 path 명시 commit:

```bash
git commit -o src/dartlab/scan/foreignFlow.py -m "문서: foreignFlow docstring 보강 — 외인 매수 모멘텀 정의 명시"
```

룰:
- `git add -A` / `git add .` **금지** (다른 작업 staged 와 섞임 사고 차단)
- `git commit -o <path>` 강행 (race 차단)
- prefix 화이트리스트: 추가/수정/개선/변경/삭제/정리/문서/테스트/빌드/릴리즈/보안/성능/리팩터/복구/설정/검증
- AI 표식 / "Claude" / "GPT" / "Codex" 단어 금지 (commit-msg hook 차단)

---

## 5단계 — 푸시 전 preflight (예상 3분)

```bash
uv run python -X utf8 tests/run.py preflight
```

12 fast tier 게이트 실행 (format, lint, architecture, smoke, test-fast 등). 모두 통과 시 push 가능.

```bash
git push origin master
```

---

## 6단계 — PR 생성 (예상 1분)

```bash
gh pr create --title "<논리 단위 한 줄>" --body "<요약 + 영향 + 테스트>"
```

PR template ([.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md)) 자동 채워짐. 자기 변경 path 명시 / preflight 결과 / 영향 audit 명시.

---

## 핫리로드 (개발 중)

### FastAPI server

```bash
uv run python -X utf8 -m dartlab.server.viz --reload
```

코드 수정 시 ~2초 안 브라우저 갱신.

### Marimo 노트북

```bash
uv run marimo edit notebooks/marimo/01_company.py
```

reactive 셀 → 의존성 자동 추적, 수정 즉시 재실행.

### Landing (SvelteKit)

```bash
cd landing
npm install
npm run dev
```

---

## 환경 변수

| 변수 | 기본 | 설명 |
|------|------|------|
| `DARTLAB_LOG_LEVEL` | INFO | logger 레벨 (DEBUG / INFO / WARNING / ERROR) |
| `DARTLAB_TEST_LOCKED` | unset | pytest lock wrapper 표시 (`bash tests/test-lock.sh` 설정) |
| `DARTLAB_PROVIDER_SCOPE` | dart,edgar | 활성 provider (edinet 제외) |
| `POLARS_MAX_THREADS` | (auto) | Polars 병렬 스레드 수 |
| `POLARS_STREAMING_CHUNK_SIZE` | (auto) | 스트리밍 chunk 크기 |
| `PYTHONIOENCODING` | utf-8 | UTF-8 강제 (Windows cp949 차단) |

예: `DARTLAB_LOG_LEVEL=DEBUG uv run python -X utf8 -m dartlab.cli analyze 005930`

---

## 자주 묻는 위치

- **테스트 추가**: `tests/unit/test_{module}.py` (단순) / `tests/integration/` (외부 API mock)
- **새 recipe**: `src/dartlab/recipes/{category}/{recipeName}.py` + scorecard
- **새 엔진**: `uv run python -X utf8 src/dartlab/skills/addEngine.py {name}` (T5-4 skeleton)
- **docstring 9섹션**: 함수 단위 수동 작성 (자동 sweep 금지, [TODO.md](../TODO.md) T10-4 참고)

---

## 관련

- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR 흐름 전체
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — 5 에러 시나리오 해결법
- [RELEASE.md](RELEASE.md) — 출시 체크리스트
- [VERSIONING.md](VERSIONING.md) — SemVer 정책
- [TODO.md](../TODO.md) — 14 KPI 트래커 + 70 T 작업 단위
- [CLAUDE.md](../CLAUDE.md) — L-local 강행규칙 (메모리 안전, UTF-8, master only)
