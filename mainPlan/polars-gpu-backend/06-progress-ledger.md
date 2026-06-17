# 06. Progress Ledger

상태: PRD v0.1 작성 완료. 구현 미착수.

---

## 2026-06-17

- 사용자 요청: "사용자 라이브러리인데 GPU 지원 포함 방향을 고민, mainPlan에 PRD급 설계만 작성, 전문에이전트 토론".
- 생성 카테고리: `mainPlan/polars-gpu-backend/`.
- 코드 변경: 없음.
- 결론: GPU 지원은 포함하되 기본 자동 GPU화와 dependency 강제는 금지. 제품명은 "선택적 GPU backend"로 제한. `scan/io/cross.py` backend 확장 + `_attempts` 실측 후 본진 진입.
- 전문가 토론 반영 정정: 현재 `DuckDbCrossScan`은 먼저 streaming collect 후 DuckDB에 등록하므로 OOC baseline이 아니다. 성능 claim 기준은 4개 패밀리 12개 쿼리, 75% median 2.0x 이상, fallback 5% 이하로 격상.

## 근거

- `src/dartlab/__init__.py`는 Polars OOM 방어 환경변수 3종을 import 전에 설정한다.
- `src/dartlab/scan/io/cross.py`는 이미 `CrossScanEngine` Protocol과 Polars/DuckDB backend dispatcher를 갖고 있다.
- 단, 현 DuckDB 구현은 OOC baseline이 아니라 compatibility 경로로만 본다.
- `src/dartlab/scan/scanClass.py::docsSections`는 이미 `engine` 인자를 받아 cross-scan dispatcher로 넘긴다.
- `feedback_no_patterns.md`와 README는 optional-dependencies/extras 금지, single base install 원칙을 명시한다.
- Polars GPU는 공식 문서상 Lazy API/RAPIDS/cuDF/NVIDIA 환경 제약과 streaming 미호환 제약이 있다.

## NEXT

운영자 go 시 순서:

1. `tests/_attempts/polarsGpuBackend/README.md` 작성.
2. `probeGpuEngine.py`로 현재 환경 status 모델 확정.
3. W1 docsIndex benchmark 작성.
4. Phase 0 inventory: 4개 패밀리 12개 쿼리 후보 확정.
5. W2 finance scan benchmark 작성.
6. W3 quant factor 후보를 코드에서 좁혀 benchmark 작성.
7. W4 EDGAR 또는 industry/prebuild bulk benchmark 작성.
8. 결과가 GO면 `scan/io/cross.py`에 `GpuPolarsCrossScan` 최소 patch.

## 보류

- `DARTLAB_CROSS_SCAN_ENGINE=auto`는 보류.
- README/Skill OS 공개 노출은 본진 backend와 테스트가 들어간 뒤.
- `cudf-polars` dependency 추가는 보류가 아니라 KILL.
