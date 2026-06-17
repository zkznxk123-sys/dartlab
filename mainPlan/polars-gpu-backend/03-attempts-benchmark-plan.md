# 03. `_attempts` 벤치마크·졸업 계획

상태: src 진입 전 필수 실험 설계.

---

## 1. 카테고리

```text
tests/_attempts/polarsGpuBackend/
```

목표: GPU backend가 dartlab workload에서 실제로 가치가 있는지 검증하고, 본진 진입 최소 surface를 확정한다.

---

## 2. 졸업 게이트

CLAUDE.md 신규 능력 게이트를 그대로 적용한다.

| 단계 | 산출물 | 통과 기준 |
|---|---|---|
| 1. 카테고리 | README + 목표/비목표 | 본 PRD 링크, scope 명시 |
| 2. 개념확립 | `probeGpuEngine.py` | gpu/cpu/unsupported 상태를 구분 |
| 3. 모듈화 | `gpuBackend.py` | status/probe/collect 함수 분리 |
| 4. 데모 | 4 패밀리 12 쿼리 benchmark | 결과 docstring + README 표 |
| 5. 덕지덕지 제거 | 환경/설치 특수케이스 축소 | version guard 정리 |
| 6. 클린코드 | 최소 API로 축소 | src 이동 후보 1~2 파일 |
| 7. docstring | 9 섹션 확정 | Args/Returns/Raises/Example 포함 |
| 8. 본진 배치 | `scan/io/cross.py` patch | 테스트/문서 동행 |

---

## 3. Phase 0 - no-claim inventory

성능 claim 없이 후보 쿼리부터 고정한다. 최소 4개 패밀리, 총 12개 쿼리:

| 패밀리 | 후보 |
|---|---|
| scan finance | account/ratio/profitability 계열 3개 |
| scan docs/report | docsIndex/report index filter/group_by 3개 |
| quant/gov price | factor/ranking/backtest batch 3개 |
| EDGAR 또는 industry/prebuild | EDGAR scan 또는 industry/prebuild bulk 3개 |

이 inventory가 끝나기 전 README/릴리즈 성능 문구는 금지다.

---

## 4. 대표 벤치마크 workload

### W1 - docsIndex cross-scan

목적: `Scan.docsSections`와 가장 가까운 slim index workload.

작업:

- `pl.scan_parquet(data/dart/scan/docsIndex.parquet)`
- filter: `year == 2024`, `contentLength > 0`
- select: `stockCode`, `corpName`, `sectionTitle`, `contentLength`
- optional group_by: `stockCode` count/sum

비교:

- CPU streaming: `collect(engine="streaming")`
- CPU default: `collect()`
- GPU: `collect(engine=GPUEngine(...))`
- DuckDB compatibility: 현재 `DuckDbCrossScan` 경로. 단, 이 구현은 먼저 streaming collect 후 DuckDB에 등록하므로 OOC baseline으로 부르지 않는다.

### W2 - finance scan account/ratio

목적: 전종목 재무 parquet filter/group_by/pivot에 가까운 workload.

작업:

- `data/dart/scan/finance.parquet` 또는 사용 가능한 scan finance artifact
- account subset filter
- year/quarter filter
- group_by stockCode/latestPeriod aggregation

주의:

- pivot/window가 포함되면 GPU/streaming 지원 차이를 따로 기록한다.

### W3 - quant factor batch

목적: 실사용 대형 batch에서 GPU가 의미 있는지 확인.

작업 후보:

- `quant/factor/build.py`의 LazyFrame collect 후보를 독립 fixture로 재현.
- 실제 provider import 없이 parquet 경로 + pure transform으로 한정.

### W4 - EDGAR 또는 industry/prebuild bulk

목적: KR scan만 빠른 착시를 피한다.

작업 후보:

- EDGAR docsIndex/finance scan parquet 중 하나.
- industry/prebuild bulk aggregation 중 LazyFrame으로 고립 가능한 쿼리.

---

## 5. 측정 항목

| 항목 | 측정법 |
|---|---|
| wall time | `time.perf_counter()` p50/p95, warmup 1회 제외 |
| result parity | schema + sorted rows hash 또는 `frame_equal` 계열 |
| peak RSS | `psutil` 가능 시, 없으면 선택 측정 |
| GPU memory | `nvidia-smi` 가능 시 snapshot, 실패해도 skip |
| fallback 여부 | `POLARS_VERBOSE=1` 로그 또는 raise-on-fail |
| environment | OS, Python, Polars, cudf_polars, CUDA, GPU name |

`POLARS_VERBOSE=1` 로그는 stdout에만 남긴다. repo root 산출물 금지.

---

## 6. 성공/실패 판정

### GO - 본진 backend 진입

- W1/W2 중 하나 이상 1.5x 이상.
- 결과 parity 통과.
- GPU 없는 환경에서 status/probe가 오류 없이 `unavailable` 반환.
- 8GB VRAM에서 OOM 없이 대표 workload 완료.
- CPU fallback을 GPU 성공으로 기록하지 않음.

### PUBLIC BETA

공개 성능 claim은 00 문서의 "공개 성능 claim 기준"을 통과해야 한다. 핵심은 총 12개 쿼리, 75% 이상 median 2.0x, p90 tail regression 0, fallback 5% 이하, parity 100%다.

### CONDITIONAL

- 특정 workload만 빠름.
- GPU 연산 지원 제약이 커서 `engine="gpu"` 수동에만 가치.
- VRAM 8GB는 불안정하지만 16GB+에서 의미 있음.

이 경우 본진 진입은 가능하나 `auto`와 공개 성능 claim은 금지하고 문서에 제한을 강하게 쓴다.

### KILL

- CPU streaming 대비 일관되게 느림.
- fallback 감지가 불가능하거나 CPU fallback을 신뢰할 수 없음.
- 설치/환경 오류가 너무 복잡해 사용자 메시지가 불명확.
- GPU path가 OOM 방어를 구조적으로 무력화.

---

## 7. 실험 산출물 규칙

- raw benchmark output은 stdout 또는 `/tmp`만.
- repo에는 README, 최소 코드, 작은 합성 fixture만.
- 대형 parquet 복사 금지.
- GPU 환경이 없으면 skip이 아니라 "unavailable 판정 테스트"를 통과로 본다.
- 본진 이전에 `tests/_attempts/polarsGpuBackend/README.md`에 결과 표를 박는다.

---

## 8. 재현 명령 후보

```bash
uv run python -X utf8 tests/_attempts/polarsGpuBackend/probeGpuEngine.py
uv run python -X utf8 tests/_attempts/polarsGpuBackend/benchCrossScan.py --workload docs-index
uv run python -X utf8 tests/_attempts/polarsGpuBackend/benchCrossScan.py --workload finance-scan
```

GPU 없는 환경:

```bash
uv run python -X utf8 tests/_attempts/polarsGpuBackend/probeGpuEngine.py
# expected: unavailable + reason, exit 0
```
