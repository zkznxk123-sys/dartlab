# 04. 테스트 · 검증 · 롤백

상태: 실행 전 검증 설계.

---

## 1. 테스트 전략

GPU는 CI 기본 환경에 없을 확률이 높다. 따라서 테스트는 두 층으로 나눈다.

1. **항상 실행되는 CPU-safe 테스트** - GPU 패키지 없음/플랫폼 미지원 상황을 정상 처리하는지 검증.
2. **GPU 환경 전용 테스트** - 명시 marker/env가 있을 때만 실제 GPU collect와 성능/parity를 검증.

---

## 2. 단위 테스트

대상: `tests/scan/test_cross_scan_engine.py` 확장.

필수 케이스:

- 기본 dispatcher는 계속 `PolarsCrossScan`.
- `DARTLAB_CROSS_SCAN_ENGINE=gpu`면 GPU backend 객체 선택.
- `engine="gpu"`가 env보다 우선.
- `engine="polars"`는 gpu env보다 우선.
- `cudf_polars`가 없을 때 `GpuPolarsCrossScan().aggregate(...)`는 명확한 예외.
- Pyodide platform monkeypatch 시 unsupported.
- `gpuStatus()`는 import error 없이 status dict/dataclass 반환.

GPU 없는 CI에서는 실제 GPU collect를 실행하지 않는다.

---

## 3. 통합/realData 테스트

marker 후보:

```python
pytestmark = [pytest.mark.realData, pytest.mark.gpu]
```

단, 새 marker는 `pyproject.toml` 등록 필요. marker 추가 자체가 공용 계약이므로 본진 진입 단계에서만 한다.

실행 조건:

- `DARTLAB_GPU_TEST=1`
- `cudf_polars` import 가능
- `pl.GPUEngine` 존재
- probe collect 성공

통과 기준:

- W1 docsIndex 결과 schema/row count 동치.
- W2 finance scan 결과 주요 컬럼 동치.
- GPU fallback이 발생하지 않음.

---

## 4. Guard Index

본진 변경 후 기본 검증:

```bash
uv run python -X utf8 tests/audit/dartlabGuard.py quick
```

L0~L1.5 경계 변경이 있으면:

```bash
uv run python -X utf8 tests/audit/dartlabGuard.py strict --scope l0-l15 --providers dart,edgar
```

전체 `pytest tests/ -v` 금지. 단일 파일은 test-lock 경유.

---

## 5. 문서/Skill OS 검증

GPU backend가 `engine="gpu"`로 공개 호출 예시에 들어가면 다음 갱신이 필요하다.

- `src/dartlab/skills/specs/engines/scan/SKILL.md`
- `src/dartlab/skills/specs/engines/data/SKILL.md`
- 필요 시 README 설계 선택 섹션
- Skill 6 JSON은 수동 `artifactSync --write`

금지:

- 자동 artifact sync.
- GPU 문서만 바꾸고 실제 dispatcher/test 누락.
- code path만 추가하고 Skill OS 누락.

---

## 6. 롤백 전략

### Phase 1 - attempts only

롤백: `tests/_attempts/polarsGpuBackend/` 삭제 또는 해당 commit revert.

영향: src 0줄, 사용자 영향 0.

### Phase 2 - backend class 추가

롤백: `scan/io/cross.py`와 `tests/scan/test_cross_scan_engine.py` 단일 revert.

조건: 기본 dispatcher가 `polars`라 사용자가 `gpu`를 명시하지 않는 한 무영향.

### Phase 3 - docs/Skill 노출

롤백: Skill/README commit revert + artifact JSON revert.

주의: 문서와 code surface를 같은 릴리즈 안에서 불일치하게 두지 않는다.

### Phase 4 - auto 후보

롤백: `auto` branch만 비활성화. `gpu` 명시 backend는 유지 가능.

---

## 7. 릴리즈 게이트

MUST:

- CPU-only CI green.
- GPU missing 상태 메시지 검증.
- 기존 `polars`/`duckdb` 동치 테스트 green.
- GPU 문구에 "일부 workload", "환경 필요", "기본값 아님" 포함.
- 현재 DuckDB를 OOC baseline으로 부르지 않음.

SHOULD:

- 최소 1개 NVIDIA Linux/WSL2 실측 표.
- 8GB VRAM 환경 결과와 한계 기록.
- `POLARS_VERBOSE=1` 또는 `raise_on_fail` 기반 fallback 방지 증거.
- public beta 전 `dartlab.capabilities()`/runtime/status 또는 `dartlab doctor gpu` 중 하나로 GPU 진단 표면 확정.

KILL:

- 성능표 없이 "GPU 가속으로 빠름" 릴리즈 노트.
- default engine 변경.
- GPU 패키지 설치 실패를 dartlab import 실패로 전파.
- GitHub hosted CI에서 CUDA/RAPIDS 설치를 시도하는 job.
