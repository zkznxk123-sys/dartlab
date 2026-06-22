# 블로그·캐러셀·SNS 자산 통합 SSOT + 라이브 카드 캐러셀 — PRD

> **상태**: 설계 완성·구현 미착수. 착수 = 운영자 go (P0 선결 = HF `dartlab-media` dataset repo 생성).
> **검증**: 4 라운드 5 축 적대평가(코드 대조) — 아키텍처·파이프라인·데이터관리·확장성·정직성/UX 전 축 ≥90 (91·91·91·92·93). 검증 과정에서 초기 설계의 과대주장(재사용·신규 0 등)이 코드 대조로 정정됨 — 아래 §설계 정정 이력.

## Context (왜)

SNS 캐러셀은 스토리를 결정론으로 고정 생성할 수 없다 → **항상 렌더되는 라이브 카드 캐러셀**을 별도로 둔다. 터미널 버튼→landing `/cards`→전 종목 캐러셀 무한스크롤·검색·SNS 공유, 클릭=인스타식 스와이프. 카드 = 라이브 차트 + 손글 narration(blog frontmatter `carousel:`) + 기존 히어로 사진. **굽지 않음**(`/report` 가 "정적 story JSON 폐기·사전 bake 없음" 으로 라이브 회사 리포트를 이미 증명).

근본 부채: 회사 이미지가 3 곳 분산 — blog(`blog/**/assets`, git-tracked·정적번들 서빙), SNS(`sns/assets`, [.gitignore:139](.gitignore#L139) ignore·로컬 전용·웹 미서빙), 상호 무지. **단일 serve SSOT** 로 세 소비자(블로그·캐러셀·SNS) 통합.

## 설계 정정 이력 (적대평가 코드 대조)

- **publish 가 glob 이 아님** — `upload_folder(allow_patterns=["[0-9]*/**/*.webp"])` 는 `huggingface_hub` 의 `fnmatch`(=`**` literal·`*` 가 `/` 매칭)상 **0 개 업로드**(실자산 `005930/dram-chip.webp`=슬래시 1, 패턴은 슬래시 2 요구)+ticker 배제+블로그번호 156/158 오염 → **build_index canonical 집합 기반 명시적 `CommitOperationAdd` 열거**로 전면 교체.
- **백본 차트 재분류** — `MonthlyReturnsHeatmap`/`YearlyReturnsBars` 는 백테스트 `eq`/`bhq` 의존(price-derivable 아님) → 백본=report 인라인 SVG 블록 렌더러 + `MiniFinChart`(무-백테스트·무-klinecharts), PriceChart·backtest 차트는 opt-in.
- **canonical 키 深化** — similarTo 슬러그참조 재작성·null-stockCode 가 주경로(~70%)·ticker 는 `company_key_from_slug` 권위(`meta`=Meta Platforms 회사→`ticker:META`)·비회사 제외는 기계적 무모호 클래스만.
- **`hfMedia` origin 명시** — `hf` 는 dartlab-data 하드코딩 → 평행 resolver + OriginId + HF-direct(콘텐츠해시 캐시버스트, hfProxy 의존 제거).
- **정직헬퍼 추출·가드 정직화** — `cellTone`/`verdictTone`/`spark` 는 `report/+page.svelte` 인라인 → 공유층 추출 필수. `checkUiDataWiring` 는 landing route 미커버(거짓 가드 주장 철회).

### 핵심 결정 (척추)

1. **Serve SSOT = HF 전용 media repo, HF-direct 서빙.** 110MB+ 성장 이미지를 git 에 박는 건 `/sns/`·`/data/` ignore 원칙([.gitignore:42-43,139](.gitignore#L42))·[bulkUploadHf.py:131-135](.github/scripts/sync/bulkUploadHf.py#L131) "~10 만→전용 repo 분리" 경고와 충돌 → day1 전용 repo:
   - **Canonical serve**: HF `eddmpython/dartlab-media` 의 `companies/{code}/{semantic}.{hash8}.webp` + `companies/index.json`(code-keyed).
   - **Authoring**: `sns/assets/`(git-ignore·Flux/imagegen) + `blog/**/assets`(git-tracked·본문). **HF media=단일 serve SSOT**, 로컬 2 곳=목적별 authoring(부채 정직 등록·단일 물리통합은 P6).
   - **서빙**: `hf` origin 은 dartlab-data 하드코딩([hf.ts:9](ui/packages/runtime/src/data/origins/hf.ts#L9))이라 복제 불가 → ① [hf.ts](ui/packages/runtime/src/data/origins/hf.ts)에 `HF_MEDIA_RESOLVE`(=`dartlab-media` base)+`hfMediaUrl()` 평행 resolver ② [registry.ts:22](ui/packages/runtime/src/data/origins/registry.ts#L22) `OriginId` 유니온 `'hfMedia'` + `ORIGINS` 등록(**HF-direct**). 카드 hero src=`originUrl('hfMedia','companies/{code}/{name}.{hash}.webp')`.
   - **캐시버스트**: 매니페스트 `assets[]`=`{name,hash}` 콘텐츠해시 접미 → 변경=새 파일명=새 URL. hfProxy `/hf` 라우트는 dartlab-data 전용([worker.js:21](infra/workers/hfProxy/worker.js#L21))이라 **hfProxy 의존 제거**·HF CDN+콘텐츠해시로 staleness 무관. 단일 변경점=매니페스트.
2. **블로그 본문=산문 마크다운 불변, 캐러셀=frontmatter `carousel:` 선택 블록.** 없으면 `ReportModel` 자동 투영. 207 편 산문 보존·폭발반경 frontmatter 한정.
3. **캐러셀 차트 백본 = report 인라인 SVG 블록 + MiniFinChart (무-백테스트·무-klinecharts).** `MonthlyReturnsHeatmap`/`YearlyReturnsBars` 는 **백테스트 자본곡선 `eq`/`bhq` 의존**([charts/BacktestReport.svelte:54](ui/packages/surfaces/src/terminal/charts/BacktestReport.svelte#L54)·price-derivable 아님) → 백본 아님:
   - **백본 LOCK(무의존)**: `/report` 인라인 SVG 렌더러(`line`/`bars`/`share`/`spark`/`metrics`/`table` — `ReportModel` 에서·SVG·경량) + `MiniFinChart`(props card/periods/h·finance.bundle). **klinecharts 0·백테스트 0** 으로 캐러셀 완성.
   - **opt-in 무거운 슬라이드**: klinecharts `PriceChart`(P3 하드 PoC 통과시만·진짜 결합=런타임+CenterStack 캔들로드 [CenterStack.svelte:98-119](ui/packages/surfaces/src/terminal/panels/CenterStack.svelte#L98)) · backtest heatmap/bars(엔진 백테스트 `eq`/`bhq` 필요·스코프 밖).
4. **거처=landing `/cards`.** landing→surfaces import 합법·기존(`@dartlab/ui-surfaces/{terminal,map,viewer}` 이미 import·[surfaces/package.json:12](ui/packages/surfaces/package.json#L12) `terminal` subpath). `$lib/report/build.ts`+surfaces 혼용=`/report`·`/terminal` 기존 패턴(L0-L4 는 `src/dartlab/**` Python 규칙·ui/ 무관).

### 분진 Phase

| Phase | 내용 | UI push |
|---|---|---|
| P0 | HF media repo + canonical build_index + **명시 열거 publish** + hfMedia origin | 무관 |
| P1 | 블로그 히어로→`sns/assets` ingest(provenance hash) | 무관 |
| P2 | frontmatter `carousel:` 계약(타입 확장+yaml 검증+문서+작성흐름) | 무관 |
| P3 | surfaces 차트 export + PriceChart PoC 게이트(실패=백본만) | 운영자 승인 |
| P4 | `/cards` route + 정직헬퍼 공유층 + projection 테이블 + a11y + 빈상태 | 운영자 승인 |
| P5 | 큐레이션 티어 + 첫 큐레이션 | 운영자 승인 |
| P6 | (보류·최고위험) 블로그 렌더 물리통합 | 운영자 승인 |

**i18n**: 캐러셀=KR 전용(horizon·known debt). [build.ts:1333](landing/src/lib/report/build.ts#L1333)는 한국어 monolith·`lang` seam 0·KR-only universe/finance → EN/ticker 는 별도 선결 phase(macroLens `Bi`/`makeL` [macroLens.ts:472](ui/packages/surfaces/src/terminal/lib/macroLens.ts#L472)을 build.ts 블록+overview thesis 정규식+cards **3 seam 관통 — debt 3 층**). UI Phase push=운영자 명시 승인(commit 자율).

---

## Section 1 — 영향 파일 (Phase별)

### P0 — HF media SSOT (명시 열거 publish · canonical 키)
- `src/dartlab/core/dataConfig.py` — `DATA_RELEASES["companyAssets"]={"dir":"companies","public":True,"repo":"eddmpython/dartlab-media"}`. `repoFor()` 라우팅(panel/gdelt 선례). **(운영자: HF `dartlab-media` dataset repo 생성 선결.)**
- `ui/packages/runtime/src/data/origins/{hf.ts,registry.ts}` — `HF_MEDIA_RESOLVE`+`hfMediaUrl()` 평행 resolver·`OriginId` 유니온 `'hfMedia'`·`ORIGINS` 등록(HF-direct).
- `sns/scripts/build_index.py` — **canonical 키 정규화 재작성**(현 [build_index.py:60-84](sns/scripts/build_index.py#L60) 폴더명 키잉·정규화 0). **명시 평가순서**(결정성 척추):
  - **(1) 비회사 제외 = 기계적 무모호 클래스만**: `_`-접두(`_topics`/`_misc`/`_plans`/`_raw`)·`dartlab-`접두·전부숫자-len≠6(블로그번호 156/157/158)·`README*`. 실데이터상 모호한 버킷 0(전 비회사가 이 클래스 중 하나) → 화이트리스트 곡예 불필요.
  - **(2) else 키 도출 = `company_key_from_slug` 권위**([sync_assets.py:74](sns/scripts/sync_assets.py#L74)): 6 자리→코드, ≤5 alpha→`ticker:{UPPER}`. **`meta`→`ticker:META`=Meta Platforms 회사**(실측 `sns/assets/meta/`=advertising-network·ai-datacenter·zuckerberg-efficiency hero) — **제외목록에서 meta 삭제**. 폴더명 파싱이 **주경로**(meta.json `stockCode` 는 ~70% null[82 dir 중] → displayName 보강용). 부수효과: 기계적 `_`-접두 규칙이 현 코드의 `_plans` 누출([build_index.py:74](sns/scripts/build_index.py#L74) ad-hoc skip)도 수정.
  - **중복 병합**: 실측 4 쌍(`005930`+`005930-samsung-electronics`·`012450`+`-hanwha-aerospace`·`064350`+`-hyundai-rotem`·`352820`+`-hybe`)→동일 canonical(assets 합집합 또는 명시 충돌 에러).
  - **similarTo 재작성**: 슬러그참조 실측 5 건(`000660→005930-samsung-electronics`·`051900→161890-kolmar`·`247540→086520-ecopro`·`003670→247540-ecopro-bm`·`003670→005490-posco-holdings`)을 canonical 로 재작성. **미해결 ref(`005490` 디렉터리 부재)는 `--check` 의도적 에러**.
  - `assets[]`=`{name,hash}` 콘텐츠해시. 출력 `companies/index.json`. **현 `_topics` descend([build_index.py:77-80](sns/scripts/build_index.py#L77))는 제거**(publish 가 canonical 집합 소비→비회사 누출 차단).
- `sns/scripts/publish_assets_hf.py` (**신규**·[noScriptsDir](tests/audit/noScriptsDir.py) 통과) — **glob 아님**. `build_index` 의 canonical `companies{}` 집합을 import → 각 회사의 hero webp 만 **Python if-필터로 열거**(suffix `.webp`·`*card*`/`*thumbnail*`/`.svg`/`.gif`/`.json` 제외·`_raw/` 세그먼트 제외) → `CommitOperationAdd(path_in_repo=f"companies/{code}/{name}.{hash}.webp")` 배치([hfUpload.py:152-176](src/dartlab/pipeline/hfUpload.py#L152)·`retryHfCall` 패턴 재사용). publish 가 build_index 산출을 소비 → 정규화·dedup 이 업로드에 **기계적으로** 바인딩(drift 차단). 운영자 로컬 실행(`HF_TOKEN`·CI 무관). **`bulkUploadHf` 위임 불가**(parquet·`data/` 전용 [bulkUploadHf.py:127](.github/scripts/sync/bulkUploadHf.py#L127) 검증).

### P1 — 블로그 히어로 ingest
- `sns/scripts/ingest_blog_assets.py` (**신규**) — `blog/05-company-reports/{NN}-{code}-{slug}/assets/{NN}-{semantic}.webp`(`card`/`thumbnail`/`.svg`/`.gif` 제외) → `sns/assets/{code}/{semantic}.webp`. **provenance**: source 경로+content hash 기록 → blog 원본 변경 stale 감지. 멱등.

### P2 — frontmatter `carousel:` 계약
- `landing/src/lib/blog/posts.ts` — `BlogModule.metadata` 를 `Record<string,unknown>` 로([posts.ts:203](landing/src/lib/blog/posts.ts#L203) 현 `string|number` 가 중첩 드롭). `buildPosts()` 에 `carousel`·`stockCode` 추출([posts.ts:239-282](landing/src/lib/blog/posts.ts#L239) String()-평탄화가 미독·**mdsvex 가 중첩객체 제공**=기존 `ai:` 블록 근거). `PostMeta` 에 `stockCode?`·`carousel?: CarouselSpec`. `getPostByStockCode(code)` 역인덱스(frontmatter `stockCode` 리프트만). **`codeBySlug` 는 [+page.server.ts:18](landing/src/routes/blog/[slug]/+page.server.ts#L18) 서버측**.
- `blog/_scripts/audit_seo.py` — carousel 검증을 **`yaml.safe_load` 로**(현 regex 중첩 못읽음). hero 매니페스트 존재·chart 키 화이트리스트·line 길이·**no-new-number**(손글 숫자⊆모델).
- `blog/BLOG.md`·`.claude/skills/blog-master-writer/SKILL.md` — `carousel:` 스키마 문서 + Phase 2.5 증류 단계.

### P3 — surfaces export + PriceChart PoC
- `ui/packages/surfaces/src/terminal/index.ts` — `MiniFinChart` 공개 export(현 비공개 [index.ts:4-22](ui/packages/surfaces/src/terminal/index.ts#L4)). heatmap/bars 는 **백본 아님**(백테스트 의존) → export 보류.
- **PriceChart PoC(하드 게이트)**: `getPublicRuntime()`+CenterStack 캔들로드 effect 복제로 `CarouselPriceSlide` 단독 마운트 검증. 성공만 P4 opt-in 슬라이드·실패=백본(SVG블록+MiniFinChart)로 확정.

### P4 — `/cards` + 정직헬퍼 공유 + projection
- `landing/src/lib/report/render.ts` (**신규 추출**) — 순수 **기하/포맷 헬퍼**(`cellTone`/`verdictTone`/robust `spark`/`lineGeo`/`isTimeSeries`/`tableHasSpark`/`chunk`/`splitTitle`/`clean`)를 [report/+page.svelte:154-258](landing/src/routes/report/+page.svelte#L154) 인라인에서 추출(명명함수→기계적 동치). `bars`/`share`/`metrics`/`table` 은 마크업 분기(인라인 `{@const}`)라 **신규 geom 헬퍼로 재포장**(동치 아님·cards 소비). **vitest: 중립색·verdict/매수 합성 0**. report 가 render.ts import.
- `landing/src/lib/cards/model.ts`·`build.ts` (**신규**) — `CarouselCard` 유니온·`CarouselSpec`. `buildCards()`:
  - **`ReportBlock`→`CarouselCard` projection 테이블 명시**(어느 블록 variant 가 어느 슬라이드가 되는지). **미매핑 variant=fail-loud 또는 명시 honest-skip**(silent drop 금지) → 새 `ReportBlock` 추가 시 "여기 추가 안 하면 의도적 비-캐러셀" 선언.
  - **pending 관점 처리**: `ReportModel.pending`/`ReportSkipped`([model.ts:88](landing/src/lib/report/model.ts#L88) `isSkipped`)→honest 빈/text 카드(broken img 아님). vitest 동행.
  - auto `line`=기존 모델 문자열 **verbatim/templated 투영**(LLM·신규합성 0). `buildOverview.takes[].line`=`conclusion` 상속([build.ts:1493](landing/src/lib/report/build.ts#L1493))·`conclusion` 생성도 LLM-free 1 회 단언.
- `landing/src/routes/cards/{+page.ts,+page.svelte}` (**신규**) — `ssr=false`·`prerender=false`·`sym`/`view` 파라미터([/report/+page.ts:9](landing/src/routes/report/+page.ts#L9)). 피드(IntersectionObserver [terminal/panels/MarketFeed.svelte:81](ui/packages/surfaces/src/terminal/panels/MarketFeed.svelte#L81)·경량 커버) + 플레이어(scroll-snap·autoplay) + 헤더(검색 `loadJson('map/search-index.json')`·SNS·⌘K) + export. **a11y**: 키보드 슬라이드 네비(←→·Space)·focus 관리·`aria-live` 진행바(**신규 작성**·MacroLensDialog 는 focus-trap 만). **빈상태**: 히어로 0=SVG/text 폴백·skip=정직 카드.
- export: `downloadSnapshot`([snapshot.ts:4](ui/packages/surfaces/src/terminal/charts/snapshot.ts#L4))=**klinecharts 전용** → opt-in price 슬라이드 한정. 비-kline 카드 PNG=DOM→canvas(html-to-image) **후속 sub-task**.

### P5·P6
- `landing/src/lib/cards/build.ts` — `getPostByStockCode(code)?.carousel` 오버레이(hero→매니페스트→`originUrl('hfMedia',...)`·손글 line·audit_seo no-new-number).
- `blog/05-company-reports/*/index.md` — 대표 3~5 편 `carousel:`.
- **P6(보류·최고위험)**: `landing/svelte.config.js` `rehypeBaseUrl()`+`landing/scripts/syncBlogAssets.js` 를 HF media URL 해석으로 — 478 이미지·207 편 영향=별도 승인·Playwright before/after.

### 규칙·메모리·gitignore
- `CLAUDE.md` — 1 줄: "회사이미지 serve SSOT=HF `dartlab-media/companies/`(authoring=`sns/assets`+`blog/**/assets`·서빙=`hfMedia` origin HF-direct). 캐러셀 route=public/local 공통배선·landing 데이터배선=convention(checkUiDataWiring 미커버)."
- `.gitignore` — **변경 불필요**([.gitignore:139](.gitignore#L139) `/sns/` ignore).

---

## Section 2 — 영향 함수/심볼 (정직 구분)

**재사용(검증)**: `buildReport(rt,code,perspectiveKey)`/`buildOverview(rt,code)`([build.ts:1333,1482](landing/src/lib/report/build.ts#L1333))·`ReportModel`/`ReportBlock`/`isSkipped`([model.ts:5,88](landing/src/lib/report/model.ts#L5))·`PERSPECTIVES`([perspectives.ts:11](landing/src/lib/report/perspectives.ts#L11))·`getPublicRuntime()`·`loadJson('map/search-index.json')`·`DARTLAB_BRAND_LINKS`/`SupportDialog`/`fetchGithubStars`·`MiniFinChart`·IntersectionObserver 패턴·`downloadSnapshot`(klinecharts 만)·CenterStack soft-swap([CenterStack.svelte:498](ui/packages/surfaces/src/terminal/panels/CenterStack.svelte#L498))·`sync_post`/`company_key_from_slug`([sync_assets.py:74,122](sns/scripts/sync_assets.py#L74))·`_resolveHfToken`/`retryHfCall`/`CommitOperationAdd` 배치([hfUpload.py:152](src/dartlab/pipeline/hfUpload.py#L152))·`repoFor()`.

**신규**: `publish_assets_hf.py`(**명시 열거**·glob 아님·bulkUploadHf 위임 불가)·build_index canonical 재작성(similarTo·ticker·dedup·제외)·`ingest_blog_assets.py`·`hfMedia` origin(평행 resolver)·`CarouselSpec`/`CarouselCard`/`buildCards()`(projection 테이블)·`CarouselPriceSlide`(PoC)·`render.ts`(헬퍼 추출)·`getPostByStockCode`/PostMeta carousel·stockCode·audit_seo yaml.

---

## Section 3 — 테스트·가드

| 가드 | 커버 범위 | 신규 배선 |
|---|---|---|
| `checkUiDataWiring.mjs` | `ui/packages/runtime/src/adapters/**/sources/*.ts` **한정**·landing route·`<img>` **미커버** | `/cards`=convention 강제(svelte-check+리뷰)·hero src `originUrl('hfMedia',...)`. |
| `test_prebuild_offline.py` | `.github/scripts/prebuild/*.py` | publish=운영자 로컬(`sns/scripts/`·CI 무관)·prebuild 무관 |
| `noScriptsDir.py` | repo 루트 `scripts/` | 신규 도구 `sns/scripts/`·`landing/scripts/` |
| svelte-check·CI Fast `tests/run.py preflight` | landing·surfaces·27 게이트 | P3~P5 0err·dataConfig preflight green·`test-lock` marker 직렬(OOM) |

**신규 테스트(필수)**: ①정직헬퍼 vitest(중립색·verdict 합성 0) ②narration **숫자토큰 정확일치**(신규 `extractNumbers` 가 부호±·단위 조/억/%/배·천단위 콤마 전부 토큰화 → `⊆모델값`·정형구 화이트리스트 통과·신규 숫자 0)+`conclusion` LLM-free 1 회 ③**publish 열거 positive-set**(픽스처[`005930`·`NVDA`·`intc`·`156`·`012450/card.webp`·`_topics`·합성 `005930/_raw/x.webp`]→업로드=실회사 webp 만[`meta`=회사 포함→`ticker:META`]·156/_topics/card/`_raw` 세그먼트 0 개·기대=픽스처 산출 카운트[하드코딩 금지·실측 ~506-573]) ④build_index canonical 결정성(중복 병합·similarTo 재작성·비회사 제외) ⑤**projection 커버리지**(미매핑 `ReportBlock` **및 `OverviewTake`** variant=fail-loud) ⑥pending/skip→honest 카드(`ReportModel.pending`·`isSkipped`·`buildOverview()===null` 3 경로) ⑦멱등.

---

## Section 4 — 롤백
- **Phase 독립·역순 안전.** P0~P1=HF media 업로드 가역·`sns/assets` 로컬(blog 원본 불변)·dataConfig 1 커밋. P2=선택필드·audit 추가만(revert=렌더 불변). P3~P5=신규 파일 격리(route·cards/*·CarouselPriceSlide·render.ts)→`/report`·터미널·블로그 렌더 **변경 0**. **정직헬퍼 추출**=report 가 `render.ts` import(동치·vitest 보장)→report 회귀 0. P6=별도플랜·Playwright·미착수=기본 롤백.
- 데이터 안전: dartlab import 순차(병렬 ≤2)·`BoundedCache`·fixture scope module.

---

## Section 5 — 평가 (개발자 + PM)

### 개발자
- **강점**: 신규 최소·재사용 최대. `/report` 라이브 무-bake 증명. SSOT=HF 가 코드 원칙·`repoFor` 선례 정합. 적대검증으로 초기 과대주장·결함이 코드 대조로 정정됨.
- **주위험①**: PriceChart 결합=런타임+CenterStack 캔들로드 → P3 하드 PoC·실패=백본(SVG블록+MiniFinChart)으로 캐러셀 완성. 폴백이 코드와 정합.
- **주위험②**: 피드 klinecharts 금지·플레이어 lazy+soft-swap.
- **주위험③**: publish 가 build_index canonical 소비 → 정규화·dedup 이 업로드에 기계 바인딩. 콘텐츠해시=캐시버스트+stale 감지.
- **주위험④(정직)**: 자산 4 표면 — remotion mirror=빌드 artifact. 진짜=authoring 2+serve 1. ingest provenance hash 로 stale 감지·P6=완전통합. 부채 정직 등록.

### PM
- **가치**: 자동 티어(전 종목)로 "항상 렌더" day1·큐레이션=enhancement.
- **위험통제**: 블로그 207 편 day1 무변경·Phase 격리·각 출하가능. UI push 운영자 승인·HF publish 운영자 트리거.
- **비용**: P0(canonical+명시열거 publish)+P4(route·정직헬퍼·projection)가 큼. 착수=P0→P1→P2→**P3 PoC**→P4→P5, P6·EN debt 보류.

---

## Verification
1. **P0**: 운영자 `dartlab-media` 생성 → `build_index.py`(canonical·dedup·similarTo 재작성·비회사 제외·`--check` green) → `publish_assets_hf.py`(열거·156/_topics/meta-제외 아님/_raw-제외·ticker 회사 포함) → 브라우저 `dartlab-media/.../companies/{code}/{name}.{hash}.webp` 200. 열거 positive-set vitest green.
2. **P1**: `ingest_blog_assets.py` 멱등·provenance hash·비-이미지 배제.
3. **P2**: `carousel:` 샘플→`audit_seo.py`(yaml) 통과·미존재 hero·신규 숫자 실패. `getPostByStockCode` 적중. 블로그 렌더 무변경.
4. **P3**: surfaces svelte-check 0err. PriceChart PoC(getPublicRuntime+캔들로드) 성공/실패 판정. MiniFinChart standalone.
5. **P4**: landing dev(`:8400` 없이 public) `/cards`→피드·검색·경량 커버·플레이어 스와이프·자동 티어(SVG블록+MiniFinChart) 라이브·pending/skip honest 카드·히어로 0 폴백·a11y(키보드·aria-live). 정직헬퍼·narration 숫자토큰·projection 커버리지 vitest green.
6. **P5**: `carousel:` 오버레이/자동 폴백.
7. **회귀**: `/report`(추출 동치)·터미널·블로그[slug] 시각 무변경(Playwright)·`tests/run.py preflight` green.

**MCP 정직성**: 카드 수치 `EngineCall`(Company.panel)·`PeerCompareN` 교차검증.
