# 부동산 실거래 데이터 — 현상 진단 (Current State Audit)

> 본 문서는 **세션 코드·API 실측**만 담는다(추측 0). PRD(00)·토론(02)의 모든 feasibility 주장은 이 사실에 대조된다.
> SSOT는 함수명·파일경로·API 파라미터다. 줄번호는 보조(현 소스 실측 기준).

---

## 1. 결론 — 부동산은 customs 와 *데이터 동형, 볼륨 비동형*

DartLab은 **공공데이터포털 단일 키(`DATA_GO_KR_KEY`)로 이미 3 소스**(gov 주가·customs 무역·pension 연금)를 호출한다. 국토부 부동산 실거래도 *같은 키·같은 포털*이라 자격증명·소스 거푸집은 customs 를 그대로 복제한다. **단 결정적 차이 = 데이터 볼륨과 일일 콜 한도**다(아래 §3). 이 한 가지가 "전수 bake" 를 막고 데이터 전략을 가른다.

---

## 2. 재사용 자산 (실측)

### 2.1 자격증명 — 추가 작업 거의 0
`src/dartlab/core/providers/dataCredentials.py` 의 `DataProviderSpec("dataGoKr")`:
- `envKey="DATA_GO_KR_KEY"`, `sources=("gov", "customs", "pension")`, `signupUrl="https://www.data.go.kr"`.
- `activation` 문구에 "활용신청(자동승인): 금융위_주식시세정보 · 관세청_품목별 수출입실적 · 국민연금공단 가입사업장" 나열.
- **부동산 추가 = `sources` 튜플에 `"realestate"` 1개 + activation 문구에 국토부 활용신청 1줄.** 새 env·새 키 0. 해석은 `resolveKey("dataGoKr")` 그대로.
- `keyHint="Decoding 키 사용"` — 부동산 API도 동일(serviceKey 1회 URL-encode).

### 2.2 소스 거푸집 — customs 5파일 1:1 미러
`src/dartlab/gather/customs/` (5파일):
| customs 파일 | 역할 | 부동산 미러 |
|---|---|---|
| `client.py` | REST + 60RPM 슬라이딩 rate-limit + XML 파싱 + 지수백오프 재시도 3회 + `cmmMsgHeader`(키미등록·트래픽초과 code 22) 분류 | `realestate/client.py` — **동일 패턴.** API도 XML 전용·`http://openapi.molit.go.kr` 비-TLS. params 만 `LAWD_CD`/`DEAL_YMD`로 교체 |
| `series.py` | 기간 윈도 분할 + 월별 집계 → 표준 `(date, value)` 반환 (FRED/ECOS 동일 계약) | `realestate/series.py` — 집계 함수가 **(지역×월) → 거래량·중위가·평단가** 다중 metric 환원 |
| `catalog.py` | `CATALOG: dict[str, list[CatalogEntry]]` (group → HS 엔트리) + `getAllEntries`/`getEntry` | `realestate/catalog.py` — group=권역/유형, 엔트리=시군구 LAWD_CD 또는 거래유형(매매/전월세/오피스텔…) |
| `facade.py` | 공개 클래스 `Customs` (`.series/.catalog/.close`) | `realestate/facade.py` — `RealEstate` (`.transactions/.index/.catalog/.close`) |
| `types.py` | `CustomsError`/`RateLimitError`/`CatalogEntry` | `realestate/types.py` — `RealEstateError`/`RateLimitError`/`RegionEntry` |

- 인증키 해석: `resolveKey("dataGoKr", apiKey)` (client `__init__` 첫 줄). customs `client.py:39` 그대로.
- `_BASE_URL` 만 교체: customs `http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList` → 부동산 `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev`.

### 2.3 회귀 외생 브릿지 — *이미 존재* + ★가격축은 이미 배선됨 (검증 정정)
**firm-level 매출민감도 외생 회로 (STRONG 거처 — 코드 실측):**
- `src/dartlab/analysis/financial/_signalsMacroSensitivity.py` `_loadAdaptive`(:457): exogenousAxes 매핑 3개 + 범용 5개 = 8후보 로드(:462) → **customs-only arm**(:489-506, `if ind.get("source")=="customs"`) 으로 customs 시리즈를 `_materializeFromHf` 적재 → `_quickCorr`(:532) abs 상관 → `candidateData.sort` greedy **top-3**(:539-540) 채택.
- lag 효과는 **별도** 산출: `_calcLagCorrelation`(호출 `_signalsMacroSensitivity.py:352`·정의 `_predictionMath.py:127`) → `_predictionMath.py:156 _pearsonCorrelation(y, x, *, lag=)` 로 lag0/1/2 corr.
- ★**이게 macro regime 회귀가 아니라 firm-level 매출증가율 OLS다.** macro forecast/regime 엔진(`forecast.py analyzeForecast`)은 `gdp_vals` 만 입력 — **외생 주입 슬롯 없음**(거래량을 regime 에 못 꽂음). 거래량의 진짜 거처 = 이 firm-level 후보 풀.

**★가격축은 이미 배선됨 (검증 — 재표면화 경계):**
- `src/dartlab/gather/mapping/exogenousAxes.py:93` `APT_PRICE = ExogenousIndicator("APT_PRICE", "ecos", "아파트가격", "domestic")`.
- **17곳에 이미 배선**(grep 19 = def :93 + 배선 17 + ALL_INDICATORS export :563): `_INDUSTRY_MAP`(:108) **15업종** — 건물건설업(:172)·시멘트(:178)·부동산임대공급(:179)·가구제조(:225)·유리(:221)·보험(:185) 등 — + `_KEYWORD_OVERRIDE`(:276) **2키워드**(:293 시멘트·:294 건설). (코드 원문에 `_INDUSTRY_MAP 162개 전수` 주석이 있으나 그건 *맵 전체 업종 수*지 APT_PRICE 배선 수가 아님.)
- `crisis.py:118` `data["apt_yoy"]=fetchYoy(g,"APT_PRICE")` — macro 위기탐지기도 **이미 apt 가격 yoy 소비**(KR 전용).
- → **결론: 부동산 *가격* 정보는 이미 분석에 흐른다(ecos 출처). 국토부 실거래의 중위가는 대체로 재표면화. net-new 는 오직 *거래량(volume)*** — 가격축이 구조적으로 못 담는 직교 유동성/회전율 축.

**HF/캐시 게이트:**
- `src/dartlab/gather/bulkData/macroHf.py:42` `_category(source)` 화이트리스트 — `'fred'/'ecos'/'customs'` 만 허용, 그 외 ValueError(:45). realestate 추가 = `_SOURCE_TO_CATEGORY`(:17-19)·`_SOURCE_TO_ENVKEY`(:24-26·`customs:DATA_GO_KR_KEY` 선례)·`_category` 화이트리스트 3곳 한 줄씩.

**(부산물) `src/dartlab/gather/mapping/productIndicators.py` + `.github/scripts/sync/collectIndustryIndicators.py`(3,158 bytes)** — 둘 다 **실재**(전자=src, 후자=`.github/` 하위라 일부 Glob 패턴이 숨김디렉터리를 누락해 '부재' 오인 — full path로 검증 가능). `PRODUCT_INDICATOR_MAP`(제품키워드→`{fred,customs}` 시리즈)는 firm 회귀 외생 후보의 *또 다른 진입*. 단 본 PRD 의 STRONG 거처는 `_signalsMacroSensitivity._loadAdaptive` customs arm 이다(거래량은 여기에 1축).

- **★해석 한계:** 이 회로는 *제품(product)* 매핑이지 *지역(region)* 매핑이 **아니다.** 집계 섹터(건설·건자재) 연결은 가능하나 "현대건설 → 강남 아파트값" 같은 **기업-지역 특정은 LAWD_CD→회사 매핑 자산 0건이라 영구 honest-skip**(§6).

### 2.4 sync→HF→prebuild 2단 파이프라인
- online sync: `.github/scripts/sync/build*.py` → 외부 API → raw parquet → HF push(`eddmpython/dartlab-data`). gov 선례 = `buildGovData.py`(draw-first-save-later 온디맨드 + date/{year} 횡단 cron, "미리 전부 bulk 안 함").
- offline prebuild: `.github/scripts/prebuild/*.py` → `enforceOffline()` 강제(외부 API 0) → HF 다운로드 + 조립.
- 정적 가드: `tests/architecture/test_prebuild_offline.py` 가 prebuild 의 online 모듈 import 를 차단.

### 2.5 터미널 UI 자산
- 거처: landing SvelteKit `landing/src/routes/terminal/+page.svelte` + `ui/packages/surfaces/src/terminal/panels/`.
- 기존 다이얼로그/패널(실측): `MacroLensDialog`·`IndustryDialog`·`MarketFeed`·`RegimeQuadrant`·`ScatterMap`·`PercentileCrossDialog`·`HoldingsDialog`·`GradeExplainDialog`·`SourcesModal` 등.
- 데이터 호출 SSOT: `ui/packages/runtime/src/data/fetch/request.ts` + `data/origins/registry.ts`(`OriginId='hf'|'hfRange'|'localApi'|'newsWorker'|'naverWorker'|'duckdbHf'`). **새 부동산 데이터는 기존 `hf` origin 재사용**(정적 parquet/json) — 새 origin 불필요. source 자체 fetch·직접 URL·자체 캐시 Map 금지(`checkUiDataWiring` 강제).
- ⛔ **macro lens 오염 금지:** `mainPlan/macro-analysis-superstrengthen` 가 MacroLensDialog 를 "새 블록 추가 금지·4블록 픽셀 불가침" 으로 동결. 부동산을 macro lens 에 끼워넣으면 안 됨 → 별도 surface.

---

## 3. 국토부 실거래 API 실측 — customs 와 다른 점 (데이터 전략의 핵심)

| 항목 | customs (무역) | 국토부 부동산 실거래 |
|---|---|---|
| 인덱싱 | (HS 코드, 기간) — HS 약 30개 | **(LAWD_CD 시군구 5자리, DEAL_YMD 월)** — 전국 **약 250 시군구 × 월** |
| 1콜 단위 | 1 HS × 1년 윈도(하위분해 합산) | **1 시군구 × 1 월** (분해 없음) |
| 전수 규모 | 30 HS × 윈도 = 수백 콜 | **250 시군구 × 월수.** 1년치 1유형 = 250×12 = **3,000콜.** 전이력(2006~, ~230개월) 1유형 = **약 57,500콜** |
| 일일 콜 한도 | 10,000/일 | **개발계정 10,000/일**(15126468 페이지 실측·운영계정 증가). customs와 동일. ※초기 '1,000콜'은 구 검색 오정보였고 실측 폐기 |
| 응답 | XML 전용 | XML 전용 (동일) |
| 행 볼륨 | HS별 월 1행(국가총계) | **거래 1건 = 1행.** 전국 월 수만 건 → 수년 누적 **수백만 행** |
| 거래유형 | 수출/수입/무역수지 | 아파트매매·전월세·오피스텔·단독다가구·연립다세대·상업업무용·토지·분양권 (**유형마다 별 엔드포인트**) |
| 개인정보 | 없음 | 층만 공개·동(번지)은 소유권이전등기 완료분만. 거래금액(만원)·전용면적·건축년도·거래일·**해제여부(취소거래)** |

**진단(★실측 교정 2026-06-20):** 콜한도는 **개발계정 10,000건/일**(data.go.kr 15126468 페이지, customs와 동일 — 초기 "1,000콜" 가정은 구 검색 오정보였음·실측으로 폐기). 따라서 전수 raw bake의 차단 사유는 *콜한도가 아니라* **Polars Rust 힙 OOM**(수백만~수천만 행). → **집계 인덱스(지역·유형·월별 거래량·중위가·평단가)를 CI bake + raw 거래는 온디맨드** 가 정공법(gov draw-first-save-later 선례와 정합·OOM 회피·k-익명 양립). 콜한도 10,000/일이라 전이력 백필도 ~6일 분할로 수렴.

---

## 4. 조합 대상 분석 엔진 (L2) — 실측 결합점

| 엔진 | 결합점 | 재사용 자산 |
|---|---|---|
| analysis (firm 매출민감도) | **거래량(volume)을 firm-level 매출증가율 OLS 외생 후보로 1축** (가격은 이미 APT_PRICE 로 배선) | `_signalsMacroSensitivity._loadAdaptive` customs arm(:489-506) — 거래량의 진짜 거처 |
| macro summary/crisis | apt 가격 yoy 는 이미 소비(crisis.py:118). summary(`macro/summary.py`)는 `_score*` ±점수 합산 단일붕괴 엔진 → 거래량을 summary 축으로 넣으면 자동붕괴 (보조 dict 격리 필요) | — (거래량은 firm 후보·summary 축 금지) |
| industry | 건설·건자재·가구·가전 — APT_PRICE 가 **17곳에 이미 배선**(`_INDUSTRY_MAP` 15업종 + `_KEYWORD_OVERRIDE` 2키워드[시멘트·건설]; grep 19 = def :93 + 배선 17 + ALL_INDICATORS export :563). 거래량은 *추가* edge | `exogenousAxes._INDUSTRY_MAP`(이미 배선)·industry edges.json(baked·재빌드 선결) |
| credit | ★거래량→종목 신용 차별성 **0** (거시 systematic factor·cross-sectional 식별력 0). `engine.py:193 evaluateCompany` 는 macro 입력 **0개** → 점수 주입 불가, 병치만 | `evaluateCompany`(macro입력0=병치강제)·`IndustryGroup.CONSTRUCTION` 게이팅 |
| (참고·범위밖) firm PF 신용 | ★**PF 정량 노트셀은 실재** — `_noteCellsFromPanel(code,"NT_D827580")`(cell.py:160)·`noteTaxonomyData.py:113 "PF우발부채"→NT_D827580`·`governance.py:552 우발부채/지급보증` 정량. **단 거래량과 무관**(firm 공시 출처) → 본 PRD 범위 밖, 별 후보 | governance.py·panel note cells |

---

## 5. 저작권·라이선스 (실측 확인 필요 항목)
- 공공데이터포털 데이터 일반 = 공공누리(KOGL). gov 주가는 "공공누리/KOGL 비상업+출처표시 재배포 가능" 으로 HF 캐시 공개 중(`buildGovData.py` docstring). 부동산 실거래도 동일 KOGL 유형이면 HF 공개 가능 — **단 국토부 실거래 데이터셋의 정확한 KOGL 유형(1~4)·재배포 조건은 PRD 착수 전 데이터셋 페이지에서 확정**(02 토론 검증 항목).
- 개인정보: 지번·동 단위 raw 를 그대로 재배포하면 민감 — **집계(지역·유형·월) 공개 + raw 는 온디맨드 로컬** 전략이 저작권·개인정보 양쪽에서 안전.

---

## 6. 한계 사전 등록 (확신오정렬 가드 — 코드 검증 정정 반영)
- **net-new 는 거래량 *수집 파이프라인* 1개뿐:** 가격축(APT_PRICE)·crisis apt_yoy·industry 17곳 외생은 *이미 배선*. 거래량만 직교 신규 정보. "부동산↔분석 능력 다수" 는 오라벨.
- **기업-지역 특정 불가:** LAWD_CD→회사 매핑 자산 **src 전체 0건**. 분양 공시·사업보고서는 서술형 텍스트지 (지역,금액) 격자 아님 + 실거래 지번 상세도 등기완료분만 공개 = **이중결손** → 영구 honest-skip.
- **거래량→종목 신용 식별력 0:** 거시 거래량은 systematic factor라 cross-sectional 식별 0. `evaluateCompany` macro 입력 0개라 점수 주입 불가 → 병치 맥락칩만.
- **PF 정량 단정 정정:** "dartlab PF 접근 불가" 는 **거짓**(NT_D827580 노트셀 실재). 정확한 사실 = "①`sectorKpi/construction.py:110-112 pfExposure` 는 충당부채 섹션 PF **키워드 카운트**(정량 노출액 아님) ②PF 정량 노출액은 `_noteCellsFromPanel(NT_D827580)`·`governance.py` 로 firm 공시에서 추출 가능하나 **거래량과 무관**(본 PRD 범위 밖)". credit/ PF "0건" settled-fact 단정 금지.
- **인과 아닌 동행/선행 신호:** 거래량→건설 실적은 선행 *상관* 이지 인과 단정 금지. 선행성은 표본·regime 의존(상승장 선행·하락장 동시붕괴), 고정 시차 단정 금지.
- **주가 예측·종합점수 단일붕괴 금지:** 부동산으로 개별 주가 예측·buy/sell·호악재·부동산점수 = 오버클레임. `macro/summary.py` 가 모든 축을 ±점수 합산하므로 realEstate 를 summary 축에 넣으면 자동 단일붕괴 → 보조 dict 격리만.
- 이 한계들은 PRD 00 `cannotClaimList` 로 박제하고 토론(02)에서 등급 강등 근거로 쓴다.

---

## 출처 (API 실측)
- 국토교통부_아파트 매매 실거래가 상세 자료 (data.go.kr 15126468) · 기본 자료 (15126469).
- ★**실호출 확정 엔드포인트**: `http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`(키有=403/키無=401, customs 200으로 네트워크·키 검증). params `LAWD_CD`(5자리)·`DEAL_YMD`(YYYYMM)·`serviceKey`(Decoding). **개발계정 10,000건/일·무료·이용허락범위 제한 없음·개발/운영 자동승인**(data.go.kr 15126468). 구 `openapi.molit.go.kr/...RTMSOBJSvc` 엔드포인트는 연결 거부(폐기 추정).
- 세션 실측 파일(full path): `core/providers/dataCredentials.py`·`gather/customs/{client,series,catalog,facade}.py`·`gather/mapping/productIndicators.py`·`.github/scripts/sync/collectIndustryIndicators.py`·`.github/scripts/sync/buildGovData.py`·`ui/packages/runtime/src/data/origins/registry.ts`·`ui/packages/surfaces/src/terminal/panels/`.
