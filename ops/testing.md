# 테스트 체계

> 커버리지 90% 목표. 엔진별 최소 80%. 새 기능은 테스트 없이 머지하지 않는다.

## 마커 체계

| 마커 | 의미 | 병렬 | CI 실행 |
|------|------|------|--------|
| `unit` | 순수 로직, mock만, 데이터 로드 없음 | 안전 | 항상 |
| `integration` | Company 1개 로딩 필요 | 주의 | CI |
| `heavy` | 대량 데이터, 단독 실행 | 금지 | 수동 |
| `requires_data` | 로컬 parquet 필요 | 주의 | skip |
| `realData` | 엔진별 실제 데이터 스모크 (HF parquet + 실제 파이프라인) | 금지 | PR/릴리즈 |
| `freshInstall` | 빈 캐시 → 자동 다운로드 — 외부 사용자 첫 호출 시나리오 | 금지 | 릴리즈 전 |

## 메모리 규칙

- **Polars는 네이티브 Rust 힙. gc.collect()로 회수 불가.**
- Company 1개 ≈ 200~500MB. 동시 3개 = OOM.
- conftest.py에 1200MB 초과 시 pytest.exit() 안전장치.
- fixture scope → `module` (session scope 금지).
- `pytest` 직접 호출 금지 → `bash scripts/dev/test-lock.sh` 사용.

## 실행 방법

```bash
# unit만 (빠름, 항상)
bash scripts/dev/test-lock.sh tests/ -m "unit" -v --tb=short

# integration (데이터 필요)
bash scripts/dev/test-lock.sh tests/ -m "not unit and not heavy and not requires_data" -v --tb=short

# heavy (단독)
bash scripts/dev/test-lock.sh tests/ -m "heavy" -v --tb=short

# realData — 엔진별 실제 데이터 스모크
bash scripts/dev/test-realdata.sh                           # realData 전체
bash scripts/dev/test-realdata.sh -m freshInstall -v        # fresh install 만

# 릴리즈 전 wheel 스모크 (격리 venv)
bash scripts/build/testWheelSmoke.sh
```

## realData 스위트

`tests/realData/` 는 엔진별 실제 데이터 파이프라인을 "공식 공개 진입점만" 호출해
None/빈 결과/크래시를 즉시 실패로 처리한다. coverage 가 아닌 **회귀 방어** 용도.

### 스모크 (representative) — 엔진별 canonical 진입점

| 파일 | 엔진 | 검증 대상 |
|------|------|----------|
| `test_companyFacade.py` | Company | `sections`, `show(IS/BS/CF)`, `select`, `topics` |
| `test_analysis.py` | analysis | `c.analysis()`, `c.analysis(axis)` |
| `test_scan.py` | scan | `dartlab.scan(axis=…)`, `available_scans()` |
| `test_macro.py` | macro | `dartlab.macro(axis)` (키 없으면 skip) |
| `test_industry.py` | industry | `c.industry`, `dartlab.industry.classify` |
| `test_credit.py` | credit | `dartlab.credit(code)`, `c.credit` |
| `test_quant.py` | quant | `c.quant` |
| `test_gather.py` | gather | `dartlab.gather("price", code)` |
| `test_search.py` | search | `dartlab.search(query)` (beta, 관대) |
| `test_review.py` | review | `review.blocks(c)`, `buildReview(c)` |
| `test_ai.py` | ai | `dartlab.ask(question)` (provider 키 필요) |
| `test_freshInstall.py` | — | cold cache 에서 `sections`/`show`/렌더 무크래시 |

### 전수 (exhaustive) — 공개 API 전 심볼 × 전 axis

| 파일 | 대상 | iterate 수 |
|------|------|-----------|
| `test_companyExhaustive.py` | `dir(Company)` 공개 속성 전부 | 59 |
| `test_companyTopics.py` | registry 등록 topic × `show/trace` | 37 × 2 |
| `test_analysisAxes.py` | `analysis._AXIS_REGISTRY` 전체 | 22 |
| `test_creditAxes.py` | `credit.axes()` 전체 | 7 |
| `test_scanAxes.py` | `scan.available_scans()` 전체 | 20 |
| `test_macroAxes.py` | `macro._AXIS_REGISTRY` 전체 | 12 |
| `test_gatherAxes.py` | `gather()` df 의 axis 컬럼 전체 | 8 |
| `test_topLevelApi.py` | `dir(dartlab)` 공개 심볼 전부 | 30+ |

**전수 테스트의 약속**: 각 axis/attr 는 독립된 pytest 노드 (parametrize) 이므로
failure 시 어떤 것이 깨졌는지 즉시 pinpoint. 새 axis/attr 를 추가하면 자동으로
iterate 범위에 포함됨 (수동 등록 불필요).

**None 화이트리스트**: 데이터 부재 시 None 이 공식 허용되는 속성/topic 은
각 파일 상단의 `_NONE_ALLOWED` / `_TOPIC_NONE_ALLOWED` frozenset 으로 명시.
화이트리스트 밖에서 None 이 나오면 FAIL — "조용히 None" 이 불가능하다.

### 메모리 예산

realData 전수 스위트는 lazy 프리빌드가 누적되어 기본 conftest 한계 (1500MB) 를
넘는다. `test-realdata.sh` 는 자동으로 `PYTEST_MEMORY_LIMIT_MB=6000` 을 주입한다.
scan 전 축 iterate 는 단일 프로세스에서 7GB 를 돌파할 수 있어 파일별 독립 실행 권장:

```bash
bash scripts/dev/test-realdata.sh   # 파일별 분리 (기본 모드)
```

### fresh-install 회귀 (2026-04-19 사고)

외부 `pip install dartlab` 환경에서 `Company("005930").sections` 한 줄이
`AttributeError: NoneType has no columns` 로 크래시. HF parquet 은 신버전 스키마,
설치된 wheel 은 이전 소스 스냅샷이라 `sections()` 가 silent None 을 리턴.
`test_freshInstall.py` 는 Phase-1 캐시를 강제로 비우고 같은 경로를 탐색해
**스키마 드리프트와 silent-None 을 릴리즈 전에 차단**한다.

실행: `bash scripts/build/testWheelSmoke.sh` (PyPI 릴리즈 전 필수).

## 엔진별 테스트 파일

각 엔진은 최소 1개 전용 테스트 파일을 가진다.

| 엔진 | 테스트 파일 | 상태 |
|------|-----------|------|
| Company | `test_company.py`, `test_company_*.py` | 있음 |
| scan | `test_scan_axes.py`, `test_scanAccount.py` | 있음 (일관성 테스트 추가 필요) |
| analysis | `test_new_axes.py`, `test_analyst.py` | 있음 |
| credit | `test_credit.py` | 보강 필요 |
| quant | — | **없음** → test_quant_engine.py 필요 |
| gather | `test_gather.py`, `test_gather_global.py` | 있음 |
| search | `test_search.py` | 있음 |
| review | `test_report_engine.py` | 보강 필요 |
| ai | `test_coding_local.py`, `test_coding_runtime.py` | 있음 |
| viz | `test_tools_chart.py` | 보강 필요 |

## 테스트 작성 규칙

1. **파일명**: `test_{모듈명}.py` (conftest가 아닌 개별 파일)
2. **마커**: 모든 테스트에 `pytestmark = pytest.mark.unit` 등 명시
3. **mock**: Company 데이터가 필요한 unit 테스트는 fixture로 mock
4. **assert**: 단순 `assert True` 금지 — 구체적 값 검증
5. **독립성**: 테스트 간 상태 공유 금지 (global 변수 사용 금지)

## CI 규칙

```yaml
# ci.yml test 작업
pytest tests/ -v --tb=short 
  -m "not requires_data and not heavy" 
  --benchmark-disable 
  --cov=dartlab --cov-report=xml
  --cov-fail-under=90
```

| 항목 | 기준 |
|------|------|
| 커버리지 | 90% 이상 (fail_under) |
| lint | ruff==0.11.6 고정 |
| format | ruff format |
| 벤치마크 | 별도 워크플로우 (CI에서 disable) |

## 커버리지 현황

| 시점 | 커버리지 | 비고 |
|------|---------|------|
| v0.8.0 | ~30% | 초기 |
| v0.8.3 | 29% | 신규 엔진 추가로 희석 |
| 목표 | 90%+ | 0.8 안정화 완료 기준 |
