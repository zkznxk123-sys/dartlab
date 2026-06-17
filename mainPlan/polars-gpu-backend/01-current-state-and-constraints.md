# 01. 현재 상태와 제약

상태: 코드 실측 + 공식 문서 제약 정리.

---

## 1. 현재 repo 실측

### 1.1 의존성

- `pyproject.toml`: `polars>=1.0.0,<2; sys_platform != 'emscripten'`
- `pyproject.toml`: `duckdb>=1.0,<2; sys_platform != 'emscripten'`
- `[project.optional-dependencies]` 없음. memory rule상 extras 금지.
- Pyodide는 `polars; sys_platform == 'emscripten'`, parquet는 pyarrow 우회.

### 1.2 Polars runtime guard

`src/dartlab/__init__.py`가 Polars import 전에 다음 환경을 박는다.

- `POLARS_MAX_THREADS=4`
- `POLARS_AUTO_NEW_STREAMING=1`
- `POLARS_STREAMING_CHUNK_SIZE=10000`

목적은 Polars Rust heap/OOM 방어다. GPU backend는 이 기본 메모리 안전 정책과 충돌하지 않아야 한다.

### 1.3 cross-scan backend 자리

`src/dartlab/scan/io/cross.py`:

- `CrossScanEngine` Protocol
- `PolarsCrossScan`: `lf.collect(engine="streaming")`
- `DuckDbCrossScan`: 현재는 LazyFrame을 먼저 `collect(engine="streaming")`한 뒤 DuckDB relation에 등록
- `pickCrossScanEngine(engine=None)`: `DARTLAB_CROSS_SCAN_ENGINE` 또는 기본 `polars`

`src/dartlab/scan/scanClass.py::docsSections`는 `engine` 인자를 이미 받고 `pickCrossScanEngine(engine=engine).aggregate(lf, limit=...)`로 위임한다.

따라서 GPU backend 삽입의 최소 경로는 `scan/io/cross.py` 확장이다.

중요 정정: 코드 주석에는 DuckDB가 OOC처럼 표현되어 있지만, 현재 구현은 진짜 out-of-core baseline이 아니다. PRD와 benchmark는 이 상태를 그대로 인정하고, DuckDB를 "OOC 대비 성능 기준"으로 쓰지 않는다. DuckDB OOC 자체를 개선하는 일은 별도 PRD 범위다.

### 1.4 현재 로컬 실측

2026-06-17 로컬 확인:

- Polars `1.41.1`
- RTX 4060 Laptop 8GB VRAM
- `pl.GPUEngine` 존재
- `cudf_polars`/`cudf` 미설치
- `lf.collect(engine="gpu")`는 `ModuleNotFoundError: cudf_polars not found`로 실패

이 상태는 "API는 있지만 backend 패키지 없음"이다. dartlab은 이를 사용자에게 명확히 구분해 보여야 한다.

---

## 2. Polars GPU 제약

공식 문서 기준:

- Polars GPU 지원은 Open Beta 성격이다.
- GPU 엔진은 Lazy API에서 사용한다.
- NVIDIA GPU + CUDA + RAPIDS cuDF 계열 패키지가 필요하다.
- streaming engine과 GPU engine은 동시에 쓰는 경로가 아니다.
- 일부 연산은 GPU에서 지원되지 않아 CPU fallback 또는 실패가 가능하다.

참조:

- https://docs.pola.rs/user-guide/gpu-support/
- https://docs.pola.rs/api/python/dev/reference/lazyframe/api/polars.LazyFrame.collect.html

---

## 3. 프로젝트 운영 제약

### 3.1 single base install

`feedback_no_patterns.md`와 README 모두 `[project.optional-dependencies]` 금지와 단일 base install을 명시한다.

함의:

- `dartlab[gpu]` extras 금지.
- `cudf-polars-cu12` 기본 dependency 강제도 현실적으로 부적합.
- 무거운/환경 제한 dependency는 lazy import + 진단 메시지로 처리한다.

### 3.2 신규 능력 졸업 게이트

CLAUDE.md 규칙:

> 신규 능력·실험 `src/dartlab/**` 직행 금지. `tests/_attempts/<카테고리>/`에서 개념확립 → 모듈화 → 데모 → 덕지덕지 제거 → 클린코드 → 9섹션 docstring 확정 후에만 본진 배치.

함의:

- 이번 PRD는 설계만.
- 첫 구현도 `tests/_attempts/polarsGpuBackend/`에서 시작.
- `src/dartlab/scan/io/cross.py` 진입은 실측 졸업 후.

### 3.3 Pyodide

Pyodide는 `sys.platform == "emscripten"`이며 Polars parquet 제약을 이미 우회한다. RAPIDS/cuDF GPU는 범위 밖이다.

함의:

- GPU 상태 API는 Pyodide에서 `unsupported`를 반환해야 한다.
- Pyodide import path에 GPU dependency import가 있어서는 안 된다.

---

## 4. 적용 가능한 workload

### 후보

- `scan.docsSections`류 docsIndex slim parquet filter/select/group_by.
- `scan/account`, `scan/ratio`, finance scan builder 중 LazyFrame 집계.
- `quant/factor` 계열 전종목 batch.
- `.github/scripts/prebuild`의 반복 대형 parquet aggregation 중 LazyFrame 경로.

### 비후보

- `Company.panel`, `Company.show`, `Company.story`.
- DART XML/HTML parsing.
- LLM/AI agent 흐름.
- eager `pl.DataFrame` 조립이 대부분인 작은 계산.
- Pyodide.

---

## 5. 주요 위험

| 위험 | 설명 | PRD 대응 |
---|---|---|
| silent CPU fallback | GPU 요청했지만 CPU로 실행 | 명시 GPU 모드는 fallback 금지, 진단 필수 |
| OOM 방어 해제 | streaming 대신 GPU collect로 RAM/VRAM 피크 증가 | attempts에서 RSS/VRAM 실측 후 제한 |
| 설치 마찰 | 사용자에게 CUDA/cuDF 설치 요구 | 기본 설치 불변, lazy import |
| platform drift | Windows native, Linux, WSL2 차이 | runtime status가 platform을 구분 |
| 과장 claim | GPU가 모든 분석을 빠르게 한다는 오해 | workload 한정 문구 |
| baseline 착시 | 현재 DuckDB 구현을 OOC baseline으로 착각 | benchmark에서 CPU streaming과 DuckDB compatibility 관측치를 분리 |
