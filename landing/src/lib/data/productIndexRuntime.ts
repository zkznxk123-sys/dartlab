import { readParquetRows, type FetchLike } from './hfRange';

const PRODUCT_INDEX_PATH = 'metadata/corpList.parquet';

export interface ProductIndexItem {
	product: string;
	productRaw: string;
	latestPeriod: string;
	homepage?: string;
	industry?: string;
	ceo?: string; // 대표자명 (KIND)
	fiscalMonth?: string; // 결산월 (예: '12월')
	listedDate?: string; // 상장일 (YYYY-MM-DD)
	region?: string; // 본사 지역 (예: '경기도')
}

interface ProductIndexRow extends Record<string, unknown> {
	stockCode?: unknown;
	product?: unknown;
	latestPeriod?: unknown;
	종목코드?: unknown;
	주요제품?: unknown;
	홈페이지?: unknown;
	업종?: unknown;
	대표자명?: unknown;
	결산월?: unknown;
	상장일?: unknown;
	지역?: unknown;
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
		columns: ['종목코드', '주요제품', '홈페이지', '업종', '대표자명', '결산월', '상장일', '지역'],
		fetchFn
	});
	const map = new Map<string, ProductIndexItem>();
	const opt = (v: unknown): string | undefined => String(v ?? '').trim() || undefined;
	for (const row of data.rows) {
		const stockCode = String(row.종목코드 ?? row.stockCode ?? '').trim();
		if (!stockCode) continue;
		const productRaw = cleanProduct(row.주요제품 ?? row.product);
		const product = summarizeProduct(productRaw);
		const homepage = normalizeHomepage(row.홈페이지);
		map.set(stockCode, {
			product,
			productRaw,
			latestPeriod: String(row.latestPeriod ?? '').trim(),
			homepage,
			industry: opt(row.업종),
			ceo: opt(row.대표자명),
			fiscalMonth: opt(row.결산월),
			listedDate: opt(row.상장일),
			region: opt(row.지역)
		});
	}
	return map;
}

function normalizeHomepage(value: unknown): string | undefined {
	const s = String(value ?? '').trim();
	if (!s || s === '-') return undefined;
	if (/^https?:\/\//i.test(s)) return s;
	return 'https://' + s.replace(/^\/+/, '');
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
