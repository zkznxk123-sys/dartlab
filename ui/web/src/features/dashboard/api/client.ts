// dashboard 백엔드 API 클라이언트.
// /api/search 는 ask 모드도 사용 (공용). /api/viz/* 는 dashboard 전용.

export type PeriodKind = 'annual' | 'quarterly';

export interface SearchHit {
	stockCode: string;
	corpName: string;
	market?: string;
	sector?: string;
	score?: number;
}

interface SearchResponse {
	results: SearchHit[];
	fuzzy: boolean;
}

export interface RechartsSeries {
	key: string;
	label: string;
	color: string;
	type: 'bar' | 'line' | 'area';
	data: (number | null)[];
	unit?: string;
	axis?: 'left' | 'right';
	stack?: string;
	intent?: 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';
}

export interface KpiTileItem {
	label: string;
	value: number | null;
	prev?: number | null;
	unit?: string;
	intent?: 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';
	subtitle?: string;
	// P-DASH-V1 D11 — 카드 빈 공간 fix.
	sparkline?: number[];
	rangeMin?: number | null;
	rangeMax?: number | null;
}

export interface TopListItem {
	label: string;
	value?: number | null;
	unit?: string;
	delta?: number | null;
	description?: string;
}

export interface ComparisonRow {
	label: string;
	self?: number | null;
	peerMedian?: number | null;
	peerP25?: number | null;
	peerP75?: number | null;
	percentile?: number | null;
	unit?: string;
	higherIsBetter?: boolean;
}

export interface GaugeBand {
	fromValue: number;
	toValue: number;
	label: string;
	intent?: 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';
}

export interface SankeyNodeSpec { name: string; }
export interface SankeyLinkSpec { source: number; target: number; value: number; }
export interface ScatterPointSpec {
	x: number;
	y: number;
	label: string;
	self?: boolean;
}
export interface HeatmapCellSpec {
	row: string;
	col: string;
	value: number | null;
	unit?: string;
}

export interface RechartsSpec {
	componentType: string;
	kind: string;
	title: string;
	categories: string[];
	series: RechartsSeries[];
	options: Record<string, unknown>;
	evidenceBinding?: Record<string, unknown>;
	meta?: Record<string, unknown>;
	cardKey?: string;
	error?: string;
	// kind 별 추가 필드 (옵셔널 — 해당 kind 일 때만 채워짐)
	tiles?: KpiTileItem[];
	periodLabel?: string;
	items?: TopListItem[];
	direction?: 'asc' | 'desc';
	rows?: ComparisonRow[];
	peerCount?: number;
	value?: number | null;
	minValue?: number;
	maxValue?: number;
	bands?: GaugeBand[];
	subtitle?: string;
	phases?: string[];
	current?: number;
	confidence?: number | null;
	nodes?: SankeyNodeSpec[];
	links?: SankeyLinkSpec[];
	points?: ScatterPointSpec[];
	xLabel?: string;
	yLabel?: string;
	xUnit?: string;
	yUnit?: string;
	xRef?: number | null;
	yRef?: number | null;
	cells?: HeatmapCellSpec[];
	rowOrder?: string[];
	colOrder?: string[];
	tone?: 'sequential' | 'diverging';
	// bento layout — entry.layout 이 pass-through 됨 (colSpan 1~4, rowSpan 1~3)
	layout?: LayoutSpec;
}

export interface LayoutSpec {
	colSpan?: 1 | 2 | 3 | 4;
	rowSpan?: 1 | 2 | 3 | 4 | 5 | 6;
}

export interface DashboardResponse {
	stockCode: string;
	periodKind: PeriodKind;
	cards: Record<string, RechartsSpec>;
	order: string[];
}

export type AnalysisTab =
	| 'financial'
	| 'portfolio'
	| 'valuation'
	| 'governance'
	| 'peer'
	| 'lifecycle'
	| 'macro'
	| 'viewer';

// P-DASH-V1 D7: growth + profitability → performance 통합.
// legacy 호환을 위해 union 에 남김 — URL 진입은 redirect.
export type FinancialSubCategory =
	| 'performance'
	| 'capitalStructure'
	| 'cashflow'
	| 'risk'
	| 'growth'
	| 'profitability';

export interface CatalogCard {
	cardKey: string;
	title: string;
	kind: string;
	topic: string;
	tab?: AnalysisTab;
	subCategory?: FinancialSubCategory | '';
	xlSpan: 1 | 2 | 3;
	seriesCount: number;
	help: string;
}

export interface CatalogResponse {
	cards: CatalogCard[];
	dashboardKeys: string[];
}

async function fetchJson<T>(url: string): Promise<T> {
	const r = await fetch(url);
	if (!r.ok) throw new Error(`HTTP ${r.status} on ${url}`);
	return (await r.json()) as T;
}

export function searchCompanies(q: string, limit = 8): Promise<SearchHit[]> {
	const qs = new URLSearchParams({ q });
	return fetchJson<SearchResponse>(`/api/search?${qs}`).then((r) => (r.results || []).slice(0, limit));
}

export function fetchDashboard(
	stockCode: string,
	periodKind: PeriodKind = 'annual',
	nPeriods = 8,
): Promise<DashboardResponse> {
	const qs = new URLSearchParams({ periodKind, nPeriods: String(nPeriods) });
	return fetchJson<DashboardResponse>(`/api/viz/dashboard/${stockCode}?${qs}`);
}

export interface TabDashboardResponse {
	stockCode: string;
	tab: AnalysisTab;
	periodKind: PeriodKind;
	cards: Record<string, RechartsSpec>;
	order: string[];
}

export function fetchTabDashboard(
	tab: AnalysisTab,
	stockCode: string,
	periodKind: PeriodKind = 'annual',
	nPeriods = 40,
): Promise<TabDashboardResponse> {
	const qs = new URLSearchParams({ periodKind, nPeriods: String(nPeriods) });
	return fetchJson<TabDashboardResponse>(`/api/viz/tab/${tab}/${stockCode}?${qs}`);
}

export function fetchCard(
	cardKey: string,
	stockCode: string,
	periodKind: PeriodKind = 'annual',
	nPeriods = 8,
): Promise<RechartsSpec> {
	const qs = new URLSearchParams({ periodKind, nPeriods: String(nPeriods) });
	return fetchJson<RechartsSpec>(`/api/viz/spec/${cardKey}/${stockCode}?${qs}`);
}

export function fetchCatalog(): Promise<CatalogResponse> {
	return fetchJson<CatalogResponse>('/api/viz/catalog');
}

// ── Layout Engine — bento packed grid (P-DASH-V1) ──

export interface PackedCard {
	cardKey: string;
	kind: string;
	title: string;
	x: number;
	y: number;
	w: number;
	h: number;
}

export interface TabLayoutResponse {
	stockCode: string;
	tab: AnalysisTab;
	view: string | null;
	periodKind: PeriodKind;
	layout: PackedCard[];
	cards: Record<string, RechartsSpec>;
}

export function fetchTabLayout(
	tab: AnalysisTab,
	stockCode: string,
	view: string | null = null,
	periodKind: PeriodKind = 'annual',
	nPeriods = 40,
): Promise<TabLayoutResponse> {
	const qs = new URLSearchParams({ periodKind, nPeriods: String(nPeriods) });
	if (view) qs.set('view', view);
	return fetchJson<TabLayoutResponse>(`/api/viz/layout/${tab}/${stockCode}?${qs}`);
}
