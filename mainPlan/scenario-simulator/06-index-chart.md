# 06. Index Chart — 지수 차트 (KR gov 지수 subject + picker + CMP 벤치마크)

상태: PRD v0.3 (코드 그라운드 전수 검증 + 적대검증 반영, 2026-06-13)
범위: 메인 주가차트에 KR 지수를 subject로 그리는 기능. 배치·IndexPort 계약·subject-swap 배선 seam·지표 호환·시뮬레이터 관계.
UI 토폴로지: `ui/packages/surfaces/src/terminal/`, 포트=`ui/packages/contracts`, 데이터 소스=`ui/packages/runtime/src/adapters/{public,local,test}/`.

---

## 0. 결론 (배치 단일 결정 — 코드 재검증 후 정정 불필요)

**안3(center Panel 헤더 segmented toggle '주가/지수') + 안4(picker: 큐레이트 preset + IDX_NM 검색) + CMP(벤치마크 rebase). PriceChart는 단일 인스턴스로 유지하고 subject만 soft-swap(둘째 차트 0).**

soft-swap의 PriceChart측 재적용 메커니즘은 **실재 확증**됨 — `PriceChart.svelte` L319-346 데이터 effect가 candles/code props에 키잉해 `reapply()`(applyNewData 단일지점)·`exitReplaySilently()`·bandIds/eventIds/refIds 제거·`drawMap.clear()`·`restoreDraws(code)`·`clearCompares()`를 **회사 전환과 동형**으로 수행. props만 지수로 바꾸면 새 차트 인스턴스 0이 맞다. **단 누가 subject를 소유하고 CenterStack이 어떻게 그것을 읽어 candles/code를 라우팅하는가(seam)는 §2.5 정공법으로 새로 확정**(현 v0.2 미설계 — 작성된 대로면 컴파일 불가였음).

---

## 1. 세 가지 역할 분리 (결정의 핵심 — 유지)

- **(a) 독립 차트(subject)**: KOSPI 자체가 주체 — full OHLC 캔들, 자체 y축(포인트), 자체 기간/봉주기/로그축, 지수값 위 지표 계산(RSI of KOSPI). → PriceChart `subject` 모드.
- **(b) 주가 위 오버레이(benchmark)**: "삼성 vs KOSPI" rebase 비교. → **CMP**(compareOverlay, 이미 존재). 지수=벤치마크 라인.
- **(c) 보조지표 계산 대상**: 역할a에서만 의미(klinecharts는 active candle pane에만 지표 stack). → subject여야 실현.

"지표 계산 ⟹ 지수가 candle series ⟹ 역할a." 이 축이 4안의 모호함을 가른다.

---

## 2. 배치 4안 — 코드 구조 근거 재검증

| 안 | 판정 | 코드 근거 |
|---|---|---|
| 안1 (차트 우측 프리셋+검색) | 기각 | 우측 스택=테이블·텍스트 region rule. 지표 계산 차트는 center 소관. 우측에 지수 차트를 놓으면 PriceChart 인스턴스 재사용 불가. |
| 안2 (좌측 '지수보기'→다이얼로그) | 기각 | 다이얼로그는 PriceChart(klinecharts) 인스턴스·fullscreen·`drawStore`·BT·지표 stack 재사용 불가 = 둘째 lesser 차트. `chartState.svelte.ts ChartCtl`이 한 인스턴스 SSOT라 분리 시 상태 중복. |
| 안3 (center Panel 헤더 toggle) | **채택** | `CenterStack.svelte` L300-301 PRICE CHART Panel이 이미 `{#snippet right()}`(EOD 뱃지)를 가짐 — segmented toggle을 여기 추가. 유일하게 역할c(지수 위 RSI/MA) 실현. |
| 안4 (gov 지수 전체 검색) | **채택(picker)** | 배치가 아닌 데이터 접근 전략. `ChartMenus.svelte` 화이트리스트 패턴 + jump-palette 검색 패턴 재사용. |

---

## 2.5 subject 소유권 + 배선 seam (★정공법 확정 — v0.2 미설계 결함 해소)

**문제(실측)**: `ChartCtl`은 `PriceChart.svelte` L44 `const ctl = new ChartCtl()`로 **컴포넌트 내부에서만** 생성되고, 자식(ChartMenus·ChartRibbon·BtConfig·DrawToolbar·IndParamEditor)에 `ctl` prop으로 **하향**만 전달된다. setContext/getContext 0건, CenterStack은 ctl을 전혀 모른다(grep 확증: `new ChartCtl` 1곳, ctl 공유 채널 0). candles/code/name props는 전부 `CenterStack.svelte` L304 한 곳에서 발원하고, 데이터 fetch effect도 CenterStack L37-53에 있다. ⟹ v0.2가 표기한 "CenterStack 데이터 effect에 `if (ctl.subject)` 분기"는 **ctl이 CenterStack 스코프에 없어 컴파일 불가**.

**정공법(택1 — (a) 채택)**:
- **subject 상태를 CenterStack-local `$state`로 소유** — ctl을 끌어올리지 않는다(PriceChart의 다수 effect가 ctl 수명 안정성에 의존 → 끌어올리면 비자명 리팩토링, 깎아서 강하게 원칙 위배).
  ```typescript
  // CenterStack.svelte (신규 — candles/chartCode/chartName 옆)
  let subject = $state<'price' | 'index'>('price'); // 세션 모드 (영속 제외)
  let indexRef = $state<IndexRef | null>(null);
  ```
- **데이터 effect(L37-53) subject 분기** — ctl 무관, CenterStack-local subject/indexRef만 읽음:
  ```typescript
  $effect(() => {
    let cancelled = false;
    if (subject === 'price') {              // 기존 경로 (L43)
      const code = co.code, nm = co.name.kr, yr = priceYear;
      candleState = 'loading';
      rt.price.initial(code, yr).then((r) => {
        if (cancelled) return;
        candles = r && r.candles.length ? r.candles : null;
        chartCode = code; chartName = nm;
        candleState = r && r.candles.length ? 'ready' : 'unavail';
      });
    } else if (indexRef) {                  // 신규 경로
      const ref = indexRef;
      candleState = 'loading';
      rt.index.series(ref).then((cs) => {
        if (cancelled) return;
        candles = cs && cs.length ? cs : null;
        chartCode = ref.code; chartName = ref.name;  // code = `idx:${market}/${name}`
        candleState = cs && cs.length ? 'ready' : 'unavail';
      });
    }
    return () => { cancelled = true; };
  });
  ```
- **PriceChart에 `subject` prop 하향** — graceful(§4: BT/VP/showRefs 비활성)에 필요. ChartCtl에는 **필드 추가 0**(v0.2의 "ChartCtl에 subject/indexRef 2필드 추가"는 폐기 — ctl이 안 흐르므로):
  ```svelte
  <PriceChart {candles} code={chartCode} name={chartName} {lang} subject={subject} .../>
  ```
  PriceChart는 `let { ..., subject = 'price' }: Props = $props();`로 받아 BacktestStrip `disabled={subject==='index'}`·VP 토글 비활성에 사용. ctl은 여전히 PriceChart-local.
- **toggle + picker UI** = CenterStack `{#snippet right()}`(L301)에 segmented `[주가|지수]` + 지수 선택 시 picker 드롭다운. picker는 ChartMenus jump-palette 패턴 복제(회사 suggest 대신 `rt.index.search(q)`).

**핵심**: subject-swap = candles/code props 교체 = 회사 전환과 동형. PriceChart L319-346이 그대로 reapply. `code=`idx:...`이므로 PriceChart 내부 `rt.price.older(hist.code)`/`loaded(hist.code)`는 `idx:` code로 `[]`·no-op 반환(무해, §6 참조).

---

## 3. IndexPort 계약 정밀 (신설 — PricePort 미러 아님)

v0.2의 `indexInitial/indexOlder/indexList`는 코드에 **없는 발명** — 폐기(실 PricePort = initial/older/loaded/govCandles/govRecent, `price.ts`). IndexPort는 더 얇은 신설 포트:

```typescript
// contracts/src/indexPort.ts (신설 — barrel index.ts 와 파일명 충돌 회피 위해 indexPort.ts. index.ts 는 re-export 만)
import type { Candle } from './price';
export interface IndexRef {
  market: string;   // 'KOSPI' | 'KOSDAQ' | 'KRX' (MARKET_GROUP)
  name: string;     // IDX_NM 원어 (예: '코스피 200')
  code: string;     // subject 식별자 = `idx:${market}/${name}` (drawStore KEY·hist.code 충돌 차단)
}
export interface IndexPort {
  /** 큐레이트 화이트리스트 (상시 노출 — 전체 dump 아님). */
  catalog(): Promise<IndexRef[]>;
  /** IDX_NM 부분일치 검색 (gov universe, 상위 limit). 빈 배열 = 해당 없음. */
  search(query: string, limit?: number): Promise<IndexRef[]>;
  /** 지수 일별 OHLCV — 구조적 Candle 오름차순. null = 미존재/미지원. */
  series(ref: IndexRef): Promise<Candle[] | null>;
}
```

- **반환 타입 = 기존 `Candle`** 재사용. gov 지수 raw → `{t:date(BAS_DD), o:OPNPRC_IDX, h:HGPRC_IDX, l:LWPRC_IDX, c:CLSPRC_IDX, v:ACC_TRDVOL, r:FLUC_RT, tv:ACC_TRDVAL}`. **OHLCV 완전체**(종가만 아님 — KR 지수는 normalizeGovIndexFrame 13컬럼).
- **required·silent fallback 금지**: `DartLabRuntime`(`runtime.ts` L70-88)에 `index: IndexPort` 추가. runtime.ts L66-69 주석("Port 메서드 전부 required — optional + 조용한 fallback 금지")이 강제. 3 어댑터 동시 조립(§5 conformance):
  - **public** (`createPublicRuntime.ts` L143-173, price/finance/macro/scan은 eager·map/search/ai 등은 `notWiredYet` throw 게이터): `index: publicIndexPort()` **eager** 조립. `indexSource.ts`가 `gov/indices/date/{YYYY}.parquet`를 `readParquetWholeFile`(hfRange)로 직독(govPriceSource.ts 템플릿). ⚠ tsc는 **shape만** 검사 — getter가 throw해도 컴파일 통과하므로 "tsc가 구현 존재를 강제"는 과장. **실구현 3종 제공이 전제**(컴파일 게이트 + 첫 surface 테스트가 런타임 fixture 대조).
  - **local** (`createLocalRuntime.ts` L43-76): 로컬 서버에 지수 API 부재 → `localFinancePort`(L35-41 `bundle()→null`) 동일 패턴으로 inline `index` 포트: `catalog`=화이트리스트, `search`=catalog 필터, `series`=`null`(미지원 정직).
  - **fake** (`createFakeRuntime.ts`): `fakeIndex()` fixture 함수(난수·현재시각 금지 결정론, fakePrice L57 패턴) 정의 + 런타임 조립 객체 L398-424에 `index: fakeIndex()` 추가. (v0.2가 fakeIndex를 "L398-424"라 한 건 *조립 블록* 위치 — fixture 함수 자체는 L57 fakePrice 옆.)
- **indexSource 직독**: columns `['BAS_DD','MARKET_GROUP','IDX_NM','OPNPRC_IDX','HGPRC_IDX','LWPRC_IDX','CLSPRC_IDX','ACC_TRDVOL','FLUC_RT','ACC_TRDVAL']`, filter `{IDX_NM=ref.name, MARKET_GROUP=ref.market}`. **검색은 최신 1~2 parquet의 IDX_NM unique 스캔**(`availableIndexNames` lru_cache 동등 패턴).
- **drift 가드(주석 명시)**: 경로는 `gov/indices/date/{YYYY}.parquet`(런타임 `_CATEGORY="govIndices"` 정본). `krx/indices`(docstring drift) 아님. **IndexPort는 parquet IDX_NM 실측만 신뢰** — Python `benchmarkMap.indexExists`의 빈-캐시 silent-true 폴백(L160-162 `if not names: return True`)을 **우회**(미존재 지수를 존재로 응답하는 거짓양성 차단).

**큐레이트 preset 화이트리스트(상시 노출 5종)** — Python `INDEX_ALIASES` distinct 5종과 1:1:
```
('KOSPI','코스피'), ('KOSPI','코스피 200'),
('KOSDAQ','코스닥'), ('KOSDAQ','코스닥 150'),
('KRX','KRX 300')
```
contracts에 `INDEX_PRESETS: IndexRef[]` 상수로 박제(MACRO_SERIES·BT_PRESETS 동일 위치 규율). **raw dump 방지**: `catalog()`=화이트리스트만, 나머지(SECTOR_INDEX_MAP의 KRX 반도체/헬스케어 등 ~30산업×~3지수 universe)는 `search(q)` 내부에서만 스캔. ESG/밸류업/배당/순수스타일은 gov 경로 미검출 → 검색해도 0건(있는 척 금지).

---

## 4. 보존/리셋 + 지표 호환 + BT graceful

**4.1 swap 시 보존/리셋 매트릭스**
| 자산 | swap 시 | 근거 |
|---|---|---|
| PriceChart 인스턴스 | **보존**(dispose 안 함) | L5 "인스턴스 영속". 깜빡임 0. |
| period/tf/log축/candleStyle/지표(overlays/subs/indParams)/fullscreen | **보존** | ChartCtl 필드 불변, swap이 안 건드림. 지수도 candle series → MA/RSI/MACD 그대로. |
| 드로잉(drawMap) | **리셋**(L336 clear+L339 restore) | code=`idx:...`라 지수별 독립 키 — stock 드로잉과 분리(정상). |
| compares(VS) | **리셋**(L340 clearCompares) | 지수 subject에서 종목 VS는 의미 약함(허용). ⚠ 종목→지수→종목 왕복마다 VS 리셋(UX 기대와 어긋날 수 있어 §6). |
| BT(btKey) | 보존하되 비활성 | 지수 거래 무의미 → §4.3. |

**4.2 지표 호환** (subject prop 하향으로 PriceChart가 판단)
- **호환(그대로)**: MA/EMA/SMA/BOLL/RSI/MACD/KDJ/CCI/WR/DMI/MTM/ROC/TRIX/BIAS/PSY/CR/AO/DMA — OHLC만 필요, 지수 OHLCV 완전체라 동작.
- **단위 주의(IDX_* 다름)**: VOL(ACC_TRDVOL)·TVAL(ACC_TRDVAL)·OBV/PVT 류 — 값은 계산되나 '종목 거래량'이 아닌 '시장 전체 거래량'. **차단 아닌 hint 텍스트로 단위 차이 노출**(정보 제공이 정직). 단 **매물대(VP)는 종목 호가 멘탈모델 전용 → 지수 subject에서 토글 비활성 + 사유**.
- **52주 기준선(showRefs)·적정주가밴드(valBand)·실적마커(events)**: 지수엔 무의미. swap 시 `priceEvents`/`priceValBand`가 회사 finBundle 기반(CenterStack L205-235)이라 지수 subject에선 미공급 → 자연히 빈값.

**4.3 BT graceful**: subject='index'일 때 BacktestStrip preset 선택을 `disabled={subject==='index'}` + 사유 칩("지수는 거래 대상 아님 — 백테스트 비활성"). btKey는 보존(swap 복귀 시 종목 BT 복원). 새 패널 0.

**4.4 이벤트레일(11)·백테스팅 도크(10)**: 같은 `.chartWrap` 하단, subject 토글 무관. 지수 모드에선 공시 레일이 자연히 빔(정상).

---

## 5. 거처·파일별 변경 집계·시퀀스

**새 패널·라우트·차트 인스턴스·verb 0.** 파일별 변경:

| 파일 | 변경 |
|---|---|
| `contracts/src/indexPort.ts` (신설) | `IndexRef`/`IndexPort`/`INDEX_PRESETS` 5종 |
| `contracts/src/runtime.ts` L70-88 | `index: IndexPort` 추가(required) |
| `contracts/src/index.ts` | indexPort re-export 추가 |
| `runtime/.../public/sources/indexSource.ts` (신설) | gov/indices/date 직독(govPriceSource 템플릿) |
| `runtime/.../public/createPublicRuntime.ts` L143 | `index: publicIndexPort()` eager 조립 |
| `runtime/.../local/createLocalRuntime.ts` L53 | inline `index`(series=null 정직, localFinancePort 패턴) |
| `runtime/.../test/createFakeRuntime.ts` L57 옆+L398 조립 | `fakeIndex()` fixture + 조립 객체 추가(conformance) |
| `surfaces/.../panels/CenterStack.svelte` L37-53, L301-304 | subject/indexRef local $state + 데이터 effect 분기 + Panel right() segmented toggle + picker + PriceChart에 subject prop 하향 |
| `surfaces/.../charts/PriceChart.svelte` | subject prop 수신 + BT/VP/showRefs graceful disabled. (CMP-지수는 §5.1 별도 — '1줄' 아님) |

**5.1 CMP-지수 통합(선택, 별 트랙)**: CMP peer 채움은 `PriceChart.svelte` L659 `rt.price.initial(p.code, yr)`다(v0.2가 적은 `govCandles` 오기). `ctl.compares`는 `{code,name}[]`(chartState L97)이라 peer.code가 `idx:`여도 `rt.index.series(ref: IndexRef)`가 요구하는 IndexRef(market+name 객체)를 **code 문자열에서 복원 불가** — v0.2의 "1줄 추가" 과소평가. KOSPI/KOSDAQ를 VS 벤치마크로 넣으려면 **compares를 IndexRef 동반으로 확장하거나 별도 indexCompares 경로 분리** 필요. 종목 peer와 지수 peer가 한 CMP에 공존 시 첫 공통봉 rebase 정합(거래일 캘린더 차이)은 검증 대상. ⟹ **CMP-지수는 06 핵심(subject)에서 분리해 후속 선택 작업**으로 격리.

**5.2 ECON 분리(코드 확인)**: `econOverlay.ts`는 가시범위 per-series min-max 자기정규화, CMP는 첫 공통봉 rebase. 둘은 의미가 다르므로 rebase 지수를 self-normalize ECON에 섞으면 '확신 오정렬'. MACRO_SERIES 10종(`macro.ts` L27-38)에 지수 0, econOverlay extendData에 지수 주입 경로 없음. **ECON에 지수 추가 금지.**

**5.3 시퀀스(07)**: 지수 subject = 통합 시퀀스 **1번**(독립·데이터 실재·즉시 가치, mainPlan 무관 선행 가능). 단 IndexPort가 `DartLabRuntime`에 추가되므로 **createPublicRuntime/createLocalRuntime/createFakeRuntime 3곳 동시 조립이 conformance 게이트(tsc shape + 첫 surface 테스트)** — 누락 시 컴파일 red. 시뮬은 지수를 투영 대상으로 흡수(시퀀스 4번, 05 의존).

**5.4 시뮬레이터 연계(05 §3-3)**: subject='index'일 때 Play(05) 미래 재생 = 지수 자체 미래 투영(가정 경로). 거시 미래경로 예측 부재(01 §9)라 **가정 오버레이만**(fan band·점선·"가정 구간" 워터마크 + "[conf:30] 투자권유 아님"). 단일 path 강조 금지. subject-swap과 sim.play는 직교(sim=별 필드, subject=데이터 출처).

---

## 6. 정직 가드 (적대검증 잔재 — 박제)

1. **US 지수(SP500/NASDAQ/DJIA/VIX)는 06 범위 밖 — 데이터 자체 부재**. grep 결과 `ui/packages` 전체에 SP500/NASDAQ/DJIA/VIXCLS/markets 참조 **0건**, MACRO_SERIES(10종)에 지수 0. 운영자 'snp 나스닥도 주가차트처럼' 요구는 subject·CMP·ECON 어느 경로로도 **현재 데이터가 없어 불가능**(있는 척 금지). US 지수 신규 소스 수집(FRED markets는 종가 1컬럼 → OHLC 부재로 subject 부적합, close-기반 MA/RSI만 가능)은 **별 트랙**으로 분리. → §운영자 확인 1건.
2. **WILL5000 = 06 비관련**. `ui/packages`에 WILL5000 참조 0건. catalog 등록 vs 폐기된 WILL5000PRFC 참조 error는 Python macro 엔진(gather/fred/catalog.py·macro/corporate/assets.py) 부채 — 06 Index Chart와 무관.
3. **indexExists 빈-캐시 silent-true 폴백**(benchmarkMap.py L160-162). IndexPort.catalog/search는 indexSource.ts parquet 직독이라 이 Python 경로를 안 거치지만, 어떤 검증 경로든 indexExists를 참조하면 미존재 지수를 존재로 응답하는 거짓양성이 샌다 — **IndexPort는 parquet IDX_NM 실측만 신뢰**(주석 명시).
4. **lazy-backfill 비대칭**: PriceChart 좌측-팬 백필(L233 `rt.price.older(hist.code)`, L271 `rt.price.loaded(hist.code)`)은 price 포트 하드코딩. 지수 subject에서 hist.code=`idx:...`라 `[]`·no-op. ⟹ **지수는 `series()` 단발 로드분(2010~ 전이력 한 번)만 표시, 좌측 팬 추가 백필 없음**. `series()`가 전 연도를 합쳐 반환(단일 IDX_NM이라 가볍다) → 백필 불필요. **회사 주가의 연도별 lazy와 다른 모델임을 indexSource 주석에 명시 필수**(미명시 시 "왜 지수는 팬해도 과거가 안 나오나" 회귀 혼동).
5. **gov OHLCV 완전체**: KR 지수는 OPNPRC/HGPRC/LWPRC/CLSPRC_IDX + ACC_TRDVOL/FLUC_RT/ACC_TRDVAL 13컬럼 — 종가만 아님. US와 달리 캔들·고저 기반 지표(ATR/KDJ) 전부 동작.

**★운영자 확인 1건**: US 지수(SP500/NASDAQ)는 현재 ui 데이터 소스에 **전무**하다(KR gov 지수만 OHLCV 완전체). (a) 별 트랙으로 US 지수 소스 수집 후 close-only 라인차트(고저 부재 → MA/RSI만, ATR/KDJ 불가)로 subject 추가할지, (b) 06은 KR gov 지수 subject로 확정하고 US는 데이터 확보 전까지 범위 밖으로 둘지? 어느 쪽이든 06 핵심(KR subject)은 불변.

---

## 7. 잔여 Open Questions (구현 시 확인)

1. **US 지수** — §6 운영자 확인 1건(위).
2. **CMP-지수 통합** — compares 타입을 IndexRef 동반 확장 vs 별도 indexCompares 경로 분리(§5.1). 06 핵심에서 분리된 후속 선택 작업.
3. **subject 왕복 시 compares(VS) 리셋**(L340)이 정직하나 UX 기대와 어긋날 수 있음 — '리셋 유지'가 정공법(이전 회사/지수 기준 비교 무의미). 1회 확인 권장.
4. **지수 거래량 지표(VOL/TVAL/OBV)** — 현 명세는 VP만 비활성·나머지는 hint로 단위 차이 노출. 시각 검수에서 혼란스러우면 더 보수적 비활성으로 좁힐 여지(검수 후 판단).
