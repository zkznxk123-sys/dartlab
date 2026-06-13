// 로컬 터미널 RawData 조립(createEngine 씨드) — 셸 글루.
// 시장 전체 데이터셋(전 종목 finance/prices/eco/search-index)은 로컬 /api 미보유 → 단일 회사로 조립한다
// (ui/web 브리지 패리티). 실시간 상세(차트 캔들·패널 격자·재무 카드)는 runtime 포트가 공급하므로 씨드는 최소.
import { getLocalRuntime } from '$lib/runtime/localRuntime';
import type { FinanceCompany, IndexRow, PriceRow, RawData } from '@dartlab/ui-surfaces/terminal';

function emptyFinanceCompany(): FinanceCompany {
	return {
		is: { sales: [], op: [], net: [], opMargin: [] },
		bs: { totals: { totalAsset: [], totalLiab: [], totalEquity: [], currAsset: [], currLiab: [] } },
		cf: { op: null, inv: null, fin: null, opening: null, closing: null, fx: null },
		ratios: { roe: [], debtRatio: [] }
	};
}

function fallbackYears(): string[] {
	const y = new Date().getFullYear() - 1;
	return [4, 3, 2, 1, 0].map((d) => String(y - d));
}

interface MetaLite {
	corpName?: string;
	sector?: string;
}

export async function loadTerminalRaw(code: string): Promise<{ raw: RawData; code: string }> {
	const runtime = getLocalRuntime();
	// 회사명/업종은 /api meta, 초기 캔들은 price 포트(price-events 캐시 워밍 동시) — 병렬.
	const [meta, prices] = await Promise.all([
		fetch(`/api/company/${encodeURIComponent(code)}/meta`)
			.then((r) => (r.ok ? (r.json() as Promise<MetaLite>) : null))
			.catch(() => null),
		runtime.price.initial(code, new Date().getFullYear())
	]);

	const corpName = meta?.corpName ?? code;
	const industry = meta?.sector ?? '';
	const candles = prices?.candles ?? [];
	const last = candles.at(-1);

	const priceRow: PriceRow = {
		currentPrice: last?.c ?? 0,
		marketCap: 0,
		return1m: null,
		return3m: null,
		return1y: null,
		volatility1y: null,
		week52High: null,
		week52Low: null,
		volumeAvg30d: null,
		foreignPct: null,
		beta: null,
		priceUpdated: last?.t ?? ''
	};

	const indexRow: IndexRow = { stockCode: code, corpName, industry, revenue: null };

	const raw: RawData = {
		finance: { years: fallbackYears(), companies: { [code]: emptyFinanceCompany() } },
		macro: null,
		meta: null,
		prices: { data: { [code]: priceRow } },
		index: [indexRow],
		eco: null,
		quarters: null
	};
	return { raw, code };
}
