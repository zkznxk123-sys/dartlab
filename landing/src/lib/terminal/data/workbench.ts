// 회사 데이터 작업대 (workbench) — 흩어진 온디맨드 로더를 단일 typed API 로 모은다.
//
// 목적:
//   1. 단일 진입점 — 패널마다 6+ 로더를 따로 import 하지 않고 workbench.* 하나로.
//   2. 병렬 prefetch — 회사 선택 즉시 price/finance/products/filings/changes 를 동시 워밍업
//      (패널 effect 가 실행될 땐 캐시가 이미 따뜻 → 멀티패널 첫 페인트 단축).
//   3. 데이터 소스 단일 교체 지점 — 특히 주가(KRX) 소스를 바꾸거나 게이트할 때 `price` 한 곳만 수정.
//   4. 메모리 경계 — 무거운 주가 캔들 캐시는 priceSeries 에서 LRU 상한(많은 회사 탐색 시 누수 방지).
//
// 점진 도입(big-bang 금지): 기존 로더를 걷어내지 않고 그대로 위임한다. 패널은 단계적으로
// 이 표면으로 이전하며, 이전 전에도 prefetch 가 같은 모듈 캐시를 덥혀 이득을 준다.
import { loadInitialOHLCV, loadOlderYear, loadedCandles, seedCandles, mergeDedup, KRX_MIN_YEAR, type Candle, type CompanyPrices } from './priceSeries';
import { loadTerminalFinance, type TerminalFinanceBundle } from './terminalFinance';
import { loadHfProductIndexMap, type ProductIndexItem } from '$lib/data/productIndexRuntime';
import { loadCompanyRelations, type CompanyRelations } from './relations';
import { loadCompanyRegularFilings, type RegularFiling } from '$lib/data/companyFilingsRuntime';
import { loadCompanyNonRegularFilings, type NonRegularFiling } from '$lib/data/companyNonRegularFilings';
import { loadLiveCompanyReportFacts, loadLiveCompanyChanges, type LiveCompanyReportFact } from '$lib/browser/companyLive';
import { loadGovCandles, loadGovRecent } from './govPrice';
import type { CompanyChange } from '$lib/scan/duckSql';

export type { Candle, TerminalFinanceBundle, ProductIndexItem, CompanyRelations, RegularFiling, NonRegularFiling, LiveCompanyReportFact, CompanyChange };

const REGULAR_LIMIT = 500;
const NONREGULAR_LIMIT = 200;
const CHANGES_LIMIT = 8;

// 마지막 본 종목 localStorage 키 (Terminal.svelte 복원 + 라우트 load 조기 prefetch 공용 SSOT)
export const LAST_SYM_KEY = 'dlTerm.lastSym';

// 주가 — 데이터 소스 단일 교체 지점. 정책 변경 시 이 세 함수만 바꾼다.
export const price = {
	minYear: KRX_MIN_YEAR,
	// 회사파일(전종목 주간 파생, 전체 이력) ∥ recent(최근 30거래일 전종목 슬림 1파일) 병렬 → 병합.
	// 회사파일이 주간 갱신이어도 recent tail 이 최신 거래일을 보장. 둘 다 미스(신규상장 직후)면
	// date/ 파티션 폴백. dev 미스는 /__gov 라이브 채움 경로가 govPrice 안에서 동작.
	initial: async (code: string, year: number): Promise<CompanyPrices | null> => {
		const [gov, recent] = await Promise.all([loadGovCandles(code), loadGovRecent()]);
		const tail = recent?.get(code.trim()) ?? [];
		if ((gov && gov.length) || tail.length) return seedCandles(code, mergeDedup(gov ?? [], tail));
		return loadInitialOHLCV(code, year);
	},
	older: (code: string, targetYear: number) => loadOlderYear(code, targetYear),
	loaded: (code: string) => loadedCandles(code)
};

// 공공데이터포털 회사별 단일 parquet 온디맨드 로더(차트 SSOT). 미스 시 /__gov 가 라이브 채움.
export const govPrice = (code: string) => loadGovCandles(code);

export const finance = (code: string): Promise<TerminalFinanceBundle | null> => loadTerminalFinance(code);

export async function products(code: string): Promise<ProductIndexItem | null> {
	const m = await loadHfProductIndexMap();
	return m?.get(code) ?? null;
}
export const productIndex = (): Promise<Map<string, ProductIndexItem> | null> => loadHfProductIndexMap();

export const relations = (code: string): Promise<CompanyRelations | null> => loadCompanyRelations(code);
export const regularFilings = (code: string): Promise<RegularFiling[]> => loadCompanyRegularFilings(code, REGULAR_LIMIT);
export const nonRegularFilings = (code: string): Promise<NonRegularFiling[]> => loadCompanyNonRegularFilings(code, { limit: NONREGULAR_LIMIT });
export const reportFacts = (code: string): Promise<LiveCompanyReportFact[]> => loadLiveCompanyReportFacts(code);
export const changes = (code: string): Promise<CompanyChange[]> => loadLiveCompanyChanges(code, CHANGES_LIMIT);

// 회사 선택 시 1 회 호출 — 무거운 두 소스(주가·재무)를 병렬로 미리 덥힌다(fire-and-forget).
// 두 로더는 in-flight dedup 이 있어 패널의 같은 호출과 스캔을 공유(중복 fetch 없음).
// 나머지 경량 로더(relations/filings/facts/changes)는 패널이 단일 호출 — 여기서 중복 발사하지 않음.
export function prefetch(code: string, priceYear: number): void {
	void loadGovCandles(code); // 회사별 gov 캐시 워밍 — dev: 라이브 fetch+HF 저장, prod: 캐시 읽기(미스=date/ 폴백)
	void loadGovRecent(); // 최근 거래일 tail — 전 종목 공유 1파일, 세션 1회
	void loadTerminalFinance(code);
	void loadHfProductIndexMap();
}

export const workbench = {
	price,
	finance,
	products,
	productIndex,
	relations,
	regularFilings,
	nonRegularFilings,
	reportFacts,
	changes,
	prefetch
};
export default workbench;
