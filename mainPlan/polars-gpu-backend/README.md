# Polars GPU Backend 적용성 검증 및 선택적 배치 가속 PRD Index

상태: 비전/실행 PRD v0.1 (2026-06-17, 전문에이전트 4 렌즈 토론 + 코드 실측 기반)
범위: dartlab 사용자 라이브러리에 **GPU 가속 가능 경로를 포함**하되, 기본 설치·기본 실행·Pyodide·CPU 사용자 경험을 깨지 않는 Polars GPU backend 설계. 구현은 아직 하지 않는다.

> 핵심 결론: GPU 지원은 포함한다. 그러나 `cudf-polars`를 기본 의존성으로 강제하거나 전역 자동 GPU화를 기본값으로 켜지는 않는다. 먼저 `tests/_attempts/polarsGpuBackend/`에서 실측한 뒤, `scan/io/cross.py`의 cross-scan backend에 명시 opt-in으로 진입한다.

---

## 한 줄 결론

dartlab의 GPU 지원은 "빠른 기본값"이 아니라 **대형 LazyFrame 횡단 배치 작업을 위한 선택 backend**다. 기본은 현재의 Polars streaming 안전 경로와 DuckDB 호환 경로를 유지하고, RAPIDS/cuDF가 준비된 Linux/WSL2 NVIDIA 환경에서만 `DARTLAB_CROSS_SCAN_ENGINE=gpu` 또는 명시 인자로 GPU를 탄다.

---

## 문서 지도

1. [00-product-prd.md](00-product-prd.md) - 제품 목표, 사용자 약속, 포함/비포함 정의, 성공 기준.
2. [01-current-state-and-constraints.md](01-current-state-and-constraints.md) - 현재 코드 실측, Polars GPU 제약, repo 운영 규칙.
3. [02-target-architecture.md](02-target-architecture.md) - backend 삽입 위치, 공개 계약, runtime 감지, fallback 정책.
4. [03-attempts-benchmark-plan.md](03-attempts-benchmark-plan.md) - `_attempts` 실험 설계, 벤치마크 데이터셋, 졸업 게이트.
5. [04-testing-validation-rollback.md](04-testing-validation-rollback.md) - 테스트 매트릭스, CI/GPU 없는 환경 처리, 롤백.
6. [05-specialist-review.md](05-specialist-review.md) - GPU 기술/패키징 UX/아키텍처 테스트/PM 렌즈 토론 수렴.
7. [06-progress-ledger.md](06-progress-ledger.md) - 세션 간 재개 원장과 NEXT 포인터.

---

## 정직 척추

- **지원 포함, 의존성 강제 아님** - 사용자는 `pip install dartlab`만으로 기존 CPU 경로가 즉시 작동해야 한다. GPU stack은 환경이 맞는 사용자가 별도로 갖춘다.
- **기본값은 안전** - `POLARS_MAX_THREADS=4`, `POLARS_AUTO_NEW_STREAMING=1`, `POLARS_STREAMING_CHUNK_SIZE=10000`의 OOM 방어를 기본으로 유지한다.
- **GPU는 LazyFrame cross-scan/배치 한정** - 단일 `Company`, `story`, eager DataFrame, Pyodide, 공시 HTML/XML 파싱은 범위 밖.
- **silent fallback 금지** - GPU를 요청했는데 CPU로 조용히 내려가면 안 된다. 명시 GPU 모드는 `raise_on_fail=True` 성격의 검증이 필요하다.
- **자동 GPU 기본값 금지** - `POLARS_ENGINE_AFFINITY=gpu`류 전역 설정을 dartlab import 시 자동 주입하지 않는다.
- **실측 전 src 0줄** - 신규 능력은 `tests/_attempts/polarsGpuBackend/` 졸업 게이트 후에만 `src/dartlab` 진입.
- **DuckDB 과장 금지** - 현재 `DuckDbCrossScan`은 LazyFrame을 먼저 streaming collect한 뒤 DuckDB에 등록한다. 이 상태를 "진짜 OOC baseline"으로 쓰지 않는다.
