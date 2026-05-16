# dartlab `tests/` 운영 방침 (SSOT)

> 본 파일은 `tests/` 디렉토리의 **실용 운영 매뉴얼** 이다. 근본 정책 SSOT 는 `src/dartlab/skills/specs/operation/testing.md` (Skill OS) — 본 파일은 그 운영판 (디렉토리 구조 · 마커 · 도구 사용법 · 6 트랙 운영 절차).
>
> 외부 기여자가 처음 `tests/` 를 열었을 때 **PR 마다 무엇을 추가해야 하는지** 가 5 분 안에 잡혀야 한다.

---

## 0. 한눈에 — 새 코드 추가 시 PR 체크리스트

| 신규 코드 유형 | 필수 테스트 추가 위치 | 필수 마커 |
|---|---|---|
| `src/dartlab/core/**` pure 함수 | `tests/core/test_{module}.py` (oracle + property) | `unit` |
| `src/dartlab/gather/**` · `providers/**` raw 생산 | `tests/gather/...` · `tests/providers/.../` + fixture | `integration` 또는 `realData` |
| `src/dartlab/{scan,frame,synth,reference}/**` (L1.5) | `tests/{scan,frame,synth,reference}/` | `unit` 또는 `integration` |
| `src/dartlab/{analysis,credit,quant,macro,industry}/**` (L2) | 해당 엔진 폴더 | `unit` (mock_company) 또는 `integration` |
| `src/dartlab/story/**` (L3) | `tests/story/` | `integration` |
| `src/dartlab/ai/**` (L4) | `tests/ai/` + AI eval set (`tests/_evals/`) 갱신 | `unit` 또는 `eval` |
| `src/dartlab/cli/**` (L4) | `tests/cli/test_output_snapshots.py` snapshot 추가 | `unit` |
| `src/dartlab/mcp/**` (L4) | `tests/mcp/` + Schemathesis (Phase 3) | `unit` |
| Pandera schema 변경 (`core/schemas.py`) | `tests/_schemas/test_finance_schema.py` fixture 통과 | `unit` |
| AI agent 동작 변경 (prompt/tool) | `tests/_evals/eval_set.jsonl` 항목 추가 + judge 통과 | `eval` |

**테스트 없이 src/ 만 바꾼 PR → CI fail** (Track 5 자동 게이트, 2026-Q3 활성화 예정).

---

## 1. 디렉토리 구조 — `src/dartlab/` 14 엔진 4 계층 mirror

```
tests/
├── core/                # L0 — Polars helpers · logger · types · naming · utils · cache
├── gather/              # L1 — DART/EDGAR/EDINET raw 생산
├── providers/           # L1 — provider 패키지 (dart, edgar, edinet)
├── scan/                # L1.5 — 횡단면
├── frame/               # L1.5 — raw 결합 → 분석 ready (현 0, 사각지대)
├── synth/               # L1.5 — 분석 후처리·매칭·시나리오
├── reference/           # L1.5 — 정적 JSON 룩업 + 매핑
├── analysis/            # L2 — 분석
├── credit/              # L2 — 신용
├── quant/               # L2 — quant factor / risk
├── macro/               # L2 — 거시
├── industry/            # L2 — 업종
├── finance/             # L2 — 재무 (analysis 하위 후보)
├── sections/            # L2 — DART docs sections
├── search/              # L2 — 검색
├── story/               # L3 — 조합기
├── ai/                  # L4 — AI agent + workbench + tools (45 파일)
├── cli/                 # L4 — CLI 출력 snapshot + e2e
├── server/              # L4 — HTTP API
├── channel/             # L4 — 메신저 어댑터
├── mcp/                 # L4 — MCP server
├── viz/                 # L4 — 차트 / 시각화
├── architecture/        # 계약 — 4 계층 import 룰 강제 (6 파일, 변경 금지)
├── realData/            # 실데이터 회귀 (HF parquet 필수)
├── benchmarks/          # 성능 (pytest-benchmark)
├── skills/              # Skill OS 검증
├── audit/               # 메타 검증 (AST · docstring · baseline)
├── _schemas/            # Pandera schema 회귀 (private)
├── _drafts/             # ghostwriter 자동 draft (default collection 제외)
├── _evals/              # AI agent eval set + judge (Track 3)
├── _fixtures/           # fixture 선언 분리
├── _helpers.py          # captureRichOutput · 공용 헬퍼
├── fixtures/            # 실 production parquet snapshot
└── conftest.py          # MockCompany · samsung/aapl module fixture · 메모리 가드
```

**경계 판정 룰**:
- 단일 엔진/모듈 검증 → 해당 엔진 폴더
- 2+ 엔진 cross-cutting → 최상단 또는 `tests/integration/` (별도 폴더 생성 시 본 SSOT 갱신)
- 메타 검증 (audit/ast/docstring) → `tests/audit/`
- 회귀 baseline 시나리오 → `tests/realData/`
- private (운영자 internal) → `tests/_{name}/` (언더스코어 prefix)

`__init__.py` 는 basename 충돌 방지용 (같은 이름 `test_engine.py` 가 여러 폴더에 존재 → pytest rootdir 해석 충돌). 신규 폴더 생성 시 **빈 `__init__.py` 필수**.

---

## 2. 마커 시스템 (pyproject `[tool.pytest.ini_options].markers`)

| 마커 | 의미 | CI 실행 시점 |
|---|---|---|
| `unit` | 순수 로직 / mock 만, 데이터 0, 병렬 안전 | Tier 1 (Fast, PR) |
| `integration` | Company 1 개 로드, 중간 무게 | Tier 2 (Full) |
| `heavy` | 대량 데이터, 단독 실행 필수 | Tier 3 (Nightly) |
| `requires_data` | 로컬 parquet 필수 (CI 에서 skip) | 자동 부착 |
| `realData` | 엔진별 실데이터 smoke (HF parquet + 실 파이프라인) | Tier 3 + 운영자 트리거 |
| `freshInstall` | 빈 캐시 → 자동 다운로드 검증 | Nightly |
| `network` | 외부 HTTP (HF/DART/EDGAR/FRED) | `realData` 자동 부착 |
| `slow` | ≥ 30 초 — PR fast path 제외 | Tier 2/3 |
| `flaky` | transient 실패 자동 재시도 (rerunfailures) | network 자동 |
| `draft` | ghostwriter 자동 생성 (review 전) | 명시 호출만 |
| `eval` | AI agent eval (LLM 호출 + judge) | 운영자 트리거 |
| `mutation` | mutmut 실행 대상 표시 (메타) | 주간 |
| `metamorphic` | 변환 후 속성 보존 검증 (quant/credit) | Tier 2 |
| `vcr` | record-replay 사용 (네트워크 mock) | Tier 1 |

**자동 부착 룰** (`tests/conftest.py::pytest_collection_modifyitems`):
- `skipif reason in 데이터 관련` → `requires_data`
- `realData` 마커 → `network` 자동
- `network` 마커 → `flaky(reruns=2)` 자동

---

## 3. 실행 — 반드시 `test-lock.sh` 경유

⛔ **`pytest tests/ -v` 전체 직접 실행 금지** — Polars 네이티브 메모리 (≈ 200~500MB / Company) 가 누적되면 OOM. `gc.collect()` 로 회수 불가. `test-lock.sh` 는 동시 실행 차단 + `DARTLAB_TEST_LOCKED=1` 환경 설정.

```powershell
# 1 단계 — unit (안전, < 30 초)
bash scripts/dev/test-lock.sh tests/ -m "unit and not requires_data" -v --tb=short

# 2 단계 — integration (Company 로딩)
bash scripts/dev/test-lock.sh tests/ -m "integration and not requires_data" -v --tb=short

# 3 단계 — heavy (단독)
bash scripts/dev/test-lock.sh tests/ -m "heavy" -v --tb=short

# 단일 파일 / 폴더 (lock 안 함, 본인이 안전 보장)
$env:DARTLAB_TEST_LOCKED="1"; uv run python -X utf8 -m pytest tests/cli/test_output_snapshots.py -v
```

메모리 안전 가드 (`conftest.py::_memory_guard_per_test`) — `PRESSURE_CRITICAL_MB=1500` 초과 시 `pytest.exit(returncode=99)`.

---

## 4. 3-Tier CI 구조

| Tier | 파일 | 트리거 | 목표 시간 | 실행 marker |
|---|---|---|---|---|
| **Fast** | `.github/workflows/ci-fast.yml` | PR + master push | ≤ 3 분 | `unit and not requires_data` + smoke + format/lint/architecture + **snapshot + schema** |
| **Full** | `.github/workflows/ci-full.yml` | master push | ≤ 10 분 | `integration` + `metamorphic` + 부분 mutation |
| **Nightly** | `.github/workflows/ci-nightly.yml` | cron 15:00 UTC | ≤ 45 분 | `realData` + `heavy` + AI eval + full mutation |

**Fast 의 6 job**: format · lint · lint-camelcase · smoke · architecture-l0-l15 · test-fast + **snapshot-regression** (syrupy) + **schema-drift** (Pandera).

PR 머지 차단 fail gate: Fast 6 + snapshot + schema. baseline 회귀 (Guard Index `strict --scope l0-l15`) 는 별도 차단.

---

## 5. 6 트랙 운영 방침 — 훌륭 수준까지

> 이번에 도입된 syrupy snapshot + Pandera schema + ghostwriter draft 는 **시작점** 일 뿐. 잘하는 라이브러리 (ruff/polars/pydantic/FastAPI/ripgrep) 수준에 도달하려면 아래 6 트랙 모두 운영해야 한다.

### Track 1 — Snapshot 회귀 (syrupy) — ★★★★★ **도입 완료**

| 항목 | 위치 |
|---|---|
| 헬퍼 | `tests/_helpers.py::captureRichOutput()` |
| 케이스 | `tests/cli/test_output_snapshots.py` (5 case) |
| 동결 | `tests/cli/__snapshots__/test_output_snapshots.ambr` |

**언제 추가**:
- 새 CLI 명령
- Rich Progress / Live / Table 출력 변경
- HF 다운로드 마커 변경
- warning routing 변경 (RichHandler 흡수)

**갱신**:
```powershell
$env:DARTLAB_TEST_LOCKED="1"; uv run python -X utf8 -m pytest tests/cli/test_output_snapshots.py --snapshot-update
```
사람 눈으로 diff 확인 후 commit. 무조건 `--snapshot-update` 금지 — 회귀를 의도된 변경으로 위장하는 거짓 동결.

### Track 2 — Schema 계약 (Pandera) — ★★★★★ **도입 완료**

| 항목 | 위치 |
|---|---|
| 스키마 | `src/dartlab/core/schemas.py` (FinanceSchema · ReportSchema · DocsSchema) |
| 회귀 | `tests/_schemas/test_finance_schema.py` (fixture 12 종 + drift reject) |
| Production 게이트 | `DARTLAB_VALIDATE_SCHEMA=1` 환경변수 (production default OFF) |

**언제 추가**:
- DART/EDGAR API 가 응답 컬럼 변경
- finance/report/docs frame 의 필수 컬럼 추가/삭제
- 새 raw 생산 endpoint

**Production 부작용 정책**: `_maybeValidateFinance()` 는 `DARTLAB_VALIDATE_SCHEMA=1` 일 때만 동작. 실패 시 raise 대신 `logger.warning` 으로 drift 기록 → 사용자 호출 깨뜨리지 않음. CI nightly 에서 `=1` 설정해 정기 검사.

### Track 3 — AI Agent eval — ★★★★★ **도입 예정 (2026-Q2)**

dartlab 정체성 = 자가개선 루프 → LLM 출력 회귀 못 잡으면 다른 모든 테스트가 무의미.

| 항목 | 위치 |
|---|---|
| Eval set | `tests/_evals/eval_set.jsonl` (질문 + 기대 평가 항목 30-50) |
| Judge | `tests/_evals/judge.py` (LLM-as-judge, 6 신호 채점) |
| 실행 | `pytest tests/_evals/ -m eval` (외부 LLM 호출, $0.01~0.05 / case) |

**6 채점 신호**: factual_correctness · evidence_citation · tool_use_appropriate · format_compliance · reasoning_depth · no_hallucination.

**언제 실행**: AI agent 코드 변경 PR + nightly. 점수 < baseline 시 fail.

**도구 선택**: `inspect-ai` (Anthropic 권장) 또는 자체 경량 구현. dartlab 같은 도메인 깊은 라이브러리는 자체 구현이 적합 (외부 의존 추가 회피).

### Track 4 — Property-based 50%+ (ghostwriter sweep) — ★★★★ **시범 → sweep 예정**

| 단계 | 위치 |
|---|---|
| 1 (현) | `tests/_drafts/test_formatting_draft.py` — 시범 3 함수 |
| 2 (sweep) | `core/{naming,formatting,utils}`, `synth/*`, `reference/*` pure 함수 전체 |
| 3 (oracle 보강) | draft → `tests/core/test_{module}.py` 정식 위치 이동 + oracle assertion |

**Draft → Oracle 사다리**:
```powershell
# 1) ghostwriter 생성
uv run python -X utf8 -m hypothesis write dartlab.core.naming > tests/_drafts/test_naming_draft.py

# 2) 사람이 oracle 보강 — 예: parsePeriod("2024Q4") == ("2024", "Q4")
# 3) 검증된 케이스만 tests/core/test_naming.py 로 이동
# 4) draft 삭제
```

**ROI 표적**: `typing.Any` 시그니처는 약함 (raise 안 함만 검증). 구체 타입 (`int`, `str`, `Decimal`) 인자가 ROI 높음.

### Track 5 — Mutation testing (mutmut) — ★★★ **도입 예정 (2026-Q3)**

"테스트가 통과한다" 가 아니라 "테스트가 깨진 코드를 잡는다" 를 측정.

| 항목 | 위치 |
|---|---|
| 설정 | `pyproject.toml [tool.mutmut]` (대상 = `src/dartlab/core/{naming,formatting,utils}`) |
| 실행 | `uv run mutmut run` (전체 1-2 시간) |
| 결과 | `.mutmut-cache` + `mutmut results` (생존 mutant 목록) |
| 목표 | mutation score ≥ 80% (잘하는 라이브러리 수준) |

**부분 적용 정책**: Polars/numpy native 호출 비중이 큰 모듈은 mutant 가 의미 없음 (예: `analysis/`, `quant/`). `core/` pure 함수 한정.

**언제 실행**: 주간 cron + `core/` 변경 PR. 생존 mutant 발견 시 oracle test 추가.

### Track 6 — Test 강제 게이트 (CI fail when src/ adds without tests/) — ★★★ **도입 예정 (2026-Q3)**

| 항목 | 위치 |
|---|---|
| 게이트 스크립트 | `scripts/audit/testCoverageGate.py` |
| CI 호출 | `.github/workflows/ci-fast.yml` job `test-coverage-gate` |
| 룰 | PR diff 에서 `src/dartlab/**/*.py` 의 새 함수 (def) 추가 → `tests/**/test_*.py` 에 해당 함수 import 또는 참조 존재해야 함 |
| 예외 | `# nocover`, `_private`, abstract method, Protocol method, `cli/main.py` 진입점 |

**부드러운 도입**: 처음 1 개월 warning-only → 통계 보고 후 fail 전환.

### Track 7 — Record-Replay (VCR) — ★★★ **도입 예정 (2026-Q3)**

| 항목 | 위치 |
|---|---|
| 카세트 | `tests/_cassettes/` (gitignored 가 아닌 commit — production HTTP 응답 동결) |
| 대상 | `providers/dart/openapi/dart.py` · `providers/edgar/openapi/sec.py` 외부 호출 |
| 도구 | `vcrpy` 또는 자체 경량 (HTTPS body hash → parquet) |
| 마커 | `vcr` |

**언제 record**: 외부 API 응답 변경 시 한 번. 이후 CI 는 카세트만 replay → 네트워크 없이 회귀 검증.

### Track 8 — Metamorphic test — ★★ **도입 예정 (2026-Q4)**

수치 분석에서 결정적 oracle 없을 때 **변환 후 보존되는 속성** 으로 검증.

| 대상 | 변환 | 보존 속성 |
|---|---|---|
| `quant/factor/calcRanking` | 입력 +1 (전체 shift) | ranking 동일 |
| `credit/scoring/calcGrade` | 통화 환산 | 등급 동일 |
| `analysis/ratios/calcDebtRatio` | 단위 변환 (원 → 백만원) | 비율 동일 |
| `macro/scenarios/applyShock` | 0 충격 | 결과 = 기준선 |

**위치**: `tests/{quant,credit,analysis,macro}/test_*_metamorphic.py`. 마커 `metamorphic`.

---

## 6. 디렉토리 신설 시 절차

1. **빈 폴더 + `__init__.py`** 만들기 (basename 충돌 방지)
2. **본 SSOT 의 1 절 트리 그림 갱신** + 6 절 (있다면) 갱신
3. **`testing.md` Skill OS 갱신** 은 운영자 트리거 시에만 (개별 PR 자동 갱신 금지 — Skill OS 는 운영자 수동 SSOT)
4. **첫 테스트 1 개 추가** — 빈 폴더 commit 금지 (`__init__.py` 만 있는 폴더는 의미 없음)

---

## 7. 사각지대 (의식적 부채 + 향후 트랙)

| 영역 | 현재 | 부채 이유 | 해결 트리거 |
|---|---|---|---|
| `tests/frame/` | 0 테스트 | L1.5 frame 엔진이 분석 ready 결합기 — 회귀 가드 자동 우선순위 낮음 | 운영자 트리거 |
| 노트북 실행 | 0 | `notebooks/` 가 marketing/demo 중심 | nbmake 또는 papermill 도입 시 |
| MCP server contract | 0 | MCP 자체가 0.x 단계 | Schemathesis 도입 (Phase 3) |
| Pyodide wasm 빌드 | 0 | dartlab-pyodide 별도 repo | wasm 호환성 회귀 발견 시 |
| 전체 flow demo | 0 | 마케팅 자산 영역 | VHS .tape 도입 (출시 직전) |
| 외부 입력 fuzz | 0 | parser 한정 보안 영역 | Atheris (보안 단계) |
| OpenTelemetry replay | 0 | 서버 운영 시점 | 서버 운영 단계 |

---

## 8. 적용 *안* 함 (ROI 검토 결과 폐기)

- **Formal verification** (TLA+, deal) — Python 라이브러리에 비싸기만. Pandera + Hypothesis 가 80% 보장을 1/100 비용에.
- **전체 repo mutation** — Polars/Rust native 호출 비중 → mutant 가 의미 없음. `core/` 한정만.
- **Devin 류 autonomous test agent** — SWE-EVO 2026: long-horizon multi-commit 평가에서 실패. 도메인 깊은 라이브러리에 부적합.
- **Diffblue Cover** — Java 전용.
- **Great Expectations** — SQL+Spark audit 용. Pandera 가 dartlab 에 적합.

---

## 9. 도구 버전 (`pyproject.toml [dependency-groups].dev`)

| 도구 | 버전 | 역할 |
|---|---|---|
| pytest | ≥ 9.0.2 | base runner |
| pytest-asyncio | ≥ 0.24.0 | async test |
| pytest-benchmark | ≥ 5.0.0 | 성능 회귀 (`tests/benchmarks/`) |
| pytest-cov | ≥ 6.0.0 | coverage (`fail_under=40`, omit policy) |
| hypothesis | ≥ 6.100.0 | property-based + ghostwriter |
| syrupy | ≥ 4.7.0 | CLI 출력 snapshot |
| pandera[polars] | ≥ 0.29.0 | DataFrame schema 계약 |
| mutmut | (도입 예정 2026-Q3) | mutation testing |
| vcrpy | (도입 예정 2026-Q3) | record-replay |
| inspect-ai | (도입 예정 2026-Q2) | AI eval framework |

---

## 10. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `pytest.exit(returncode=99) 메모리 안전 종료` | Company 누적 → 1500MB 초과 | 마커별 분리 실행 또는 `PYTEST_MEMORY_LIMIT_MB=2000` |
| `PytestUnknownMarkWarning: draft` | `tests/_drafts/` 가 norecursedirs 우회 | `pyproject.toml [tool.pytest.ini_options].markers` 에 등록 확인 |
| `same basename test_engine.py duplicate` | `__init__.py` 누락 | 신규 폴더에 빈 `__init__.py` 추가 |
| syrupy `snapshot does not exist` | 첫 실행 | `--snapshot-update` 1 회 + 사람 눈 diff 검토 |
| Pandera `SchemaErrors` in production | `DARTLAB_VALIDATE_SCHEMA=1` 켜진 상태 | 끄거나 warning 로그 확인 후 schema 갱신 |
| ghostwriter `Resolved typing.Any to st.nothing()` | 시그니처 weak | `typing.Any` 대신 구체 타입으로 시그니처 좁히거나 oracle test 로 이동 |

---

## 11. 관련 SSOT

- 정책 근본 — `src/dartlab/skills/specs/operation/testing.md`
- 강행규칙 — `CLAUDE.md` "메모리 안전" · "변경 단위"
- 도구 SSOT (운영자↔AI 메모리) — `memory/testing_stack.md`
- 4 계층 import — `src/dartlab/skills/specs/operation/architecture.md` · `memory/core_boundary.md`
- 회귀 가드 — `scripts/audit/dartlabGuard.py strict --scope l0-l15`
