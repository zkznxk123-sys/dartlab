# dartlab 테스트 · CI 운영 규칙

Phase 3 개편 (2026-04-22) 으로 확립된 **3-tier CI + 직교 marker + 메모리
정책 단일화** 의 규칙. 매일 CI 가 깨지고 재수정하던 근본 원인 (logger/print
혼동 · realdata PR 과잉 · flaky retry 부재) 해소가 목적.

## 핵심 원칙

1. **CI 는 tier 로 분리된다** — 모든 push 마다 전 스위트 돌리지 않음.
2. **logger 와 print 는 책임이 다르다** — 섞이면 테스트 캡처 설계 연쇄 깨짐.
3. **Polars 메모리는 프로세스 단위로만 해제된다** — fixture scope, xdist
   worker, `--forked` 가 전부.
4. **network 테스트는 자동 재시도** — transient 실패를 진짜 회귀로 오인 금지.

---

## 3-Tier CI 구조

### Tier 1 — `ci-fast.yml` (PR + master push, 목표 ≤ 3분)

즉시 피드백 게이트. 머지 전 blocking.

| Job | 역할 | 실측 목표 |
|---|---|---|
| `format` | ruff format --check | < 30s |
| `lint` | ruff + silent-fail 검사 | < 30s |
| `typecheck` | pyright (warning-only) | < 2m |
| `smoke` | import smoke | < 30s |
| `test-fast` | `pytest -m unit -n auto` | < 2m |
| `wheel-smoke` | python -m build + 번들 검증 | < 1m |
| `quality-gate` | radon/vulture (warning-only) | < 30s |
| `security` | pip-audit (warning-only) | < 1m |
| `deps-check` | deptry (warning-only) | < 1m |
| `notebooks` | 문법만 검증 | < 30s |

**제외**: realData · integration · requires_data · cross-os · fixture-
integration (전부 Tier 2+ 로 이동).

### Tier 2 — `ci-full.yml` (master push only, 목표 ≤ 10분)

머지 후 통합 회귀 검증.

| Job | 역할 | 실측 목표 |
|---|---|---|
| `test-full` | 3.12/3.13 matrix, integration + requires_data 포함 | < 10m |
| `fixture-integration` | high-memory 파일 격리 실행 | < 8m |
| `cross-os-smoke` | ubuntu/windows/macos 3 OS bundle 검증 | < 5m |
| `realdata-plan` | git diff → test 파일 리스트 | < 30s |
| `realdata-suite` | path-filter matrix (변경된 엔진 + facade smoke) | < 20m |

### Tier 3 — `ci-nightly.yml` (cron 15:00 UTC = KST 00:00, 목표 ≤ 45분)

환경·데이터·분포 edge 검증.

| Job | 역할 | 실측 목표 |
|---|---|---|
| `realdata-suite-full` | 20 shard 전수 (path-filter 우회) | < 30m |
| `external-venv-smoke` | 최신 PyPI wheel 빈 venv 설치 후 8 엔진 | < 15m |
| `freshInstall` | 빈 캐시 → HF 자동 다운로드 경로 | < 30m |

### Tier 4 — 수동 dispatch / weekly (on-demand)

`workflow_dispatch` 로 수동 트리거. bench / coverage-report / pyodide
smoke 등.

---

## Marker 정책 (직교 체계)

`pyproject.toml::tool.pytest.ini_options.markers`:

| Marker | 의미 | 실행 tier |
|---|---|---|
| `unit` | 순수 로직, mock 만, 데이터 로드 X, 병렬 안전 | Tier 1 (test-fast) |
| `integration` | Company 1개 로딩 | Tier 2 (test-full) |
| `heavy` | 대량 데이터 로드, 단독 실행 | Tier 3 or manual |
| `realData` | 엔진별 실제 데이터 스모크 (HF parquet) | Tier 2 (path-filter) / Tier 3 (전수) |
| `requires_data` | 로컬 parquet 필요 — CI 에서 자동 skip (conftest 자동 부착) | Tier 2 |
| `freshInstall` | 빈 캐시 → 자동 다운로드 | Tier 3 |
| `network` | 외부 HTTP 호출 (HF/DART/EDGAR/FRED) — flaky retry 적용 | 직교 (realData 가 자동 부착) |
| `slow` | 실행 30초 이상 — PR fast path 제외 | 직교 |

### 자동 부착 규칙 (conftest.py `pytest_collection_modifyitems`)

```
realData    → network        (자동)
network     → flaky(reruns=2) (자동, pytest-rerunfailures 설치 시)
skipif-data → requires_data   (자동)
```

**효과**: `@pytest.mark.realData` 만 달면 network + flaky 가 암묵 적용.
테스트 작성자가 신경 쓸 marker 는 `unit` / `integration` / `realData` 3개.

---

## 메모리 정책

Polars 는 네이티브 Rust 힙 사용 → Python `gc.collect()` 로 회수 불가 →
**프로세스 종료가 유일한 완전 해제 방법**.

### 메모리 한계 매트릭스

| 컨텍스트 | `PYTEST_MEMORY_LIMIT_MB` | 이유 |
|---|---|---|
| default (unit) | 1500 | Company 로드 없음, 여유 마진 |
| `test-fast` (Tier 1) | 1900 | xdist -n auto, worker 당 안전 |
| `test-full` (Tier 2) | 1900 | xdist -n 2, Polars 누적 방지 |
| `fixture-integration` (Tier 2) | 5000 | 파일별 독립 프로세스 |
| `realdata-suite` (Tier 2/3) | 6000 | scan 20 axes 시 3~4GB 관측 |

환경변수 `PYTEST_MEMORY_LIMIT_MB` 미지정 시 `conftest.py` 가 `PRESSURE_
CRITICAL_MB=1500` 적용.

### 프로세스 격리 메커니즘

1. **xdist** (`pytest -n N`): N 개 worker 프로세스. worker 간 메모리 격리.
2. **`test-realdata.sh`**: 파일 단위 독립 pytest 프로세스 — `for f in tests/realData/*.py; do pytest $f; done`. realdata matrix 각 shard 가 이 모드.
3. **`test-lock.sh`**: `/tmp/dartlab-test.lock` 기반 세션 간 직렬화. 동시
   pytest 실행 방지.

### Fixture scope 규칙

- **module scope 권장** — 파일 단위 로드/해제.
- **session scope 금지** — Company 여러 개 로드 누적 → OOM (2026-03-21 사고 이력).
- **function scope**: 필요하면 사용. 단 `gc.collect()` 권장.

---

## logger vs print 경계

코드 어디에 무엇을 쓸지 혼동하면 테스트가 깨진다. **섞으면 안 된다**.

### 어떤 출력이 어느 채널인가

| 코드 위치 | 출력 방식 | 이유 |
|---|---|---|
| 라이브러리 내부 진단 (`src/dartlab/**/*.py`) | `logger = getLogger(__name__)` | 사용자 `setLevel(WARNING)` 로 제어 가능 |
| CLI user-facing (`src/dartlab/cli/**`) | `print()` | 터미널 응답 자체가 사용자 가치 |
| 사용자 interactive (`setup()`, `ask()` 등) | `print()` | REPL/노트북 직접 반응 |
| 시각화 marker (`viz.emit_chart` `<!--DARTLAB_VIZ:-->` ) | `print()` | webview/extension 이 stdout 파싱 |
| 서버 부트스트랩 (`server/runtime.py`) | `print()` | logger 초기화 전 가능성 |
| 테스트 도우미 | `print()` OK | 디버그 편의성 |

### 테스트 시 캡처 방법

| 대상 | 올바른 fixture | 사례 |
|---|---|---|
| logger 출력 (`_log.info(...)` 등) | **`caplog`** | `with caplog.at_level(logging.WARNING, logger="dartlab.viz"): ...; assert "..." in caplog.text` |
| 사용자 print (CLI, viz marker) | `capsys` | `out = capsys.readouterr().out; assert "..." in out` |
| 파일 디스크립터 레벨 (서브프로세스 포함) | `capfd` | 드물게 필요 |

**흔한 실수**: `logger.info` 출력을 `capsys.readouterr().out` 으로 검증
→ 캡처 실패. 반드시 `caplog.text` 사용.

**dartlab logger 설계 (`src/dartlab/core/logger.py`)**:
- root `dartlab` logger 에 stderr StreamHandler 자동 부착 (최초 1회).
- `propagate=True` 유지 → pytest caplog 가 dartlab 레코드 캡처 가능.
- 기본 레벨 INFO. 사용자는 `logging.getLogger("dartlab").setLevel(WARNING)` 으로 silence 가능.

---

## 실행 가이드

### 로컬 (개발 중)

```bash
# 빠른 smoke (unit 만, ~90초)
bash scripts/dev/test-lock.sh tests/ -m "unit" -v --tb=short

# 특정 엔진 integration
bash scripts/dev/test-lock.sh tests/test_scan_*.py -v

# realData smoke (파일별 프로세스 격리)
bash scripts/dev/test-realdata.sh tests/realData -v

# 특정 realData 파일만 (단일 세션)
bash scripts/dev/test-realdata.sh tests/realData/test_analysis.py -v
```

### CI 재현 (어느 tier 에서 돌 지 확인)

```bash
# Tier 1 PR push 재현
pytest tests/ -n auto -m "unit" --no-cov

# Tier 2 master push 재현 (test-full)
pytest tests/ -n 2 -m "not realData and not heavy and not freshInstall" --cov=dartlab

# realdata path-filter 계산
GITHUB_BASE_REF=master python -X utf8 .github/scripts/planRealdata.py

# external venv smoke
python -m venv /tmp/smoke && /tmp/smoke/bin/pip install dartlab
/tmp/smoke/bin/python scripts/audit/externalVenvSmoke.py
```

---

## 깨지기 쉬운 영역과 회피법

### 1. Logger refactor 후 capsys 테스트 실패

**증상**: `assert "[dartlab]" in captured.out` → empty.

**원인**: print → logger 치환 후 출력이 stderr(logger)로 이동. capsys 는
stdout 만 자동 캡처.

**회피**: logger 관련 assertion 은 `caplog.text` 사용. 위 [logger vs print]
섹션 표 참조.

### 2. 매 push 마다 realdata 도는 것 같음

**증상**: PR push 에 realdata-suite 실행.

**원인**: ci-fast 에 realdata 가 있으면 안 됨. ci-fast.yml 체크.

**회피**: realdata 는 ci-full.yml (master push) 또는 ci-nightly.yml 에만.

### 3. 메모리 초과로 pytest 중단

**증상**: `⚠ 메모리 안전 종료: 1566MB > 1500MB 한계 초과`.

**원인**: Polars 누적. 단일 세션에서 Company 여러 개 로드.

**회피**: 파일별 독립 pytest (`test-realdata.sh`) 또는 xdist `-n 2+` 로
worker 격리.

### 4. Network 의존 테스트 간헐적 실패

**증상**: HF 429, DART timeout 등 transient.

**원인**: 재시도 없으면 한 번 hiccup → CI red.

**회피**: `@pytest.mark.realData` 달면 자동으로 `network` + `flaky(reruns=
2)` 부착. 아니면 수동 `@pytest.mark.network`.

### 5. 번들 리소스 누락 (2026-04-19 사고)

**증상**: wheel 설치 후 런타임에서 `sectionMappings.json` 등 누락 → None
조용히 반환.

**원인**: `pyproject.toml::[tool.hatch.build.targets.wheel].include` 누락.

**방어**: `wheel-smoke` job (Tier 1) + `test_bundledResources` 유닛 + `test_
wheelPackaging` heavy 3중 체크.

---

## 품질 게이트 (변동 허용 범위)

`scripts/audit/qualityGate.py` 가 Tier 1 `quality-gate` 에서 실행:
- E/F-rank 함수 수 — baseline 기록 대비 증가 시 warning (block 아님).
- Dead code — vulture 기준 0건 요구.
- baseline 파일: `scripts/audit/qualityHistory.jsonl` (master push 에서만 기록).

Coverage ratchet:
- 현재 `--cov-fail-under=40` (Tier 2 `test-full`).
- 상향은 사용자 지시 시에만. 자동 조정 금지.

---

## 참고 문서

- `ops/code.md` — docstring 9섹션 rule, 릴리즈 절차, 1.0.0 판정 기준.
- `CLAUDE.md` — 메모리 안전 강행 규칙 + 사용자 지시 이행.
- `.github/scripts/planRealdata.py` — realdata path-filter 매핑 코드.
- `scripts/dev/test-lock.sh` — 세션 직렬화 스크립트.
- `scripts/dev/test-realdata.sh` — realData 파일별 프로세스 분리.

---

## 변경 이력

- 2026-04-22: Phase 3 — 3-tier split + 직교 marker + flaky retry 자동화.
- 이전: `커버리지 90% 목표` 중심이었으나 실행 게이트 설계가 미흡 → 본 개편으로 tier 별 책임 분리.
