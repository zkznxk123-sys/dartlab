# 01. 현황 감사 — KR ↔ EDGAR Ground-Truth Census

상태: **v0.3 (2026-06-22)** — R1·R2 패널 평가 후 *직접 코드 재검증*으로 census 정정. 표기 규칙: **[확인]** = 작성자 직접 grep/read 검증, **[보고]** = census 에이전트 보고(미재검증), **[정정]** = 오류 → 코드 사실.

> ★교훈(메모리 정합): v0.1 census(탐색 에이전트 보고)는 "비대칭 0·notesDetail 완전미러·scan 1/8·비대칭테스트 신설" 등 **다수가 코드와 모순**이었다. 실코드 직접대조가 이를 도려냈다. 이후 모든 단정은 [확인] 근거만 단정조로 쓴다(05 §4 never-claim 자기적용).

---

## A. 빌드 파이프라인 — 카테고리별 KR↔EDGAR

| 카테고리 | KR | EDGAR | 상태 | 근거 |
|---|---|---|---|---|
| **panel** | `dart/panel/{code}` baked | `edgar/panel/{ticker}` per-filing | **빌드경로 완성 / native payload backfill 미실측** | [확인] `edgarPanel.py` `_runFullRebuild`=dispatch전용, `_runIncremental`=변경종목만 |
| **finance** | `dart/finance/{code}` | `edgar/finance/{cik}` companyfacts | **완성** | [보고] companyfacts.zip 벌크 |
| **scan (모델 자체가 다름)** | `dart/scan/*` **baked parquet** (changes/finance/finance_lite/report/shares + docsIndex/valuation) | `edgar/scan/finance.parquet` baked 1종 + **라이브 dispatch 13축** | **[정정] "1/8 미러"는 오인 — KR=baked, EDGAR=런타임 계산. 아키텍처 결정 필요(02 §3.5)** | [확인] `scan/router.py:289-334` `_edgarDispatch` 11 XBRL축→`edgarScan()` 라이브 + account/ratio; baked는 finance만 |
| **scan/changes** | panel 본문 텍스트 diff baked | — | **개념검증 선행 후 미러** (panel contentRaw 입력 가능, item 경계 정의 선결) | [보고] `kr/docs/changes.py` |
| **scan/sharesOutstanding** | panel 한글표 파싱 → 17-col 시계열 | `getSharesOutstanding`=`dei:` **단일 스냅샷 1값** | **[정정] 부분 EXEMPT — KR 17-col(authorized/treasury/floating/preferred) US XBRL로 불가** | [보고] `kr/shares.py`·`edgar/finance/pivotPost.py:376` |
| **scan/docsIndex** | baked | `buildEdgarDocsIndex` **이미 구현** (입력=`edgar/docs` deprecated) | **[정정] 신설 아님 — sections 재배선 + edgarSync step 추가** | [보고] `kr/docs/index.py:252`; [확인] `edgarScan` 카테고리 등록됨 |
| **scan/report 17 apiType** | `dart/scan/report/*` | — | **EXEMPT** (SEC 폼 구조 상이) | [보고] |
| **allFilings (비정기)** | `dart/allFilings/` baked | live SEC API (baked 미빌드) | **부분** (US 라이브 의존, 퍼블릭 floor 약) | [보고] |
| **prices** | `gov/prices` baked (KOGL) | `gather("price")` **라이브만**(yahoo/fmp chain), baked **부재** | **갭 — US baked 가격 소스 없음** | [보고] |
| **indices** | `gov/indices` baked | FRED markets | **완성** (프론트 indexPort US 배선) | [확인] `contracts/indexPort.ts` |
| **macro/fred** | `macro/fred` | `macro/fred` | **완성** (시장공용) | [보고] |
| **edgarScan 카테고리** | — | `dataConfig.py:152-156` `edgar/scan`, **public=False** | **이미 등록 — 공개 전환 결정 필요** | [확인] |

**핵심 정정:**
- panel은 "완성"이 아니라 **"빌드경로 완성 + backfill 미실측"**. `_runFullRebuild`는 dispatch 전용, daily는 변경종목만 → 유니버스 native 보유율 미확정. [정정] backfill은 외부 cron 아님 — `edgarRebuildContinue.yml`이 `f46a58931`로 제거되고 **운영자 로컬 resumable rebuild** 전환(2026-06-10). 03 Slice0 S0.1 정량 게이트.
- **scan은 KR(baked)과 EDGAR(라이브) 모델이 다르다.** 퍼블릭 셸이 HF 직독(`:8400` 없이)이라면 브라우저가 per-CIK parquet 수백개 라이브 계산 불가 → **EDGAR scan도 baked로 통일**이 사실상 강제(02 §3.5 결정).
- docsIndex 빌더·edgarScan 카테고리는 **이미 존재**. 진짜 작업 = sections 재배선 + 워크플로 step + public 전환.

근거: `src/dartlab/scan/router.py:289-334`, `src/dartlab/core/dataConfig.py:152-156`, `src/dartlab/pipeline/stages/edgarPanel.py`, [보고] `kr/docs/index.py`·`kr/shares.py`·`edgar/finance/pivotPost.py`.

## B. 라이브러리 — 엔진별 US 미러 (정정)

| 엔진/메서드 | US 상태 | 근거 |
|---|---|---|
| `panel`·`finance`·`select`·`trace`·`diff` | **표면+데이터 미러** | [보고] |
| `disclosure`/`liveFilings`/`readFiling`/`filings` | **미러** | [보고] |
| `analysis`/`quant`/`macro`/`story` | **[정정] 표면 미러 / 계산 KR가정(정직 None)** | [확인] `_revenueSelect.py:110` US면 `return None`; story `sixAct._sectorScore`→KR `industry()` graceful None |
| `credit` | **⛔ [정정] 회색지대 — 침묵 KR-garbage** | [확인] market 가드 0, `sectorThresholds.py:85` `sector None→_defaultThresholds()`(KR) → US 숫자 non-None 가짜 등급. `_revenueSelect`(정직 None)와 비대칭 — Slice1 가드 필수 |
| `search`/`listing`/`notes`(wrapper) | **미러** | [보고] |
| `report` 메서드 | **[정정] 미러됨 (XBRL `_ReportAccessor`)** — EXEMPT는 *DART OpenAPI report 17 apiType*에 한정 | [확인] `company.py:3798 def report` |
| `scan(market="us")` | **라이브 13축 dispatch** (11 XBRL + account/ratio). changes/shares/docsIndex 축 미라우팅(`return None`) | [확인] `router.py:306-334` |
| `notesDetail`·`flow`·`executivePay`·`relatedPartyTx`·`simulate` | **[정정] 비대칭 missing — EDGAR 메서드 부재** | [확인] `_baselines/providerSymmetry.json` missing 5건; grep 0 |
| `industry`/`sector`/`sectorParams`/`rank`/`network`/`topicSummaries` | **영구 EXEMPT** (일부 stub `return None`, 일부 메서드 부재) | [보고] `SKILL.md:246-254` |

**핵심 정정:**
- **비대칭 = 0이 아니다.** `tests/audit/_baselines/providerSymmetry.json` missing **5건**: `executivePay`·`flow`·**`notesDetail`**·`relatedPartyTx`·`simulate`(shallow 0). [확인] 직접 read. → v0.1 "비대칭 0·notesDetail 완전미러"는 거짓. notesDetail은 미러 아님.
- **비대칭 테스트는 이미 존재.** `tests/audit/providerSymmetry.py` + baseline 원장 + **P-PR6/7/8 트랙**(XBRL/10-K sections/DEF 14A 통과마다 missing 축소, P-PR8 종료=strict 0). [확인] Glob. → L1.1 "신설"은 거짓. EXEMPT allowlist SSOT = 코드 상수(`_DART_ONLY`), SKILL 파싱 아님.
- **3-provider SSOT.** dart↔edgar뿐 아니라 **EDINET(일본)** provider 존재 — 비대칭 게이트가 3-provider. 2-provider 가정은 회귀 위험(05 비목표).
- `analysis/credit/quant/story`는 *호출은 되나 계산이 KR 가정* → "배선만 통일하면 끝" 프레임 밖. **계산 정합은 별도 트랙**(00 §1.1 재분류).

근거: [확인] `tests/audit/_baselines/providerSymmetry.json`, `tests/audit/providerSymmetry.py`(존재), `src/dartlab/providers/edgar/company.py:616·3798`, `src/dartlab/analysis/financial/_revenueSelect.py:110`, `src/dartlab/scan/router.py:289-334`.

## C. 프론트 — 제품 인벤토리 + 시장 차원

### C.1 제품 / C.2 구조
- Surface: terminal·viewer·scan·map (+ ask/chat 로컬). report=terminal 패널. `ui/web`(React DEPRECATED)=TerminalSurface bridge만, **제외 안전**.
- landing(퍼블릭 셸 @5173, `marketDefault='KR'`)·ui/apps/local(로컬 셸 @5174, `marketDefault='KR'`) 동일 surface 호스팅, 어댑터만 상이. [확인] `contracts/runtime.ts:32`.

### C.3 시장 차원
- **있음**: `indexPort.ts` `IndexMarket` US 포함 · `macro.ts` `'KR'|'US'|'GLOBAL'` · `runtime.ts:32` `marketDefault:'KR'|'US'`(값 항상 'KR'). [확인] · `local/sources/priceSource.ts:18` `market:'KR'` **이미 하드코딩**(존재하나 KR고정).
- **없음**: CompanyPort·PricePort·FinancePort·FilingPort·ScanPort·ReportPort·NewsPort·ViewerPort.

### C.4 KR 식별자/경로 하드코딩 (정정 — 경로 + 범위 확장)
정확 경로 prefix = `ui/packages/runtime/src/adapters/public/sources/`. [정정: v0.1은 `sources/public/`으로 오기]
| 파일:line | 경로 |
|---|---|
| `…/financeSource.ts:59` | `dart/finance/${code}` |
| `…/govPriceSource.ts:58·99` | `gov/prices/company/${code}`·`recent.parquet` |
| `…/priceSource.ts:65·67·99` | `gov/prices/date/${year}` + `ISU_CD='A'+code` 필터·KRX 원어 컬럼·`KRX_MIN_YEAR` |
| `…/reportSource.ts:83·692` | `dart/scan/report/*`·`dart/scan/valuation.parquet` |
| `…/gateSource.ts:29` | `gov/fundamental-gate.parquet` |

**[정정] 감사 밖 하드코딩 다수**: [확인] `surfaces/src/scan/{duckSql,tableSources,universe/load,financeLiteRuntime}.ts` 등 8파일이 `registerHfParquet('gov/prices/...')` 직접 등록 + [보고] `landing/src/lib/browser/{hfFinance,companyLive}.ts`·`runtime/src/data/finance/annual.ts:184`·`surfaces/terminal/lib/engine.ts`. → L3 범위는 "adapter source 8개"가 아니라 **scan surface DuckDB·landing browser·viewer 백엔드 라우트(/api panel)·data층**까지. `checkUiDataWiring.mjs`는 이들을 *감사 안 함* → "위반 0 = 안전"은 부분보증.

### C.5 식별자 라우팅 (L2 핵심)
- **[확인] 라이브러리 라우팅은 priority 기반.** `edgar/company.py:616` canHandle은 `s.isdigit() and len(s)<=10`이면 True → 6자리 KR코드도 EDGAR True. 분기는 식별자 모양이 아니라 **provider priority(dart<edgar=20)**. → 프론트 `resolveMarket`을 순수 식별자 함수로 미러하면 6자리 CIK(예 Apple=320193)와 KR코드 충돌. **명시 market override 1순위 + KR우선 비대칭 규칙 필요**(03 L2.1 재설계).

## D. 종합 — 정정된 아래→위 갭
1. **L0/Slice0 빌드**: panel backfill 정량실측([정정] 로컬 rebuild, cron 제거 f46a58931) + edgar/tickers HF publish. scan **baking 모델 결정**(KR baked ↔ EDGAR 라이브). docsIndex=[정정] marketNs 비기능 정정. shares=부분 EXEMPT. US 가격=별도 Slice2(라이선스).
2. **L1 라이브러리**: 비대칭 missing 5건(baseline 원장, P-PR 트랙)·테스트 **이미 존재**. 진짜 갭 = analysis/credit/quant/story **KR 계산가정**(별도 트랙) + scan 보조축 dispatch.
3. **L2 계약/런타임**: resolveMarket **priority-비대칭** 재설계. 6포트 market + **호출부 전수 전달**(code만 넘김). 식별자 매핑(code↔cik↔ticker) 데이터 소스.
4. **L3 소스**: adapter source + **scan duckSql·landing browser·viewer 백엔드**까지. EXEMPT=throw(notWiredYet) 관례.
5. **L4 서피스**: 4 surface US + EXEMPT 정직(빈 항목 카운트 노출) + 식별자 표시.
6. **L5 제품**: 시장 스위처. 무회귀.
