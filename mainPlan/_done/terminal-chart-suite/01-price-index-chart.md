# 01. Price/Index Chart — 주가/지수 차트 (KR gov OHLCV subject + US FRED 종가 라인 subject + picker + CMP)

> **참조 규약(분리 후):** 본 문서는 `mainPlan/terminal-chart-suite/`(현재/과거 차트 suite)에 속한다. suite 내부 = 01(차트)/02(레일)/03(백테스팅). **시뮬 PRD 참조(05 Play·07 통합로드맵·08 valuation·09 정합화 등 바 번호)는 `../scenario-simulator/NN`을 가리킨다**(단방향: suite ⟶ 시뮬, 역참조 없음).

상태: PRD v0.4 (US=FRED 종가 라인 subject 통합 — 운영자 결정 '미국 지수는 FRED 고려' 반영 + 로컬 FRED 데이터 실측·적대검증 정정, 2026-06-13). **2026-06-14 현재기준 코드 재검증** — A~I 9개 claim 전부 TRUE 확인(IndexPort/govIndexSource/fredIndexSource 신규 확정·3어댑터 conformance 유효), CenterStack 데이터 effect 라인범위만 L43-59 soft-swap 으로 정정(아래 §0 ⚠). 본 PRD 는 공통배선(포트/어댑터) 이후 기준에 이미 정합 — suite 의 로컬/퍼블릭 공동배선 *예시 문서*다(§3.5 IndexPort 3어댑터).
범위: 메인 주가차트에 KR gov 지수(OHLCV 캔들) + US FRED 지수(종가 라인)를 subject로 그리는 기능.
       배치·IndexPort 계약·subject-swap 배선 seam·render 모드 격리·종가전용 지표 매트릭스·시뮬레이터 관계.
UI 토폴로지: `ui/packages/surfaces/src/terminal/`, 포트=`ui/packages/contracts`, 데이터 소스=`ui/packages/runtime/src/adapters/{public,local,test}/`.

---

## 0. 결론 (배치 단일 결정 — 코드 재검증)

**안3(center Panel 헤더 segmented toggle '주가/지수') + 안4(picker: 큐레이트 preset + 검색) + CMP(벤치마크 rebase). PriceChart는 단일 인스턴스로 유지하고 subject만 soft-swap(둘째 차트 0).**

soft-swap의 PriceChart측 재적용 메커니즘은 **실재 확증**됨 — `PriceChart.svelte` L319-346 데이터 effect가 candles/code props에 키잉해 `reapply()`·`exitReplaySilently()`·bandIds/eventIds/refIds 제거·`drawMap.clear()`·`restoreDraws(code)`·`clearCompares()`를 **회사 전환과 동형**으로 수행. props만 지수로 바꾸면 새 차트 인스턴스 0. subject 소유권·CenterStack 라우팅 seam은 §2.5 정공법으로 확정(CenterStack-local `$state`, ctl 미상향).

> **US 지수(S&P500·NASDAQ·다우·VIX)는 FRED 종가 라인 subject로 06 범위 내 통합**(v0.3 §6.1 'US 범위 밖' 정정 — 운영자 결정 '미국 지수는 FRED 고려'). KR=OHLCV 캔들, US=종가(value) 1컬럼 라인. 둘 다 `IndexPort.series()→Candle[]` 단일 계약, `IndexRef.market` 분기. **새 차트·새 포트 0** — US는 `candleStyle='area'` 모드 + degenerate candle(o=h=l=c=value, v=0) 변환 1함수.

> **⚠ 선행 의존 순서(필수)**: 본 v0.4는 v0.3의 KR subject 본체(PriceChart `subject` prop·CenterStack subject/indexRef `$state`·picker·데이터 effect 분기·IndexPort KR 경로)가 **선행 구현된 위에 US 델타를 얹는다**. 현 코드 실측(2026-06-14 재검증): `PriceChart.svelte` Props(L28-40)에 `subject`/`indexLine` 없음, `CenterStack.svelte` 데이터 effect(**L43-59**)는 `co.code` 단일 키로 `rt.price.initial(code, yr)` 를 soft-swap(candles/chartCode/chartName/candleState 원자적 갱신) 호출 — subject/indexRef/picker state 부재·PriceChart 하향 전무. ⟹ v0.4를 독립 착수하면 컴파일 실패. 구현 순서 = v0.3 KR subject → v0.4 US 델타.

---

## 1. 세 가지 역할 분리 (결정의 핵심 — 유지)

- **(a) 독립 차트(subject)**: KOSPI/SP500 자체가 주체 — 자체 y축(포인트), 자체 기간/봉주기, 지수값 위 지표 계산. KR=full OHLC 캔들, US=종가 라인. → PriceChart `subject` 모드.
- **(b) 주가 위 오버레이(benchmark)**: "삼성 vs KOSPI" rebase 비교. → **CMP**(compareOverlay, 이미 존재). 지수=벤치마크 라인. (cross-market US 벤치마크는 §5.1 후속 별트랙.)
- **(c) 보조지표 계산 대상**: 역할a에서만 의미. → subject여야 실현. **단 US 종가전용은 고저 부재로 일부 지표 degenerate(§4.2).**

"지표 계산 ⟹ 지수가 candle series ⟹ 역할a." 이 축이 4안의 모호함을 가른다.

---

## 2. 배치 4안 — 코드 구조 근거 재검증

(v0.3 §2 본체 불변 — 안3 center Panel 헤더 toggle 채택, 안4 picker 채택.)

| 안 | 판정 | 코드 근거 |
|---|---|---|
| 안1 (차트 우측 프리셋+검색) | 기각 | 우측 스택=테이블·텍스트 region rule. 지표 계산 차트는 center 소관. |
| 안2 (좌측 '지수보기'→다이얼로그) | 기각 | 다이얼로그는 PriceChart 인스턴스·fullscreen·drawStore·BT·지표 stack 재사용 불가 = 둘째 lesser 차트. |
| 안3 (center Panel 헤더 toggle) | **채택** | `CenterStack.svelte` PRICE CHART Panel `{#snippet right()}`에 segmented toggle 추가. 유일하게 역할c 실현. |
| 안4 (gov 지수 전체 검색) | **채택(picker)** | 데이터 접근 전략. ChartMenus 화이트리스트 + jump-palette 검색 재사용. |

## 2.5 subject 소유권 + 배선 seam (★정공법 확정 — v0.3 §2.5 불변)

`ChartCtl`은 PriceChart 내부 생성·setContext 0건이라 CenterStack-local `$state`로 subject/indexRef 소유, 데이터 effect subject 분기, PriceChart에 `subject` prop 하향. ctl 끌어올리지 않음(PriceChart 다수 effect가 ctl 수명 안정성 의존). v0.4는 이 위에 `indexLine` derived 하향만 추가(§3.6).

---

## 3. IndexPort 계약 정밀 (v0.4 — KR+US 통합)

`contracts/src/indexPort.ts` 갱신. `IndexRef.market`을 KR 3값 + 'US'로 확장:

```typescript
// contracts/src/indexPort.ts
import type { Candle } from './price';

/** 'US' = FRED markets 그룹(종가 전용). KR 3종 = gov/indices(OHLCV 완전체). */
export type IndexMarket = 'KOSPI' | 'KOSDAQ' | 'KRX' | 'US';

export interface IndexRef {
  market: IndexMarket;
  name: string;     // KR=IDX_NM 원어('코스피 200') · US=한글 라벨('S&P 500')
  code: string;     // subject 식별자 = `idx:${market}/${seriesKey}`
                    //   KR seriesKey=IDX_NM · US seriesKey=FRED seriesId(SP500 등)
  /** US 전용 — FRED 시리즈 ID(SP500/NASDAQCOM/DJIA/VIXCLS). KR은 undefined. */
  seriesId?: string;
  /** 렌더 힌트 — series()가 채움. 'candle'=OHLCV(KR) · 'line'=종가전용(US). */
  ohlc?: 'candle' | 'line';
}

export interface IndexPort {
  /** 큐레이트 화이트리스트(상시 노출). KR 5종 + US 4종 = 9종. 전체 dump 아님. */
  catalog(): Promise<IndexRef[]>;
  /** 부분일치 검색. KR=gov IDX_NM universe 스캔 · US=US_INDEX_PRESETS 라벨/ID 매칭(확장 0). */
  search(query: string, limit?: number): Promise<IndexRef[]>;
  /** 일별 시계열 — 구조적 Candle 오름차순. KR=OHLCV · US=종가(o=h=l=c=value,v=0). null=미존재. */
  series(ref: IndexRef): Promise<Candle[] | null>;
}
```

### 3.0 ★구현 정정 (2026-06-15 데이터레이어 구현 + 실측 — 본 절이 §3.1/§3.2/§3.5 KR 경로 SSOT)

데이터레이어 구현(contracts `indexPort.ts` + runtime `fred/gov/indexSource.ts` + 3어댑터 + ui/web bridge, contracts·runtime **tsc GREEN**, 적대 리뷰 통과) 중 KR gov 지수 데이터 파이프라인 실측으로 §3.1/§3.2 의 일부가 **무효 — 본 절로 정정**:

- **§3.1 "gov/indices/date/{YYYY}.parquet 직독, IDX_NM filter" = 폐기**: date/ 는 *전지수 횡단*(연 1.1MB, BAS_DD 우선 정렬)이라 한 지수 전이력 추출에 17 연도파일(~18MB) 다운로드 = 브라우저 비현실. 정공법 = **per-index `gov/indices/index/{key}.parquet`(전이력, 작음) ∪ date/ 최근 N년(daily-fresh tail) `mergeDedup`** — `govPriceSource`(회사파일+recent tail 병합) 동형. `key = indexKey(market, IDX_NM)` = `{market}-{안전이름}`(buildGovData.py `indexKey` 1:1, byte-identical 검증). raw 컬럼 `{t:BAS_DD,o:OPNPRC_IDX,h:HGPRC_IDX,l:LWPRC_IDX,c:CLSPRC_IDX,v:ACC_TRDVOL,r:FLUC_RT,tv:ACC_TRDVAL}` (실측 일치).
- **§3.2 "KR gov 지수는 카탈로그 자동수집이라 preset 1줄로 충분" = 부정확**: cron `dailyIndex` 는 date/(전지수)만 유지, **per-index `index/{key}` 는 자동 생성 안 됨**(`--index` 온디맨드). ⟹ KR 전이력은 per-index **seed 필요**(아래). preset 추가만으론 *date/ 최근 N년 fallback* 만 산다(전이력 없음).
- **v1 데이터 상태(현재)**: per-index seed 전엔 **date/ 최근 2년만 live**(`FALLBACK_YEARS=2`). 전이력 = per-index seed 후. US(FRED)는 즉시 전이력 live(observations.parquet 실재). KR 5 presets·MARKET_GROUP·IDX_NM 실측 정확 일치 확인.
- **per-index seed = follow-up(운영자 게이트, HF 토큰 필요)**: 기존 `buildGovData.py produceIndex(market, idxNm)` (`--index`) 가 date/→index/{key} 추출. 큐레이트 5종을 *가끔*(주간/수동) 재seed → 전이력. 매일 date/ fresh tail 이 seed 이후 갭을 메우므로 daily seed 불요(중복 HF read 회피). 운영자 1-command 편의 `--seed-curated`(produceΙndex 루프)는 후속 소추가.
- **§3.5 local = 정정**: "KR=null" 폐기 → **local 도 `createPublicIndexPort()` 전체 재사용**(gov/indices·FRED 둘 다 HF 브라우저 직독 = `publicPricePort`/`createHfMacroPort` 재사용과 동형, 백엔드 0). KR·US 둘 다 local 에서 동작. ui/web bridge 도 동일(`index: createPublicIndexPort()`).
- **fake** = `fakeIndex()` 결정론 fixture(코스피 OHLCV 3봉 + SP500 degenerate 3봉). **검증 보강**: scanGovIndexNames 빈-universe 캐시 poisoning 방지(성공 시만 캐시) + search 이중-limit KR 압착 방지(`limit - us.length`).

### 3.1 KR 경로 (v0.3 §3 불변 — ★단 데이터 읽기 경로는 §3.0 으로 정정)
`gov/indices/date/{YYYY}.parquet` 직독, OHLCV 완전체(`{t:BAS_DD, o:OPNPRC_IDX, h:HGPRC_IDX, l:LWPRC_IDX, c:CLSPRC_IDX, v:ACC_TRDVOL, r:FLUC_RT, tv:ACC_TRDVAL}`), `ohlc:'candle'`. filter `{IDX_NM=ref.name, MARKET_GROUP=ref.market}`. 검색=최신 1~2 parquet IDX_NM unique 스캔. drift 가드(`gov/indices/date`·`_CATEGORY="govIndices"` 정본, `krx/indices` 아님; benchmarkMap 빈-캐시 silent-true 폴백 우회). v0.3 그대로.

### 3.2 큐레이트 화이트리스트 (KR 5 + US 4 = 9)

```typescript
// contracts/src/indexPort.ts — KR(Python INDEX_ALIASES 1:1) + US(FRED markets 중 '지수'만)
export const KR_INDEX_PRESETS: IndexRef[] = [
  { market: 'KOSPI',  name: '코스피',      code: 'idx:KOSPI/코스피',     ohlc: 'candle' },
  { market: 'KOSPI',  name: '코스피 200',  code: 'idx:KOSPI/코스피 200', ohlc: 'candle' },
  { market: 'KOSDAQ', name: '코스닥',      code: 'idx:KOSDAQ/코스닥',    ohlc: 'candle' },
  { market: 'KOSDAQ', name: '코스닥 150',  code: 'idx:KOSDAQ/코스닥 150', ohlc: 'candle' },
  { market: 'KRX',    name: 'KRX 300',     code: 'idx:KRX/KRX 300',      ohlc: 'candle' }
];
// gather/fred/catalog.py markets 그룹 9종 중 '주가지수'(unit='Index')만 4종.
// DTWEXBGS(달러인덱스)·DCOILWTICO(WTI)·IR14270(금)·WILL5000IND·CBBTCUSD는
// 자산가격/환율이지 시장지수가 아니거나 §6.4 제외 — subject 부적합·picker 혼동 방지.
export const US_INDEX_PRESETS: IndexRef[] = [
  { market: 'US', name: 'S&P 500',    code: 'idx:US/SP500',     seriesId: 'SP500',     ohlc: 'line' },
  { market: 'US', name: 'NASDAQ 종합', code: 'idx:US/NASDAQCOM', seriesId: 'NASDAQCOM', ohlc: 'line' },
  { market: 'US', name: '다우존스',     code: 'idx:US/DJIA',      seriesId: 'DJIA',      ohlc: 'line' },
  { market: 'US', name: 'VIX(변동성)',  code: 'idx:US/VIXCLS',    seriesId: 'VIXCLS',    ohlc: 'line' }
];
export const INDEX_PRESETS: IndexRef[] = [...KR_INDEX_PRESETS, ...US_INDEX_PRESETS];
```

- **US 4종 선정 근거(코드 실측)**: `gather/fred/catalog.py` markets 그룹 9종 — 그중 주가지수 단위('Index')이며 '시장 지수'인 것만 4종. WILL5000IND는 §6.4 제외(assets.py 부채·시장전체 혼동), DTWEXBGS/DCOILWTICO/IR14270/CBBTCUSD는 자산가격·환율·암호화폐이지 시장지수가 아니라 비채택(`search()`로도 0건 — 있는 척 금지). 후속 운영자가 원자재 subject를 원하면 별 PRESET으로 확장(범위 분리).
- **VIX 라벨 명시**: VIXCLS는 가격이 아니라 변동성 지수(CBOE) → 라벨 'VIX(변동성)'로 가격 오인 차단(§6.3).
- **★US 지수 *증분*(데이터 추가 핵심 배선)**: 새 US 지수(예: Russell 2000/RUT)는 **2곳** 등록 — ① `US_INDEX_PRESETS`(contracts) 1줄 ② `gather/fred/catalog.py` markets 그룹 `CatalogEntry`. `buildFred`(`getAllEntries` 전수)가 parquet 에 넣어야 `loadSource('fred')` 우회(§3.3)가 꺼낼 수 있다 — 현 4종은 markets catalog 기존재라 즉시 라이브(§6.5)지만, **`US_INDEX_PRESETS` 1줄만 추가하면 catalog 부재로 빈 시리즈**(KR gov 지수는 gov 카탈로그 자동 수집이라 preset 1줄로 충분 — 비대칭 명시).

### 3.3 US 데이터 소스 — fredIndexSource (배선갭 정공 해소)

**문제(코드 실측)**: 브라우저 `MacroPort.getSeries(id)`는 `macroSource.ts` `defById = new Map(MACRO_SERIES)` 화이트리스트로 게이팅 — SP500 등은 MACRO_SERIES 10종 미수록이라 `def=undefined → null` 즉시 반환(`getSeries('SP500')=null` 확정). 즉 *MacroPort 경로로는 US 지수를 못 가져온다*. 반면 `loadSource('fred')`는 seriesId 필터 없이 parquet 전 행을 `bySeries`에 그룹화 — srcCache 공유로 SP500을 꺼내는 우회가 기술적으로 작동(적대검증 확증).

**3가지 길의 평가(정공 택1)**:
1. ❌ **MACRO_SERIES에 SP500 등 추가** — MACRO_SERIES는 ECON 오버레이 화이트리스트이자 KPI 티커 카탈로그. 지수를 넣으면 §5.2 'ECON에 지수 추가 금지'(self-normalize 스케일 오정렬)와 KPI 티커 오염이 동시 발생. **기각**.
2. ❌ **임의 FRED 시리즈 fetch 경로 신설(무게이팅)** — 'public-contract verb+인자만' + '큐레이트만 노출(raw dump 방지)' 규율 위배. **기각**.
3. ✅ **IndexPort 전용 소스 `fredIndexSource.ts` 신설** — MacroPort를 안 거치고 `macro/fred/observations.parquet`을 직독하되 `US_INDEX_PRESETS`의 seriesId 4종으로만 게이팅. MACRO_SERIES 불변. **채택**.

```typescript
// runtime/.../public/sources/fredIndexSource.ts (신설)
// US FRED 지수 = macro/fred/observations.parquet 직독(종가 value 1컬럼) → degenerate Candle.
// macroSource.ts 의 srcCache(loadSource('fred')) 재사용 — 파일 1회 로드 공유(중복 다운로드 0).
import type { Candle, IndexRef } from '@dartlab/ui-contracts';
import { US_INDEX_PRESETS } from '@dartlab/ui-contracts';
import { loadFredSeriesPoints } from './macroSource'; // srcCache 공유 내부함수 export

const US_BY_SERIES = new Map(US_INDEX_PRESETS.map((r) => [r.seriesId!, r]));

/** FRED 종가 시리즈 → degenerate Candle[]. o=h=l=c=value, v=0(거래량 부재 — 명시). null=미존재. */
export async function loadFredIndexCandles(ref: IndexRef): Promise<Candle[] | null> {
  const sid = ref.seriesId;
  if (!sid || !US_BY_SERIES.has(sid)) return null;  // 화이트리스트 게이팅(임의 fetch 차단)
  const pts = await loadFredSeriesPoints(sid);       // [{d:'YYYYMMDD', v:number}] 오름차순 or null
  if (!pts || !pts.length) return null;
  return pts.map((p) => ({ t: p.d, o: p.v, h: p.v, l: p.v, c: p.v, v: 0, r: null, tv: null }));
}
```

**macroSource.ts 보강(최소 표면 1개 export)**: `loadFredSeriesPoints`를 신설 export — `loadSource('fred')`(기존 srcCache 공유)에서 raw seriesId 그룹만 꺼내고 화이트리스트·yoy 변환을 *안 거친다*(지수는 yoy 무의미). MACRO_SERIES 게이팅은 `loadMacroSeries`에만 유지:

```typescript
// macroSource.ts 신설 export — loadSource srcCache 공유, MACRO_SERIES 게이팅 우회(IndexPort 전용 raw 채널).
export async function loadFredSeriesPoints(seriesId: string): Promise<MacroPoint[] | null> {
  if (!browser) return null;
  const bySeries = await loadSource('fred'); // 기존 srcCache 재사용 — fred 파일 1회 로드 공유
  const pts = bySeries.get(seriesId);
  return pts && pts.length ? pts : null;
}
```

> ⚠ 이 우회는 IndexPort 화이트리스트(US_INDEX_PRESETS 4종)가 `fredIndexSource`에서 *이미 게이팅*하므로 'raw dump 방지' 규율을 깨지 않는다. `loadFredSeriesPoints`는 IndexPort 전용 내부 채널이며 surface가 임의 ID로 직접 호출하지 않는다(public 표면=`rt.index.series(ref)`뿐). [열린 안: 운영자가 'macroSource는 ECON 전용 유지, fredIndexSource가 독립적으로 readParquetRows'를 선호하면 srcCache 공유 대신 소스 독립 — §7 OQ2.]

### 3.4 indexSource 라우팅 (KR/US 분기 — public 어댑터 조립부)

```typescript
// runtime/.../public/sources/indexSource.ts (신설) — KR(gov 직독) + US(fred) 라우팅
import type { Candle, IndexRef } from '@dartlab/ui-contracts';
import { KR_INDEX_PRESETS, US_INDEX_PRESETS } from '@dartlab/ui-contracts';
import { loadGovIndexCandles, scanGovIndexNames } from './govIndexSource'; // KR gov/indices(§3.1)
import { loadFredIndexCandles } from './fredIndexSource';                  // US fred(§3.3)

export function createPublicIndexPort() {
  return {
    async catalog(): Promise<IndexRef[]> {
      return [...KR_INDEX_PRESETS, ...US_INDEX_PRESETS]; // 화이트리스트 9종(상시)
    },
    async search(query: string, limit = 12): Promise<IndexRef[]> {
      const q = query.trim();
      if (!q) return [];
      const us = US_INDEX_PRESETS.filter((r) => r.name.includes(q) || r.seriesId!.toUpperCase().includes(q.toUpperCase()));
      const kr = await scanGovIndexNames(q, limit); // gov 최신 parquet IDX_NM unique 부분일치
      return [...us, ...kr].slice(0, limit);
    },
    series(ref: IndexRef): Promise<Candle[] | null> {
      return ref.market === 'US' ? loadFredIndexCandles(ref) : loadGovIndexCandles(ref); // 분기 단일 지점
    }
  };
}
```

### 3.5 required·3 어댑터 conformance (US 포함)

`DartLabRuntime`(`runtime.ts` L70-88, 모든 포트 required·optional 0)에 `index: IndexPort` 추가 → tsc structural typing이 3 어댑터 동시 구현 강제:
- **public** (`createPublicRuntime.ts` L150 macro 옆): `index: createPublicIndexPort()` **eager**. US/KR 둘 다 실구현.
- **local** (`createLocalRuntime.ts` L60 macro 옆): inline index. US는 `createHfMacroPort`처럼 HF 공개 데이터라 local 셸도 재사용 — `catalog`=화이트리스트 9종, `search`=US preset 필터, `series`=`ref.market==='US' ? loadFredIndexCandles(ref) : null`(KR=null, US=HF 직독 공유). 거시·지수는 회사/앱 무관 HF 데이터라는 macroSource 주석 패턴과 동형.
- **fake** (`createFakeRuntime.ts` L57 fakePrice 옆 + L408 조립): `fakeIndex()` fixture — 결정론(난수·Date.now 금지). KR 1종(코스피 OHLCV) + US 1종(SP500 o=h=l=c) fixture candle, 그 외 null. fakeMacro(L183) 결정론 패턴과 동형.

```typescript
// createFakeRuntime.ts — fakePrice 옆
function fakeIndex(): IndexPort {
  const krCandles: Candle[] = [ /* 결정론 OHLCV 3봉(코스피) */ ];
  const usCandles: Candle[] = [ /* 결정론 o=h=l=c 3봉(SP500) */ ];
  return {
    async catalog() { return [...KR_INDEX_PRESETS, ...US_INDEX_PRESETS]; },
    async search(q) { return INDEX_PRESETS.filter((r) => r.name.includes(q)); },
    async series(ref) {
      if (ref.code === 'idx:KOSPI/코스피') return krCandles;
      if (ref.code === 'idx:US/SP500') return usCandles;
      return null;
    }
  };
}
```

---

## 3.6 subject 렌더 모드 격리 (★candleStyle 전역 오염 차단 — (B)안 채택)

**위험(ground)**: `ctl.candleStyle`은 PriceChart-local `$state`이고 localStorage persist(chartState L147). US subject에서 `ctl.candleStyle='area'` 강제 시 (1)KR 복귀 때 candle 자동 복원 안 됨(swap은 candleStyle 미터치) + (2)persist가 'area'를 기억해 다음 세션 KR/종목 차트가 area로 시작하는 2차 오염.

**정공(B안 — render mode를 candleStyle과 분리)**: `ctl.candleStyle`은 *사용자 선택 영속값*으로 불변 유지, US 종가전용은 **PriceChart-local `effectiveCandleType` derived**로 강제. ctl 미터치 → 영속 오염 0. (chartState L15 `CandleStyle` union에 'area' 실재, L50 라벨='라인'/Line 확인.)

```svelte
<!-- PriceChart.svelte — Props 에 indexLine 추가(CenterStack 하향). subject 는 v0.3 §2.5 이미 하향. -->
let { candles, code, name, lang, subject = 'price', indexLine = false }: Props = $props();
//                                                       ↑ subject==='index' && ref.market==='US' → true

// 종가전용(US 지수) = 사용자 candleStyle 무시하고 'area' 강제. ctl.candleStyle 영속값 불변(2차 오염 0).
const effectiveCandleType = $derived(indexLine ? 'area' : kcCandleType(ctl.candleStyle));
```

themeStyles()의 `candle.type`(L148)와 candleStyle effect(L593-605)를 **둘 다** `effectiveCandleType`로 교체(한 곳 누락 시 깜빡임/오염 잔존). HA 재적용 가드(L600-604)는 `indexLine`이면 reapply 스킵(US에서 ha 전환 무의미 + degenerate candle 재변환 낭비).

- **CenterStack 하향**: 데이터 effect(§2.5)에서 `indexRef` 로드 시 `let indexLine = $derived(subject==='index' && indexRef?.market==='US')` → `<PriceChart ... {subject} {indexLine} />`.
- **CandleStyle 토글 UI(ChartMenus/Ribbon)**: US subject일 때 candleStyle 세그먼트 `disabled` + tooltip '종가 전용 — 라인 고정'. ctl 값은 그대로.
- **y축**: 포인트(지수값). US/KR 공통 `ctl.yMode`(normal/log/%). VIX는 %축 무의미하나 차단 안 함.

---

## 4. 보존/리셋 + 지표 호환 + BT graceful

**4.1 swap 시 보존/리셋 매트릭스** (v0.3 §4.1 불변 — 인스턴스 보존·period/tf/log축/지표 보존·drawMap 리셋·compares 리셋·BT 비활성. US subject도 동일.)

**4.2 보조지표 호환 매트릭스 (★subject별 3분기 — SubKey 실union 정합)**

PriceChart가 `subject`/`indexLine` prop으로 판단. SubKey 22종(`chartState.svelte.ts` L8: VOL·TVAL·MACD·RSI·KDJ·OBV·CCI·WR·DMI·MTM·ROC·TRIX·PSY·VR·BRAR·BIAS·CR·DMA·EMV·AO·PVT·AVP) + OverlayKey 8종(L10: MA·EMA·SMA·BOLL·BBI·SAR·ICHI·ENV)에 맞춰 3분기:

| 지표 | (1) 종목·KR지수 (OHLCV) | (2) US FRED (종가전용) | 사유 |
|---|---|---|---|
| MA·EMA·SMA·BOLL·BBI·ENV (overlay) | ✅ 정상 | ✅ 정상 | close만 사용 |
| RSI·MACD·TRIX·MTM·ROC·BIAS·PSY·DMA·VR (sub) | ✅ 정상 | ✅ 정상 | close 기반 |
| SAR (overlay) | ✅ 정상 | ✅ 정상(근사) | 고저 부재 시 close로 근사 |
| AO·CR (sub) | ✅ 정상 | ⛔ degenerate | **median (H+L)/2 기반** → o=h=l=c에서 flat. (close 전용 아님 — '정상'에서 이동) |
| KDJ(스토캐스틱)·CCI·WR (sub) | ✅ 정상 | ⛔ degenerate | 고저범위=0 → K=D=J=50·CCI=0·%R=0 constant |
| DMI(ADX) (sub) | ✅ 정상 | ⛔ degenerate | TR=0 → ADX=0 flat |
| BRAR (sub, momentum) | ✅ 정상 | ⛔ degenerate | 고저 기반 momentum (거래량군 아님 — 분류 정정) |
| ICHI(일목) (**overlay**) | ✅ 정상 | ⛔ degenerate | conv=base=close flat 5선. **OverlayKey라 overlay 분기 별도 처리**(SubKey Set 아님) |
| VOL·TVAL·OBV·PVT·EMV·VR·AVP (거래량 sub) | ⚠ hint(단위) | ⛔ 비활성 | KR=시장전체 거래량 hint / US=v=0이라 0막대 무의미 |
| VP(매물대) | ⛔ 비활성(전 지수 공통) | ⛔ 비활성 | 종목 호가 멘탈모델 전용(v0.3 §4.2) |

> ⚠ 분류 정정(적대검증 #4): (1) **ICHI는 OverlayKey**(L10)지 SubKey(L8) 아님 — `Set<SubKey>`에 넣으면 타입 불일치. overlay 분기 별도 처리. (2) **AO(Awesome Oscillator)·CR은 median price (H+L)/2 기반**이라 degenerate(flat)로 이동('정상' 아님). (3) **BRAR은 momentum(고저 기반)** — 거래량군이 아니라 momentum degenerate.

- **(2) US degenerate 처리**: chip **회색 + 비활성** + tooltip **'종가 전용 — 고가/저가 데이터가 없어 부정확'**. 클릭 무반응. klinecharts crash는 없으나 '있는 척' 방지 위해 *비활성 처리가 맞음*.
- **(1) KR 거래량지표 hint(차단 아님)**: VOL=ACC_TRDVOL·TVAL=ACC_TRDVAL='시장 전체 거래량'(종목 아님) — 값 계산되나 hint 텍스트로 단위 노출. KR 지수는 OHLCV 완전체라 KDJ/CCI/ATR 전부 정상(US와 결정적 차이).
- **degenerateSubs SSOT(PriceChart-local)**: `degenerateSubs = $derived(indexLine ? new Set<SubKey>(['KDJ','CCI','WR','DMI','BRAR','AO','CR','VOL','TVAL','OBV','PVT','EMV','VR','AVP']) : new Set())`. ICHI는 OverlayKey라 별도 `degenerateOverlays = indexLine ? new Set<OverlayKey>(['ICHI']) : new Set()`. ChartRibbon/Menus의 sub/overlay chip이 set 포함 시 회색+disabled+tooltip. 새 지표 분류 SSOT는 PriceChart-local(chartState에 안 올림 — 덕지덕지 방지).
- **★swap 시 이미 켜진 페인 능동 제거(적대검증 #5)**: PriceChart 페인 동기화(L488-490)는 want에 없는 키만 removeIndicator. US subject swap 시 `indexLine`이 want 집합에서 `degenerateSubs`를 **능동 배제**해야 함(chip disable만으론 부족 — 이미 켜진 VOL 페인이 v=0 빈 막대로 잔존). reapply/페인 effect에 `if (indexLine) want = want.filter((k) => !degenerateSubs.has(k))` 분기 추가 → degenerate sub 전부 removeIndicator. 미처리 시 '왜 거래량이 0인가' 회귀 혼동.

**4.3 BT graceful**: subject='index'(KR·US 공통)일 때 BacktestStrip preset `disabled` + 사유 칩("지수는 거래 대상 아님"). btKey 보존(복귀 시 종목 BT 복원). v0.3 불변.

**4.4 이벤트레일(02)·백테스팅 도크(03)**: subject 토글 무관. 지수 모드 공시 레일 자연히 빔(정상). v0.3 불변.

---

## 5. 거처·파일별 변경 집계·시퀀스 (v0.4 — US 델타 추가)

**새 패널·라우트·차트 인스턴스·verb 0.** US 통합 파일/변경:

| 파일 | 변경(v0.4 델타) |
|---|---|
| `contracts/src/indexPort.ts` (신설) | `IndexMarket`(US 포함)·`IndexRef`(seriesId/ohlc)·`IndexPort`·`KR_INDEX_PRESETS`·`US_INDEX_PRESETS`·`INDEX_PRESETS` |
| `contracts/src/index.ts` | indexPort re-export |
| `contracts/src/runtime.ts` L70-88 | `index: IndexPort` 추가(required) |
| `runtime/.../public/sources/govIndexSource.ts` (신설) | KR gov/indices/date 직독(govPriceSource 템플릿)·`scanGovIndexNames` |
| `runtime/.../public/sources/fredIndexSource.ts` (신설) | US FRED 종가→degenerate Candle(`loadFredIndexCandles`) |
| `runtime/.../public/sources/macroSource.ts` | `loadFredSeriesPoints` export 추가(srcCache 공유, MACRO_SERIES 게이팅 우회 — IndexPort 전용 raw 채널). **MACRO_SERIES·loadMacroSeries·createHfMacroPort 불변** |
| `runtime/.../public/sources/indexSource.ts` (신설) | `createPublicIndexPort`(KR/US 라우팅 단일 분기) |
| `runtime/.../public/createPublicRuntime.ts` L150 옆 | `index: createPublicIndexPort()` eager |
| `runtime/.../local/createLocalRuntime.ts` L60 옆 | inline index(US=HF 공유 동작, KR=null) |
| `runtime/.../test/createFakeRuntime.ts` L57·L408 | `fakeIndex()` fixture(KR+US 결정론) + 조립 |
| `surfaces/.../panels/CenterStack.svelte` | subject/indexRef local $state·데이터 effect 분기·toggle·picker(KR+US 9 preset + 검색)·`indexLine` derived·PriceChart에 `{subject} {indexLine}` 하향 |
| `surfaces/.../charts/PriceChart.svelte` | `subject`/`indexLine` prop·`effectiveCandleType` derived(candleStyle 격리)·degenerateSubs/degenerateOverlays 매트릭스·swap 시 degenerate 페인 removeIndicator·BT/VP graceful |

**불변(US 통합이 절대 건드리지 않음)**:
- `MACRO_SERIES`(macro.ts) — ECON 화이트리스트, 지수 0 유지(§5.2).
- `econOverlay.ts` — ECON에 지수 주입 경로 신설 금지(self-normalize 스케일 오정렬).
- `assets.py` WILL5000PRFC(L295) — Python macro 부채, 06 무관(§6.4).

**5.1 CMP-지수 통합(선택, 별 트랙)**: `ctl.compares`는 `{code,name}[]`(chartState L97)이라 peer.code가 `idx:`여도 `rt.index.series(ref: IndexRef)`가 요구하는 IndexRef(market+name+seriesId)를 **code 문자열에서 복원 불가** — KR/US 공통 차단. compares를 IndexRef 동반 확장 or 별도 indexCompares 경로 분리 필요. ⟹ **CMP-지수는 06 핵심(subject)에서 분리해 후속 별 트랙**. ★US 지수를 KR 종목 벤치마크로 넣을 경우 **거래일 캘린더 미스매치가 KR보다 심각**(미국 영업일·공휴일이 KR과 완전 다름) — `compareOverlay.ts` L58 `if (a < 0) return`이 정렬 인덱스 음수 구간을 조용히 skip해 비교선이 사라질 수 있음. forward-fill 본주 캘린더 정렬 전처리(첫 공통봉 rebase 불연속 가드)가 **필수 선행**. 운영자가 US 벤치마크를 06 핵심으로 끌어올리면 이 전처리가 추가 작업(과소평가 금지).

**5.2 ECON 분리(코드 확인)**: `econOverlay.ts`는 가시범위 self-normalize, CMP는 첫 공통봉 rebase. rebase 지수를 self-normalize ECON에 섞으면 '확신 오정렬'. MACRO_SERIES 10종에 지수 0, econOverlay extendData에 지수 주입 경로 없음. **ECON에 지수 추가 금지.** US도 동일(MACRO_SERIES 불변).

**5.3 시퀀스(07)**: KR 지수 subject = 통합 시퀀스 1번. US 델타는 KR subject 선행 의존(§0 ⚠). IndexPort가 `DartLabRuntime`에 추가되므로 public/local/fake 3곳 동시 조립이 conformance 게이트(tsc shape + 첫 surface 테스트).

**5.4 시뮬레이터 연계 (v0.4 — US 동일)**: subject='index' & market='US'일 때 Play(05) 미래 재생 = 지수 자체 미래 투영(가정 경로). 거시 미래경로 예측 부재(01 §9)라 **가정 오버레이만**(fan band·점선·'가정 구간' 워터마크 + '[conf:30] 투자권유 아님'). KR 지수와 동일 — US라고 더 강한 주장 금지(오히려 미국 거시는 dartlab 예측 자산 더 빈약 → 가정 강조). 단일 path 강조 금지. subject-swap과 sim.play 직교 불변(sim=별 필드, subject=데이터 출처).

---

## 6. 한계 표기 가드 (v0.4 — US 정정 전면)

**6.1 (정정) US 지수 = FRED 종가 라인 subject — 06 범위 내**
v0.3 §6.1 'US 범위 밖·데이터 부재'를 폐기. 운영자 결정 '미국 지수는 FRED 고려'로 통합. **단 종가 전용 제약은 전면 명시**:
- FRED `/series/observations` API = `(date, value)` 2컬럼. **OHLC 없음**(`gather/fred/series.py` L113 실측). HF `macro/fred/observations.parquet` = `(seriesId, date, value)` 3컬럼(로컬 실측 확정).
- US subject = `Candle{o=h=l=c=value, v=0}` degenerate → `candleStyle='area'`(라인) 강제. 캔들·ATR·KDJ·CCI·WR·DMI·ICHI·AO·CR·VP 불가(§4.2). MA/RSI/MACD/BOLL 등 close-기반만 정상.

**6.2 (신설) US 화이트리스트 4종만 — 임의 FRED fetch 차단**
S&P500·NASDAQ종합·다우·VIX 4종(`US_INDEX_PRESETS`)만. `search()`도 이 4종 라벨/ID 매칭만(FRED universe 확장 0). 임의 시리즈 fetch 경로 없음(public-contract·raw dump 방지). 원자재(WTI/금/달러인덱스/BTC)는 시장지수 아니라 비채택 — 후속 별 PRESET 분리.

**6.3 (신설) VIX = 가격 아닌 변동성 지수**
VIXCLS는 CBOE 변동성 지수(공포지수)지 가격이 아님. 라벨 'VIX(변동성)'로 오인 차단. 다른 3종과 y축 단위(포인트) 다르나 subject 단일 표시라 무해. CMP에 VIX를 벤치마크로 넣으면 의미 왜곡(주가↔변동성 역상관) — 후속 CMP-지수 트랙에서 hint.

**6.4 (정정) WILL5000IND·WILL5000PRFC = 06 무관 Python 부채**
- `US_INDEX_PRESETS`는 WILL5000 미수록(시장 전체 지수라 혼동 + 아래 부채). 06 IndexPort 영향 0.
- `assets.py` L295가 폐기된 `WILL5000PRFC` fetch → `SeriesNotFoundError` 잠재(`catalog.py`는 `WILL5000IND`로 대체). **Python macro 엔진 부채**(Buffett Indicator), 06 Index Chart UI와 무관. **별 트랙 수정**(06 범위 밖).

**6.5 (정정 — 데이터 라이브 확정) HF FRED 지수 데이터 = 즉시 활성, 신선도만 cron**
v0.3·초안의 '운영자 cron publish 선행이 유일 선결·구현했는데 안 보일 위험'은 **거짓**. 로컬 `data/macro/fred/observations.parquet` 실측(2026-06-13) — **SP500 2609행(2016-06-13~2026-06-11)·NASDAQCOM 14440행(1971-02-05~2026-06-11)·DJIA 2609행(2016-06-13~2026-06-11)·VIXCLS 9508행(1990-01-02~2026-06-11) 4종 전부 publish 확인**. `buildMacroData.py buildFred`가 `getAllEntries()`(markets 그룹 포함) 전수 빌드하므로 publish는 조건부 미확정이 아니라 **구조적으로 보장**. ⟹ **데이터 라이브, 즉시 활성 가능**. cron은 신선도(daily, 06:30 KST 권장)만 담당.
- **데이터 한계 명시**: FRED SP500/DJIA는 rolling ~10년만 제공(실측 둘 다 2016-06-13 시작). 장기 이력은 NASDAQCOM(1971)·VIXCLS(1990)만. SP500/DJIA의 빈 좌측 팬(2016 이전 없음)은 정상 — 데이터 한계 고지(있는 척 금지). FRED API의 명목 시작일(SP500 1928 등)과 *실제 제공 범위*(rolling 10yr)는 다름.

**6.6 (신설) lazy-backfill 비대칭 — US도 동일**
PriceChart 좌측-팬 백필(`rt.price.older`)은 price 포트 하드코딩. US subject도 `code='idx:US/...'`라 `[]`·no-op. US `series()`도 전 이력 단발 로드(단일 seriesId라 가벼움) → 좌측 팬 추가 백필 없음. KR/US 공통. `indexSource` 주석 명시.

**6.7 (신설) 미래여백 0 — US subject 동일 적용**
`PriceChart` L188-189 `setOffsetRightDistance(0)`·`setMaxOffsetRightDistance(0)`는 인스턴스 단위라 subject-swap 무관하게 US subject에도 적용(EOD 미래 축 0). 05 §2 live 분기와 정합 — Play 미래 재생(§5.4)시에만 가정 구간 우측 확장.

**★운영자 확인(v0.4 — 1건, 데이터 아닌 표면 선호)**: `macroSource.ts`에 `loadFredSeriesPoints` export 추가가 srcCache 공유(중복 다운로드 0) vs `fredIndexSource`가 독립적으로 `readParquetRows`하는 소스 독립성 — 본 명세는 공유 우선. 운영자 선호 확인 가능(§7 OQ2). **그 외 US 통합 설계·데이터는 전부 확정**(데이터 라이브 실측).

---

## 7. 잔여 Open Questions (v0.4 갱신)

1. **(해소)** US 지수 — FRED 종가 라인 subject로 06 통합 확정 + **데이터 라이브 실측 확정**(§6.5). 잔여 선결 0(코드 구현만 남음).
2. **macroSource 우회 표면 선호** — `loadFredSeriesPoints` export(srcCache 공유) vs `fredIndexSource` 소스 독립 `readParquetRows`. 본 명세=공유 우선(중복 다운로드 0). 운영자 선호 확인 가능.
3. **CMP-지수 통합(KR+US 공통)** — `compares` 타입 IndexRef 동반 확장 vs 별도 indexCompares. US는 거래일 캘린더 미스매치가 KR보다 커 forward-fill 본주 정렬 전처리 **필수 선행**(§5.1). 후속 별트랙.
4. **subject 왕복 시 compares(VS) 리셋** — '리셋 유지' 정공(v0.3).
5. **US degenerate 지표 시각 검수** — §4.2는 비활성. 시각 검수 후 더 보수적 비활성 여지.
6. **(신설) US picker UX** — catalog 9종(KR 5 + US 4)을 한 드롭다운에 시장 헤더('한국'/'미국') 그룹핑 vs 별도 탭. search limit를 KR(gov universe 스캔)+US(preset 4종 고정) 사이에 어떻게 분배할지는 시각 검수 후 미세조정.
7. **(범위 밖) SP500 장기 이력** — FRED SP500/DJIA는 rolling ~10년만(2016~). 장기 이력이 제품 핵심 요구가 되면 별도 장기 소스(Shiller 등) 수집 필요 — 현 06 범위 밖.
