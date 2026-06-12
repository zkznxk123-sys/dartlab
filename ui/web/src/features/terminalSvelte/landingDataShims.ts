export interface ProductIndexItem {
	code?: string;
	stockCode?: string;
	corpName?: string;
	products?: string[];
	keywords?: string[];
	summary?: string;
	[key: string]: unknown;
}

export interface RegularFiling {
	rceptNo: string;
	rceptDate: string;
	reportType: string;
	year: string;
	url: string;
}

export interface NonRegularFiling {
	rceptNo: string;
	rceptDate: string;
	reportNm: string;
	filer: string;
	url: string;
}

export interface LiveCompanyReportFact {
	label: string;
	value: string;
	source?: string;
	period?: string;
	[key: string]: unknown;
}

export interface CompanyChange {
	date?: string;
	kind?: string;
	title?: string;
	description?: string;
	[key: string]: unknown;
}

type LocalAdapter = {
	productIndex?: () => Promise<Map<string, ProductIndexItem> | null>;
	regularFilings?: (code: string) => Promise<RegularFiling[]>;
	nonRegularFilings?: (code: string) => Promise<NonRegularFiling[]>;
	reportFacts?: (code: string) => Promise<LiveCompanyReportFact[]>;
	changes?: (code: string, limit?: number) => Promise<CompanyChange[]>;
};

function adapter(): LocalAdapter | null {
	return (window as unknown as { __DARTLAB_LOCAL_TERMINAL__?: LocalAdapter }).__DARTLAB_LOCAL_TERMINAL__ ?? null;
}

export async function loadHfProductIndexMap(): Promise<Map<string, ProductIndexItem> | null> {
	return adapter()?.productIndex?.() ?? new Map();
}

export async function loadCompanyRegularFilings(stockCode: string, limit = 5): Promise<RegularFiling[]> {
	const rows = await (adapter()?.regularFilings?.(stockCode) ?? Promise.resolve([]));
	return rows.slice(0, limit);
}

export async function loadCompanyNonRegularFilings(
	stockCode: string,
	{ limit = 30 }: { limit?: number } = {},
): Promise<NonRegularFiling[]> {
	const rows = await (adapter()?.nonRegularFilings?.(stockCode) ?? Promise.resolve([]));
	return rows.slice(0, limit);
}

export async function loadLiveCompanyReportFacts(stockCode: string): Promise<LiveCompanyReportFact[]> {
	return adapter()?.reportFacts?.(stockCode) ?? [];
}

export async function loadLiveCompanyChanges(stockCode: string, limit = 8): Promise<CompanyChange[]> {
	return adapter()?.changes?.(stockCode, limit) ?? [];
}
