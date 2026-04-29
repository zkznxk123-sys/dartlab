import { loadJson } from '$lib/data/dartlabData';
import { tryBuildLiveFinanceTable } from './hfFinance';
import type {
	BrowserShowOptions,
	BrowserShowResult,
	BrowserShowTopic,
	BrowserTable,
	DashboardBundle,
	DartlabBrowserOptions
} from './types';

export class BrowserCompany {
	readonly stockCode: string;
	private readonly options: DartlabBrowserOptions;
	private dashboardPromise: Promise<DashboardBundle> | null = null;

	constructor(stockCode: string, options: DartlabBrowserOptions) {
		this.stockCode = stockCode;
		this.options = options;
	}

	async dashboard(): Promise<DashboardBundle> {
		if (!this.dashboardPromise) {
			this.dashboardPromise = this.loadDashboardBundle();
		}
		return await this.dashboardPromise;
	}

	async show(topic: string, options: BrowserShowOptions = {}): Promise<BrowserShowResult> {
		const resolved = normalizeTopic(topic);
		const freq = options.freq ?? 'Y';

		if (resolved === 'IS' || resolved === 'BS' || resolved === 'CF') {
			const live = await tryBuildLiveFinanceTable(this.stockCode, resolved, freq);
			if (live) return live;
		}

		const bundle = await this.dashboard();

		if (resolved === 'businessOverview') return buildBusinessOverview(bundle);
		if (resolved === 'IS') return buildIsTable(bundle, freq);
		if (resolved === 'BS') return buildBsTable(bundle, freq);
		if (resolved === 'CF') return buildCfTable(bundle, freq);
		if (resolved === 'ratios') return buildRatioTable(bundle);

		throw new Error(`지원하지 않는 browser show topic: ${topic}`);
	}

	private async loadDashboardBundle(): Promise<DashboardBundle> {
		const fetchFn = this.options.fetchFn;
		const stockCode = this.stockCode;

		const globalP = Promise.all([
			loadJson<any>('map/ecosystem.json', { fetchFn }),
			loadJson<any>('dashboards/finance.json', { fetchFn }),
			loadJson<any>('dashboards/quarters.json', { fetchFn }),
			loadJson<any>('dashboards/meta.json', { fetchFn }),
			loadJson<any>('dashboards/macro.json', { fetchFn })
		]);

		const companyMetaP = loadJson<any>(`map/companies/${stockCode}.json`, { fetchFn });
		const [[ecosystem, finance, quarters, meta, macro], companyMeta] = await Promise.all([
			globalP,
			companyMetaP
		]);

		const industryId =
			companyMeta?.ego?.industry ??
			ecosystem?.nodes?.find((n: any) => n.id === stockCode)?.industry ??
			null;
		const industryMeta = industryId
			? await loadJson<any>(`map/industries/${industryId}.json`, { fetchFn })
			: null;

		return {
			stockCode,
			ecosystem: ecosystem ?? { nodes: [], links: [] },
			finance: finance ?? { companies: {}, years: [] },
			quarters: quarters ?? { companies: {}, periods: [] },
			meta: meta ?? { engines: [], blog: {}, thesisTemplates: {} },
			macro,
			companyMeta,
			industryMeta,
			industryId,
			version: 'v23'
		};
	}
}

function normalizeTopic(topic: string): BrowserShowTopic {
	const key = topic.trim();
	const lower = key.toLowerCase();
	if (lower === 'is' || key === '손익계산서' || key === '손익') return 'IS';
	if (lower === 'bs' || key === '재무상태표' || key === '재무상태') return 'BS';
	if (lower === 'cf' || key === '현금흐름표' || key === '현금흐름') return 'CF';
	if (lower === 'ratios' || lower === 'ratio' || key === '비율' || key === '재무비율') {
		return 'ratios';
	}
	if (
		lower === 'businessoverview' ||
		lower === 'business' ||
		key === '사업개요' ||
		key === '사업 개요'
	) {
		return 'businessOverview';
	}
	throw new Error(`지원하지 않는 browser show topic: ${topic}`);
}

function arr(values: unknown, len: number, options: { zeroSeriesAsMissing?: boolean } = {}): Array<number | null> {
	const source = Array.isArray(values) ? values : [];
	const result = Array.from({ length: len }, (_, i) => {
		const value = source[i];
		return typeof value === 'number' && Number.isFinite(value) ? value : null;
	});
	if (
		options.zeroSeriesAsMissing &&
		result.some((value) => value === 0) &&
		result.every((value) => value == null || value === 0)
	) {
		return Array.from({ length: len }, () => null);
	}
	return result;
}

function table(
	bundle: DashboardBundle,
	topic: BrowserShowTopic,
	columns: string[],
	rows: BrowserTable['rows'],
	source: string
): BrowserTable {
	return {
		kind: 'table',
		topic,
		stockCode: bundle.stockCode,
		unit: 'row-specific',
		columns,
		rows,
		source
	};
}

function financeOf(bundle: DashboardBundle): any {
	return bundle.finance?.companies?.[bundle.stockCode] ?? null;
}

function quartersOf(bundle: DashboardBundle): any {
	return bundle.quarters?.companies?.[bundle.stockCode] ?? null;
}

function buildIsTable(bundle: DashboardBundle, freq: 'Y' | 'Q'): BrowserTable {
	if (freq === 'Q') {
		const q = quartersOf(bundle);
		const columns = bundle.quarters?.periods ?? [];
		const len = columns.length;
		return table(
			bundle,
			'IS',
			columns,
			[
				{ key: 'sales', label: '매출액', unit: '조원', values: arr(q?.is?.sales, len, { zeroSeriesAsMissing: true }) },
				{ key: 'op', label: '영업이익', unit: '조원', values: arr(q?.is?.op, len, { zeroSeriesAsMissing: true }) },
				{ key: 'net', label: '순이익', unit: '조원', values: arr(q?.is?.net, len, { zeroSeriesAsMissing: true }) }
			],
			'dashboards/quarters.json'
		);
	}

	const fin = financeOf(bundle);
	const columns = bundle.finance?.years ?? [];
	const len = columns.length;
	return table(
		bundle,
		'IS',
		columns,
		[
			{ key: 'sales', label: '매출액', unit: '조원', values: arr(fin?.is?.sales, len) },
			{ key: 'op', label: '영업이익', unit: '조원', values: arr(fin?.is?.op, len) },
			{ key: 'net', label: '순이익', unit: '조원', values: arr(fin?.is?.net, len) },
			{ key: 'opMargin', label: '영업이익률', unit: '%', values: arr(fin?.is?.opMargin, len) }
		],
		'dashboards/finance.json'
	);
}

function buildBsTable(bundle: DashboardBundle, freq: 'Y' | 'Q'): BrowserTable {
	if (freq === 'Q') {
		const q = quartersOf(bundle);
		const columns = bundle.quarters?.periods ?? [];
		const len = columns.length;
		return table(
			bundle,
			'BS',
			columns,
			[
				{ key: 'totalAsset', label: '총자산', unit: '조원', values: arr(q?.bs?.totalAsset, len, { zeroSeriesAsMissing: true }) },
				{ key: 'totalLiab', label: '총부채', unit: '조원', values: arr(q?.bs?.totalLiab, len, { zeroSeriesAsMissing: true }) },
				{ key: 'totalEquity', label: '총자본', unit: '조원', values: arr(q?.bs?.totalEquity, len, { zeroSeriesAsMissing: true }) },
				{ key: 'cash', label: '현금성자산', unit: '조원', values: arr(q?.bs?.cash, len, { zeroSeriesAsMissing: true }) }
			],
			'dashboards/quarters.json'
		);
	}

	const fin = financeOf(bundle);
	const columns = bundle.finance?.years ?? [];
	const len = columns.length;
	return table(
		bundle,
		'BS',
		columns,
		[
			{ key: 'cash', label: '현금성자산', unit: '조원', values: arr(fin?.bs?.assets?.cash, len) },
			{ key: 'receivables', label: '매출채권', unit: '조원', values: arr(fin?.bs?.assets?.recv, len) },
			{ key: 'inventory', label: '재고자산', unit: '조원', values: arr(fin?.bs?.assets?.inv, len) },
			{ key: 'tangible', label: '유형자산', unit: '조원', values: arr(fin?.bs?.assets?.tang, len) },
			{ key: 'intangible', label: '무형자산', unit: '조원', values: arr(fin?.bs?.assets?.intan, len) },
			{ key: 'payables', label: '매입채무', unit: '조원', values: arr(fin?.bs?.liab?.pay, len) },
			{ key: 'shortDebt', label: '단기차입금', unit: '조원', values: arr(fin?.bs?.liab?.shortDebt, len) },
			{ key: 'longDebt', label: '장기차입금', unit: '조원', values: arr(fin?.bs?.liab?.longDebt, len) },
			{ key: 'bonds', label: '사채', unit: '조원', values: arr(fin?.bs?.liab?.bonds, len) },
			{ key: 'totalAsset', label: '총자산', unit: '조원', values: arr(fin?.bs?.totals?.totalAsset, len) },
			{ key: 'totalLiab', label: '총부채', unit: '조원', values: arr(fin?.bs?.totals?.totalLiab, len) },
			{ key: 'totalEquity', label: '총자본', unit: '조원', values: arr(fin?.bs?.totals?.totalEquity, len) }
		],
		'dashboards/finance.json'
	);
}

function buildCfTable(bundle: DashboardBundle, freq: 'Y' | 'Q'): BrowserTable {
	if (freq === 'Q') {
		const q = quartersOf(bundle);
		const columns = bundle.quarters?.periods ?? [];
		const len = columns.length;
		return table(
			bundle,
			'CF',
			columns,
			[
				{ key: 'ocf', label: '영업CF', unit: '조원', values: arr(q?.cf?.ocf, len, { zeroSeriesAsMissing: true }) },
				{ key: 'icf', label: '투자CF', unit: '조원', values: arr(q?.cf?.icf, len, { zeroSeriesAsMissing: true }) }
			],
			'dashboards/quarters.json'
		);
	}

	const fin = financeOf(bundle);
	const cf = fin?.cf ?? {};
	const latestYear = bundle.finance?.years?.at?.(-1) ?? 'latest';
	return table(
		bundle,
		'CF',
		[latestYear],
		[
			{ key: 'op', label: '영업CF', unit: '조원', values: [numberOrNull(cf.op)] },
			{ key: 'inv', label: '투자CF', unit: '조원', values: [numberOrNull(cf.inv)] },
			{ key: 'fin', label: '재무CF', unit: '조원', values: [numberOrNull(cf.fin)] },
			{ key: 'opening', label: '기초현금', unit: '조원', values: [numberOrNull(cf.opening)] },
			{ key: 'closing', label: '기말현금', unit: '조원', values: [numberOrNull(cf.closing)] },
			{ key: 'fx', label: '환율효과', unit: '조원', values: [numberOrNull(cf.fx)] }
		],
		'dashboards/finance.json'
	);
}

function buildRatioTable(bundle: DashboardBundle): BrowserTable {
	const fin = financeOf(bundle);
	const columns = bundle.finance?.years ?? [];
	const len = columns.length;
	return table(
		bundle,
		'ratios',
		columns,
		[
			{ key: 'roe', label: 'ROE', unit: '%', values: arr(fin?.ratios?.roe, len) },
			{ key: 'debtRatio', label: '부채비율', unit: '%', values: arr(fin?.ratios?.debtRatio, len) }
		],
		'dashboards/finance.json'
	);
}

function numberOrNull(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function buildBusinessOverview(bundle: DashboardBundle): BrowserShowResult {
	const ego = bundle.companyMeta?.ego;
	const title = `${ego?.corpName ?? bundle.stockCode} 사업 개요`;
	const narrative = bundle.companyMeta?.aiInsight?.narrative;
	const fallback = ego
		? `${ego.corpName ?? bundle.stockCode}은 ${ego.industry ?? '미분류'} 산업의 ${ego.stage ?? '일반'} 단계에 속한 ${ego.role ?? '회사'}입니다.`
		: `${bundle.stockCode} 사업 개요 데이터가 아직 준비되지 않았습니다.`;
	return {
		kind: 'text',
		topic: 'businessOverview',
		stockCode: bundle.stockCode,
		title,
		text: typeof narrative === 'string' && narrative.trim() ? narrative : fallback,
		source: 'map/companies/{stockCode}.json'
	};
}
