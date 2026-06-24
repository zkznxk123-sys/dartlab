# 블로그·캐러셀 단일 SSOT — 글-슬러그 키 1:N 통합 (P7)

> **상태**: 설계 확정·구현 착수. 00-prd 의 code-키 1:1 계약을 **글(=회사+주제) 슬러그 키 1:N** 로 전환하고, 손글 SSOT 를 `sns/carousels/E*` 분리본에서 **블로그 글 frontmatter `carousel:` 단일 계약**으로 통합.
> **승인**: 운영자 2026-06-24 — "ssot를 어떻게 둘것인가 / 블로그 산문도 같은회사 다른내용으로 발행할수있는데 / 원래는 같이 가려고 / 해라 운영까지 완벽하게."

## Context (왜 — 00-prd 대비 정정)

00-prd 가 만든 라이브 캐러셀은 두 결함이 있다(코드 대조 확인):

1. **code-키 1:1 — 회사당 1편 덮어쓰기.** [build_carousel_contracts.py:137](../../sns/scripts/build_carousel_contracts.py#L137) "코드당 최신 E-번호 우선" 이 한 회사의 여러 편집 카루셀 중 **하나만 남기고 버린다**. 실데이터는 1:N — 003230(삼양)=3편(`009`·`014`·`E06`), 000660·373220·336260·278470·267260·259960·247540·012450·CPNG = 각 2편. 인덱스도 `{codes:[]}` 로 회사당 1엔트리.
2. **SSOT 가 분리** — 손글 편집 카피가 `sns/carousels/E*/hook.json` 에 있고 블로그 산문은 `blog/05-company-reports/*/index.md` 에 있어 **두 곳**. 운영자 원래 의도 = "블로그랑 캐러셀 한 호출계약". 블로그 글도 회사당 N편(같은 회사 다른 주제)이라 **양쪽 다 1:N** 이어야 하고 한 소스에서 나와야 한다.

**핵심 통찰**: 블로그 글 폴더 `{NN}-{code}-{slug}` 자체가 *이미* 회사당 N편 단위다. 캐러셀 키를 **코드 → 글 슬러그**로 바꾸면 1:N 이 공짜로 풀리고, 손글 계약을 **그 글의 frontmatter `carousel:`** 에 두면 블로그·캐러셀이 한 파일에서 나온다(= 호출계약 SSOT). 슬러그(`003230-samyang-foods`)가 코드를 포함하므로 serve 경로는 `carousels/{slug}.json` 로 충분(00-prd 의 `{code}/{slug}` 보다 단순).

## 핵심 결정 (척추)

1. **SSOT = 블로그 글 frontmatter `carousel:` 블록(YAML).** 한 글 = 한 스토리(회사+주제) = 산문(본문) + 캐러셀(frontmatter). 슬러그 키 → 회사당 N편. `sns/carousels/E*` 는 **마이그레이션 원천**으로 강등(편집 카피를 blog frontmatter 로 1회 이관) — 이후 손글 SSOT 는 blog frontmatter 단일. PNG SNS 렌더(render.py)는 별도 출력 채널로 현행 유지(후속 통합 여지).
2. **frontmatter `carousel:` = 풀 계약.** 기존 CarouselContract(`title·caption·pinnedComment·slides[]`) + CarouselSpec(`hero·order·notes`) 를 **한 블록**에 병합. `slides[]` = editorial/editorialBeat/editorialStat 손글. `image` = semantic 파일명(해시·확장자 없음, hfMedia 매니페스트 해석). caption/pinned 는 YAML block scalar(`|`).
3. **Serve = `carousels/{slug}.json` + `carousels/index.json={posts:[{code,slug,title,date}]}`.** 슬러그 globally-unique(블로그 폴더 유니크). 인덱스 = posts 배열, date 내림차순(인스타식 최신순 피드). 발행 = blog frontmatter → 컴파일 → hfMedia (라이브·무-rebuild, 브라우저 JSON 직독).
4. **읽기측 슬러그 키.** 피드가 posts 순회(회사당 N편 별개 카드). `buildDeck(rt,{code,slug})` — report 는 코드별(재무), 편집 lead/spec 는 슬러그별 계약에서. /cards 가 blog 번들 비의존(spec 도 계약에 실어 hfMedia 라이브).

---

## Section 1 — 영향 파일

### 타입·읽기측 (landing/ui — 운영자 push 승인 대상)
- `landing/src/lib/cards/model.ts` — `ContractIndex = { posts: ContractPost[] }`(was `{codes}`); `ContractPost = {code,slug,title?,date?}`; `CarouselContract` 에 `slug:string`·`spec?:CarouselSpec` 추가.
- `landing/src/lib/cards/contract.ts` — `loadContractPosts():Promise<ContractPost[]>`(was `loadContractCodes`→Set); `loadContract(slug)` → `carousels/{slug}.json`(키=slug, was code); `contractToCards` 불변(이미 contract 인자).
- `landing/src/lib/cards/build.ts` — `buildDeck(rt, post:{code,slug}, perspectiveKey)` → `[buildReport(rt,post.code,k), loadMediaIndex(), loadContract(post.slug)]`. spec=`contract.spec`(blog 번들 `getPostByStockCode` 의존 제거). `resolveHeroes` 불변.
- `landing/src/routes/cards/+page.svelte` — 피드 = `loadContractPosts()` → posts 순회. 검색=corpName/code/title. CoverThumb/PostModal 에 `{code,slug,title}` 전달. 터미널 `?sym=code` 진입 = 그 코드의 첫 post 로(없으면 전체 피드).
- `landing/src/lib/cards/CoverThumb.svelte` — props `{code,slug}`. `loadContract(slug)`.
- `landing/src/lib/cards/PostModal.svelte` — props `{code,slug}`. `loadContract(slug)`. Deck 에 `slug` 전달.
- `landing/src/lib/cards/Deck.svelte` — props `slug` 추가. `buildDeck(rt,{code:sym,slug},k)`.
- `landing/src/routes/cards/+page.ts` — `?post=slug` 파라미터 수용(기존 `?sym` 호환 유지).
- `ui/packages/surfaces/src/terminal/**` — /terminal 「카드뉴스」가 PostModal 을 code 로 열던 경로(있으면) → 그 코드 첫 post slug 로. (TerminalSurface 의 carousels 참조 확인 대상.)

### 발행·검증 (sns·blog — 운영자 로컬 도구, CI 무관)
- `sns/scripts/build_carousel_contracts.py` — **전면 재작성**. 원천 = `blog/05-company-reports/*/index.md` frontmatter `carousel:`(was `sns/carousels/E*/hook.json`). 슬러그 키 → `carousels/{slug}.json`. 인덱스 = `{posts:[{code,slug,title,date}]}` date 내림차순. 업로드 로직(CommitOperationAdd 배치·retryHfCall·HF_MEDIA_REPO) 재사용.
- `sns/scripts/migrate_carousels_to_blog.py` — **신규**. `sns/carousels/{E*,0NN*}/{hook.json,caption.txt,comment_pinned.txt,meta.json}` → 편집 슬라이드/캡션/제목 추출(기존 `_slide_from_card` 로직 이관) → meta.json `blogSlug`/`blogFolder` 로 대상 blog 글 식별 → 그 글 frontmatter 에 `carousel:` 블록 주입(멱등·이미 있으면 skip 또는 `--force`). X-시리즈(비회사) 는 대상 글 없음 → 스킵 + surface.
- `blog/_scripts/audit_seo.py` — `validate_carousel` 확장: `slides[]` 풀 스키마(layout enum·layout별 필수필드·image 문자열) + caption/pinnedComment 타입 + slide 텍스트 no-new-number(본문 숫자 ⊆) + 기존 hero/order/notes 검증 유지.

### 테스트
- `landing/src/lib/cards/contract.test.ts`(신규) — `loadContractPosts` posts 파싱·`loadContract(slug)` URL.
- `landing/src/lib/cards/project.test.ts`(기존) — lead+spec 투영 불변 회귀(슬러그 무관·동치).
- `sns/scripts/test_assets_pipeline.py`(확장) — build_carousel_contracts: blog frontmatter fixture → 1:N 계약(같은 코드 2 slug = 2 계약)·index posts date 정렬·migration 멱등.

---

## Section 2 — 영향 함수/심볼 (재사용/신규)

**재사용**: `buildReport`·`projectResult`/`projectReport`(opts.lead/spec 그대로)·`contractToCards`·`resolveHeroes`·`loadMediaIndex`·`heroUrls`·IntersectionObserver 피드 패턴·`_resolveHfToken`/`retryHfCall`/`CommitOperationAdd` 배치([hfUpload.py:156](../../src/dartlab/pipeline/hfUpload.py#L156))·`HF_MEDIA_REPO`·`build_carousel_contracts._slide_from_card`/`_image_stem`/`_read_text`(migration 으로 이관)·audit_seo `yaml.safe_load` frontmatter 파싱·`PostMeta.carousel`/`getPost(slug)`.

**신규**: `ContractPost` 타입·`loadContractPosts`·`buildDeck({code,slug})` 시그니처·`migrate_carousels_to_blog.py`·build_carousel_contracts 의 blog-frontmatter 리더(`_read_frontmatter(index_md)→dict`)·audit_seo slides 검증·contract.test.

---

## Section 3 — 테스트·가드

| 가드 | 커버 | 신규 배선 |
|---|---|---|
| svelte-check (landing) | cards/* 슬러그 전환 타입 | 0 err 필수 |
| vitest (landing) | contract posts·projection 동치 | contract.test 신규·project.test 회귀 |
| `test_assets_pipeline.py` | build_contracts 1:N·index posts·migration 멱등 | blog frontmatter fixture |
| audit_seo (수동) | carousel slides 스키마·no-new-number | 풀 슬라이드 검증 |
| landing build (lightningcss) | terminal.css·dev≠build | `✓ built` 확인 |
| `checkUiDataWiring` | cards = landing route 미커버 | convention(originUrl hfMedia)·리뷰 |

**필수 신규 테스트**: ①같은 코드 2 글(slug A·B) → 계약 2개·index posts 2엔트리(덮어쓰기 0) ②index posts date 내림차순 ③migration 멱등(2회=동일 frontmatter) ④loadContract(slug) URL=`carousels/{slug}.json` ⑤projection lead+spec 동치(슬러그 전환 회귀 0) ⑥audit no-new-number(slide 숫자 ⊄ 본문 → 경고).

---

## Section 4 — 롤백

- **읽기측·발행 독립.** model/contract/build/cards 타입 전환 = 1 논리커밋(svelte-check 게이트). 되돌리면 code-키 복귀.
- **migration 가역** — blog frontmatter `carousel:` 주입은 `--dry-run` 선검 + 멱등 + git diff 로 회귀 가능. 공개 블로그 글 편집이므로 **운영자 눈검수 후 push**(CLAUDE.md UI/public 가드).
- **serve 가역** — hfMedia `carousels/*.json` 재발행 가역(콘텐츠 mutable·10분 캐시). 옛 `carousels/{code}.json` 잔존은 무해(읽기측이 index posts 만 소비).
- 데이터 안전: dartlab import 순차(blog frontmatter 파싱은 yaml 만·dartlab 무거운 import 없음).

---

## Section 5 — 평가 (개발자 + PM)

### 개발자
- **강점**: 키 1차원 추가(code→slug)로 1:N·통합 동시 해결. 발행 인프라(upload·retry·CommitOperationAdd) 100% 재사용. 읽기측 라이브 구조 불변(키만 slug). spec 을 계약에 실어 /cards 의 blog 번들 의존 제거(완전 라이브).
- **주위험①**: 공개 블로그 30편 frontmatter 편집(migration) — `--dry-run`+멱등+눈검수+눈문서 push 게이트로 통제. 본문(산문) 무변경(frontmatter 만).
- **주위험②**: 기존 hook.json 리치 카드(lineChart/list/timeline)는 editorial 3종만 추출(현 build_contracts 와 동일·차트는 auto 투영이 담당) — 손실 아님(설계상 lead=텍스트 훅, 차트=ReportModel).
- **주위험③**: 슬러그 유니크 가정 — 블로그 폴더 유니크가 보장(parsePostPath·getPost). 충돌 시 audit 에러.

### PM
- **가치**: "같은 회사 다른 주제" 가 블로그·캐러셀 양쪽에서 N편으로 산다(운영자 핵심 요구). 호출계약 SSOT = 한 글 = 한 발행단위.
- **위험통제**: 산문 무변경·Phase 격리·발행 운영자 트리거·UI push 눈검수 승인. 이미지 불만은 직교(semantic 참조 → hfMedia 에서 lazy 교체, 계약 무관).
- **비용**: 읽기측 전환 + 발행 재작성 + migration + 검증. 단발 집중.

## Verification
1. 타입·읽기측: svelte-check 0err·vitest green(contract posts·projection 동치).
2. 발행: build_carousel_contracts `--dry-run` → 같은 코드 다글 = 다계약·index posts date 정렬.
3. migration: `--dry-run` → 대상 글 매핑·멱등. 실행 후 blog git diff 눈검수.
4. audit_seo: 샘플 carousel → slides 스키마·no-new-number 통과/실패.
5. /cards dev(`:8400` 없이 public): 회사당 N편 별개 카드·검색·스와이프·pending 빈카드. landing build `✓ built`.
6. push = 운영자 눈검수 승인 후(공개 블로그+UI).
