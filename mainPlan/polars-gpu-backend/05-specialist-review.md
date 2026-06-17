# 05. 전문에이전트 토론 수렴

상태: 4 렌즈 토론 수렴본. 개별 의견은 PRD 결정으로 흡수한다.

---

## 1. 렌즈 구성

| 렌즈 | 질문 |
|---|---|
| GPU 기술 검토 | Polars/RAPIDS 제약상 어디까지 가능한가 |
| 패키징/사용자 경험 | 사용자 라이브러리에서 GPU stack을 어떻게 노출해야 설치가 안 깨지는가 |
| 아키텍처/테스트 | 신규 능력 게이트, import 계층, CI 없는 GPU 환경을 어떻게 통과할 것인가 |
| PM/채택 전략 | 누가 쓰고, 어떤 claim을 할 수 있으며, 언제 출시할 것인가 |

---

## 2. 합의점

1. **지원은 포함한다.**
   - 사용자 라이브러리라도 GPU path가 있는 것은 가치가 있다.
   - 단, 포함은 dependency 강제가 아니라 backend/진단/문서/벤치 포함이다.

2. **기본값은 CPU streaming이다.**
   - 현재 메모리 가드가 제품 안정성의 핵심이다.
   - GPU는 streaming과 상충하므로 기본 자동화하면 OOM 방어를 약화시킨다.

3. **1차 삽입 위치는 `scan/io/cross.py`다.**
   - 이미 backend protocol과 env dispatcher가 있다.
   - caller 변경 없이 `engine="gpu"`를 수용할 수 있다.

4. **`_attempts` 실측 전 src 진입 금지.**
   - GPU 효과는 workload 의존성이 크다.
   - 성능 claim은 데이터 없이 쓰면 제품 신뢰를 깎는다.

5. **silent fallback 금지.**
   - GPU를 요청했는데 CPU로 내려가는 것은 사용자에게 거짓 성능 감각을 준다.
   - 명시 GPU 모드는 실패를 드러낸다.

6. **DuckDB baseline 정정.**
   - 현재 `DuckDbCrossScan`은 LazyFrame을 먼저 streaming collect한 뒤 DuckDB에 등록한다.
   - PRD v0.1에서 이를 OOC baseline으로 쓰지 않는다.

---

## 3. 쟁점과 판정

### 쟁점 A - `cudf-polars`를 기본 dependency에 넣을 것인가

판정: **KILL**.

이유:

- 환경 제한이 강하다.
- Pyodide/Windows/CPU-only 사용자에게 무의미하거나 해롭다.
- single base install 원칙은 "모든 환경에서 한 번에 작동"이지 "모든 무거운 특수환경 dependency를 강제"가 아니다.

대안:

- lazy import.
- 진단 메시지.
- 공식 Polars GPU 문서 링크.

### 쟁점 B - `dartlab[gpu]` extras를 만들 것인가

판정: **KILL**.

이유:

- repo memory와 README가 optional-dependencies/extras 금지를 명시한다.
- GPU 설치 안내는 외부 환경 준비 문서로 제공하고, package schema는 건드리지 않는다.

### 쟁점 C - `auto`를 언제 도입할 것인가

판정: **public beta 이후 후보, 기본값 금지**.

조건:

- attempts에서 workload별 win/loss가 정리됨.
- GPU fallback 감지가 안정적.
- threshold가 있고 실패 시 사유가 남음.

### 쟁점 D - 공개 진단 API가 필요한가

판정: **public beta 전 필수. 단 top-level 신규 함수는 보류**.

이유:

- `dartlab.gpuStatus()` 새 top-level은 apiContract상 성급하다.
- `capabilities()` 또는 runtime/status 표면에 붙이는 것이 장기적으로 자연스럽다.
- CLI는 `dartlab doctor gpu` 또는 `dartlab status --gpu` 후보. 사용 코드는 끝까지 `import dartlab` 하나여야 한다.

### 쟁점 E - 제품명과 claim

판정: **"GPU 지원" 단독 금지, "선택적 GPU backend"로 제한**.

이유:

- 단독 headline은 모든 scan/analysis가 빨라진다는 기대를 만든다.
- claim은 4개 패밀리 12개 쿼리, 75% 이상 median 2.0x, fallback 5% 이하, parity 100% 전에는 금지다.

---

## 4. PRD 반영 결정

| 결정 | 반영 문서 |
|---|---|
| GPU 지원 포함의 의미를 backend/진단/문서/벤치로 정의 | 00 |
| 기본 dependency/extra 금지 | 00, 02 |
| `scan/io/cross.py` backend 확장 | 02 |
| `_attempts/polarsGpuBackend` 졸업 게이트 | 03 |
| CPU-safe CI + GPU opt-in 테스트 분리 | 04 |
| 성능 claim 최소 기준 | 00, 03 |
| DuckDB OOC 표현 정정 | 01, 02, 03, 04 |

---

## 5. 적대 검증

### 반대 1 - "GPU는 사용자 라이브러리에 너무 복잡하다"

수용 일부. 기본 경로에 복잡성을 노출하지 않는다. 그러나 backend 선택기를 내부에 갖추는 것은 사용자 가치가 있다. 특히 전종목 scan/prebuild 운영자는 설치 복잡성을 감수할 수 있다.

### 반대 2 - "단일 base install이면 GPU dependency도 넣어야 일관된다"

기각. 단일 base install의 목적은 첫 사용 마찰 제거와 ImportError 방지다. 환경 제한적인 CUDA wheel을 강제하는 것은 오히려 목적을 깬다. lazy import가 정공이다.

### 반대 3 - "auto GPU가 없으면 사용자가 못 쓴다"

부분 수용. 문서와 env var를 제공하되, auto는 실측 후다. 잘못된 auto는 성능보다 위험하다.

### 반대 4 - "DuckDB가 있는데 GPU가 필요한가"

조건부 수용. 다만 현 `DuckDbCrossScan`은 진짜 OOC baseline이 아니므로 "DuckDB OOC 대비"라고 쓰지 않는다. GPU와 DuckDB는 대체가 아니라 선택 backend이며, attempts에서 CPU streaming 대비 우위가 없으면 GPU backend는 수동 실험 기능으로만 남긴다.

---

## 6. 최종 판정

GO for PRD and attempts. NO-GO for src implementation until benchmark graduation.

다음 작업은 구현이 아니라 `tests/_attempts/polarsGpuBackend/` 실험 카테고리 개설과 probe/bench 작성이다. 운영자 go 전까지 본진 코드는 0줄 유지한다.
