# PRD — 좌측 시장 공시 피드 (Market Filings Feed)

**전상장사 최근 3개월 수시공시 흐름 · 주가영향 카테고리 탭 · 좌측 패널**
v0.1 · 2026-06-19 · 5도메인 토론 + 4적대검증 수렴(`wf_9f54e359-0c8`) · 코드 실측 검증 완료

> SSOT = `mainPlan/market-filings-feed/`(메모리=포인터). 착수 = 운영자 go · **UI push = 운영자 명시 승인 후에만**.
> 모든 feasibility 숫자는 [01-current-state-audit.md](01-current-state-audit.md) 실측(3개월 윈도) 기준 — 직전 정기보고서 PRD 맹점("데이터경로·로드상태 추적 없이 주장") 회피.

---

## 1. 무게중심 (본질)

이 기능은 "한 회사의 공시"가 아니라 **"지금 시장 전체에서 주가 움직일 일이 어디서 터졌나"의 멘탈모델**이다. 우측 RightStack 비정기 패널은 *선택한 한 회사*의 전이력(stock_code 필터)이고, 새 좌측 피드는 *전상장사 2,659종목*의 최근 3개월 수시공시를 **rcept_dt 시간순**으로 흘려보내며 주가영향 카테고리(지분·내부자 / 자기주식 / 증자·사채 / 최대주주·경영권 / 실적·계약)로 거른다. 정기보고서(사업/분기/반기)는 panel 엔진 소유라 이미 빌드에서 제외되어 있어, 이 피드는 자연히 *수시공시 위주*(주가영향 큰 것들)다.

무게중심은 **새 분류기가 아니라 노이즈 게이트와 정직성**이다. 두 가지를 동시에 한다:
- (a) `classifyFiling`이 한 `equity` 바구니에 묶어버린 **임원·주요주주 소유(약신호·도배 위험)와 5% 대량보유(강신호)를 쪼개서** 신호를 살린다.
- (b) 사용자가 요청한 '연금/기관' 탭은 report_nm에 '연금'이 **0건**이라 flr_nm 제출자명으로만 식별 가능한데 그게 **약 9.5%(940/9,934 equity 행)**만 잡히고 개인 오너와 섞이므로, 기관을 잡았다고 위장하지 않고 **'제출자=기관(부분식별·약10%)' 정직 라벨 + 보조 필터칩**으로만 표면화한다.

★적대검증 정정 핵심: 진짜 결함은 '개인을 기관으로 오분류(false positive, 측정상 거의 0)'가 아니라 **'기관을 못 잡아 과소표시(false negative)'**다 — `J.P.MORGAN` 같은 명백한 기관도 점(.) 때문에 사전이 못 잡는다. 강함은 탭을 쌓아서가 아니라 약신호를 깎고 침묵을 라벨로 드러내서 온다.

---

## 2. 데이터층 결정 — 옵션 B 확정 (CI bake 슬림 parquet)

### 최종 택1: **옵션 B** (CI에서 rcept_dt 내림차순 정렬 + 3개월 슬림 parquet bake → 브라우저 단일 whole-file GET). 5도메인 만장일치, 4적대검증 전부 survives.

**옵션 A(전체 recent.parquet 1.89MB 읽고 클라 날짜필터) 기각 — 근거 정정(적대검증 fix 반영):**
- ⛔ **기각 메커니즘에서 '1.89MB > WHOLE_FILE_MAX_BYTES(1536KB) → range-session falldown'을 삭제한다.** 코드 실측: `requestParquetWholeFile`([request.ts:126](../../ui/packages/runtime/src/data/fetch/request.ts#L126))은 `ref.size`를 검사하지 않고 무조건 `hfUrl` 단일 GET 후 전체 파싱한다. 1536KB 임계는 `openHfParquet`([hfRange.ts:156](../../ui/packages/runtime/src/data/parquet/hfRange.ts#L156), `requestParquetRows` 경로) 전용이다. 옵션 A를 whole-file로 구현하면 1.89MB여도 range로 안 떨어진다 — 이 논거는 틀렸다.
- ✅ **진짜 기각 근거(둘 다 실측):** (1) recent.parquet은 `out.sort(["stock_code","rcept_dt"])`([buildAllFilingsRecent.py:92](../../.github/scripts/sync/buildAllFilingsRecent.py#L92)) 정렬이라 **전체시장 날짜순 자체가 안 나온다** — 11 row-group 전부 rcept_dt=[20240902..20260612] 동일(statistics 직접 측정), 날짜 row-group pruning 0건 → 옵션 A는 무조건 210,963행 전량 다운로드(1.89MB) + 클라 날짜필터. (2) 매 진입마다 1.89MB 전송 + 210K행 hyparquet 파싱은 좌측 핫패스(첫 페인트)를 지연 — `companyLive.ts` `e801f42f0`(DuckDB 수십초 멈춤→hyparquet) 교훈의 *읽기 무게* 함정과 동질.

### 옵션 B 구현
- 빌드(`buildAllFilingsRecent.py` 편승, 새 cron/스크립트 0): `build()`가 line 90-92에서 보유한 dedup·정렬 완료 `out` 프레임에서 → `.filter(rcept_dt >= cutoff).sort("rcept_dt", descending=True).write_parquet(..., compression="zstd", row_group_size=5000)` 후 별도 push. **cutoff = 데이터 max − 90일 동적 계산**(절대일자 하드코딩 금지 — 데이터 max 20260612가 today 0619보다 7일 stale, 하드코딩 시 빈 피드 위험).
- ⚠ **'5줄'은 낙관 — 실제 ~15줄(적대검증 fix):** `push()`([:113](../../.github/scripts/sync/buildAllFilingsRecent.py#L113))가 `_RECENT_NAME` 하드코딩이라 **`path_in_repo`를 인자화**해야 한다(또는 2번째 push). corp_name 컬럼 유지(`_KEEP`에 이미 있음). cutoff 동적계산. 빌드 끝에 **size assert(>1.5MB 시 CI 실패)** — 윈도 확장 시 whole-file GET 분기 falldown을 조용히 겪지 않게.

### ★ 실측 정정 (적대검증 fix — PRD에 박을 정확한 숫자)

| 항목 | 설계 초안 (과소/오류) | **실측 정정값(정본)** |
|---|---|---|
| 3개월 윈도 행수 | 33,686 (캘린더 today−3mo) | **38,015** (데이터max−90d rolling, cutoff 20260314) |
| 3개월 bake 크기 | 562.9KB / 606KB / 0.30MB | **656.3KB** (rg5000) |
| 6개월 윈도 | 75,296행 / 1.22MB "여유" | **79,167행 / 1322KB** = 임계 1536KB의 **86%**(가변·비권장) |
| etc 비율 | 36.6% "블랙홀" | **20.3%** (3개월 윈도; exchange 28.5%·equity 26.1%가 더 큰 바구니) |
| 기관 식별률 | 10.1% / 11.8% / 16.7% (분모 상충) | **9.5%** (equity 9,934행 분모) |

**결론: 윈도 = 3개월 고정**(656KB = 임계의 43%, 안전마진 최대). 6개월은 마진 150KB뿐이라 채택 시 임계 재실측 게이트 필수.

### ★ 캐시·신선도 must-fix (적대검증 4건 만장일치 — 코드 실측 확정)

[worker.js:27](../../infra/workers/hfProxy/worker.js#L27) `cacheControlFor(path)`는 `path.endsWith('recent.parquet')`에만 `max-age=600`을 준다. `marketFeed.parquet`·`recentFeed.parquet`·`recent_by_date.parquet`는 전부 endsWith **false** → `max-age=3600`(1시간)으로 떨어진다 → 일일 cron 갱신 데이터가 최대 1시간 stale. **'폴더가 같아서 자동 흡수·한 줄'은 거짓.** 두 정공법 중 택1(운영자 결정):
- **(A·권장·worker 배포 0):** 파일명을 `recent.parquet` 접미로 끝나게. ★주의: `marketRecent.parquet`은 끝이 `…tRecent.parquet`라 **false**. 구분자 필요 → **`dart/allFilings/market_recent.parquet`** → `'market_recent.parquet'.endsWith('recent.parquet')` = **true**. worker 수정/재배포 0, govRecent와 동일 600s 자동.
- **(B):** 임의 파일명 + `worker.js:28`에 분기 1줄 추가(`if (path.endsWith('marketFeed.parquet')) return 'public, max-age=600'`) — infra/workers Cloudflare Worker 별도 배포(가역)를 배포 순서에 명시.

### 로딩/캐시/타임아웃 (직전 DuckDB 교훈 반영)
- **읽기 스택: hyparquet whole-file 강행, DuckDB 금지**(`e801f42f0`). 38K행/656KB는 가볍다.
- 진입점: `core.requestParquetWholeFile({ origin:'hf', path:'dart/allFilings/market_recent.parquet', columns:[6컬럼], cacheKey:'allFilings.marketFeed' })` — `govRecent`([govPriceSource.ts:88](../../ui/packages/runtime/src/adapters/public/sources/govPriceSource.ts#L88)) 패턴 1:1, **새 추상 0**.
- 캐시: `{ scope:'memory', ttlMs:10*60_000, maxEntries:2 }`(govRecent 선례 — soft-swap 중 2 entry). RuntimeCache+RequestDedup 코어 경유(자체 Map 금지·checkUiDataWiring rule 4/6).
- 상태기계: RightStack `nonRegState: 'loading'|'ready'|'empty'` 3상태 + **'불러오지 못함'(콜드 403 영구실패)을 'empty'와 구분** 표면화(무한 스피너 금지). `fetchResilient`([hfRange.ts:113](../../ui/packages/runtime/src/data/parquet/hfRange.ts#L113)) 403/429/5xx 백오프 내장. catch → empty 정직 degrade.
- 분류는 1회 계산 후 파생 메모이즈, 탭 필터는 분류결과 위 O(n)만(탭 전환마다 38K행 재분류 금지 — 작은 재발 가드).

---

## 3. 카테고리 탭 최종안 — **6탭 + 보조칩**

적대검증 만장일치: 12탭(설계 초안 2건) **kill**(과세분화·300px 가로붕괴·약신호 별탭=덕지덕지). IA·도메인의 6탭 수렴이 정직한 깎기. 사용자 5요구(자기거래·내부자·연금·기관·주주변경)를 6탭+보조칩에 **전부 수용**.

| # | 한국어 라벨 | 식별 규칙 (report_nm 정규식, 클라 분류) | 비고 |
|---|---|---|---|
| 1 | **전체** | (무필터·시간순) | 약신호 포함 모두, etc 섞임 |
| 2 | **지분·내부자** | `임원[ㆍ·]?주요주주\|특정증권`(임원소유) + `대량보유\|주식등의\|의결권`(5% 보유) | ★`classifyFiling`이 한 `equity`로 묶은 걸 **2개 패턴으로 분리**. 보조칩 [기관] 거주 |
| 3 | **자기주식** | `자기주식`(취득·처분·소각·신탁) | 사용자 '자기거래' 명시. classifyFiling은 major에 묻음 |
| 4 | **증자·사채** | `유[ㆍ·]?무상증자\|유상증자\|무상증자\|전환사채\|신주인수권\|교환사채\|감자` | 희석·자본조달. 투자설명서·발행실적은 후행정렬 |
| 5 | **최대주주·경영권** | `최대주주\|합병\|분할\|영업[ 양]?양[수도]\|주식교환\|주식이전` | 경영권 이동·지배구조 |
| 6 | **실적·계약** | `손익구조\|매출액\|공정공시\|단일판매\|공급계약` | 펀더 서프라이즈. content_raw 없으니 금액 미파싱·'잠재' |

**etc 처리:** etc(20.3%)는 IR개최·지배구조보고서·기준일설정 등 **약신호 행정공시**다 — '숨겨진 신호'가 아니다. 별 탭으로 승격하지 않고 **'전체' 탭에만 섞이게**(침묵 금지·1번 탭이 first-class 접근), 분류 정확도 끌어올리는 데 공력 쓰지 않는다. 밸류업·배당·주총IR도 동일(수요 입증 후 승격, 덕지덕지 누적 금지).

**탭 라벨 가치판단어 제거(적대검증 fix):** '강신호·최고관심·주주환원·정책테마' 같은 형용은 주가영향 판정으로 읽혀 중립 위반 → **사실 그룹명만**('자기주식 취득·처분·소각').

### 연금/기관 정직성 가드 (must-fix · 5설계+4검증 합의)
- ⛔ **'연금/기관' 독립 1급 탭 kill.** report_nm '연금' 0건 · flr_nm 식별률 9.5% · 88~90% 침묵 = 전상장사 커버 위반.
- ✅ **'지분·내부자' 탭 내부 보조 [기관] 필터칩**으로만. flr_nm이 광의 사전(국민연금공단·자산운용·은행·증권·보험·BlackRock·NorgesBank·Vanguard·Fund·Capital·Asset·Advisors) 매칭 시 칩으로 거름.
- ✅ 칩 라벨·ⓘ: **'제출자=기관(부분식별·약10%·근사)'** — '기관 매수/보유' 단정 금지(과대약속). flr_nm 원문을 행 hover/툴팁에 노출해 사용자 검증 가능(impute 금지·확신오정렬>정렬실패).
- ✅ **분모 단일 실측 SSOT:** equity 9,934행 중 기관패턴 flr_nm 940건 = 9.5%(as-of 데이터max). 초안 분모 상충 폐기.

---

## 4. IA · 경계 — 멘탈모델 3분리

| | 데이터 read 경로 | 정렬키 | 범위 | 소유 |
|---|---|---|---|---|
| **좌측 시장 피드** (신규) | whole-file no-filter | rcept_dt desc | 전상장사 3개월 | 이 PRD |
| **좌측 WATCH 탭** (기존) | `$in:[codes]` | rcept_dt desc | 큐레이션 집합(CAP 100) | terminal-improvement PRD |
| **우측 단일기업 비정기** (기존) | stock_code 필터(1 row-group) | rcept_dt desc | 선택 1회사 전이력 | RightStack |
| **차트 하단 이벤트레일** (기존) | (우측 패널 데이터 재사용) | 날짜축 dot | 선택 1회사 | eventRail.ts SSOT |

**코드상 중복 0(검증):** read 경로·정렬키·범위가 전부 다르다. watchlist.svelte.ts=codes 집합만, RightStack=단일코드 종속, 피드=필터제거+날짜정렬. **인지 충돌은 라벨로 차단:** WATCH='내 종목 신선도' vs FEED='시장 전체 흐름'(둘 다 '최근 공시'를 보여 혼동 위험 — 라벨이 ship 게이트).

**경계 PRD 재소유 금지(소비만):** terminal-improvement(watchlist·델타·freshness) / periodic-report-dossier(단일기업 정기보고서 비재무팩트, panel 엔진) / industry-analysis-lab(섹터) / table-export(egress) / scenario-simulator(미래). 이 기능은 '시장 전체 수시공시 시간순 피드' 한 점.

**순 변화:** 좌측 패널 **+1**(eMarketFeed 1섹션) · 카테고리 칩 스트립 1줄(패널 내부 가로 토글, 별 패널 아님) · 신규 행 그리드 `.feedRow` · 신규 HF 파일 +1(매번 덮어씀, 증식 아님 — gov/recent 선례) · 새 cron/워크플로 **0**. **탭 토글 흡수 기각**(멘탈모델 3분리, 운영자 '그 아래 별도 섹션' 명시).

---

## 5. UI/UX

### 좌측 레이아웃 (LeftRail.svelte, 300px 고정폭)
- 현 3섹션: eMacro(auto) / eIndustry(auto) / eQuant(**단독 fillCol**, [:135](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L135)). → **4섹션**.
- **★fillCol 2분점 KILL**(적대검증 만장일치): terminal.css `.col > .panel.fillCol { flex:1 1 auto }` — fillCol 2개면 잔여높이 50/50 분할 → eQuant·eFeed 둘 다 4~5행 압착('강함=빼기' 위반). 신규 **eMarketFeed = max-height 고정(~200-240px) + 내부 .filingList 스크롤**, **fillCol은 eQuant 단독 유지**(Screener=워크플로 주역). 운영자 '산업 조금 줄이고 그 아래' = 고정높이 섹션으로 충족.
- **산업 스윕 높이 축소(적대검증 fix):** swMap에 **max-height 캡 금지** — ScatterMap은 viewBox 220×134 고정 SVG에 `height:auto`라 캡 걸면 산점도 하단 잘림. 정공법: **swNote([:130](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L130))+swMore([:129](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L129)) 2줄→1줄 합쳐 ~24px 절감**(ScatterMap 점·라벨·viewBox 불변이 ship 게이트). 또는 compact viewBox H 134→110 prop.

### 행 구조 — 회사명 1순위 (우측과 결정적 차별)
- ⚠ **`.filingRow.nonreg`를 그대로 못 쓴다(적대검증 fix):** [RightStack:680](../../ui/packages/surfaces/src/terminal/panels/RightStack.svelte#L680) nonReg 행은 `<a href={f.url} target=_blank>` = **행 전체가 DART 앵커**(클릭=원문, onPick 없음). 피드는 '행 본체=onPick 점프 + 중첩 ↗=원문'이라 `<a>` 안 `<a>` 무효 → **`<div role=button onclick onkeydown> + 중첩 <a class=flArrow stopPropagation>` 신규 구조**. CSS만 재사용, 요소/인터랙션 신설.
- 회사명 컬럼 추가로 4-col grid `auto 1fr auto 12px` = [회사명 bold amber-tint 11px] [제목 dim 10px ellipsis] [MMDD mono 9px] [↗ 10px] → 별 클래스 **`.feedRow`**.
- flr_nm은 행에 4번째 텍스트로 넣지 않음(300px 과밀) → hover 툴팁 + [기관] 칩으로 흡수.

### 클릭 동작
- 행 본체 = `onPick(stock_code)` 회사 점프(차트+우측 단일기업 패널 자연 갱신) — [LeftRail rankRow:164](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L164)·Watchlist:94 role=button+onkeydown 패턴 재사용.
- 행 끝 ↗ = stopPropagation으로 `f.url`(dart.fss.or.kr rcpNo) 새탭. hit-area 12px+패딩·hover 시 ↗만 amber.
- **disclosureFocus.pulse 배선 금지(v1)** — pulse는 '같은 회사 차트↔목록 동기'인데 피드 행은 *다른 회사*라 점프 전 대상 차트 없음. 점프 후 자연 갱신으로 충분(추가 배선 0). '추후 확장점·v1 미사용'으로 강등.

### 가상화 · 300px 가독성
- **33K행 전량 DOM 금지, 가상화 라이브러리 신규 도입 금지**(좌측 어떤 리스트도 가상화 안 씀·Screener는 slice(0,80)). 데이터층 3개월 필터 → 활성 카테고리 필터 → rcept_dt desc → **표시 상한 200행** + '더 보기'.
- **200 cap은 top-N 침묵 절단 아님:** 칩별 전수 카운트 배지 + **'최근순 200건 표시 · 전체 N건 · 더 보기'** 정직 라벨 + cutoff/카운트 as-of.
- 카테고리 칩 스트립: 패널 헤더 아래 가로 스크롤 칩 행(`leftTab` 톤 재사용), 2~4자 라벨, 활성 칩 amber underline + 카운트 배지. overflow-x auto.

---

## 6. 간판 기능 1~3 (새 fetch 최소)

1. **전상장사 시간순 피드** — 좌측에서 시장 전체 최근 3개월 수시공시가 rcept_dt 내림차순으로 흐른다. 회사명 1순위·클릭=회사 점프. 새 fetch = HF 파일 1개(빌드 편승).
2. **주가영향 6탭 필터** — 지분·내부자/자기주식/증자·사채/최대주주·경영권/실적·계약로 강신호를 위로. classifyFiling 묻힌 자기주식·내부자vs5%를 분리. 새 fetch 0(클라 분류).
3. **기관 보조칩 + 정직 라벨** — '지분·내부자' 탭 내 [기관] 토글이 flr_nm 사전으로 ~10% 식별, '제출자=기관(부분식별·근사)' 라벨 + flr_nm 원문 툴팁. 새 fetch 0(같은 파일 flr_nm 컬럼).

---

## 7. 정직 컷 (killList) — 하면 안 되는 것 (5설계+4검증 수렴)

1. 호재/악재·buy/sell·종합점수·등급·레이더·주가영향 판정 금지(중립 시간순 나열만).
2. 연금/기관 독립 1급 탭 금지 — 식별률 9.5%·88% 침묵·오너 혼재. 보조칩+'(추정)' 라벨로만.
3. 개인 오너를 기관으로 단정/impute 금지. flr_nm 원문 노출로 검증 가능하게.
4. top-N cap 침묵 절단 금지 — 200 cap 시 칩별 전수 카운트 + '최근순 200건·전체 N건' 라벨.
5. content_raw 없는 메타 피드에서 본문 영향·금액 추정 금지. 공급계약 규모 '잠재' 라벨. 본문은 viewerPort 딥링크로만 위임.
6. **옵션 A 기각 근거에서 '1.5MB 임계 falldown' 메커니즘 금지**(requestParquetWholeFile은 size 미검사) — stock_code 정렬·210K행 파싱 근거만.
7. **category를 빌드시 parquet 컬럼으로 bake 금지** — classifyFiling 정규식 Python 복제 = 클라 eventRail.ts와 영구 SSOT drift. report_nm 원본 컬럼 유지·클라 분류.
8. classifyFiling/EVENT_CATS(eventRail.ts) **재소유·개조 금지** — 우측 이벤트레일 SSOT. 형제 함수 신설하되 공통 정규식 리터럴은 export 재사용(복붙 금지).
9. fillCol 2분점 금지 · 가상화 라이브러리 금지 · DuckDB 금지(hyparquet whole-file 강행).
10. swMap max-height 캡 금지(ScatterMap 잘림). 산점도 점·위치 불변이 ship 게이트.
11. Watch 탭·우측 단일기업 패널·경계 PRD 재소유 금지.
12. **UI 자동 push 금지** — LeftRail.svelte·새 source·worker는 화면/배선이라 운영자 명시 승인('푸시해'·'올려') 전 commit까지만 + '검사 대기' 한 줄. svelte-check 0err + checkUiDataWiring 신규위반 0 확인 후.

---

## 8. Phase 0~4 (단독 ship 가능 단위)

- **Phase 0 — 데이터층 bake (백엔드/CI, UI 무관·자동 push 가능):** `buildAllFilingsRecent.py`에 ① `push()` `path_in_repo` 인자화 ② cutoff=데이터max−90d 동적 ③ `.filter().sort(desc).write_parquet(rg5000)` ④ size assert(>1.5MB) ⑤ 파일명 `market_recent.parquet`(worker 600s 자동) → HF push. 검증: HF에 656KB·rcept_dt desc·6컬럼 파일 확인. **단독 ship.**
- **Phase 1 — read 배선 (배선 표면 5곳):** ① ui-contracts `corpName` optional 추가(NonRegularFiling 또는 MarketFeedRow) ② `loadMarketFeed(core)` 신규 source(whole-file·필터 없음·corp_name COL 추가) ③ `createPublicRuntime.ts`·`local/filingSource.ts`·`test/createFakeRuntime.ts` 3곳 filing 포트 메서드 배선 ④ core.requestParquetWholeFile 경유. 검증: 단위 테스트로 38K행 read·정규화. **단독 ship(UI 미배선이면 자동 push 가능).**
- **Phase 2 — 분류기:** eventRail.ts에서 공통 정규식 리터럴 export → `marketFeedCategory(reportNm)` 신규(임원 vs 대량보유 분리 + 6키) + `isInstitutionalFiler(flrNm)` 사전. classifyFiling 회귀 0(이벤트레일 골든 통과). **UI push 운영자 승인 대기.**
- **Phase 3 — 좌측 UI:** eIndustry swNote/swMore 1줄 축약 + 신규 eMarketFeed 섹션(max-height 고정) + 칩 스트립 + .feedRow(div role=button + 중첩 a) + 상태기계 + 200 cap 라벨 + [기관] 보조칩. svelte-check 0err·스크린샷 전수 눈검수. **UI push 운영자 명시 승인 후에만.**
- **Phase 4(선택·worker B안 채택 시):** worker.js cacheControlFor 분기 + CF 재배포. ★A안(`market_recent.parquet`)이면 Phase 4 불필요.

---

## 9. 영향 파일·함수·테스트·롤백 (plan-deep 5섹션)

### 영향 파일 (구현 착수 시)
**Phase 0 (백엔드/CI):**
- [.github/scripts/sync/buildAllFilingsRecent.py](../../.github/scripts/sync/buildAllFilingsRecent.py) — `build()` 끝에 슬림 bake 단락 + `push()` `path_in_repo` 인자화 + cutoff 동적 + size assert.

**Phase 1 (read 배선):**
- [ui/packages/contracts/src/filing.ts](../../ui/packages/contracts/src/filing.ts) — `NonRegularFiling`에 `corpName?` 또는 `MarketFeedRow` 신설 + `FilingPort.marketFeed()` 메서드.
- [ui/packages/runtime/src/adapters/public/sources/nonRegularFilingsSource.ts](../../ui/packages/runtime/src/adapters/public/sources/nonRegularFilingsSource.ts) — `loadMarketFeed(core)` 신설(필터 없음·whole-file·corp_name COL).
- `ui/packages/runtime/src/adapters/public/createPublicRuntime.ts` · `ui/packages/runtime/src/adapters/local/sources/filingSource.ts` · `ui/packages/runtime/src/test/createFakeRuntime.ts` — filing 포트 `marketFeed` 배선 3곳.

**Phase 2 (분류기):**
- [ui/packages/surfaces/src/terminal/lib/eventRail.ts](../../ui/packages/surfaces/src/terminal/lib/eventRail.ts) — 공통 정규식 리터럴 export(classifyFiling 불변) + `marketFeedCategory()` + `isInstitutionalFiler()` 형제 함수.

**Phase 3 (UI):**
- [ui/packages/surfaces/src/terminal/panels/LeftRail.svelte](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte) — eIndustry swNote/swMore 축약 + 신규 eMarketFeed 섹션 + 칩 스트립 + .feedRow.
- `ui/packages/surfaces/src/terminal/panels/MarketFeed.svelte`(신규) 또는 LeftRail 인라인 — 행 렌더·탭·상태기계.
- `ui/packages/surfaces/src/terminal/terminal.css` — `.feedRow` 4-col 그리드 + 칩 스트립 톤(.filingRow/.leftTab 확장).
- `ui/packages/surfaces/src/terminal/TerminalSurface.svelte` — 필요 시 피드 탭/스토어 상태(bottomTab 패턴 참고, 단 탭 흡수 아님).

**Phase 4(선택):**
- [infra/workers/hfProxy/worker.js](../../infra/workers/hfProxy/worker.js) — B안 시 cacheControlFor 분기(A안이면 불필요).

### 영향 함수
`build()`/`push()`(bake) · `loadMarketFeed`(신규 source) · `FilingPort.marketFeed`(포트) · `marketFeedCategory`/`isInstitutionalFiler`(신규 분류) · `classifyFiling`(불변·정규식만 export) · `requestParquetWholeFile`(소비) · `onPick`(행 클릭) · `viewerPort` 딥링크(소비).

### 테스트·가드
- **Phase 0:** bake 산출 단위검증 — 행수(~38K)·rcept_dt 내림차순·6컬럼·size<1.5MB assert. CI에서 파일 존재+스키마.
- **Phase 1:** `loadMarketFeed` 단위 — fakeRuntime stub로 38K행 정규화·corp_name 포함·dedup. `node tests/audit/checkUiDataWiring.mjs`(rule 2/4/6 신규위반 0).
- **Phase 2:** `marketFeedCategory` 6키 매핑 골든(임원 vs 대량보유 분리 확인) + `classifyFiling` 이벤트레일 골든 회귀 0(SSOT 불변 증명) + `isInstitutionalFiler` 사전 정밀도 표본.
- **Phase 3:** `npx svelte-check`(0 err) + 스크린샷 전수 눈검수(산업 ScatterMap 점 불변·칩 가독성·행 회사명·로딩/빈/에러 상태). 공개/로컬 동일 렌더.

### 롤백
- Phase 0: bake 단락은 추가 산출(기존 recent.parquet 불변) → HF 파일 1개 삭제로 완전 롤백. recent.parquet·우측 단일기업 경로 영향 0.
- Phase 1~2: 신규 포트 메서드·신규 함수 → UI 미배선 상태면 무영향. 되돌리면 dead code 제거.
- Phase 3: LeftRail 섹션 추가가 유일한 가시 변경 → 섹션 제거로 롤백(산업 swNote/swMore 축약만 잔존, 무해). 미push 상태로 검수.
- Phase 4(B안): worker 분기 1줄 → CF 재배포로 가역.

### 개발자·PM 이중 평가
- **개발자**: 최대 위험 = ① worker cacheControlFor 파일명 게이트(놓치면 1h stale — A안 `market_recent.parquet`로 원천 차단) ② 배선 표면 5곳('한 줄' 과소평가 — 포트+어댑터 3곳+contract) ③ category SSOT drift(빌드 bake 금지·클라 분류) ④ fillCol 2분점(금지·고정높이) ⑤ ScatterMap 잘림(max-height 캡 금지). 전부 적대검증으로 사전 식별·해법 확정.
- **PM**: 사용자 명령("시장 전체 공시·카테고리 세분·주가영향") 정확 충족. ROI 높음 — 데이터 자급(빌드 편승·새 fetch 최소)·재사용 풍부(govRecent 선례·classifyFiling·filingRow CSS)·순 패널 +1로 시장 디스커버리 레인 신설. 정직 비용(기관 9.5% 라벨·etc 약신호·메타 한계)을 위장 않고 표면화. **컷라인**: Phase 0+1+3 = MVP(기관 칩 없이 5탭도 ship 가능). Phase 2 기관칩은 정직 라벨 전제로만.

---

## 10. 남은 열린 결정 (운영자 확인용)

1. **캐시정책 경로** — A안 파일명 `market_recent.parquet`(worker 배포 0, 600s 자동) vs B안 임의명+worker 분기+CF 재배포. → **A안 권장**(배포 부채 0).
2. **시간창** — 3개월 고정(656KB·임계 43%) vs 6개월(1322KB·임계 86%·가변). → **3개월 고정 권장**. 6개월은 임계 재실측 게이트 필요.
3. **기관 사전 범위** — 광의(자산운용·은행·증권·보험·외국기관, ~10% 식별·일부 사업회사명 오매칭 위험) vs 협의(연금·국부펀드만, 정밀도↑ 재현율↓). → 광의+정직 라벨이 실측상 정직하나 운영자 선호 확인.
4. **임원소유 도배** — '지분·내부자' 별 탭 분리로 충분(전용 탭=주제니 도배 아님) vs '회사당 집계+접힘' 그룹핑. → **v1은 그룹핑 상태머신 신설 금지**(안티클러터), 탭 분리+200cap+카운트로 처리, 집계는 수요 검증 후 v2.

---

## 출처

전문에이전트 9인 토론(5 도메인 설계 + 4 적대검증) + 종합 리드 1인(`wf_9f54e359-0c8`, 2026-06-19, 10에이전트·1.13M 토큰). 데이터엔지니어·UI/UX·IA·시장미시구조·한국자본시장 5렌즈 설계 → 데이터층/정직성/안티클러터/UI회귀 4렌즈 적대검증으로 모든 feasibility 주장을 worker.js·classifyFiling·build()·govPriceSource·request.ts·hfRange.ts 코드 실측에 대조·정정. 토론 정본 = [02-debate-and-verification.md](02-debate-and-verification.md).
