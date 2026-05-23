# TROUBLESHOOTING — 5 에러 시나리오 + 해결법

> dartlab 개발 시 가장 자주 만나는 5 에러. 각 시나리오 grep 결과 ≤ 3줄 안 해결 step 도달 강제 (T4-2 트랙).
> 본 문서에 없는 에러는 `memory/incidents.md` (운영자) → [INCIDENTS.md](INCIDENTS.md) (공개) → GitHub issue.

---

## 1. `UnicodeEncodeError: 'cp949' codec ...` (Windows)

### 증상
```
UnicodeEncodeError: 'cp949' codec can't encode character '\uXXXX' in position N
```

또는 한글 출력 시 깨짐 (`?` 또는 mojibake).

### 원인
Windows 기본 인코딩이 cp949 (한국어 Windows). dartlab 은 UTF-8 강제.

### 해결
1. `python` 명령 대신 `python -X utf8` 사용:
   ```bash
   uv run python -X utf8 script.py
   ```
2. PowerShell harness 경유 (자동 UTF-8):
   ```powershell
   .claude/utf8.ps1 script.py
   ```
3. 영구 (선택): 환경 변수 `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` 시스템 설정.

### 재발 가드
CLAUDE.md 강행규칙 "UTF-8 강제" 박힘. PreToolUse hook (`.claude/hooks/`) 가 `-X utf8` 없는 `python` 명령 차단.

---

## 2. `OOMKilled` / 메모리 폭증 (Company 다수)

### 증상
- pytest 실행 중 프로세스 죽음 (exit 137 또는 silent kill)
- `MEMORY CRITICAL: 1500 MB` 류 로그 후 응답 0
- WSL2 의 경우 `OOMKilled` 명시

### 원인
Polars = 네이티브 Rust 힙. `gc.collect()` 회수 불가. Company 1 개 ≈ 200~500MB. 다수 인스턴스 fixture 가 누적.

### 해결
1. pytest fixture scope = `module` 또는 `function` 강제 (session 금지):
   ```python
   @pytest.fixture(scope="module")
   def company():
       return Company("005930")
   ```
2. Company 사용 테스트는 marker `serial` 부여 + xdist 제외:
   ```python
   @pytest.mark.serial
   def test_company_show():
       ...
   ```
3. pytest 직접 호출 금지. lock wrapper 경유:
   ```bash
   bash tests/test-lock.sh tests/unit/ -m "unit" -v
   ```

### 재발 가드
CLAUDE.md "메모리 안전" 섹션 + `tests/audit/memoryBudgetAudit.py` gate (smoke tier blocking).

---

## 3. `OfflineViolation` (prebuild 단계)

### 증상
```
OfflineViolation: 외부 host '{api.dart.fss.or.kr}' 접근 차단 (prebuild 단계는 offline only).
```

### 원인
`.github/scripts/prebuild/` 안 스크립트가 외부 API 호출. sync (online) vs prebuild (offline) 책임 분리 룰 위반.

### 해결
1. 외부 API 호출이 필요한 step → `.github/scripts/sync/` 로 이동.
2. prebuild 는 sync 산출물 (HF dataset) 다운로드만:
   ```python
   from huggingface_hub import hf_hub_download
   path = hf_hub_download(repo_id="eddmpython/dartlab-data", filename="corp/profile.parquet")
   ```
3. prebuild `main()` 첫 줄에 `enforceOffline()` 호출 (정적 import lint 강제).

### 재발 가드
3층 가드: 런타임 (`core/offlineGuard.py`) + 정적 import (`tests/architecture/test_prebuild_offline.py`) + main entry lint.

---

## 4. `ImportLinter: contract violation`

### 증상
```
broken contracts:
  - L2 must not import from L1 (Forbidden import: dartlab.analysis -> dartlab.providers.dart)
```

### 원인
4 계층 단방향 import 위반 (CLAUDE.md L0/L1/L1.5/L2/L3/L4 표).

### 해결
1. 영향 import 그래프 확인:
   ```bash
   uv run python -X utf8 -m importlinter --config pyproject.toml
   ```
2. L2 (analysis/macro/quant/industry/credit) 는 L1.5 만 import. L1 직접 import 는 *L1.5 에 없는 raw 가 필요할 때만 예외*.
3. 예외 추가 시 `pyproject.toml [tool.importlinter]` 의 ignore list + reason 명시. monthly 5건 quota.

### 재발 가드
`tests/architecture/` 16 파일 + import-linter contract 4 종 + `dartlabGuard.py strict --scope l0-l15`.

---

## 5. `[ai-policy] 커밋 메시지 규칙` 차단

### 증상
```
[ai-policy] 커밋 메시지 규칙을 위반했습니다.
  - 의심 단어 추가: {word}
  - 커밋 메시지는 한글 위주로 작성해야 합니다.
```

또는:
```
- 첫 단어가 화이트리스트가 아닙니다.
```

### 원인
commit-msg hook (`.claude/hooks/check_no_ai_markers.py`) 차단:
- 첫 단어 화이트리스트 17 종 (추가/수정/개선/변경/삭제/정리/문서/테스트/빌드/릴리즈/보안/성능/리팩터/리팩토링/복구/설정/검증)
- 본문 금지 단어: `chatgpt|claude|codex|gpt|gemini|llm|ai` (단어 경계)
- 한글 위주 작성 강제

### 해결
1. 첫 단어를 화이트리스트로 시작.
2. body 안 영어 banned 단어 우회 (예: `ai-tooling` → `외부 도구`).
3. 자기 변경 path 명시:
   ```bash
   git commit -o <path> -m "<prefix>: <description>"
   ```

### 재발 가드
commit-msg hook 강제. 메시지 규칙은 [CLAUDE.md](../CLAUDE.md) "변경 단위" 섹션 + `memory/git_rules.md`.

---

## 그 외 자주 만나는 사고

| 증상 | 빠른 진단 |
|------|----------|
| `git status` 가 다른 브랜치 표시 | CLAUDE.md "master only" — 별도 브랜치 0, 즉시 보고 + master 복귀 |
| `lint-camelcase` 위반 신규 | snake_case 사용 안 됨. 신규 변수/함수 camelCase 강제 |
| pytest 가 OOM 됐는데 marker 없음 | `serial` marker 부여 + lock wrapper 경유 |
| `tests/_attempts/` 시도 *.py 가 lint fail | `# noqa: E731` 등 시도 코드 부분 허용 (인큐베이션, CI 게이트 의무 0) |
| pyproject 의존성 추가 후 `lint-imports` fail | `pip install -e .` 재실행 → import-linter contract 재로드 |

---

## 관련

- [DEVELOPMENT.md](DEVELOPMENT.md) — 첫 수정 10분 가이드
- [INCIDENTS.md](INCIDENTS.md) — 공개 사고 RCA
- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR 흐름
- [CLAUDE.md](../CLAUDE.md) — L-local 강행규칙
- 신규 에러 발생 시: `memory/incidents.md` 비공개 기록 → 패턴화되면 본 문서 6번째 시나리오로 승격
