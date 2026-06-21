# PRD — 공동작업대 데이터빌드 SSOT 확립
## (In-library `dartlab.pipeline` 흡수 — 흩어진 `.github/scripts` 정본 오케스트레이션화, macro 첫 증명)

> 상태: 설계(PRD) · plan-deep 자기충족 표준 · 범위 = 데이터 전부(모든 도메인 빌드 배선), 실행 = phased(macro 우선 증명)
> SSOT 거처(권장): `mainPlan/data-build-workbench-ssot/` (본 PRD = `00-prd.md`)
> 정직 가드: artifact shape / HF 경로 / consume seam **절대 불변**. churn 최소. 재구현 금지(별도빌드 금지 재확인). 위치만 흡수.

---

## 1. 한 줄 결론 + 비전

**공동작업대(in-library `dartlab.pipeline`)가 모든 데이터 빌드의 정본 오케스트레이션이며, `.github/scripts/{sync,prebuild}` 에 흩어진 빌드 로직을 stage 모듈로 흡수한다 — 단, 빌드 *재구현*은 이미 0(전부 gather/scan 위임)이므로 본 PRD가 옮기는 것은 "오케스트레이션 위치"뿐이다.**

### 비전
- **하나의 진입점, 하나의 SSOT.** 로컬 CLI(`dartlab sync`)와 CI(`python -m dartlab.pipeline <stage>`)가 같은 `orchestrator.runStage(category)` 를 호출한다. CI 워크플로 yml은 이미 이 진입점을 부르고 있으며(`macroData.yml:63` = `uv run python -X utf8 -m dartlab.pipeline macro`), 본 PRD 후에도 **그대로 유지**된다.
- **stage가 빌드의 본체를 안다.** 현재 macro/krx/news/dart stage는 `runScript()` 서브프로세스로 `.github/scripts/sync/*` 에 위임(전환기 brige). 흡수 후 stage 함수가 직접 gather/scan/analysis 공개함수를 호출(edgar/allFilings가 이미 증명한 패턴).
- **데이터 전부가 범위.** macro(sync 3 + prebuild 1)를 **첫 증명 인스턴스**로 완전 흡수하고, 동일 템플릿으로 krx/news/dart + 나머지 도메인을 SHOULD 웨이브로 일반화한다.
- **불변 3종.** HF artifact shape(observations/cycle/regime JSON·parquet 스키마) · HF 경로(`macro/{fred,ecos,customs,cycle,regime}`·`landing/dashboards/macro.json`) · UI consume seam(`dartlabData.ts loadJson('dashboards/macro.json')`)은 byte 동등으로 보존한다.

---

## 2. 현상 진단

### 2.1 pipeline stage MIXED 상태 표 (검증 실측)

| stage 모듈 | 흡수 상태 | 빌드 본체 위치 | HF push 모델 | 근거(파일:라인) |
|---|---|---|---|---|
| `edgar.py::runEdgar` | ✅ **in-library (build-only)** | `providers.edgar.bulk.*` 직접 호출 | 없음(deploy 별 stage) | `stages/edgar.py:49-56`, `upload`/`token` param 미사용 |
| `allFilings.py::runAllFilings`(+Reconcile/Backfill) | ✅ **in-library (build+deploy)** | `gather.dart.allFilingsCollector.{collectMetaRange,fillContent}` + `allFilingsSync.pushAllFilings(token=token)` | stage 내 `pushAllFilings(dates, token=token)` | `stages/allFilings.py:154-155, 198` |
| `dartZip.py::runDartZip`(+panelRceptReconcile) | ✅ **in-library (build+deploy, 증분 seed)** | `providers.dart.panel.build` 스트림 + HF seed/merge | stage 내 `_bundleAndUpload` | `registry.py:62-73` 등록 |
| `edgarPanel.py::runEdgarPanel`(+Reconcile) | ✅ **in-library (build+deploy, per-filing 증분)** | `_seedTickerPanel` + per-ticker append | `uploadCategoryToHf`/reconcile | `registry.py:74-91` |
| `reconcile.py::runPanelReconcile`/`runEdgarPanelReconcile` | ✅ **in-library** | `reconcileCategory(dataCat, pull, push, token)` 제네릭 | `push=upload, token=token` | `registry.py:80-91` |
| **`dart.py::runDartRecent`/Full/NewStocks/Panel** | ⚠ **subprocess (미흡수)** | `runScript('.github/scripts/sync/syncRecent.py')` 등 | stage 가 `uploadCategoryToHf(category, token)` (수집만 위임·업로드는 흡수) | `stages/dart.py:71, 102, 133, 179-181` |
| **`macro.py::runMacro`** | ⚠ **subprocess (미흡수)** | `runScript('.github/scripts/sync/buildMacroData.py' --push)` ×3 | **스크립트 자체 `--push`**(stage는 HF 지식 0) | `stages/macro.py:40-42` |
| **`news.py::runNewsHeadlines`/Enrich/GdeltForward/NaverNews** | ⚠ **subprocess (미흡수)** | `runScript('.github/scripts/sync/syncNewsHeadlines.py')` 등 + `bulkUploadHf.py` | **스크립트(`bulkUploadHf`) 자체 push** | `stages/news.py:51-65` 등 |
| `krx.py` | ⛔ **운영 OFF** (gov로 대체, 저작권) | registry 미import (unwire) | — | `registry.py:30, 92-93` |
| **prebuild `buildMacroJson.py`** | ⚠ **미흡수 (pipeline 밖)** | `.github/scripts/prebuild/buildMacroJson.py` (offline, `enforceOffline()`) | 없음(landing 정적 asset) | `mapBuild.yml:60-61` 가 스크립트 직접 호출 |

**핵심 비대칭**: `runMacro`(스크립트 `--push`)와 `runDartRecent`/`runNews`(stage는 수집만 위임·업로드 일부 흡수 또는 스크립트 push)는 HF push 소유권이 제각각이다. macro 흡수가 이 비대칭을 정렬한다.

### 2.2 44 스크립트 인벤토리 분류 (실측: sync 31 + prebuild 11 = 42 `.py`, F3의 "~44"는 `__pycache__` 포함 추정치)

#### sync 31개 (online — 외부 API → raw + HF push)

| 분류 | 스크립트 | 처리 |
|---|---|---|
| **A. 흡수 대상 (macro · MUST)** | `buildMacroData.py` · `buildMacroCycle.py` · `buildMacroRegime.py` | → `stages/macro.py` 인라인 |
| **A. 흡수 대상 (dart · SHOULD)** | `syncRecent.py` · `syncData.py` · `syncNewStocks.py` · `onlinePanel.py` · `buildPanel.py` | → `stages/dart.py` 인라인 |
| **A. 흡수 대상 (news · SHOULD)** | `syncNewsHeadlines.py` · `enrichNewsHeadlines.py` · `syncGdeltBackfill.py` · `syncNaverNews.py` | → `stages/news.py` 인라인 |
| **A. 흡수 대상 (edgar 보강 · SHOULD)** | `buildEdgarPanel.py` · `buildEdgarSections.py` · `buildAllFilingsRecent.py` | → 해당 stage 인라인(부분 이미 흡수) |
| **A. 흡수 대상 (gov · SHOULD)** | `buildGovData.py` | → `stages/gov.py`(신설) |
| **B. thin-CI-glue 유지 (흡수 강제 X)** | `bulkUploadHf.py` · `uploadData.py` · `uploadHfReadme.py` · `seedFromHf.py` · `buildIpcMirror.py` · `buildSymbologyCache.py` · `repair_cache_with_progress.py` · `dataDriftCheck.py` | CI 운영 도구·범용 업로더. 본체는 이미 `pipeline.hfUpload`/gather에 있음. shim 또는 그대로. |
| **B. 운영자 도구 / cron 보강** | `collectIndustryIndicators.py` · `updateDamodaranERP.py` · `prebuildValuation.py` · `buildKrxData.py` · `buildKrxIndexData.py`(krx OFF) · `buildNaverCompanyNews.py` · `macro_backtest.py` | 도메인 cron·실험. 흡수는 각 도메인 웨이브 또는 보류. |

#### prebuild 11개 (offline only — HF download → derived, `enforceOffline()` 강제)

| 분류 | 스크립트 | 처리 |
|---|---|---|
| **A. 흡수 대상 (macro · MUST)** | `buildMacroJson.py` | → `stages/prebuild.py::runMacroJson()`(신설, `@enforceOffline`) |
| **A. 흡수 대상 (SHOULD)** | `buildFinanceJson.py` · `buildQuartersJson.py` · `buildMetaJson.py` · `buildIndustryMap.py` · `buildPricesSnapshot.py` · `buildFundamentalGate.py` · `buildUniversePanel.py` · `buildStoryManifest.py` · `prebuildData.py` | → `stages/prebuild.py` 형제 함수 |
| **B. 1회성 마이그레이션 (흡수 X)** | `migrateBitemporalSchema.py` | 일회 스키마 마이그. 유지/폐기 별건. |

**증명된 패턴 = edgar/allFilings.** edgar=빌드만(deploy 별 stage), allFilings=빌드+deploy(token 인자). macro는 둘 다 필요(빌드+deploy)이므로 **allFilings 모델**이 macro 흡수의 직접 템플릿이다.

### 2.3 별도빌드 위반 audit (재구현 여부) — **위반 0 확인**

- `buildMacroData.py:66-67` → `from dartlab.gather.fred import Fred` + `getAllEntries()` (L1 위임). ECOS/Customs 동일(`:113-114, :163`). crawl/parse 재구현 0.
- `buildMacroCycle.py:32` → `from dartlab.macro.cycles.cycle import analyzeCycle` (L2 위임).
- `buildMacroRegime.py:328-335` → `analyzeForecast`/`analyzeRates`/`growthAtRisk`/`hamiltonRegime`/`getGather` (L2 위임).
- `buildMacroJson.py:204` → `from dartlab.macro.transmission import analyzeTransmission` (L2, fetch-independent) + `SECTOR_SENSITIVITY` 정적 dict.

**결론**: 위반은 "오케스트레이션 위치(스크립트 산재)"뿐. 본 PRD는 **위치 흡수**이지 빌드 재작성이 아니다.

---

## 3. SSOT 원칙

### 3.1 in-library 여야 하는 것 (= stage 함수 본체)
1. **빌드 오케스트레이션 시퀀스** — 어떤 gather/analysis 함수를 어떤 순서로, 어떤 실패격리/의존게이트로 호출하는가. (현 `runMacro`의 rc1→rc2/rc3 게이트 = 흡수 대상)
2. **HF push 호출 시점·증분 판정** — `pushAllFilings`/`uploadCategoryToHf`/`api.upload_file` 호출. (현 macro는 스크립트 `--push`에 위임 → stage로 끌어올림)
3. **offline 합성 로직** — prebuild의 HF download → derived JSON 조립. (현 `buildMacroJson.main` → `stages/prebuild.runMacroJson`)
4. **env→param 변환** — `MACRO_SOURCE`/`SYNC_LOOKBACK_DAYS` 등 운영 env 해석은 stage 함수 입구에서.

### 3.2 `.github/scripts` shim 으로 남는 것 (= CI 진입점·secret 경계)
- **secret 주입 경계는 CI(GitHub Actions env)에만.** stage 코드는 secret을 env에서 읽되 **로그에 출력 금지**. HF_TOKEN은 `hfUpload._resolveHfToken(token)` 단일 SSOT(인자>env>.env). FRED_API_KEY/ECOS_API_KEY/DATA_GO_KR_KEY는 gather 모듈 진입점(`Fred(apiKey=...)`)에서 `os.environ` 직접 읽음 — stage/CLI layer는 이 API 키들을 모름(layer 무관).
- **online HF push 진입점 = CI.** in-library 흡수해도 실제 push 실행은 CI workflow가 secret env를 주입한 상태에서 `python -m dartlab.pipeline macro` 호출 시에만 발생. 로컬은 token=None → `_resolveHfToken` ValueError → stage가 격리(`report.fail`).
- **워크플로 yml = thin CI glue.** `macroData.yml`은 이미 `dartlab.pipeline macro`를 부른다. 흡수 후에도 yml 무변경(진입점 불변). 단 **prebuild**(`mapBuild.yml:60-61`)는 현재 스크립트 직접 호출 → 흡수 후 `dartlab.pipeline macroJson`(또는 동등 prebuild stage)으로 1줄 교체 가능(선택적·동작 동등).
- **shim 스크립트(선택)** — 흡수 후 `buildMacroData.py`는 3줄 entrypoint로 역전 가능: `from dartlab.pipeline.stages.macro import runMacroData; sys.exit(0 if runMacroData(...).report.err==0 else 1)`. 단 **본 PRD는 shim 역전을 강제하지 않는다**(WONT — 스크립트 삭제/역전은 후속작). 흡수 후 스크립트는 "더 이상 호출되지 않는 dead entrypoint"로 남고, 운영자 결정 시 별도 commit으로 정리.

### 3.3 별도빌드 금지 재확인
- 금지되는 것 = **gather/scan 함수를 우회한 자체 crawl/parse/mapping 재구현**(CLAUDE.md L27).
- 허용·목표 = **gather/scan 위임을 그대로 둔 채 호출 위치를 in-library stage로 이동**.
- 위반 가드(불변): `tests/architecture/test_prebuild_offline.py`(`_FORBIDDEN_IMPORTS` 7종) + 4계층 단방향 import.

---

## 4. 흡수 설계 (핵심)

### 4.0 추출한 edgar/allFilings in-library 패턴 (5 규칙)
1. **lazy import** — stage 함수 *내부*에서 gather/analysis 모듈 import(순환 회피, `edgar.py:49`).
2. **공개함수 직접 호출** — `runScript()` 제거, gather/L2 함수를 이름으로 호출(`allFilings.py:154`).
3. **per-item/per-section 예외 격리** — `try/except` 후 `res.report.{ok,err,fail}` 누산, 절대 raise 안 함(`edgar.py:67-70`).
4. **HF push는 stage 내부 + token 인자** — `pushAllFilings(dates, token=token)`(`allFilings.py:198`), `upload=False`면 skip.
5. **StageResult 반환** — `category`/`report`/`rows`/`uploaded`/`changedFiles`로 집계.

### 4.1 macro 흡수 — 신규 모듈 배치 결정

**거처: `src/dartlab/pipeline/stages/macro.py` 인라인 (별도 `dartlab.macro.build`/`scan.macro` 신설 안 함).**

근거(스코프 절제):
- 빌드 로직은 이미 전부 L2 `dartlab.macro.*` 공개함수다(§2.3). stage가 추가로 추출할 "gather/compute"가 없다 — macro 스크립트는 이미 *얇은 오케스트레이터*(루프 + JSON 직렬화 + HF push)다.
- 따라서 흡수 = "스크립트의 얇은 오케스트레이션을 stage 함수로 복사 + `runScript` 제거"이지, gather 함수 추출(이중 비용)이 아니다. (회의론자 R4 이중비용은 macro에는 **부재** — macro는 (a)(b)(c) 모두 충족.)
- `dartlab.macro.build` 신설은 L2에 빌드/직렬화 책임을 섞어 layer를 오염시킨다. 직렬화·HF push는 L4(pipeline) 책임 — stage에 둔다.

#### `runMacroData` (신규, sync online)
`stages/macro.py::runMacroData(*, source, upload, token) -> StageResult`. `buildMacroData.py:65-204`의 `buildFred`/`buildEcos`/`buildCustoms` + `_write`를 인라인:
```python
def runMacroData(*, source="all", upload=True, token=None):
    import polars as pl
    from dartlab.gather.fred import Fred
    from dartlab.gather.fred.catalog import getAllEntries
    # ... ecos/customs 동일 (buildMacroData.py 의 3 루프 byte 동형)
    res = StageResult(category="macroData")
    outRoot = Path(os.environ.get("DARTLAB_DATA_DIR", "data")) / "macro"
    try:
        if source in ("fred", "all"):   _buildFred(outRoot / "fred")      # 기존 로직 인라인
        if source in ("ecos", "all"):   _buildEcos(outRoot / "ecos")
        if source in ("customs", "all"):_buildCustoms(outRoot / "customs")
        res.report.ok = 1
    except Exception as exc:
        res.report.err = 1; res.report.failures.append(f"macroData: {type(exc).__name__}: {exc}")
        return res
    if upload:
        try:
            for cat in ("macroFred", "macroEcos", "macroCustoms"):
                uploadCategoryToHf(cat, token=token)   # ← 스크립트 deploy(upload_folder) 대체
        except Exception as exc:
            res.report.fail = 1; res.report.failures.append(f"macroData push: {exc}")
    return res
```
**HF push 정렬**: 스크립트 `deploy()`는 `api.upload_folder(folder, path_in_repo='macro/{subdir}')`. `uploadCategoryToHf('macroFred')`는 `DATA_RELEASES['macroFred']['dir'] = 'macro/fred'`로 동일 경로에 `upload_folder` → **byte 경로 동등**(§7.3 검증 게이트). `_requireEnv("HF_TOKEN")` → `_resolveHfToken(token)`로 정렬(token 인자 우선·격리).

#### `runMacroCycle` (신규, sync online)
`buildMacroCycle.py:30-65` 인라인. `analyzeCycle(market)` for KR/US → `data/macro/cycle/{kr,us}.json` write → HF `macro/cycle/{kr,us}.json` push(`api.upload_file` retryHfCall 래핑). 결과 0건 → `report.err`(현 스크립트 rc=1 동형).

#### `runMacroRegime` (신규, sync online)
`buildMacroRegime.py:323-382` 인라인. `_analyzeRegime`(forecast 4모델+rates+gar+regimeBand) for KR/US → `data/macro/regime/{kr,us}.json` write → HF push. 축별 try/except는 기존 함수(`_extractForecast` 등)에 이미 존재 → 그대로 호출.

#### `runMacro` (개정 — runScript 제거)
```python
def runMacro(*, category="macro", mode="recent", codes=None, upload=True, token=None):
    source = os.environ.get("MACRO_SOURCE", "all")
    res = StageResult(category="macro")
    rData = runMacroData(source=source, upload=upload, token=token)
    cycleOk = regimeOk = True
    if rData.report.err == 0:                                  # rc1==0 게이트 (FRED bulk 캐시 공유)
        rCycle  = runMacroCycle(upload=upload, token=token)    # cycle·regime 상호 독립
        rRegime = runMacroRegime(upload=upload, token=token)
        cycleOk  = (rCycle.report.err == 0)
        regimeOk = (rRegime.report.err == 0)
    else:
        cycleOk = regimeOk = False
    if rData.report.err or rData.report.fail or not cycleOk or not regimeOk:
        res.report.err = 1
        res.report.failures.append(f"macro data:{rData.report.err}/cycle:{int(not cycleOk)}/regime:{int(not regimeOk)}")
    else:
        res.report.ok = 1
    return res
```
**의존게이트 보존 + 독립성 정직화**: 현 `macro.py:5-6` 주석이 "cycle/regime 서로 독립·둘 다 rc1 의존"을 명시. 개정판은 이를 **코드로** 보존 — rc1 실패 시 cycle/regime 둘 다 skip(둘 다 FRED bulk 캐시 의존), rc1 성공 시 cycle 실패가 regime을 막지 않음(현 `macro.py:41-42`는 rc1==0이면 둘 다 독립 실행 — **이미 올바름**). UI consume seam 회귀 평가단(skeptic)이 우려한 "rc2 실패가 rc3 강제 실패"는 **현 코드에 없으며**(둘 다 rc1==0에만 의존), 흡수판도 동일하게 독립.

#### `runMacroJson` (신규, prebuild offline)
**거처: `src/dartlab/pipeline/stages/prebuild.py`(신규 모듈)::`runMacroJson()`.**
`buildMacroJson.py:232-285` 인라인. **첫 실행문이 `enforceOffline()`**(AST 게이트 통과):
```python
def runMacroJson(*, category="macroJson", mode="offline", codes=None, upload=False, token=None):
    from dartlab.core.offlineGuard import enforceOffline
    enforceOffline()                                          # ← 첫 stmt 불변
    from dartlab.macro.transmission import analyzeTransmission  # L2 fetch-independent (허용)
    # _analyze_market(HF cycle download) · _load_regime(HF regime download) · SECTOR_SENSITIVITY lookup
    # → landing/static/dashboards/macro.json (v20) write. HF push 없음(landing 정적 asset).
    res = StageResult(category="macroJson")
    try:
        ... ; res.report.ok = 1
    except Exception as exc:
        res.report.err = 1; res.report.failures.append(f"macroJson: {exc}")
    return res
```
**offline 가드 회귀 0 핵심**: `runMacroJson`은 `dartlab.gather.fred`/`dartlab.macro.cycles.cycle`/`dartlab.macro.seriesFetch`/`forecast`/`rates`를 **import 하지 않는다**(`_FORBIDDEN_IMPORTS` 7종 회피). `analyzeTransmission`만 import — 이는 fetch-independent(macro observation 없으면 missing payload로 닫힘, `buildMacroJson.py:200-229`). HF download(`hf_hub_download`)는 offlineGuard allow-list(`huggingface.co`) 통과.

> **⚠ 가드 설계 정정(ground-truth 검증·아키텍트 blocker 1):** 현 `test_prebuild_offline.py`의 enforceOffline AST 가드(`test_prebuild_main_enforces_offline`)는 `_findMainFunc`(`:55-59`)로 **literally `main` 이름 함수만** 찾아 `assert mainFunc is not None`(`:99`) 한다. stage 함수는 `runMacroJson()`(=`main` 아님)이므로 **PREBUILD_DIR glob만 확장하면 `main` 부재로 가드가 FAIL(no-op 아님)** — "glob 확장"만으로는 불가. 따라서 §8.2-3은 *신규 전용 테스트*로 한다: `tests/architecture/test_inlibrary_prebuild_offline.py` — `stages/prebuild.py`를 AST 파싱해 `run`* FunctionDef 전수에 대해 (a) 기존 헬퍼 `_firstNonDocstringStmt`+`_callsEnforceOffline`(`:62-79`) 재사용으로 첫 비-docstring stmt가 `enforceOffline()`인지, (b) 기존 `_collectImports`+`_FORBIDDEN_IMPORTS`(`:82-127`) 재사용으로 모듈 import가 7종 미포함인지 단언. `_findMainFunc` 재작성·기존 `.github/scripts/prebuild` 테스트(여전히 `main` 계약) 변경 0 — 헬퍼만 재사용한 평행 테스트.

#### prebuild stage 의존 순서 (R2 박제)
`runMacroJson`은 sync(`runMacroCycle`/`runMacroRegime`)가 HF에 publish한 `macro/cycle|regime/{kr,us}.json`을 download한다. sync 미완 시 → `buildMacroJson.py:144-146, 178-179`의 fallback(`_fallback`/missing payload)으로 graceful degrade(stale 아닌 명시 missing). 현 `mapBuild.yml`은 `macroData.yml`(sync)과 별 cron이며 **순서 강제 없음** — 흡수판도 동일 계약(R2: HF mtime 신뢰·fallback 명시). 순서 강제는 WONT(워크플로 오케스트레이션 별건).

### 4.2 krx/news/dart 일반화 개요 (SHOULD 웨이브)

| 도메인 | 흡수 난이도 | 패턴 | 비고 |
|---|---|---|---|
| **dart** | 중 | `runScript('syncRecent.py')` → `dartlab.gather.dart.*` 직접 호출. 업로드는 이미 `uploadCategoryToHf` 흡수됨(`dart.py:34`) → 수집만 인라인 | syncRecent/syncData/syncNewStocks/onlinePanel/buildPanel = 5 스크립트. panel은 `panelXbrlRef` 전제(graceful skip) 보존. |
| **news** | 중 | `runScript('syncNewsHeadlines.py')` + `bulkUploadHf.py` → gather + `uploadCategoryToHf`. KR/US 루프 인라인 | naver private repo(`repoFor` 라우팅)·무키 green-noop 보존. `bulkUploadHf --since 86400` 의미(시각 필터)는 `changedPath` 매니페스트로 대체 검토 필요(byte 동등 audit 선행). |
| **gov** | 중 | `buildGovData.py` → `stages/gov.py` 신설(현재 stage 없음·workflow가 스크립트 직접) | krx 대체 주력 소스. registry 1줄 등록. |
| **edgar 보강** | 저 | `buildEdgarSections.py`/`buildEdgarPanel.py` — 일부 이미 `edgarPanel.py` 흡수. sections는 별 stage 검토 | — |

**흡수 전 audit 게이트(각 도메인 공통)**: (1) 스크립트가 gather/scan 위임만 하는지(재구현 0) 확인 → 위반 시 "별도빌드" 보고. (2) byte 동등성(산출 artifact shape/HF 경로) 확인. (3) offline 위반(prebuild로 가야 할 online 호출) 확인. macro는 (1)(2)(3) 통과 확인 완료.

---

## 5. online/offline + CI 경계

### 5.1 sync online (HF push · secret env · CI 진입점)
- 진입점: `python -m dartlab.pipeline macro` (CI yml 불변, `macroData.yml:63`).
- secret: CI가 env 주입(`macroData.yml:57-62` = FRED_API_KEY/ECOS_API_KEY/DATA_GO_KR_KEY/HF_TOKEN/MACRO_SOURCE). stage는 gather 진입점(`Fred(apiKey=...)`)·`_resolveHfToken(token)`로만 읽음. **stage/CLI는 API 키 미인지**.
- 로컬 안전: token=None + HF_TOKEN env 부재 → `_resolveHfToken` ValueError → stage가 `report.fail` 격리(crash 아님). `upload=False`면 push 자체 skip → 로컬 테스트 가능.

### 5.2 prebuild offline (enforceOffline 불변)
- `runMacroJson` 첫 stmt = `enforceOffline()`(socket monkey-patch). 외부 API(FRED/ECOS/DART)는 `OfflineViolation`. HF download만 allow(`huggingface.co` suffix).
- import 가드: `_FORBIDDEN_IMPORTS` 7종(`test_prebuild_offline.py:34-42`) 미import. `analyzeTransmission`만(fetch-independent).
- **가드 적용 범위 확장 필수** — 현 AST 테스트는 `.github/scripts/prebuild/*.py`만 glob. `stages/prebuild.py`로 흡수하면 커버 누락 → §8.2.

### 5.3 workflows yml 최소변경
- sync: `macroData.yml` **무변경**(이미 `dartlab.pipeline macro`).
- prebuild: `mapBuild.yml:60-61`은 현재 `python -X utf8 .github/scripts/prebuild/buildMacroJson.py` 직접 호출. 흡수 후 **선택적** `python -X utf8 -m dartlab.pipeline macroJson`(또는 prebuild dispatch)로 교체 가능 — 단 macro.json byte 동등 검증(§7.3) 통과 후. MUST는 stage 함수 존재·동작 동등이며, yml 교체는 검증 후 SHOULD.

---

## 6. 공통배선 consume 끝단 (데이터 전부까지)

### 6.1 현황 — UI consume seam은 이미 SSOT 준수 (문서화만)
- `ui/packages/runtime/src/data/dartlabData.ts`:
  - `loadJson('dashboards/macro.json')` 단일 진입점(`:82`).
  - `hasHfLandingJson()` whitelist에 `dashboards/macro.json`(`:34`) → HF-first.
  - `shouldCacheJson()`에서 `dashboards/macro.json` **제외**(`:55`) → zero-cache HF-first freshness.
  - `RequestDedup` 동시 로드 dedup. ad-hoc fetch 0. `checkUiDataWiring` 위반 0.
- regime 키는 macro.json에 편승(`buildMacroJson.py:276`) → **consume 신규 배선 0**.

### 6.2 빌드→consume seam 불변 계약 (PRD 강제)
| artifact | HF/파일 경로 | shape | 소비 진입점 | 불변 강제 |
|---|---|---|---|---|
| observations | `macro/{fred,ecos,customs}/observations.parquet` | `{seriesId, date, value}` + manifest | gather macro reader | §7.3 byte 동등 |
| cycle | `macro/cycle/{kr,us}.json` | `{phase, confidence, signals, sectorStrategy, ...}` (timeseries 제거) | `buildMacroJson._analyze_market` | §7.3 |
| regime | `macro/regime/{kr,us}.json` | `{forecast.models, rates, gar, regimeBand}` (composite 없음) | `buildMacroJson._load_regime` | §7.3 |
| macro.json | `landing/static/dashboards/macro.json` (+HF `landing/dashboards/macro.json`) | v20: `{version, asOf, kr, us, transmission, sectorTailwind, regime}` | `dartlabData.loadJson` → `macroSource.loadMacroTransmission` | §7.3 + UI 무변경 |

**데이터 전부까지**: 본 PRD의 consume 끝단 책임 = "흡수가 consume seam을 *건드리지 않음*을 byte로 증명"이다. UI/landing 코드 변경 0(WONT). finance/quarters/meta/map 형제도 동일 패턴(macro 증명 후 일반화 시 동일 불변 계약).

---

## 7. 영향 파일·함수 (SSOT)

### 7.1 신규
| 파일/함수 | 내용 |
|---|---|
| `src/dartlab/pipeline/stages/macro.py::runMacroData` | sync online — FRED/ECOS/Customs build + `uploadCategoryToHf` ×3 (`buildMacroData.py` 인라인) |
| `src/dartlab/pipeline/stages/macro.py::runMacroCycle` | sync online — `analyzeCycle` KR/US + HF push (`buildMacroCycle.py` 인라인) |
| `src/dartlab/pipeline/stages/macro.py::runMacroRegime` | sync online — forecast/rates/gar/regimeBand KR/US + HF push (`buildMacroRegime.py` 인라인) |
| `src/dartlab/pipeline/stages/macro.py::_buildFred`/`_buildEcos`/`_buildCustoms`/`_write` 등 헬퍼 | 스크립트 헬퍼 byte 동형 인라인(module-private) |
| `src/dartlab/pipeline/stages/prebuild.py` (신규 모듈) | offline — `runMacroJson()` (`buildMacroJson.py` 인라인, `enforceOffline` 첫 stmt) + `SECTOR_SENSITIVITY` 이전 |
| `tests/pipeline/test_macro_stage.py` (신규) | macro 흡수 단위/통합 + byte 동등 테스트 (§8) |
| `tests/architecture/test_stage_no_runscript.py` (신규) | 흡수 완료 stage가 `runScript` import 안 하는지 단언 (§8.2) |

### 7.2 변경
| 파일/함수 | 변경 |
|---|---|
| `src/dartlab/pipeline/stages/macro.py::runMacro` | `runScript` 3회 → `runMacroData`/`runMacroCycle`/`runMacroRegime` in-library 호출. import에서 `_runner.runScript` 제거 |
| `src/dartlab/pipeline/registry.py::buildRegistry` | `macroJson` StageSpec 1줄 등록(`run=prebuild.runMacroJson, online=False`). macro StageSpec `uploadCategories` 유지 |
| `tests/architecture/test_inlibrary_prebuild_offline.py` (신규) | in-library prebuild stage(`stages/prebuild.py`)의 `run`* 함수 전수에 enforceOffline 첫-stmt + 금지 import AST 가드. 기존 `test_prebuild_offline.py` 헬퍼(`_firstNonDocstringStmt`/`_callsEnforceOffline`/`_collectImports`/`_FORBIDDEN_IMPORTS`) 재사용. (`_findMainFunc`는 `main`만 찾으므로 glob 확장 불가 — §4.1 정정) |
| `tests/architecture/test_prebuild_offline.py` | **불변**(`.github/scripts/prebuild` 대상·`main` 계약 유지). 헬퍼만 신규 테스트가 import 재사용 |
| `.github/workflows/mapBuild.yml:60-61` (선택·검증 후) | `buildMacroJson.py` → `dartlab.pipeline macroJson` (byte 동등 통과 후) |

### 7.3 불변 (구조 동등 — 절대 변경 금지)
- HF artifact shape: observations/cycle/regime parquet·JSON 키.
- HF 경로: `macro/{fred,ecos,customs,cycle,regime}`·`landing/dashboards/macro.json`.
- macro.json v20 schema 전 필드(키·값·타입).
- `dartlabData.ts`/`macroSource.ts` consume 코드(UI 일체).
- `DATA_RELEASES` macro 카테고리(`macroFred`/`macroEcos`/`macroCustoms` dir).
- `offlineGuard.py`/`_FORBIDDEN_IMPORTS` 의미(대상만 확장).
- **HF 업로드 의미: full-folder.** 스크립트 `deploy()`=`upload_folder`(전체). `uploadCategoryToHf`는 `changed_<cat>.txt` 매니페스트 우선·부재 시 full fallback(`hfUpload.py:86`). macro는 changed 매니페스트를 **만들지 않으므로** full-folder로 동등 — 흡수 후에도 macro에 changed 매니페스트 **도입 금지**(증분 부분 업로드 silent drift 차단·skeptic blocker 1). §8.2-5가 매니페스트 부재를 단언.

> **동등 대상이 *아닌* 것(비교 제외·거짓실패 방지):** 날짜성 필드 `asOf=date.today()`(`buildMacroJson.py:271`)·regime `computedAt`(실행 시각) — 비결정(아키텍트 blocker 2). HF `commit_message`(스크립트 `"build: macro {subdir}..."` vs `uploadCategoryToHf` 표준 메시지) — 메타데이터지 artifact shape/경로 아님(skeptic blocker 2). 동등 게이트는 이 셋을 정규화 제외한 뒤 판정.

### 7.4 삭제 (본 PRD 범위 외 — WONT)
- `.github/scripts/sync/buildMacro{Data,Cycle,Regime}.py` · `prebuild/buildMacroJson.py` 삭제/shim 역전 = **후속작**. 흡수 후 dead entrypoint로 보존, 운영자 결정 시 별도 commit.

---

## 8. 테스트·가드

### 8.1 흡수 회귀 가드 (기존 불변)
- `test_prebuild_offline.py` — `enforceOffline` AST + 7 금지 import. **불변**(`.github/scripts/prebuild` 대상·`main` 계약 유지). in-library stage 커버는 헬퍼 재사용 신규 평행 테스트(§8.2-3).
- `test_l15_no_cross_import.py` — L1.5 4형제 cross import 금지. macro stage(L4)는 L2 macro 호출 합법.
- import direction — pipeline=L4 sink, gather/providers/analysis 호출 허용.
- 메모리 안전 — 전수 pytest 금지. 검증 = `uv run python -X utf8 tests/run.py preflight` (CI 27 게이트 SSOT) + 단일 파일 `bash tests/test-lock.sh tests/pipeline/test_macro_stage.py -m "<marker>" -v`. fixture scope `module`.

### 8.2 신규 흡수 단언 테스트
1. **구조 동등 (핵심)** — `test_macro_stage.py`: mock Fred/ECOS/Customs(고정 시리즈) → `runMacroData(upload=False)` 산출 `observations.parquet`이 기존 `buildMacroData.py` 산출과 schema·정렬·dtype 동일. cycle/regime JSON·macro.json v20 = **타임스탬프(`asOf`/`computedAt`) 제외** 정규화 deep-equal(키·값·타입, `runMacroJson` mock HF download). byte 비교 아님(날짜 비결정·§7.3).
2. **no-runScript 단언** — `test_stage_no_runscript.py`: AST로 `stages/macro.py`가 `_runner.runScript`를 import/호출 안 함 단언(흡수 회귀 = runScript 재등장 차단). dart/news는 흡수 전까지 allowlist.
3. **offline 가드 확장 (신규 전용 테스트)** — `test_inlibrary_prebuild_offline.py`: `stages/prebuild.py`의 `run`* FunctionDef 전수에 (a) 첫 비-docstring stmt가 `enforceOffline()`(헬퍼 `_firstNonDocstringStmt`+`_callsEnforceOffline` 재사용), (b) 모듈 import가 `_FORBIDDEN_IMPORTS` 7종 미포함(헬퍼 `_collectImports` 재사용). **주의(아키텍트 blocker 1·검증됨): 기존 `test_prebuild_main_enforces_offline`는 `_findMainFunc`로 `main` 이름만 찾으므로(`test_prebuild_offline.py:55-59,99`) PREBUILD_DIR glob 확장만으로는 `runMacroJson`을 못 잡고 FAIL** — 신규 테스트가 stage 함수 finder로 이 갭을 닫는다(현재는 `.github/scripts/prebuild/`만 검사 → 흡수 시 커버 누락 = 최대 회귀 위험).
4. **secret 격리** — `runMacroData(upload=False, token=None)`이 HF push 미실행(token 미해석)·crash 없음. `upload=True, token=None`+HF_TOKEN 부재 → `report.fail`(crash 아님).
5. **HF 경로 + full-folder 동등** — `uploadCategoryToHf('macroFred')` path_in_repo가 `macro/fred/...`(기존 `deploy` `path_in_repo='macro/fred'` 동일) 단언(mock HfApi). **추가(skeptic blocker 1): `data/macro/fred/changed_macroFred.txt` 등 changed 매니페스트가 생성되지 않음을 단언** → `uploadCategoryToHf`가 full-folder fallback(upload_folder 전체)로 동작, 스크립트 `deploy()` upload_folder와 의미 동등(증분 부분 업로드 silent drift 차단).
6. **의존게이트** — `runMacroData` 실패(mock) 시 cycle/regime skip + macro `report.err=1` 단언.

### 8.3 reconcile 부재 확인
macro는 per-entity 파일 없음(append-only parquet per source) → dartZip/edgar 같은 reconcile stage **불필요**(WONT). cycle/regime은 KR/US 2파일 전체 재생성.

---

## 9. 롤백

### 9.1 stage별 독립 롤백 (무손실)
- 흡수는 **stage 함수 단위**. `runMacro` 한 함수만 교체 → 문제 시 git revert 1 commit으로 `runScript` 위임 복원(`.github/scripts/sync/buildMacro*.py` 미변경·보존).
- artifact 동등성 = byte 무손실. 흡수판이 동일 parquet/JSON를 동일 경로에 쓰므로, 롤백해도 HF dataset/macro.json 무변경. consume seam 무영향.
- **shim 미역전 정책의 이점**: 스크립트를 삭제하지 않으므로 롤백이 "import 교체"뿐 — 파일 복원 불필요.

### 9.2 단계적 안전 전환
- Phase 1: `runMacro*` 인라인 함수 추가(스크립트 병존). 흡수판은 테스트로만 검증(CI 미연결).
- Phase 2: `runMacro` 가 인라인 호출로 전환(스크립트 미호출·보존). CI dry-run 1회로 byte 동등 확인(operator).
- Phase 3(선택): mapBuild.yml prebuild 진입점 교체.
- 어느 Phase든 직전 commit revert로 즉시 복원.

---

## 10. Phase (MUST / SHOULD / WONT)

### MUST (본 PRD 구현 범위 — macro 첫 증명)
1. **원칙 박제** — §3 SSOT 원칙을 `operation.architecture`(데이터 빌드 SSOT 섹션)에 반영. edgar/allFilings 패턴 5규칙(§4.0) 명문화.
2. **macro sync 흡수** — `runMacroData`/`runMacroCycle`/`runMacroRegime` 인라인 + `runMacro` runScript 제거.
3. **macro prebuild 흡수** — `stages/prebuild.py::runMacroJson` (`enforceOffline` 첫 stmt) + registry 등록.
4. **HF push 정렬** — 스크립트 `--push`/`deploy` → stage 내부 `uploadCategoryToHf`/`upload_file`(token 인자·격리).
5. **테스트·가드** — §8.2 신규 6종(byte 동등·no-runScript·offline 확장·secret 격리·HF 경로·의존게이트). offline AST 가드를 `stages/prebuild.py`로 확장.
6. **byte 동등 증명** — observations/cycle/regime/macro.json 산출이 기존과 동등(테스트 + operator dry-run).

### SHOULD (후속 웨이브 — 동일 템플릿)
- dart 흡수(syncRecent/syncData/syncNewStocks/onlinePanel/buildPanel → `stages/dart.py`).
- news 흡수(syncNewsHeadlines/enrich/gdelt/naver → `stages/news.py`, `bulkUploadHf` 의미 byte audit 선행).
- gov stage 신설(`buildGovData.py` → `stages/gov.py` + registry).
- 나머지 prebuild 흡수(financeJson/quartersJson/metaJson/industryMap 등 → `stages/prebuild.py` 형제).
- mapBuild.yml prebuild 진입점 → `dartlab.pipeline` dispatch 교체.

### WONT (강제 금지)
- truly-CI-glue(`bulkUploadHf`/`uploadData`/`seedFromHf`/`buildIpcMirror` 등 범용 업로더·운영 도구) 강제 흡수 — 본체는 이미 `hfUpload`/gather에 있고 스크립트는 CI 진입점.
- artifact shape/HF 경로/consume seam **변경**(byte 동등 절대).
- 44개 일괄 흡수 — phased(macro 우선). 도메인별 audit 게이트 통과 후 1웨이브씩.
- 스크립트 삭제/shim 역전 — 흡수 후 dead entrypoint 보존, 별도 운영자 commit.
- 워크플로 오케스트레이션 재설계(sync→prebuild 순서 강제·cron 통합).
- L2 `dartlab.macro.*` 함수 리팩토링(layer-correct·stable).
- macro reconcile stage(per-entity 파일 부재).

---

## 11. 이중 평가 (시니어 개발자 + PM)

### 11.1 시니어 개발자 평가
- **강점**: (1) macro는 흡수 비용이 최소인 *이상적 첫 인스턴스* — 빌드가 이미 100% L2 위임(§2.3)이라 "gather 추출 이중비용"이 부재(회의론자 R4는 macro에 미적용). 흡수 = 얇은 오케스트레이션 복사 + runScript 제거뿐. (2) HF push 정렬이 `uploadCategoryToHf` 단일 SSOT로 수렴(스크립트 `--push` 비대칭 제거). (3) byte 동등 게이트가 회귀 위험을 측정가능하게 봉인.
- **최대 위험 = offline 가드 커버 누락**: `test_prebuild_offline.py`가 `.github/scripts/prebuild/`만 glob → `stages/prebuild.py` 흡수 시 `enforceOffline` AST·금지 import 검사가 *자동으로 빠진다*. §8.2-3을 MUST로 못 박았으나, 이 한 줄을 놓치면 prebuild에 online 호출이 박혀도 CI green. **구현 시 가드 확장을 흡수보다 먼저** 작성(test-first).
- **둘째 위험 = `bulkUploadHf --since 86400`(news)**: 시각 필터 업로드 의미가 `changedPath` 매니페스트와 다를 수 있음 → news 흡수는 byte audit 선행(SHOULD에 명시). macro는 `upload_folder`(전체)라 무관.
- **권고**: macro 흡수를 test-first(byte 동등 fixture 먼저)로. dry-run은 operator CI 1회(로컬 secret 없음).

### 11.2 PM 평가
- **GOAL 정합**: F1("데이터배선까지 확립·PRD는 데이터 전부") 충족 — 범위=데이터 전부(§2.2 인벤토리·§4.2 일반화), 실행=phased(macro 증명). 설계 산출물(PRD)로 한정.
- **ROI**: 흡수 4스크립트(sync 3+prebuild 1)로 전 도메인 템플릿 확립. churn 최소(스크립트 보존·UI 무변경·yml 무변경). 회의론자 우려(흡수 비용>ROI)는 macro에는 역전 — macro는 비용 최소·증명 가치 최대.
- **리스크 관리**: 롤백 1-commit(§9)·byte 동등(§8)으로 무손실. UI push 회귀 위험 0(consume 코드 미변경 → 운영자 UI 승인 불필요, 본 작업은 백엔드/파이프라인).
- **우선순위**: MUST(macro) 후 dart→news→gov 순(F4 laggard·운영 빈도순). krx는 OFF 유지.

---

## 12. 성공/실패 기준 (측정가능)

### 성공
1. `stages/macro.py`에 `runScript` import/호출 0 (`test_stage_no_runscript.py` green).
2. `runMacroData`/`Cycle`/`Regime`/`runMacroJson` 산출 artifact가 기존 스크립트 산출과 **구조 동등**(parquet schema/정렬/dtype 일치 · JSON 키 집합·값 일치) — 단 **날짜성 필드(`asOf=date.today()`·`computedAt`)는 비교에서 제외**(비결정·아키텍트 blocker 2 검증: `buildMacroJson.py:271`·regime `computedAt`). 동등 정의 = "타임스탬프 필드 제외 후 정규화 JSON deep-equal + parquet schema/정렬/dtype 동일"(`test_macro_stage.py` green).
3. `runMacroJson` 첫 stmt = `enforceOffline()` + `_FORBIDDEN_IMPORTS` 7종 미import (확장된 `test_prebuild_offline.py` green).
4. HF 경로 동등 — `uploadCategoryToHf('macroFred')` → `macro/fred/`(mock 단언).
5. secret 격리 — `upload=False`/`token=None` crash 0·push 0; `upload=True`+토큰 부재 → `report.fail`(crash 0).
6. `uv run python -X utf8 tests/run.py preflight` 신규 failure 0.
7. operator CI dry-run 1회 — macro.json·observations/cycle/regime **구조 동등**(타임스탬프 `asOf`/`computedAt` 제외 정규화 diff 0).
8. consume seam 무변경 — `dartlabData.ts`/`macroSource.ts`/macro.json 소비 코드 diff 0, `checkUiDataWiring` 위반 0.

### 실패
1. byte 비동등(artifact shape/HF 경로/macro.json 1필드라도 drift).
2. offline 가드 커버 누락 — `stages/prebuild.py`가 AST/import 검사에서 빠짐.
3. secret이 로그 노출 또는 token=None에서 crash.
4. `runScript`가 macro stage에 잔존(흡수 미완).
5. consume seam(UI/landing) 변경 발생.
6. L2 macro 함수 시그니처 변경 또는 4계층 import 위반.
7. 스코프 크리프 — macro 외 도메인을 본 PRD에서 일괄 흡수.

---

## 부록 A — 검증된 ground-truth 인덱스 (재조사 불필요)

| 사실 | 파일:라인 |
|---|---|
| edgar in-library build-only 패턴 | `src/dartlab/pipeline/stages/edgar.py:49-97` |
| allFilings build+deploy(token 인자) | `src/dartlab/pipeline/stages/allFilings.py:154-204` |
| macro 현 subprocess 위임(rc1 게이트) | `src/dartlab/pipeline/stages/macro.py:40-49` |
| runScript 전환기 헬퍼 | `src/dartlab/pipeline/stages/_runner.py:40-69` |
| buildMacroData FRED/ECOS/Customs 위임 + deploy(upload_folder) | `.github/scripts/sync/buildMacroData.py:65-227, 230-247` |
| buildMacroCycle analyzeCycle + upload_file | `.github/scripts/sync/buildMacroCycle.py:30-103` |
| buildMacroRegime forecast/rates/gar/regimeBand + upload_file | `.github/scripts/sync/buildMacroRegime.py:323-425` |
| buildMacroJson offline(enforceOffline:237) + transmission + SECTOR_SENSITIVITY | `.github/scripts/prebuild/buildMacroJson.py:43-100, 196-290` |
| offlineGuard socket monkey-patch + HF allow-list | `src/dartlab/core/offlineGuard.py:63-76, 184-208` |
| prebuild offline AST + 7 금지 import 가드(PREBUILD_DIR glob) | `tests/architecture/test_prebuild_offline.py:28, 34-127` |
| hfUpload `_resolveHfToken`(인자>env>.env) + `uploadCategoryToHf`(경로=DATA_RELEASES dir) | `src/dartlab/pipeline/hfUpload.py:24-56, 78-222` |
| DATA_RELEASES macroFred/Ecos/Customs(dir=macro/fred 등) | `src/dartlab/core/dataConfig.py:123-137` |
| registry macro StageSpec + RECENT_SET | `src/dartlab/pipeline/registry.py:14, 94-99` |
| orchestrator runStage(category)=CLI+CI SSOT | `src/dartlab/pipeline/orchestrator.py:47-81` |
| __main__ `python -m dartlab.pipeline <stage>` | `src/dartlab/pipeline/__main__.py:31-66` |
| macroData.yml secret env + `dartlab.pipeline macro` | `.github/workflows/macroData.yml:53-63` |
| mapBuild.yml prebuild 스크립트 직접 호출(macro.json) | `.github/workflows/mapBuild.yml:60-61` |
| UI consume seam(loadJson·hasHfLandingJson·shouldCacheJson 제외) | `ui/packages/runtime/src/data/dartlabData.ts:34, 55, 82-115` |
| 스크립트 인벤토리 실측 | sync 31 + prebuild 11 = 42 `.py` (F3 "~44"=`__pycache__` 포함 추정) |
| 현재 pipeline stage 모듈 + prebuild 모듈 부재 | `src/dartlab/pipeline/stages/*.py` (prebuild.py NONE) |