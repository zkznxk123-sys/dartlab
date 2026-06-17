# 00. 제품 PRD - Polars GPU Backend 적용성 검증 및 선택적 배치 가속

상태: PRD v0.1. 사용자 라이브러리 관점의 "GPU 지원 포함"을 "선택적 배치 가속 경로"로 정의한다.

---

## 1. 문제 정의

dartlab은 Polars 기반 재무·공시 데이터 라이브러리다. 현재 성능 병목은 크게 둘이다.

1. **대형 횡단 scan/prebuild/batch** - 전종목 parquet를 LazyFrame으로 읽고 filter/group_by/join/aggregation을 수행하는 경로.
2. **단일 회사 분석/공시 파싱/story** - 회사 1개 parquet, XML/HTML parsing, Python object 조립, LLM/tool 흐름.

Polars GPU 엔진은 1번 일부에만 직접 가치가 있다. 2번은 GPU보다 IO, parsing, Python orchestration, 기존 cache/memory lifecycle이 지배한다.

따라서 "GPU 지원"의 제품 정의는 다음이다.

> RAPIDS/cuDF가 준비된 사용자가 대형 횡단 LazyFrame 작업에서 CPU streaming보다 유의미하게 빠른 선택 backend를 쓸 수 있게 한다. 기존 CPU/브라우저/서버 사용자는 아무 설정 없이 지금처럼 안전하게 작동한다. 공개 제품명은 "GPU 지원" 단독이 아니라 "선택적 GPU backend" 또는 "일부 배치 workload GPU 가속"으로만 쓴다.

---

## 2. 사용자

### 2.1 1차 사용자

- 로컬 고성능 워크스테이션 또는 WSL2/Linux NVIDIA GPU를 가진 파워유저.
- 전종목 `scan`, `docsSections`, `quant factor`, prebuild 류 작업을 반복하는 운영자/기여자.
- CI가 아니라 수동 배치나 연구용 노트북에서 대형 parquet 연산 시간을 줄이고 싶은 사용자.

### 2.2 비대상 사용자

- `Company("005930")`로 단일 회사 분석만 하는 일반 사용자.
- Pyodide/browser 사용 환경.
- GPU는 있으나 RAPIDS/cuDF를 설치할 수 없는 Windows native/CPU-only 환경.
- 메모리 안정성이 성능보다 중요한 기본 서버/runtime.

---

## 3. 제품 약속

### MUST

- `pip install dartlab` 후 CPU 경로는 기존과 동일하게 작동한다.
- GPU가 없어도 import, scan guide, Company, Pyodide가 깨지지 않는다.
- GPU 사용 가능 여부를 사용자가 명확히 확인할 수 있다.
- GPU를 명시 요청했는데 backend가 준비되지 않았으면 명확한 오류 또는 상태 메시지를 낸다.
- 성능 claim은 실측 데이터셋, row 수, 연산 종류, CPU baseline, GPU 모델을 함께 적는다.

### SHOULD

- `DARTLAB_CROSS_SCAN_ENGINE=gpu` 또는 해당 engine 인자로 cross-scan GPU backend를 고를 수 있다.
- `DARTLAB_CROSS_SCAN_ENGINE=auto`는 실측이 충분히 쌓인 후 도입하되, 기본값으로 삼지 않는다.
- GPU backend는 `scan/io/cross.py`의 backend protocol을 확장해 기존 caller 변경을 최소화한다.
- README/Skill OS에는 "GPU 가속 경로 내장, 환경 준비 시 사용 가능" 정도로 정직하게 노출한다.
- public beta 전에는 `import dartlab`만으로 확인 가능한 runtime/capabilities 진단 또는 `dartlab doctor gpu` CLI 중 하나를 제공한다.

### KILL

- `cudf-polars-cu12`를 `pyproject.toml` 기본 dependency에 넣는 것.
- `[project.optional-dependencies]` 또는 `dartlab[gpu]` extras를 만드는 것.
- dartlab import 시 `POLARS_ENGINE_AFFINITY=gpu`를 자동 설정하는 것.
- GPU 실패 시 CPU로 조용히 fallback하고 "GPU 사용"처럼 보이게 하는 것.
- 단일 회사 분석, story, Pyodide에 GPU 효과를 암시하는 문구.
- "DartLab GPU 가속 지원"을 단독 headline으로 쓰는 것.
- "자동 GPU 최적화", "모든 scan/analysis 가속", "OOM 해결책" 같은 문구.

---

## 4. 포함의 정의

본 PRD에서 "포함"은 다음을 뜻한다.

1. 코드 구조가 GPU backend를 수용한다.
2. runtime 감지와 진단 표면이 있다.
3. GPU 없는 환경의 test/CI가 green이다.
4. GPU 있는 환경에서만 실행되는 수동/realData 벤치가 있다.
5. 문서가 설치·환경·제약을 정직하게 설명한다.

본 PRD에서 "포함"이 아닌 것:

- 모든 사용자에게 GPU 의존성을 설치시키는 것.
- GPU를 기본 실행 엔진으로 삼는 것.
- CPU streaming/DuckDB 호환 경로를 제거하는 것.

---

## 5. 성공 기준

### 기능 성공

- `pickCrossScanEngine(engine="gpu")`가 GPU 환경에서 `GpuPolarsCrossScan`을 반환한다.
- GPU 환경 미충족 시 진단이 다음을 구분한다: `polars ok`, `cudf_polars missing`, `unsupported platform`, `no cuda device`, `gpu collect failed`.
- `Scan.docsSections(..., engine="gpu")`류 호출이 기존 반환 schema와 동치다.

### 내부 backend 진입 기준

실측 전 claim 금지. 본진에 `engine="gpu"` backend를 넣는 최소 기준은 다음이다.

| workload | 최소 기준 |
|---|---|
| docsIndex 대형 filter/group_by | CPU streaming 대비 p50 1.5x 이상, 결과 동치 |
| finance scan account/ratio | CPU streaming 대비 p50 1.5x 이상, peak RSS 악화 없음 |
| quant factor batch | CPU streaming 대비 p50 1.3x 이상, 실패율 0 |

8GB VRAM급 GPU에서 OOM이 잦으면 "지원 가능"은 유지하되 기본 auto 후보에서 제외한다.

현재 `DuckDbCrossScan`은 LazyFrame을 먼저 `collect(engine="streaming")`한 뒤 DuckDB에 등록하므로, 본 PRD v0.1에서는 DuckDB를 "진짜 OOC 성능 baseline"으로 부르지 않는다. DuckDB와의 비교는 compatibility 관측치로만 둔다.

### 공개 성능 claim 기준

README/릴리즈/블로그에서 "N배 빠름" 또는 "GPU 가속"을 성능 claim으로 쓰려면 별도 public beta 기준을 통과해야 한다.

| 항목 | 기준 |
|---|---|
| 데이터셋 | 최소 4개 패밀리: scan finance, scan/report 또는 docsIndex, gov/prices quant batch, EDGAR 또는 industry/prebuild bulk |
| 쿼리 수 | 각 패밀리 3개 이상, 총 12개 이상 |
| 반복 | cold/warm 분리, 각 5회 이상 |
| 속도 | 대상 workload 75% 이상에서 median 2.0x 이상 |
| tail risk | p90이 CPU보다 10% 이상 느린 케이스 0 |
| fallback | public beta 후보의 GPU fallback 비율 5% 이하. fallback 실행은 speedup 계산에서 제외 |
| 안정성 | crash 0, GPU OOM 0 또는 명시 unsupported 처리, 결과 parity 100% |
| 표기 | 하드웨어, CUDA/cuDF/Polars 버전, row 수, 연산 종류를 함께 공개 |

이 기준 전 허용 문구는 "일부 배치 workload에서 빨라질 수 있음"까지만이다.

### 사용자 성공

- CPU-only 사용자는 새 dependency 설치 요구를 보지 않는다.
- GPU 사용자는 실패 원인을 한 줄로 이해하고 다음 행동을 알 수 있다.
- 문서에 "Open Beta/환경 제한/일부 연산 fallback 가능/기본값 아님"이 노출된다.

---

## 6. 비목표

- RAPIDS 설치 자동화.
- CUDA/드라이버 관리.
- Pyodide/WebGPU Polars 가속.
- pandas/cuDF 직접 변환 API 추가.
- 모든 `pl.read_parquet`/`pl.DataFrame` 경로 GPU화.
- 기존 Polars streaming/DuckDB 경로 대체.
