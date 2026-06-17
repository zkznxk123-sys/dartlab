# 02. 목표 아키텍처

상태: 구현 착수 전 설계. 코드 변경은 아직 없다.

---

## 1. 설계 원칙

1. 기존 public API를 흔들지 않는다.
2. GPU는 backend 선택지이지 새 분석 엔진이 아니다.
3. 기본값은 `polars` streaming이다.
4. `duckdb` 호환 경로는 유지하되, 현재 구현을 OOC baseline으로 과장하지 않는다.
5. GPU 요청 시 silent fallback은 금지한다.
6. Pyodide와 CPU-only 환경은 import 시 무영향이어야 한다.
7. `src/dartlab/__init__.py`에 GPU probe, GPU import, GPU 환경변수 설정을 넣지 않는다.

---

## 2. 삽입 위치

### 2.1 1차 본진 위치

`src/dartlab/scan/io/cross.py`

추가 후보:

```python
class GpuPolarsCrossScan:
    def aggregate(self, lf: pl.LazyFrame, *, limit: int | None = None) -> pl.DataFrame:
        ...
```

`pickCrossScanEngine` 확장:

```text
polars -> PolarsCrossScan
duckdb -> DuckDbCrossScan
gpu -> GpuPolarsCrossScan
auto -> phase 2 이후 후보, 기본값 금지
```

`Literal["polars", "duckdb"]`는 졸업 후 `Literal["polars", "duckdb", "gpu", "auto"]`로 확장한다.

### 2.2 runtime 진단 위치

후보 A: `src/dartlab/core/polarsGpu.py`

- 장점: L0 core라 scan/quant/prebuild가 공통 사용 가능.
- 단점: core가 RAPIDS 세부를 너무 많이 알면 잡동사니화 위험.

후보 B: `src/dartlab/scan/io/gpuStatus.py`

- 장점: cross-scan 범위에 가둔다.
- 단점: 향후 quant/prebuild가 재사용하려면 위치 이동 필요.

판정: `_attempts` 단계에서 먼저 독립 모듈로 검증하고, 본진 진입 시 **L0에는 순수 진단 enum/환경판정만**, Polars collect 구현은 `scan/io/cross.py`에 둔다.

---

## 3. 공개 계약

### 3.1 1차 공개 표면

기존 표면 확장:

```python
dartlab.scan.docsSections(year=2024, engine="gpu")
```

환경변수:

```bash
DARTLAB_CROSS_SCAN_ENGINE=gpu
```

새 top-level 공개 함수는 만들지 않는다. `operation.apiContract`상 새 공개 진입점은 엔진명/축 dispatch 우선이다.

### 3.2 진단 표면

1차는 public API가 아니라 문서화된 진단 helper 후보:

```python
from dartlab.scan.io.cross import gpuStatus  # 내부/개발자 경로
```

public beta 전에는 `import dartlab`만으로 접근 가능한 진단 표면이 필요하다. 다만 `dartlab.gpuStatus()` 같은 새 top-level 함수는 apiContract상 성급하므로, 1차 후보는 다음 둘이다.

- `dartlab.capabilities()` 또는 기존 runtime/status 표면에 `gpu` 항목 포함.
- CLI `dartlab doctor gpu` 또는 `dartlab status --gpu`.

초기 `engine="gpu"` backend patch 단계에서는 내부 helper로 시작하고, 문서 공개 전 위 진단 표면 중 하나를 반드시 확정한다.

---

## 4. GPU backend 동작

### 4.1 명시 gpu

동작:

1. `sys.platform == "emscripten"`이면 `RuntimeError("GPU backend unsupported in Pyodide")`.
2. `cudf_polars` import 확인.
3. Polars `GPUEngine` 사용 가능 확인.
4. `limit` 적용 후 `lf.collect(engine=pl.GPUEngine(...))`.
5. fallback/unsupported 연산 발생 시 명확히 실패.

목표 코드는 실측 후 결정하지만 원칙은 다음이다.

```python
gpuEngine = pl.GPUEngine(raise_on_fail=True)
return lf.collect(engine=gpuEngine)
```

`raise_on_fail=True`에 상응하는 방식이 버전별로 다르면 `_attempts`에서 version guard를 확정한다.

### 4.2 auto

Phase 1에서는 구현하지 않는다.

Phase 2 후보 조건:

- `gpuStatus().usable is True`
- LazyFrame plan이 GPU 지원 연산 위주
- row estimate 또는 file size threshold 이상
- 사용자가 `DARTLAB_CROSS_SCAN_ENGINE=auto`를 명시
- 실패 시 `polars` streaming으로 fallback하되 로그/metadata에 fallback 사유와 `engineUsed="polars"`를 남김

기본값 `auto`는 금지.

---

## 5. 상태 모델

`GpuStatus` 후보 필드:

| field | 의미 |
|---|---|
| `available` | GPU backend 사용 가능 여부 |
| `reason` | unavailable 사유 코드 |
| `polarsVersion` | Polars 버전 |
| `hasGpuEngine` | `pl.GPUEngine` 존재 여부 |
| `hasCudfPolars` | `cudf_polars` import 가능 여부 |
| `platform` | `sys.platform` |
| `deviceSummary` | 가능하면 GPU 이름/VRAM, 실패 시 None |
| `engineUsed` | 실제 실행 엔진. status probe는 None, 실행 결과 metadata는 `gpu`/`polars` |
| `fallback` | fallback 발생 여부 |

reason 후보:

- `ok`
- `pyodideUnsupported`
- `platformUnsupported`
- `missingCudfPolars`
- `missingPolarsGpuEngine`
- `noCudaDevice`
- `probeFailed`

---

## 6. 문서와 메시지

오류 메시지는 extras를 안내하지 않는다.

허용:

```text
GPU backend requires RAPIDS cudf-polars for your CUDA version.
See Polars GPU support docs: https://docs.pola.rs/user-guide/gpu-support/
CPU backend remains available with DARTLAB_CROSS_SCAN_ENGINE=polars.
```

금지:

```text
pip install dartlab[gpu]
pip install --upgrade dartlab[gpu]
GPU acceleration is automatic for all dartlab workloads.
pip install polars[gpu]
import cudf
```

---

## 7. 영향 파일 후보

실측 졸업 후 예상 touchpoints:

| 파일 | 변경 |
|---|---|
| `src/dartlab/scan/io/cross.py` | `GpuPolarsCrossScan`, dispatcher 확장, docstring 갱신 |
| `tests/scan/test_cross_scan_engine.py` | gpu unavailable/dispatcher/unit tests |
| `tests/_attempts/polarsGpuBackend/` | 벤치/데모/README/docstring 결과 |
| `src/dartlab/skills/specs/engines/scan/SKILL.md` | engine 값에 gpu 명시, runtime 제한 |
| `src/dartlab/skills/specs/engines/data/SKILL.md` | prebuild/batch GPU opt-in 운영 문구 |
| `README.md` | 설계 선택 또는 성능 섹션에 제한 문구 |

Skill OS 수정 시 6 JSON 산출물은 수동 `artifactSync --write` 대상이다.
