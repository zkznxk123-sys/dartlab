# 03. 단계 로드맵 — 슬라이스 × 6층 (아래부터 누적)

상태: **v0.4 (2026-06-22)** — R1·R2 수렴 + ★운영자 챌린지(결측 해결) 대응. Slice 0(선결)/1(배선)/2(미빌드+결측 채움)/3(진짜 잔여). 결측 해결 상세=08.

> **델타 선언**: 기존 `project_edgar_dart_parity`(✅ 완료, commit 27337605d)가 **L1 라이브러리(compare·scan router·panel native 메커니즘)·SKILL EXEMPT 분류**를 이미 실행. 본 PRD의 *진짜 신규* = **L2~L5 프론트 시장배선 + L0 보조축 빌드 + Slice0 선결**. L0/L1은 *점검·정정*이지 재구현 아님.
> **슬라이스 원칙**: Slice 0 = 선결 데이터(backfill·tickers, 배선 코드와 병렬). Slice 1 = *이미 baked + 미러된* panel/finance/scan-**finance**를 L2~L4 배선. Slice 2 = 미빌드(가격·scan 라이브축 baking)를 빌드 후 배선("빌드부터 아래로"가 슬라이스2 안에서 성립).

---

# Slice 0 — 선결 데이터 ([정정] 배선 코드와 *병렬*)

[정정] Slice 1을 "데이터 무작업"이라 부르려면 데이터 작업 2건을 앞으로 분리해야 정직(R2 P0 확정). 둘은 KR 경로로 짜는 배선 골격(S1-L2/L3)과 **병렬** — 최종 S1-L4 US 렌더 검증만 의존.

## S0.1 — panel backfill (로컬 resumable rebuild) [정정]
- **[확인] CI cron 아님** — `edgarRebuildContinue.yml`이 `f46a58931`로 *의도적 제거*되고 **운영자 로컬 머신 resumable rebuild** 전환(2026-06-10). ledger(`edgar/_rebuildState.json`) 배치 upload+재개.
- **현 상태 실측 1순위**: 로컬 전환 후 완료율 불명 → 진입 전 ledger done-set 실측.
- **게이트(정량)**: **S&P500 전체 + 비-S&P 대표 20종목(섹터 8분류 분산) `c.panel("is",freq="Y")` native ≠ ∅**. placeholder 금지.

## S0.2 — edgar/tickers HF publish [정정 신설]
- **무엇**: [확인] ticker↔CIK 매핑(`edgar/tickers`)이 **DATA_RELEASES 미등록**(panel/finance/scan/meta/sections/docs만) → 퍼블릭 브라우저 AAPL→cik 해소 불가. 이중키(finance=cik·panel=ticker) 필수.
- **영향**: `dataConfig.py` DATA_RELEASES `edgar/tickers` 등록 + HF publish + edgarSync step.
- **게이트**: 퍼블릭 셸 `:8400` 없이 ticker↔CIK range-fetch.

---

# Slice 1 — 배선 우선 (Slice0 위, AAPL을 터미널에 KR과 같은 화면으로)

[정정] 대상 = **panel · finance · scan-finance(baked 1종) · search**. ⚠ **scan 라이브 13축은 Slice 1 아님** — [확인] `_edgarDispatch`는 ThreadPoolExecutor 로컬 glob(Python 전용), 퍼블릭 브라우저 실행경로 0(ui `edgar/scan` 소비자 0). 라이브축은 S2 baking 후. 가격=비활성, EXEMPT=정직 빈, **회색지대 4엔진=경고/비활성(S1-L4.3)**.

## S1-L2 — 계약/런타임 시장 차원 (resolveMarket 재설계 포함)
- **S1-L2.1 resolveMarket (priority-비대칭 + 이중키, 1순위)**: [확인] 라이브러리는 식별자 모양이 아니라 provider priority 분기(`edgar/company.py:616` 6자리도 True). 순수 식별자 함수 금지. 규칙: **① 명시 market override 1순위 ② 자동판정: 6자리 숫자→KR, 영문 ticker 1-5자→US, 숫자 CIK→명시 필수**. [정정] 반환은 `'KR'|'US'`가 아니라 **`{market, cik?, ticker?}`** — finance=cik·panel=ticker 이중키라 market만으론 경로 조립 불가. 라우팅 *계약*을 L1 SSOT(상수/codegen) import해 drift 차단.
- **S1-L2.2 식별자 매핑(Slice0 산출 소비)**: S0.2 publish된 `edgar/tickers`를 프론트가 읽어 code/ticker→cik 해소. 단위테스트 "AAPL→{us, cik:0000320193, ticker:AAPL}".
- **S1-L2.3 6포트 market 차원**: `contracts/{company,price,finance,filing,scan,report}.ts`에 `market?:'KR'|'US'`(기본 KR). indexPort/macro 패턴. filing은 rceptNo↔accessionNo `dart:`/`edgar:` prefix.
- **S1-L2.4 marketDefault 스위처**: `runtime.ts` 값 토글 + runtimeContext 시장 상태.
- **게이트**: tsc/svelte-check 0. resolveMarket 단위 테스트(005930→KR, AAPL→US, 320193 CIK→명시필요).

## S1-L3 — 소스 분기 (감사 밖 영역 포함)
- **S1-L3.1**: `adapters/public/sources/{finance,company}Source.ts` + **[정정] 감사 밖**: `surfaces/src/scan/{duckSql,tableSources,universe/load}.ts`(registerHfParquet 경로)·`landing/src/lib/browser/*`·`runtime/data/finance/annual.ts`·viewer 백엔드 `/api panel` 라우트까지 market 분기. origins registry **무변경**(둘 다 hf/hfRange). 식별자는 경로뿐 아니라 code→cik/ticker 변환 동반.
- **S1-L3.2 EXEMPT/미지원 = throw(notWiredYet) 관례 정합**: [확인] 기존 미배선 관례 = `createPublicRuntime.ts` `notWiredYet()` throw. US 가격/EXEMPT는 신규 null이 아니라 *기존 throw 관례 재사용* + surface가 잡아 정직 라벨. ReportPort는 13메서드 대부분 EXEMPT → "US 전체 EXEMPT 포트"로 분류(market 추가 형식적).
- **게이트**: US finance/panel/scan-재무축 baked 읽음. `checkUiDataWiring.mjs` 위반 0(상대경로 `edgar/...`는 URL 아님→미트리거 [확인]).

## S1-L4 — 서피스 시장 인지 + EXEMPT 정직
- **S1-L4.1**: terminal/viewer/scan이 US 종목에서 panel/finance/scan-finance 렌더. 식별자(ticker/CIK)·통화(USD)·회계연도. **호출부 전수 market 전달** — [정정] `code`만 넘기는 콜사이트 **~40건(10파일: RightStack 15·CenterStack 11·PriceChart 5·FinFullscreen 3 등)**. duckSql의 `registerHfParquet` 14지점은 "분기"가 아니라 KRX 원어컬럼·`ISU_CD='A'+code` 의존이라 **US 평행 빌더** 규모.
- **S1-L4.2 EXEMPT 정직 카운트**: US 진입 시 비활성 패널(가격·industry·sector·rank·network·report17)을 *숨기거나 "미국 시장 미제공(데이터 부재)"* + **빈 항목 수 명시 노출**(positive 게이트). 가짜 채움·KR 데이터 오염 0.
- **★S1-L4.3 회색지대 4엔진 게이트 (R2 P0 — 정직 경계 핵심)**: [확인] analysis/credit/quant/story는 EXEMPT(비활성)도 정상도 아닌 *회색지대* — 호출은 되나 계산이 KR 가정. 특히 **credit은 침묵 오염**: `creditCompany(EdgarCompany)` market 가드 0 → `sectorThresholds.py:85` `sector is None→_defaultThresholds()`(KR) → US 숫자에 KR 임계 먹여 **non-None 가짜 등급**(`_revenueSelect.py:110`의 정직 None과 비대칭). **Slice 1 게이트**: US에서 이 4엔진은 (a) `market!="KR"→return None`/EXEMPT 가드 추가 **or** (b) "계산 미검증·KR기준" 경고 배지 강제. EXEMPT 카운트와 별개 **"계산 미정합" 제3 정직 분류**로 화면 노출. credit 가드는 *필수*(현재 활성 회귀).
- **게이트**: 검증 유니버스 = **S&P500 + 대표 20종목(섹터 8분류)** panel→finance→scan 렌더 스크린샷 + EXEMPT 빈 패널 + 회색지대 배지 정직 표면. svelte-check 0. KR 무회귀(눈검수).

## S1-L5 — 제품 스위처 (Slice 1 출하)
- landing + ui/apps/local 시장 스위처(또는 식별자 자동판정). US도 퍼블릭(`:8400` 없이) floor. **UI push=운영자 명시 승인**.
- **Slice 1 완료 = 사용자가 AAPL을 터미널/뷰어/스캔에서 KR과 같은 화면으로(가격·EXEMPT는 정직 빈).**

---

# Slice 2 — 미빌드 완성 (빌드부터 아래로) + 배선

## S2-L0 — 빌드 (가장 무거운 결정들)
- **S2-L0.1 scan baking 모델 통일 결정 (P0)**: [확인] KR=baked parquet, EDGAR=라이브 dispatch(11 XBRL축 + **account/ratio 2축도 라이브**, `router.py:325-332`). 퍼블릭 HF 직독 floor를 위해 **EDGAR 13 라이브축 + changes/docsIndex/(shares)를 baked로** 빌드할지 결정. 결정이 S2-L1 dispatch 코드 변경 범위(라이브→parquet read)를 정함.
- **S2-L0.2 scan 보조축 빌드**:
  - `docsIndex`: [정정 강화] `buildEdgarDocsIndex` 함수는 존재하나 **EDGAR 비기능** — `buildDocsIndex`가 `panelTextRows(code)`를 `marketNs="kr"` 고정 호출(`kr/docs/index.py`)이라 `dart/panel`만 읽음. 진짜 작업 = **marketNs/source-extractor 파라미터 주입 + sections nested layout(`{ticker}/{period}`) 대응 + edgarSync step + deployEdgarToHF cats 추가**(1줄 "재배선" 아닌 4-함수 변경). `edgarScan` public 전환 + memory budget·job 분리(180분 timeout).
  - `changes`: panel contentRaw 입력 가능하나 10-K item 경계 비교단위 정의 = 개념검증 선행.
  - `sharesOutstanding`: [정정] 부분 EXEMPT — US는 발행주식수 1값(+shares_basic/diluted)까지, KR 17-col 분해 불가. 해당 분해축 EXEMPT 명시.
- **S2-L0.3 US 가격 baked (라이선스 선결, 최난도)**: KR `gov/prices` 동형 `edgar/prices`. 소스 라이선스 실조사(yfinance ToS 재배포 회색·stooq EOD 가능·기타) 표로 박기. **불가 시 Slice 1의 가격 비활성(옵션 C) 영구 유지**.
- **게이트**: 결정된 scan 산출물 baked + (가능 시) `edgar/prices`. backfill 완주.

## S2-L0.4 — ★결측 데이터 채우기 (08 상세, 운영자 챌린지 대응)
v0.3가 "EXEMPT"로 퉁친 데이터 대부분이 *채울 수 있음*(코드검증, 08). Slice2 빌드 편입:
- **report 14 apiType cross-sectional bake**: [확인] `reportAccessor._SUPPORTED` 14 추출기(dividend/treasury/employee/audit/executive/majorHolder/...) 이미 작동 → 전종목 aggregate해 `edgar/scan/report/*` bake(데이터 있음, build 작업). KR 17 중 14 커버.
- **SIC→US sector crosswalk**: [확인] `datasetBulk.py:75` SIC 존재 → 공개 SIC 분류 기반 자체 sector(GICS 아님, 정직 라벨) → rank=peer 백분위(scan 재사용).
- **sharesOutstanding XBRL 확장**: [확인] `capitalChange.py`/`majorHolder.py`가 issued/outstanding/treasury 파싱 → authorized/preferred 추가해 ~6col 복원(1값 아님).
- **신규 파서(B)**: relatedPartyTx(10-K Item13/ASC850, sections 재사용)·auditContract(DEF 14A fees).

## S2-L1 — scan 보조축 dispatch + 계산정합 트랙
- **S2-L1.1**: S2-L0 산출 parquet을 scan이 읽도록. [확인] 현 `_edgarDispatch`는 라이브 계산이라, baked로 가면 `scanClass`(market 진입점) + `_EDGAR_XBRL_AXES` 확장 + builder 3곳 동시 수정.
- **S2-L1.2 계산정합 census (별도 트랙, Slice1 가드는 S1-L4.3에서 선제)**: [확인] analysis/credit/quant/story가 KR 계정명·WICS 임계·KR industry 호출에 의존. credit=US sector(S2-L0.4) 확정 후 `_usDefaultThresholds()` 재캘리브. analysis/story는 (a) US-GAAP 경로 or (b) 정직 "US 미지원". **주의**: [확인] `_DART_ONLY` allowlist에 analysis/story/credit/industry/search 포함 → 비대칭 게이트 사각지대 → 별도 oracle(US fixture sanity) 필요.

## S2-L2~L5 — 가격/보조축 배선
- 가격 source 분기(US baked or 비활성 유지)·scan 보조축/report surface·검증 유니버스 확장. Slice 1 배선 재사용.

---

# Slice 3 — 진짜 잔여 (구조적 부분·라이선스, 최후순위·정직 한계)

08 분류 C/D — *채울 수 있는 건 Slice2서 다 채운 뒤* 남는 소수. "정직하게 빈다"가 진짜 적용되는 곳.
- **network US-native**: Exhibit 21(자회사)·SC 13D/G·13F·Form 4 파서 → 자회사+보유자 그래프. **재벌 계열 아님**(US-native 라벨).
- **industry 가치사슬 엣지**: 분류(SIC)는 Slice2 완료. *공급망 엣지*는 10-K major-customer(ASC 280) 공시 텍스트 파싱=저커버리지 **부분 그래프**(커버리지 라벨) or 비활성. 합성 금지.
- **executivePay 전임원**: NEO5(DEF 14A)까지만, KR 전임원 불가 → "NEO5" 라벨.
- **US 가격 baked**: 재배포 라이선스 소스 확보 시 `edgar/prices`, 불가 시 영구 비활성(옵션 C). 라이선스 실조사가 게이트.

---

## 라이브러리 비대칭 가드 (양 슬라이스 가로지름)
- **[정정] 신설 아님**: `tests/audit/providerSymmetry.py` + baseline 원장 **이미 운영**(P-PR6/7/8 트랙, P-PR8 종료=strict 0). 본 PRD 작업 = baseline missing 5건을 줄이거나(파서 구현) *명시 유지*. EXEMPT allowlist SSOT = 코드 상수 `_DART_ONLY`(SKILL 파싱 폐기). **3-provider(dart/edgar/edinet)** 인지 — 2-provider 재설계 금지.
- executivePay(US=DEF 14A NEO5, 10-K item11 아님)·relatedPartyTx(10-K notes ASC850)·notesDetail·flow·simulate = 데이터대기 or 범위밖. EXEMPT 2태그(permanent/dataWaiting).

## 의존·순서 ([정정] Slice0 병렬)
- **Slice0(데이터) ∥ S1-L2/L3(배선 코드)**: backfill·tickers publish는 KR 경로로 짜는 계약/소스 골격과 **병렬**. 최종 **S1-L4 US 렌더 검증만 Slice0 완주에 의존**(이게 "배선 우선"의 장점 — 외부의존 없이 코드부터 끝냄).
- **L2 ∥ L1**: 계약은 데이터 무관이나 resolveMarket이 L1 *라우팅 계약*에 의존 → "데이터 무관 병렬, 계약 의존". 계약 SSOT import로 drift 차단.
- **롤백**: market 기본 KR — 역순 비활성으로 KR-only 복귀. Slice0/S2 HF parquet 빌드는 추가일 뿐(KR 무영향).
