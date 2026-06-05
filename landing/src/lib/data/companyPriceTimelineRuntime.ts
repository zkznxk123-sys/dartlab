import { readParquetRows, type FetchLike } from './hfRange';
import {
	normalizePriceRows,
	type CompanyPriceRawRow,
	type PricePoint
} from '$lib/company/priceTimelineModel';

export interface CompanyPriceTimeline {
	stockCode: string;
	source: string;
	points: PricePoint[];
	requests: number;
}

const COLUMNS = [
	'date',
	'stockCode',
	'name',
	'market',
	'open',
	'high',
	'low',
	'close',
	'priceChange',
	'fluctuationRate',
	'volume',
	'tradedValue',
	'marketCap',
	'listedShares'
];

export async function loadCompanyPriceTimeline(
	stockCode: string,
	fetchFn: FetchLike = fetch
): Promise<CompanyPriceTimeline> {
	const code = stockCode.trim().replace(/^A/, '');
	if (!/^\d{6}$/.test(code)) {
		return { stockCode: code, source: '', points: [], requests: 0 };
	}
	const source = `krx/prices/company/${code}.parquet`;
	const data = await readParquetRows<CompanyPriceRawRow>(source, {
		columns: COLUMNS,
		fetchFn
	});
	return {
		stockCode: code,
		source,
		points: normalizePriceRows(data.rows, code),
		requests: data.requests.length
	};
}
