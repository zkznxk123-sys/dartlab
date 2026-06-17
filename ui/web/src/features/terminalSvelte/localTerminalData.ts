import {
	fetchCompanyInsights,
	fetchCompanyMeta,
	fetchPanelGrid,
	fetchPanelInit,
	fetchPanelToc,
	type CompanyInsightsResponse,
	type CompanyMeta,
	type PanelGridResponse as ClientPanelGrid,
	type PanelInitResponse as ClientPanelInit,
	type PanelTocResponse as ClientPanelToc,
	type SerializedTablePayload,
} from '@/features/dashboard/api/client';
import { fetchPriceEvents, type PriceEventsPayload } from '@/features/dashboard/api/priceEvents';
// 계약 타입 정본 = @dartlab/ui-contracts (옛 로컬 재정의 제거 — 4a-2 포트화)
import type {
	Candle,
	CompanyPrices,
	DartLabRuntime,
	FinCard,
	FinMode,
	NonRegularFiling,
	PanelGridResponse,
	PanelInitResponse,
	PanelTocResponse,
	ProductIndexItem,
	RegularFiling,
	RuntimeEnvironment,
	StmtKind,
	StmtRow,
	TerminalFinance,
	TerminalFinanceBundle,
} from '@dartlab/ui-contracts';
import { createHfMacroPort, createPublicIndexPort, publicNewsPort } from '@dartlab/ui-runtime';
import type { FinanceCompany, IndexRow, MetaFile, RawData } from '@dartlab/ui-surfaces/terminal';

type Num = number | null;
type FinFreq = TerminalFinance['freq'];

export interface LocalTerminalRuntime {
	raw: RawData;
	/** DartLabRuntime 포트 묶음 — Terminal.svelte 에 prop 으로 주입 (전역 locator 철거, 4a-2). */
	runtime: DartLabRuntime;
}

type LocalRawData = RawData & { __localCandles?: Candle[] };

interface PeriodInfo {
	column: string;
	year: number;
	q: number | null;
	annual: boolean;
	order: number;
}

interface StatementTables {
	is?: SerializedTablePayload;
	bs?: SerializedTablePayload;
	cf?: SerializedTablePayload;
}

interface RuntimeSeed {
	code: string;
	meta: CompanyMeta;
	insights: CompanyInsightsResponse | null;
	price: PriceEventsPayload | null;
	tables: StatementTables;
}

const runtimeCache = new Map<string, Promise<LocalTerminalRuntime>>();

export function loadLocalTerminalRuntime(stockCode: string): Promise<LocalTerminalRuntime> {
	const code = stockCode.trim();
	const hit = runtimeCache.get(code);
	if (hit) return hit;
	const p = buildRuntime(code);
	runtimeCache.set(code, p);
	return p;
}

function optional<T>(p: Promise<T>): Promise<T | null> {
	return p.catch(() => null);
}

async function buildRuntime(code: string): Promise<LocalTerminalRuntime> {
	const end = isoDate(new Date());
	const start = isoDate(new Date(Date.now() - 390 * 24 * 60 * 60 * 1000));
	const [meta, insights, price] = await Promise.all([
		fetchCompanyMeta(code),
		optional(fetchCompanyInsights(code)),
		optional(fetchPriceEvents({ stockCode: code, start, end, sources: 'disclosure', includeRegime: false, includeShocks: false })),
	]);
	const seed: RuntimeSeed = {
		code,
		meta,
		insights,
		price,
		tables: {},
	};
	const raw = buildRaw(seed);
	return { raw, runtime: buildBridgeRuntime(seed, raw) };
}

function notWiredYet(what: string, stage: string): never {
	throw new Error(`[local 브리지] ${what} 는 ${stage}에서 구현된다 — 이 호출이 보이면 배선 순서 위반이다.`);
}

// ── 로컬 HTTP 응답 → 계약 정규화 ──
// 로컬 panel toc 는 leafType/disclosureKey 메타를 싣지 않는다 — 미제공 = null 정직 표기 (위조 금지).
function tocToContract(toc: ClientPanelToc): PanelTocResponse {
	return {
		stockCode: toc.stockCode,
		corpName: toc.corpName,
		periods: toc.periods,
		chapters: toc.chapters.map((ch) => ({
			chapter: ch.chapter,
			sections: ch.sections.map((s) => ({
				sectionLeaf: s.sectionLeaf,
				sectionKey: s.sectionKey,
				blocks: s.blocks.map((b) => ({ blockLeaf: b.blockLeaf, leafType: null, disclosureKey: null })),
			})),
		})),
	};
}

// chapter/sectionLeaf 가 null 인 응답은 sectionKey(`${chapter}␟${sectionLeaf}`)에서 파생 — 키가 SSOT.
function gridToContract(g: ClientPanelGrid): PanelGridResponse {
	const [keyChapter = '', keyLeaf = ''] = g.sectionKey.split('␟');
	const dartUrlByPeriod = g.dartUrlByPeriod
		? Object.fromEntries(Object.entries(g.dartUrlByPeriod).filter((e): e is [string, string] => e[1] != null))
		: undefined;
	return {
		stockCode: g.stockCode,
		corpName: g.corpName,
		chapter: g.chapter ?? keyChapter,
		sectionLeaf: g.sectionLeaf ?? keyLeaf,
		sectionKey: g.sectionKey,
		periods: g.periods,
		rows: g.rows.map((r) => ({ ...r, leafType: null })),
		dartUrlByPeriod,
	};
}

// init 필수 구성(grid·first 포인터) 결손 = 사용 가능한 패널 없음 → null 정직 표기.
function initToContract(init: ClientPanelInit | null): PanelInitResponse | null {
	if (!init || !init.grid || init.firstChapter == null || init.firstSectionKey == null) return null;
	return {
		stockCode: init.stockCode,
		corpName: init.corpName,
		toc: tocToContract(init.toc),
		firstChapter: init.firstChapter,
		firstSectionKey: init.firstSectionKey,
		grid: gridToContract(init.grid),
	};
}

// 로컬 서버(/api) 씨드 1개 회사 범위의 DartLabRuntime — Terminal 임베드 전용.
// 빈값 규약 준수: 씨드 밖 회사 = null/[], 로컬 미보유 데이터셋(report 시계열) = null 정직 표기.
function buildBridgeRuntime(seed: RuntimeSeed, raw: RawData): DartLabRuntime {
	let panelPromise: Promise<ClientPanelInit | null> | null = null;
	let eventPromise: Promise<PriceEventsPayload | null> | null = null;
	const candles = (raw as LocalRawData).__localCandles ?? [];
	const financeBundle = buildTerminalFinance(seed.tables, raw);
	const productItem: ProductIndexItem = {
		product: seed.meta.products.slice(0, 4).join(', '),
		productRaw: seed.meta.products.join(', '),
		latestPeriod: '',
		industry: seed.meta.sector || undefined,
	};

	const loadPanel = () => {
		panelPromise ??= optional(fetchPanelInit(seed.code));
		return panelPromise;
	};
	const loadEvents = () => {
		eventPromise ??= optional(fetchPriceEvents({ stockCode: seed.code, sources: 'disclosure', includeRegime: false, includeShocks: false }));
		return eventPromise;
	};
	const isSeed = (code: string) => code.trim() === seed.code;

	const env: RuntimeEnvironment = {
		kind: 'local',
		basePath: '',
		locale: 'ko',
		marketDefault: 'KR',
		buildVersion: __DARTLAB_VERSION__,
		readonly: false,
	};

	return {
		env,
		company: {
			async products(code) {
				return isSeed(code) ? productItem : null;
			},
			async productIndex() {
				return { [seed.code]: productItem };
			},
			async relations(code) {
				if (!isSeed(code)) return null;
				return { suppliers: [], customers: [], peers: [], neighborCount: 0, blog: null };
			},
			async reportFacts() {
				return [];
			},
		},
		price: {
			async initial(code, year) {
				if (!isSeed(code) || !candles.length) return null;
				return { candles, oldestYear: Math.min(year - 1, Number(candles[0]?.t.slice(0, 4)) || year) } satisfies CompanyPrices;
			},
			async older() {
				return [];
			},
			loaded(code) {
				return isSeed(code) ? candles : [];
			},
			async govCandles(code) {
				return isSeed(code) ? candles : null;
			},
			async govRecent() {
				return { [seed.code]: candles.slice(-40) };
			},
		},
		filing: {
			async regular(code, limit = 500) {
				if (!isSeed(code)) return [];
				return regularFilingsFromPanel(await loadPanel()).slice(0, limit);
			},
			async nonRegular(code, limit = 200) {
				if (!isSeed(code)) return [];
				return nonRegularFromEvents(await loadEvents()).slice(0, limit);
			},
			async panelToc(code) {
				if (!isSeed(code)) return null;
				const toc = await optional(fetchPanelToc(code));
				return toc ? tocToContract(toc) : null;
			},
			async panelInit(code) {
				if (!isSeed(code)) return null;
				return initToContract(await loadPanel());
			},
			async panelGrid(code, sectionKey) {
				if (!isSeed(code)) return null;
				const grid = await optional(fetchPanelGrid(code, sectionKey));
				return grid ? gridToContract(grid) : null;
			},
		},
		finance: {
			async bundle(code) {
				return isSeed(code) ? financeBundle : null;
			},
		},
		viewer: {
			mode: 'external-url',
			urlForCompany(code, options) {
				const qs = new URLSearchParams({ period: 'quarterly', terminalEmbed: '1' });
				if (options?.vs?.length) qs.set('vs', options.vs.join(','));
				return `/analysis/${encodeURIComponent(code)}/viewer?${qs.toString()}`;
			},
			async openCompany(code, options) {
				const url = this.urlForCompany(code, options);
				if (url) location.assign(url);
			},
			async openFiling(filing) {
				window.open(filing.url, '_blank', 'noopener');
			},
		},
		index: createPublicIndexPort(), // 지수도 회사 무관 HF 공개 데이터(gov/indices+FRED) — 공용 포트 재사용
		macro: createHfMacroPort(), // 거시 시계열은 회사 무관 HF 공개 데이터 — 명시적 공용 포트 재사용
		news: publicNewsPort(), // 종목 뉴스도 회사 무관 워커(/news) 서버사이드 read — 공용 포트 재사용(seed 무관)
		report: {
			// 로컬 서버는 정기보고서 파생 시계열 미보유 — null = 데이터셋 미존재 정직 표기 (옛 동작 동일)
			workforce: async () => null,
			investments: async () => null,
			shareholderReturn: async () => null,
			ownership: async () => null,
			shareholders: async () => null,
			shareholderPeriods: async () => null,
			execBoard: async () => null,
			debtProfile: async () => null,
			capitalChanges: async () => null,
			auditTrail: async () => null,
			topExecPay: async () => null,
			auditFees: async () => null,
		},
		scan: {
			async changes() {
				return [];
			},
			listTableSources: () => notWiredYet('scan.listTableSources', '단계-8(scan 추출)'),
			getPresets: () => notWiredYet('scan.getPresets', '단계-8(scan 추출)'),
			savePreset: () => notWiredYet('scan.savePreset', '단계-8(scan 추출)'),
		},
		get map() {
			return notWiredYet('map', '단계-8(map 추출)');
		},
		get search() {
			return notWiredYet('search', '단계-8(search 추출)');
		},
		get ai() {
			return notWiredYet('ai', '단계-7(ask 추출)');
		},
		get services() {
			return notWiredYet('services', '단계-5(서비스 레지스트리 배선)');
		},
		get navigation() {
			return notWiredYet('navigation', '단계-4a-3(셸 내비 주입)');
		},
		get storage() {
			return notWiredYet('storage', '단계-4a-3(셸 스토리지 주입)');
		},
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false },
	};
}

function buildRaw(seed: RuntimeSeed): RawData {
	const candles = candlesFromPrice(seed.price);
	const annualPeriods = annualPeriodColumns(seed.tables);
	const fallbackYears = fallbackYearRange();
	const years = annualPeriods.length ? annualPeriods.map((p) => String(p.year)) : fallbackYears;
	const financeCompany = buildFinanceCompany(seed.tables, annualPeriods, years);
	const quarters = buildQuarters(seed.tables, seed.code);
	const price = buildPriceRow(candles, financeCompany, seed.insights);
	const industry = industryKey(seed.meta.sector);
	const revenue = lastNonNull(financeCompany.is.sales);
	const opMargin = lastNonNull(financeCompany.is.opMargin);
	const roe = lastNonNull(financeCompany.ratios.roe);
	const debtRatio = lastNonNull(financeCompany.ratios.debtRatio);
	const revCagr = cagr(financeCompany.is.sales);
	const indexRow: IndexRow = {
		stockCode: seed.code,
		corpName: seed.meta.corpName,
		industry,
		stage: 'local',
		revenue,
	};
	const ecoNode = {
		id: seed.code,
		label: seed.meta.corpName,
		industry,
		industryName: seed.meta.sector || '기타',
		market: seed.meta.market,
		stageName: 'local',
		role: seed.meta.products.slice(0, 2).join(' · '),
		revenue,
		// 단독-유니버스(peer 1사)라 상장사매출비중·산업순위는 분모=자기자신 = 동어반복 날조 →
		// 값 미설정(undefined). 소비처는 null-guard 로 '—' 폴백. (industry-analysis-lab 07 §구멍5)
		roe,
		opMargin,
		debtRatio,
		revCagr,
		profGrade: profitGrade(opMargin),
		growthGrade: growthGrade(revCagr),
		govGrade: seed.insights?.grades?.governance ?? seed.insights?.grades?.gov ?? 'B',
		qualGrade: qualityGrade(financeCompany),
		liqGrade: liquidityGrade(financeCompany),
		auditRisk: '저위험',
		stability: stabilityGrade(debtRatio),
		cfPattern: cashflowPattern(financeCompany),
	};
	const meta: MetaFile = {
		version: 'local',
		blog: Object.fromEntries(
			(seed.meta.blogPosts || []).slice(0, 1).map((p) => [
				seed.code,
				{ slug: p.slug || p.url || seed.code, title: p.title, date: '', excerpt: p.url },
			]),
		),
	};
	const raw = {
		finance: { version: 'local', years, companies: { [seed.code]: financeCompany } },
		macro: null,
		meta,
		prices: { count: 1, data: { [seed.code]: price } },
		index: [indexRow],
		eco: { version: 'local', nodes: [ecoNode] },
		quarters,
		// 로컬 단일사 seed — 업종 분포(industryStats) 미보유, null 정직 표기(밴드 미표시). public 셸만 로드.
		industryStats: null,
	} satisfies RawData;
	return Object.assign(raw, { __localCandles: candles }) as RawData;
}

function annualPeriodColumns(tables: StatementTables): PeriodInfo[] {
	const infos = uniquePeriods([...periodsOf(tables.is), ...periodsOf(tables.bs), ...periodsOf(tables.cf)]);
	const annual = new Map<number, PeriodInfo>();
	for (const p of infos) {
		if (!p.annual && p.q !== 4) continue;
		const prev = annual.get(p.year);
		if (!prev || (p.annual && !prev.annual)) annual.set(p.year, p);
	}
	return [...annual.values()].sort((a, b) => a.year - b.year).slice(-6);
}

function quarterPeriodColumns(tables: StatementTables): PeriodInfo[] {
	return uniquePeriods([...periodsOf(tables.is), ...periodsOf(tables.bs), ...periodsOf(tables.cf)])
		.filter((p) => p.q != null)
		.sort((a, b) => a.order - b.order)
		.slice(-16);
}

function periodsOf(table: SerializedTablePayload | undefined): PeriodInfo[] {
	if (!table) return [];
	return table.columns.map(parsePeriod).filter((p): p is PeriodInfo => p != null);
}

function uniquePeriods(periods: PeriodInfo[]): PeriodInfo[] {
	const out = new Map<string, PeriodInfo>();
	for (const p of periods) {
		const key = `${p.year}-${p.q ?? 'A'}`;
		if (!out.has(key)) out.set(key, p);
	}
	return [...out.values()];
}

function parsePeriod(column: string): PeriodInfo | null {
	const raw = column.trim();
	const compact = raw.toUpperCase().replace(/[\s._/-]/g, '');
	let m = compact.match(/^FY(\d{2})$/);
	if (m) {
		const year = 2000 + Number(m[1]);
		return { column, year, q: null, annual: true, order: year * 10 + 4 };
	}
	m = compact.match(/^(20\d{2})Q([1-4])$/);
	if (m) {
		const year = Number(m[1]);
		const q = Number(m[2]);
		return { column, year, q, annual: false, order: year * 10 + q };
	}
	m = compact.match(/^(20\d{2})([1-4])Q$/);
	if (m) {
		const year = Number(m[1]);
		const q = Number(m[2]);
		return { column, year, q, annual: false, order: year * 10 + q };
	}
	m = compact.match(/^(20\d{2})$/);
	if (m) {
		const year = Number(m[1]);
		return { column, year, q: null, annual: true, order: year * 10 + 4 };
	}
	return null;
}

function buildFinanceCompany(tables: StatementTables, annualPeriods: PeriodInfo[], fallbackYears: string[]): FinanceCompany {
	const cols = annualPeriods.length ? annualPeriods : fallbackYears.map((y) => ({ column: y, year: Number(y), q: null, annual: true, order: Number(y) * 10 + 4 }));
	const sales = amountSeries(tables.is ?? tables.cf, cols, ['매출액', '영업수익', '수익(매출액)', 'revenue', 'adjustments_for_sales']);
	const op = amountSeries(tables.is, cols, ['영업이익', '영업이익(손실)', 'operating income'], ['영업이익률']);
	const net = amountSeries(tables.is, cols, ['당기순이익', '분기순이익', '순이익', 'net income'], ['지배기업']);
	const totalAsset = amountSeries(tables.bs, cols, ['자산총계', 'total assets'], ['유동자산']);
	const totalLiab = amountSeries(tables.bs, cols, ['부채총계', 'total liabilities'], ['유동부채']);
	const totalEquity = amountSeries(tables.bs, cols, ['자본총계', 'total equity'], ['비지배']);
	const currAsset = amountSeries(tables.bs, cols, ['유동자산', 'current assets'], ['비유동']);
	const currLiab = amountSeries(tables.bs, cols, ['유동부채', 'current liabilities'], ['비유동']);
	const cash = amountSeries(tables.bs, cols, ['현금및현금성자산', '현금성자산', 'cash']);
	const recv = amountSeries(tables.bs, cols, ['매출채권', 'trade receivables', 'receivables']);
	const inv = amountSeries(tables.bs, cols, ['재고자산', 'inventories']);
	const tang = amountSeries(tables.bs, cols, ['유형자산', 'property plant']);
	const intan = amountSeries(tables.bs, cols, ['무형자산', 'intangible']);
	const cfo = amountSeries(tables.cf, cols, ['영업활동현금흐름', 'operating cash', 'operating_cashflow', 'cash_flows_from_business']);
	const cfi = amountSeries(tables.cf, cols, ['투자활동현금흐름', 'investing cash', 'investing_cashflow']);
	const cff = amountSeries(tables.cf, cols, ['재무활동현금흐름', 'financing cash', 'financing_cashflow']);
	const opMargin = ratioSeries(op, sales, 100);
	const roe = ratioSeries(net, totalEquity, 100);
	const debtRatio = ratioSeries(totalLiab, totalEquity, 100);
	return {
		is: { sales, op, net, opMargin },
		bs: {
			assets: { cash, recv, inv, tang, intan },
			totals: { totalAsset, totalLiab, totalEquity, currAsset, currLiab },
		},
		cf: {
			op: lastNonNull(cfo),
			inv: lastNonNull(cfi),
			fin: lastNonNull(cff),
			opening: null,
			closing: null,
			fx: null,
		},
		ratios: { roe, debtRatio },
	};
}

function buildQuarters(tables: StatementTables, code: string): RawData['quarters'] {
	const cols = quarterPeriodColumns(tables);
	if (!cols.length) return null;
	const sales = amountSeries(tables.is ?? tables.cf, cols, ['매출액', '영업수익', '수익(매출액)', 'revenue', 'adjustments_for_sales']);
	const op = amountSeries(tables.is, cols, ['영업이익', '영업이익(손실)', 'operating income'], ['영업이익률']);
	const net = amountSeries(tables.is, cols, ['당기순이익', '분기순이익', '순이익', 'net income'], ['지배기업']);
	const ocf = amountSeries(tables.cf, cols, ['영업활동현금흐름', 'operating cash', 'operating_cashflow', 'cash_flows_from_business']);
	const icf = amountSeries(tables.cf, cols, ['투자활동현금흐름', 'investing cash', 'investing_cashflow']);
	return {
		periods: cols.map((p) => `${String(p.year).slice(2)}Q${p.q ?? 4}`),
		companies: {
			[code]: {
				is: { sales, op, net },
				cf: { ocf, icf },
			},
		},
	};
}

function amountSeries(
	table: SerializedTablePayload | undefined,
	periods: PeriodInfo[],
	keywords: string[],
	avoid: string[] = [],
): Num[] {
	const row = pickRow(table, keywords, avoid);
	return periods.map((p) => toTrillion(row?.[p.column]));
}

function pickRow(table: SerializedTablePayload | undefined, keywords: string[], avoid: string[]): Record<string, unknown> | null {
	if (!table) return null;
	const keys = keywords.map(norm);
	const avoids = avoid.map(norm);
	let best: { row: Record<string, unknown>; score: number } | null = null;
	for (const row of table.rows) {
		const label = norm(rowLabel(row, table.columns));
		if (!label || avoids.some((a) => label.includes(a))) continue;
		let score = 0;
		for (const key of keys) {
			if (label === key) score += 100;
			else if (label.includes(key)) score += 30;
		}
		if (!score) continue;
		score -= Math.min(label.length, 80) / 100;
		if (!best || score > best.score) best = { row, score };
	}
	return best?.row ?? null;
}

function rowLabel(row: Record<string, unknown>, columns: string[]): string {
	const candidates = ['account_nm', 'accountName', 'account', 'label', 'name', '계정명', '항목', 'disclosureKey', 'snakeId', 'tag'];
	const out: string[] = [];
	for (const c of candidates) {
		const v = row[c];
		if (v != null && String(v).trim()) out.push(String(v));
	}
	if (!out.length) {
		const col = columns.find((c) => !parsePeriod(c));
		const v = col ? row[col] : null;
		if (v != null) out.push(String(v));
	}
	return out.join(' ');
}

function norm(v: unknown): string {
	return stripHtml(String(v ?? '')).toLowerCase().replace(/[\s,_()[\]{}·:：-]/g, '');
}

function toTrillion(value: unknown): Num {
	const s = stripHtml(String(value ?? '')).trim();
	if (!s || s === '-' || s === '—') return null;
	const n = Number(s.replace(/,/g, '').replace(/[^\d.+-]/g, ''));
	if (!Number.isFinite(n)) return null;
	if (s.includes('조')) return round(n);
	if (s.includes('억')) return round(n / 10_000);
	if (s.includes('백만')) return round(n / 1_000_000);
	if (Math.abs(n) > 10_000_000_000) return round(n / 1e12);
	return round(n);
}

function stripHtml(text: string): string {
	return text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function round(v: number, digits = 3): number {
	const m = 10 ** digits;
	return Math.round(v * m) / m;
}

function ratioSeries(num: Num[], den: Num[], scale = 100): Num[] {
	return num.map((v, i) => (v != null && den[i] ? round((v / den[i]) * scale, 1) : null));
}

function lastNonNull(values: Num[]): Num {
	for (let i = values.length - 1; i >= 0; i -= 1) {
		const v = values[i];
		if (v != null && Number.isFinite(v)) return v;
	}
	return null;
}

function cagr(values: Num[]): Num {
	const xs = values.filter((v): v is number => v != null && v > 0);
	if (xs.length < 2) return null;
	return round((Math.pow(xs[xs.length - 1] / xs[0], 1 / (xs.length - 1)) - 1) * 100, 1);
}

function candlesFromPrice(payload: PriceEventsPayload | null): Candle[] {
	const candles = (payload?.ohlc ?? [])
		.map((row) => {
			const [ts, o, h, l, c, v] = row;
			const t = ymdFromTs(ts);
			if (!t || !Number.isFinite(c) || c <= 0) return null;
			return { t, o: o || c, h: h || c, l: l || c, c, v: v || 0 } satisfies Candle;
		})
		.filter((x): x is Candle => x != null)
		.sort((a, b) => a.t.localeCompare(b.t));
	if (candles.length) return candles;
	const today = compactDate(new Date());
	return [{ t: today, o: 1000, h: 1000, l: 1000, c: 1000, v: 0 }];
}

function ymdFromTs(ts: number): string {
	const ms = ts > 10_000_000_000 ? ts : ts * 1000;
	const d = new Date(ms);
	if (!Number.isFinite(d.getTime())) return '';
	return compactDate(d);
}

function compactDate(d: Date): string {
	return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}

function isoDate(d: Date): string {
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function buildPriceRow(candles: Candle[], finance: FinanceCompany, insights: CompanyInsightsResponse | null): RawData['prices']['data'][string] {
	const closes = candles.map((c) => c.c);
	const last = closes[closes.length - 1] ?? 1000;
	const ret = (days: number): Num => {
		const prev = closes[Math.max(0, closes.length - 1 - days)];
		return prev ? round(((last - prev) / prev) * 100, 1) : null;
	};
	const returns = closes.slice(1).map((v, i) => (closes[i] ? (v - closes[i]) / closes[i] : 0));
	const vol = returns.length > 5 ? round(stddev(returns) * Math.sqrt(252) * 100, 1) : null;
	const marketCapFromProfile = deepNumber(insights?.profile, ['marketCap', 'mktcap', '시가총액']);
	const revenue = lastNonNull(finance.is.sales);
	const marketCap = marketCapFromProfile ?? Math.max(1, (revenue ?? 1) * 1e12 * 1.8);
	return {
		currentPrice: last,
		marketCap,
		return1m: ret(22),
		return3m: ret(66),
		return1y: ret(252),
		volatility1y: vol,
		week52High: Math.max(...closes.slice(-252)),
		week52Low: Math.min(...closes.slice(-252)),
		volumeAvg30d: avg(candles.slice(-30).map((c) => c.v)),
		foreignPct: null,
		beta: null,
		priceUpdated: candles[candles.length - 1]?.t ?? compactDate(new Date()),
	};
}

function avg(values: number[]): Num {
	const xs = values.filter((v) => Number.isFinite(v));
	return xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : null;
}

function stddev(values: number[]): number {
	const m = values.reduce((a, b) => a + b, 0) / values.length;
	const variance = values.reduce((a, b) => a + (b - m) ** 2, 0) / values.length;
	return Math.sqrt(variance);
}

function deepNumber(input: unknown, needles: string[]): number | null {
	if (!input || typeof input !== 'object') return null;
	for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
		if (needles.some((n) => norm(key).includes(norm(n)))) {
			const parsed = typeof value === 'number' ? value : Number(String(value).replace(/,/g, '').replace(/[^\d.+-]/g, ''));
			if (Number.isFinite(parsed) && parsed > 0) return parsed;
		}
		if (value && typeof value === 'object') {
			const hit = deepNumber(value, needles);
			if (hit != null) return hit;
		}
	}
	return null;
}

function buildTerminalFinance(tables: StatementTables, raw: RawData): TerminalFinanceBundle | null {
	const code = raw.index[0]?.stockCode;
	if (!code) return null;
	const fin = raw.finance.companies[code];
	const annualPeriods = raw.finance.years.map((y) => `FY${y.slice(2)}`);
	const annual = makeFinanceView(annualPeriods, 'annual', {
		revenue: fin.is.sales,
		op: fin.is.op,
		net: fin.is.net,
		assets: fin.bs.totals.totalAsset,
		liabilities: fin.bs.totals.totalLiab,
		equity: fin.bs.totals.totalEquity,
		currentAssets: fin.bs.totals.currAsset,
		currentLiabilities: fin.bs.totals.currLiab,
		cfo: fillSeries(fin.cf.op, annualPeriods.length),
		cfi: fillSeries(fin.cf.inv, annualPeriods.length),
		cff: fillSeries(fin.cf.fin, annualPeriods.length),
	});
	const q = raw.quarters?.companies[code];
	const quarter = q && raw.quarters
		? makeFinanceView(raw.quarters.periods, 'quarter', {
				revenue: q.is.sales,
				op: q.is.op,
				net: q.is.net,
				assets: amountSeries(tables.bs, quarterPeriodColumns(tables), ['자산총계', 'total assets'], ['유동자산']),
				liabilities: amountSeries(tables.bs, quarterPeriodColumns(tables), ['부채총계', 'total liabilities'], ['유동부채']),
				equity: amountSeries(tables.bs, quarterPeriodColumns(tables), ['자본총계', 'total equity'], ['비지배']),
				currentAssets: amountSeries(tables.bs, quarterPeriodColumns(tables), ['유동자산', 'current assets'], ['비유동']),
				currentLiabilities: amountSeries(tables.bs, quarterPeriodColumns(tables), ['유동부채', 'current liabilities'], ['비유동']),
				cfo: q.cf?.ocf ?? [],
				cfi: q.cf?.icf ?? [],
				cff: fillSeries(null, raw.quarters.periods.length),
			})
		: null;
	const modes: FinMode[] = [];
	if (quarter) modes.push('quarter');
	if (annual) modes.push('annual');
	if (!modes.length) return null;
	return {
		modes,
		views: { annual, quarter, ttm: null },
		defaultMode: quarter ? 'quarter' : 'annual',
		filedDates: {},
	};
}

function makeFinanceView(periods: string[], freq: FinFreq, s: Record<string, Num[]>): TerminalFinance | null {
	if (!periods.length || !s.revenue?.some((v) => v != null)) return null;
	const revYoy = yoy(s.revenue, freq === 'quarter' ? 4 : 1);
	const opYoy = yoy(s.op, freq === 'quarter' ? 4 : 1);
	const cashQuality = s.cfo.map((v, i) => (v != null && s.net[i] && s.net[i]! > 0 ? round(v / s.net[i]!, 2) : null));
	const margin = ratioSeries(s.op, s.revenue, 100);
	const debtRatio = ratioSeries(s.liabilities, s.equity, 100);
	const currentRatio = ratioSeries(s.currentAssets, s.currentLiabilities, 100);
	const cards: FinCard[] = [
		{ key: 'incomeBreakdown', title: '손익구조', unit: '조', series: [
			{ name: '매출', data: s.revenue, color: '#5b9bf0', type: 'bar' },
			{ name: '영업익', data: s.op, color: '#fb923c', type: 'line', axis: 'r' },
			{ name: '순익', data: s.net, color: '#34d399', type: 'line', axis: 'r' },
		] },
		{ key: 'growthYoy', title: '성장 YoY', unit: '%', series: [
			{ name: '매출', data: revYoy, color: '#5b9bf0', type: 'bar' },
			{ name: '영업익', data: opYoy, color: '#fb923c', type: 'line' },
		] },
		{ key: 'cashflowSigned', title: '현금흐름', unit: '조', series: [
			{ name: '영업', data: s.cfo, color: '#34d399', type: 'bar' },
			{ name: '투자', data: s.cfi, color: '#60a5fa', type: 'bar' },
			{ name: '재무', data: s.cff, color: '#fb923c', type: 'bar' },
		] },
		{ key: 'leverageTrend', title: '레버리지·유동', unit: '%', refLines: [100], series: [
			{ name: '부채비율', data: debtRatio, color: '#f0616f', type: 'bar' },
			{ name: '유동비율', data: currentRatio, color: '#60a5fa', type: 'line', axis: 'r' },
		] },
	];
	const statements: Record<StmtKind, StmtRow[]> = {
		IS: [
			{ key: 'revenue', kr: '매출액', en: 'Revenue', values: s.revenue },
			{ key: 'operatingIncome', kr: '영업이익', en: 'Operating income', values: s.op },
			{ key: 'netIncome', kr: '당기순이익', en: 'Net income', values: s.net },
		],
		BS: [
			{ key: 'assets', kr: '자산총계', en: 'Assets', values: s.assets },
			{ key: 'liabilities', kr: '부채총계', en: 'Liabilities', values: s.liabilities },
			{ key: 'equity', kr: '자본총계', en: 'Equity', values: s.equity },
			{ key: 'currentAssets', kr: '유동자산', en: 'Current assets', values: s.currentAssets },
			{ key: 'currentLiabilities', kr: '유동부채', en: 'Current liabilities', values: s.currentLiabilities },
		],
		CF: [
			{ key: 'cfOperating', kr: '영업활동현금흐름', en: 'Operating CF', values: s.cfo },
			{ key: 'cfInvesting', kr: '투자활동현금흐름', en: 'Investing CF', values: s.cfi },
			{ key: 'cfFinancing', kr: '재무활동현금흐름', en: 'Financing CF', values: s.cff },
		],
	};
	const ratios = [
		{ key: 'opm', kr: '영업이익률', en: 'Operating margin', unit: '%', values: margin },
		{ key: 'debtRatio', kr: '부채비율', en: 'Debt/Equity', unit: '%', values: debtRatio },
		{ key: 'currentRatio', kr: '유동비율', en: 'Current', unit: '%', values: currentRatio },
		{ key: 'earningsQuality', kr: '이익품질(CFO/NI)', en: 'Earnings quality', unit: '배', values: cashQuality },
	];
	return {
		periods,
		freq,
		cards,
		tabCards: { profitability: cards.slice(0, 2), cashflow: cards.slice(2, 3), debt: cards.slice(3), shareholder: [] },
		revYoy,
		opYoy,
		cashQuality,
		statements,
		ratios,
	};
}

function yoy(values: Num[], lag: number): Num[] {
	return values.map((v, i) => (v != null && values[i - lag] ? round(((v - values[i - lag]!) / Math.abs(values[i - lag]!)) * 100, 1) : null));
}

function fillSeries(value: Num, n: number): Num[] {
	const out = Array.from({ length: n }, () => null as Num);
	if (n > 0) out[n - 1] = value;
	return out;
}

function industryKey(sector: string): string {
	const s = sector.toLowerCase();
	if (s.includes('반도체') || s.includes('semiconductor')) return 'semiconductor';
	if (s.includes('자동차') || s.includes('auto')) return 'auto';
	if (s.includes('소프트') || s.includes('it') || s.includes('software')) return 'software';
	if (s.includes('바이오') || s.includes('제약') || s.includes('pharma')) return 'pharma';
	if (s.includes('화학') || s.includes('chemical')) return 'chemical';
	if (s.includes('금융') || s.includes('은행') || s.includes('finance')) return 'finance';
	if (s.includes('유통') || s.includes('retail')) return 'retail';
	if (s.includes('건설') || s.includes('construction')) return 'construction';
	return 'misc';
}

function profitGrade(opMargin: Num): string {
	if (opMargin == null) return '보통';
	if (opMargin < 0) return '적자';
	if (opMargin >= 15) return '우수';
	if (opMargin >= 7) return '양호';
	return '저수익';
}

function growthGrade(revCagr: Num): string {
	if (revCagr == null) return '정체';
	if (revCagr >= 15) return '고성장';
	if (revCagr >= 3) return '성장';
	if (revCagr <= -15) return '급감';
	if (revCagr < 0) return '역성장';
	return '정체';
}

function qualityGrade(fin: FinanceCompany): string {
	const cfo = fin.cf.op;
	const net = lastNonNull(fin.is.net);
	if (cfo == null || net == null || net <= 0) return '보통';
	return cfo / net >= 1 ? '우수' : cfo / net >= 0.6 ? '양호' : '주의';
}

function liquidityGrade(fin: FinanceCompany): string {
	const ca = lastNonNull(fin.bs.totals.currAsset);
	const cl = lastNonNull(fin.bs.totals.currLiab);
	if (ca == null || cl == null || cl <= 0) return '보통';
	const r = (ca / cl) * 100;
	if (r >= 180) return '우수';
	if (r >= 110) return '양호';
	if (r >= 80) return '주의';
	return '위험';
}

function stabilityGrade(debtRatio: Num): string {
	if (debtRatio == null) return '보통';
	if (debtRatio < 100) return '안정';
	if (debtRatio < 200) return '보통';
	if (debtRatio < 350) return '취약';
	return '위험';
}

function cashflowPattern(fin: FinanceCompany): string {
	if ((fin.cf.op ?? 0) < 0) return '현금위기형';
	if ((fin.cf.inv ?? 0) < 0 && (fin.cf.op ?? 0) > 0) return '성장투자형';
	return '안정형';
}

function fallbackYearRange(): string[] {
	const y = new Date().getFullYear() - 1;
	return [4, 3, 2, 1, 0].map((d) => String(y - d));
}

function regularFilingsFromPanel(panel: ClientPanelInit | null): RegularFiling[] {
	const periods = panel?.toc.periods ?? [];
	const urlByPeriod = panel?.grid?.dartUrlByPeriod ?? {};
	return periods.flatMap((period) => {
		const url = urlByPeriod[period];
		const rceptNo = rceptNoFromUrl(url);
		if (!rceptNo) return [];
		return [{
			rceptNo,
			rceptDate: rceptDateFromNo(rceptNo),
			reportType: reportTypeFromPeriod(period),
			year: period.slice(0, 4),
			url: url ?? `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`,
		}];
	});
}

function rceptNoFromUrl(url: string | null | undefined): string {
	if (!url) return '';
	const m = url.match(/rcpNo=(\d{8,})/) ?? url.match(/(\d{14})/);
	return m?.[1] ?? '';
}

function rceptDateFromNo(rceptNo: string): string {
	const s = rceptNo.slice(0, 8);
	return /^\d{8}$/.test(s) ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` : '';
}

function reportTypeFromPeriod(period: string): string {
	const key = period.toUpperCase();
	if (key.endsWith('Q4')) return '사업보고서';
	if (key.endsWith('Q2')) return '반기보고서';
	if (key.endsWith('Q1') || key.endsWith('Q3')) return '분기보고서';
	return '정기보고서';
}

function nonRegularFromEvents(payload: PriceEventsPayload | null): NonRegularFiling[] {
	const out: NonRegularFiling[] = [];
	for (const [date, events] of Object.entries(payload?.events ?? {})) {
		for (const d of events.disclosures ?? []) {
			if (['사업보고서', '반기보고서', '분기보고서'].some((name) => d.title.includes(name))) continue;
			out.push({ rceptNo: d.rceptNo, rceptDate: date, reportNm: d.title, filer: payload?.corpName ?? '', url: d.url });
		}
	}
	return out.sort((a, b) => b.rceptDate.localeCompare(a.rceptDate)).slice(0, 30);
}
