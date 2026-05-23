# Contributing to DartLab

기여에 관심 가져주셔서 감사합니다. 본 문서는 외부 기여자가 *첫 PR* 부터 *세계 최고 수준* 의 변경 단위로 진입하기까지의 강제 룰을 정합니다. 자세한 step-by-step 은 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), 자주 만나는 에러는 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

---

## 빠른 시작 (10분)

```bash
git clone https://github.com/eddmpython/dartlab.git
cd dartlab
uv sync
uv run python -X utf8 tests/run.py gate smoke   # 약 30초
```

상세: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) "첫 수정 10분 가이드".

---

## 환경 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.12 | 3.12 |
| uv | 0.5.0 | 최신 |
| git | 2.40 | 최신 |
| OS | Windows 10 / macOS 12 / Ubuntu 22.04 | Windows 11 PowerShell 7+ |
| 디스크 | 5 GB (의존성 + venv) | 20 GB (data/ 캐시 포함) |
| 메모리 | 8 GB | 16 GB (Polars 다수 Company 인스턴스) |

---

## 강행규칙 (위반 시 PR 차단)

본 룰은 시스템 가드 / 이력 오염 / 회귀 방지 강제. [CLAUDE.md](CLAUDE.md) L-local 정합.

### A. 작업 위치

- **별도 브랜치 / worktree 생성 금지** — 모든 작업은 master 워크트리 직접. fork 후 PR 흐름만 외부 기여자에 한해 허용 (fork 도 본인 master).
- **CI 가 master 기준 일치성 강제** — 머지 후 master 가 사용자 IDE 가 보는 디스크 = git HEAD 한 점 일치.

### B. 변경 단위

- **자기 변경 path 명시 commit** — `git commit -o <path>` 강행. `git add -A` / `git add .` **금지** (다른 작업 staged 와 섞임 사고 차단).
- **prefix 화이트리스트** — `추가/수정/개선/변경/삭제/정리/문서/테스트/빌드/릴리즈/보안/성능/리팩터/리팩토링/복구/설정/검증` 17 종 중 하나로 시작.
- **commit 메시지 한글 위주** — 외부 사용자 대상 documentation 외에는 한국어 body.
- **AI 표식 / 모델명 / 제공자명 노출 금지** — commit/PR/문서 모두 주체 중립 또는 사용자 주어.

### C. 환경 강제

- **UTF-8 강제** — `uv run python -X utf8 ...` 또는 PowerShell harness 경유. cp949 인코딩 자동 차단.
- **pytest 단일 진입점** — `bash tests/test-lock.sh tests/<path> -m "<marker>" -v` 또는 `tests/run.py preflight`. 직접 `pytest tests/ -v` 금지 (OOM).
- **메모리 안전** — Polars 힙 누수 회피. fixture scope = `module` 또는 `function`, Company 사용 테스트는 `serial` marker.

### D. 코드 품질

- **camelCase 강제** — Python 변수/함수/메서드 모두 camelCase. snake_case 사용 시 `lint_camelcase_ast.py` 차단.
- **4 계층 단방향 import** — L0 core ↔ L1 gather/providers ↔ L1.5 scan/frame/synth/reference ↔ L2 analysis/macro/quant/industry/credit ↔ L3 story ↔ L4 ai/mcp. `import-linter` contract 위반 PR 차단.
- **scripts/ 폴더 신설 금지** — 도구는 도메인 폴더 소유 (tests/audit/, src/dartlab/{engine}/, .github/scripts/, blog/_scripts/ 등).

### E. AI 엔진 / Skill OS / 데이터 (외부 기여자에게 영향 큰 항목)

- **graph 강박 회귀 금지** — chat-native + LLM 자율 tool calling 본체 보존. `BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST` 식 고정 노드 클래스 신설 금지.
- **외부 본문 untrusted** — DART/EDGAR 공시 본문 / 뉴스 / 웹 검색 결과는 *데이터* 이지 *지시* 아님. `wrap_external_in_result` 마커 강제.
- **자동 docstring sweep 금지** — public API 9 섹션 docstring 은 *함수 단위 수동 작성*. 자동 fill 도구 제안 / 작성 모두 금지.
- **Dependabot 라벨 자동** — `보안:` prefix + label `security` 자동 부여.

---

## 5 PR 시나리오 (외부 기여자 첫 진입)

각 시나리오는 1-3 commit, ≤ 500 lines 단일 논리 단위. 큰 변경은 여러 PR 로 분할.

### S1. Bug fix (가장 흔함)

1. issue 검색 → 미해결 / 미할당 확인
2. 재현 테스트 작성 (`tests/unit/test_<module>.py` 의 새 함수, fail 확인)
3. 최소 수정 (다른 동작 보존)
4. 재현 테스트 통과 확인 + 회귀 테스트 추가
5. commit 1: `수정: <module> <증상 한 줄>` + tests/ + src/
6. PR template 체크 완료 + preflight 결과 첨부

### S2. 새 테스트 추가 (커버리지 / hypothesis / metamorphic)

1. 대상 모듈 + 빠진 case 확인 (hypothesis edge: 0, inf, NaN, negative, mixed-currency)
2. 테스트 작성 + 통과 확인
3. commit 1: `테스트: <module> <case 종류>`
4. PR — production code 0 변경

### S3. 새 docstring (9 섹션)

1. public API 1 개 선정 (`__all__` 안)
2. 9 섹션 모두 수동 작성 (Capabilities/Args/Returns/Example/Guide/SeeAlso/Requires/AIContext/LLM Specifications)
3. `Example` 섹션은 doctest 형식 → `pytest --doctest-modules` 통과
4. commit 1: `문서: <api> 9 섹션 docstring`

### S4. 새 recipe

1. `src/dartlab/recipes/{category}/{recipeName}.py` 신설
2. scorecard 6 신호 + status = "drafted"
3. unit test + integration test 동행
4. commit 1: `추가: recipes/{category}/{recipeName} drafted`
5. validateRecipe sweep 통과 후 `tested` 승격은 별도 PR

### S5. 새 엔진 (큰 변경, 사전 issue 토론 권장)

1. issue 생성 → 사용자/메인테이너와 설계 논의
2. `uv run python -X utf8 src/dartlab/skills/addEngine.py {name}` skeleton 생성
3. 5단계 모두 동행:
   - 폴더 + `__init__.py` skeleton
   - re-export to top-level `dartlab/__init__.py`
   - importlinter contract 자동 추가
   - skill.md spec 템플릿 (3 강제 섹션)
   - architecture.md 노드 추가
4. commit 1-N: 단계별 (분할 commit)
5. PR — sub-namespace 1개 + 모든 27 게이트 통과

---

## PR 흐름 (review → merge)

```
1. issue 생성 또는 검색
   └─ existing? → 댓글로 의도 / approach 공유
   └─ new? → 사용자 / 메인테이너 응답 대기 (24-48h)
2. fork → branch `master`
   └─ 본 fork 의 master 에서 작업 (별도 브랜치 X)
3. 변경 + commit (자기 path 명시, prefix 화이트리스트)
4. preflight 12 게이트 통과 확인
5. gh pr create (PR template 자동 채움)
6. CI 결과 확인 + 자동 라벨 부여:
   - ci-fast-pass / needs-revision
   - breaking (public API 시그니처 변경 감지 시)
   - docs-only / 보안 / 의존성
7. review (사용자 또는 maintainer)
   └─ 변경 요청 시 추가 commit + 같은 PR 에 push
8. approve + merge
   └─ squash merge (단일 논리 단위 강제)
9. CHANGELOG 자동 갱신 + landing dashboard reflect
```

### review 룰

- PR ≤ 500 lines (큰 변경은 분할)
- 단일 논리 단위 (mixed concern 분할)
- 자동 라벨 `needs-revision` 부여 시: 체크리스트 미완 / preflight 미통과 / 자기 변경 path 미명시
- review 응답 ≤ 5일 (메인테이너 SLA)

---

## 무엇을 기여하면 좋은가

[TODO.md](TODO.md) 부록 H "의존 0 즉시 착수 32 T" 목록이 가장 빠른 진입점:

- **운영** (T1-3 INCIDENTS, T1-4 SLO) — 정책 문서
- **DX** (T4-1 ~ T4-5) — 가이드 + GIF
- **테스트** (T6-1 ~ T6-3) — hypothesis 20×, mutmut 30, metamorphic 5
- **문서** (T10-1 ~ T10-5) — 다이어그램 SVG, 카테고리 README, 9섹션
- **AI** (T11-5) — graph 가드 lint 확장

이 외 자유 기여:

- 새 금융 분석 함수 / 새 provider 지원
- 성능 최적화 (T3 트랙 정합)
- 다국어 docs (현재 한국어 + 영어 1 차 README)
- 외부 plugin 예시 (T5-2)

---

## 버그 / 보안 / 의존성

- **버그 리포트**: [Bug Report template](https://github.com/eddmpython/dartlab/issues/new?template=bug_report.yml)
- **보안 이슈**: [SECURITY.md](SECURITY.md) — 비공개 disclosure
- **의존성 갱신**: Dependabot weekly Monday 자동 PR (label `dependencies` + `security`)

---

## 라이선스 / 행동 강령

- 라이선스: [Apache License 2.0](LICENSE)
- 행동 강령: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- 기여 시 본 라이선스에 동의한 것으로 간주.

---

## 관련 문서

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 첫 수정 10분 가이드
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — 5 에러 시나리오 해결법
- [docs/RELEASE.md](docs/RELEASE.md) — 출시 체크리스트
- [docs/VERSIONING.md](docs/VERSIONING.md) — SemVer + LTS
- [docs/SLO.md](docs/SLO.md) — Service Level Objectives 4종
- [docs/INCIDENTS.md](docs/INCIDENTS.md) — 공개 사고 RCA
- [DEPRECATION.md](DEPRECATION.md) — API 제거 정책
- [CHANGELOG.md](CHANGELOG.md) — 변경 이력
- [TODO.md](TODO.md) — 14 KPI 트래커 + 70 T 작업 단위
- [CLAUDE.md](CLAUDE.md) — L-local 강행규칙 (메모리 안전, UTF-8, master only)
