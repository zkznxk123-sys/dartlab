# `.github/scripts/` — GitHub Actions 전용 파이프라인 스크립트

GitHub Actions workflow (`.github/workflows/*.yml`) 가 호출하는 Python 스크립트들. 도메인 동사별 sub-dir 로 분류.

repo 의 `scripts/` (build/dev/audit 도구) 와 *별개* — `.github/scripts/` 는 *Actions runner 에서만* 호출된다.

## 디렉터리 구조

```
.github/scripts/
├── _hfRetry.py             # HF API retry helper (sub-dir 5 개가 sys.path parent 로 접근)
├── sync/                   # HF ↔ 로컬 양방향 sync
├── prebuild/               # derived artifact build
├── meta/                   # 메타 데이터 (corp/kind list refresh)
├── search/                 # search index build
└── ops/                    # operational (monitor / plan)
```

## 도메인별 스크립트 + 호출 workflow

### sync/ — HF ↔ 로컬 양방향 sync · 외부 API 수집

| 스크립트 | 역할 | 호출 workflow |
|---|---|---|
| [sync/seedFromHf.py](sync/seedFromHf.py) | HF→로컬 idempotent seed (size 다른 파일 다운로드) | `dataSync.yml`, `dataPrebuild.yml`, `docs.yml` |
| [sync/syncRecent.py](sync/syncRecent.py) | DART list.json 기반 정기공시 누락분 수집 + HF 업로드 트리거 | `dataSync.yml` |
| [sync/syncData.py](sync/syncData.py) | 88분기 차집합 full collect (heavy fallback) | `dataSync.yml` (workflow_dispatch full 모드) |
| [sync/syncNewStocks.py](sync/syncNewStocks.py) | KindList 신규 상장 종목 초기 수집 | `dartNewStocks.yml` |
| [sync/uploadData.py](sync/uploadData.py) | `dist/changed.txt` 기반 HF 증분 업로드 (batch 300/commit) | `dataSync.yml`, `dartNewStocks.yml` |
| [sync/uploadHfReadme.py](sync/uploadHfReadme.py) | HF dataset README 갱신 | (수동) |
| [sync/bulkUploadHf.py](sync/bulkUploadHf.py) | HF 전체 폴더 일괄 업로드 | (수동, cold start) |
| [sync/buildKrxData.py](sync/buildKrxData.py) | KRX OpenAPI → 연도별 raw parquet + HF push | `buildKrxData.yml` |
| [sync/buildKrxIndexData.py](sync/buildKrxIndexData.py) | KRX 지수 OHLCV bulk 수집 + HF push | `buildKrxIndexData.yml` |
| [sync/buildMacroData.py](sync/buildMacroData.py) | FRED/ECOS 카탈로그 → HF macro 벌크 parquet | `macroData.yml` |

### prebuild/ — derived artifact build (parquet → JSON / aggregate)

| 스크립트 | 역할 | 호출 workflow |
|---|---|---|
| [prebuild/prebuildData.py](prebuild/prebuildData.py) | DART scan prebuild parquet 빌드 + HF 업로드 | `dataPrebuild.yml` |
| [prebuild/prebuildValuation.py](prebuild/prebuildValuation.py) | valuation snapshot parquet 빌드 + HF 업로드 | `valuationSnapshot.yml` |
| [prebuild/buildIndustryMap.py](prebuild/buildIndustryMap.py) | 산업지도 시각화 JSON (atlas/industries/companies) | `mapBuild.yml` |
| [prebuild/buildFinanceJson.py](prebuild/buildFinanceJson.py) | finance.parquet → dashboards/finance.json (전 상장사 5Y) | `mapBuild.yml` |
| [prebuild/buildQuartersJson.py](prebuild/buildQuartersJson.py) | finance.parquet → dashboards/quarters.json (분기 시계열) | `mapBuild.yml` |
| [prebuild/buildMetaJson.py](prebuild/buildMetaJson.py) | dashboards/meta.json (engines + 블로그 + thesis) | `mapBuild.yml` |
| [prebuild/buildMacroJson.py](prebuild/buildMacroJson.py) | macro.cycle → dashboards/macro.json | `mapBuild.yml` |
| [prebuild/buildStoryManifest.py](prebuild/buildStoryManifest.py) | story SSOT → static/story/manifest.json | `mapBuild.yml` |

### meta/ — 메타 데이터 refresh

| 스크립트 | 역할 | 호출 workflow |
|---|---|---|
| [meta/updateKindList.py](meta/updateKindList.py) | KRX KIND 상장법인 목록 크롤 (`corpList.parquet`) | `kindlist.yml` |
| [meta/updateDartList.py](meta/updateDartList.py) | OpenDART CORPCODE.xml → `dartList.parquet` | `kindlist.yml` |

### search/ — search index build

| 스크립트 | 역할 | 호출 workflow |
|---|---|---|
| [search/buildSearchDelta.py](search/buildSearchDelta.py) | 최근 N 일 content delta 인덱스 빌드 + HF 업로드 | `searchIndexDelta.yml` |
| [search/buildSearchMain.py](search/buildSearchMain.py) | content main 인덱스 빌드 + HF 업로드 | `searchIndexMain.yml` |
| [search/buildSkillMarket.py](search/buildSkillMarket.py) | GitHub Discussion → Skill Market 정적 인덱스 | `docs.yml` |

### ops/ — operational

| 스크립트 | 역할 | 호출 workflow |
|---|---|---|
| [ops/monitorPipeline.py](ops/monitorPipeline.py) | 파이프라인 health check (실패 잡 issue 자동 생성) | `dataAudit.yml` |
| [ops/planRealdata.py](ops/planRealdata.py) | PR diff 기반 realData 테스트 plan JSON 생성 | `ci-full.yml` |

## sub-dir 스크립트의 `_hfRetry` import 규약

5 개 스크립트 (`sync/uploadData`, `prebuild/prebuildData`, `prebuild/prebuildValuation`, `search/buildSearchDelta`, `search/buildSearchMain`) 가 `_hfRetry` 사용. sub-dir 의 sys.path 가 부모를 못 잡으므로 다음 boilerplate:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _hfRetry import retryHfCall  # noqa: E402
```

## workflow 추가 시 (새 스크립트 정착 절차)

1. 도메인 식별 → `sync/`·`prebuild/`·`meta/`·`search/`·`ops/` 중 적절한 sub-dir 에 작성.
2. `_hfRetry` 사용 시 위 boilerplate 적용.
3. `.github/workflows/<workflow>.yml` 의 `run:` 라인에 `.github/scripts/<domain>/<name>.py` 경로 명시.
4. 본 README 의 도메인별 표에 행 추가.
