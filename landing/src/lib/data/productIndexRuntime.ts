import { readParquetRows, type FetchLike } from './hfRange';

const PRODUCT_INDEX_PATH = 'metadata/corpList.parquet';

export interface ProductIndexItem {
	product: string;
	productRaw: string;
	latestPeriod: string;
}

interface ProductIndexRow extends Record<string, unknown> {
	stockCode?: unknown;
	product?: unknown;
	latestPeriod?: unknown;
	종목코드?: unknown;
	주요제품?: unknown;
}

let productIndexPromise: Promise<Map<string, ProductIndexItem>> | null = null;

export async function loadHfProductIndexMap(fetchFn: FetchLike = fetch): Promise<Map<string, ProductIndexItem>> {
	if (fetchFn === fetch) {
		productIndexPromise ??= readHfProductIndexMap(fetchFn);
		return productIndexPromise;
	}
	return readHfProductIndexMap(fetchFn);
}

async function readHfProductIndexMap(fetchFn: FetchLike): Promise<Map<string, ProductIndexItem>> {
	const data = await readParquetRows<ProductIndexRow>(PRODUCT_INDEX_PATH, {
		columns: ['종목코드', '주요제품'],
		fetchFn
	});
	const map = new Map<string, ProductIndexItem>();
	for (const row of data.rows) {
		const stockCode = String(row.종목코드 ?? row.stockCode ?? '').trim();
		const productRaw = cleanProduct(row.주요제품 ?? row.product);
		const product = summarizeProduct(productRaw);
		if (!stockCode || !productRaw) continue;
		map.set(stockCode, {
			product,
			productRaw,
			latestPeriod: String(row.latestPeriod ?? '').trim()
		});
	}
	return map;
}

function cleanProduct(value: unknown): string {
	return String(value ?? '')
		.replace(/&cr;/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

function summarizeProduct(value: string): string {
	return value
		.split(/[,;/·ㆍ]| 및 | 등 |와 |과 | 제조| 판매| 도매| 서비스/g)
		.map((part) =>
			part
				.replace(/\([^)]*\)/g, '')
				.replace(/\s+/g, ' ')
				.trim()
		)
		.filter((part) => part.length >= 2 && !/^(제품|상품|기타|수출입)$/.test(part))
		.filter(unique)
		.slice(0, 4)
		.join(', ');
}

function unique(value: string, index: number, array: string[]): boolean {
	return array.indexOf(value) === index;
}
