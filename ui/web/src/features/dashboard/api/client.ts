// dashboard 백엔드 API 클라이언트.
// /api/search 는 ask 모드도 사용 (공용). /api/viz/* 는 dashboard 전용.

export type PeriodKind = 'annual' | 'quarterly';

export interface SearchHit {
	stockCode: string;
	corpName: string;
	market?: string;
	sector?: string;
	products?: string;
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
	// Bloomberg/Koyfin 패턴 KPI 카드용 (운영자 디자인 제안). backend 채우면 KpiTile 가
	// 우상단 TTM + 좌하단 YoY/QoQ 동시 표시. 옛 deltaPct (prev 계산) 와 호환:
	// yoyPct/qoqPct 가 있으면 우선, 없으면 prev → deltaPct fallback.
	ttmValue?: number | null;
	yoyPct?: number | null;
	qoqPct?: number | null;
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
	// narrativeBridge — Story view 6 막 인과 자연어
	transitions?: Array<{ from: string; to: string; text: string }>;
	summaryLine?: string;
	// scoreBadge — Snowflake 5 차원 종합 평점
	grade?: string;
	overallScore?: number | null;
	dimensions?: Array<{ key: string; label: string; score: number }>;
	// bento layout — entry.layout 이 pass-through 됨 (24-col 기준, colSpan/rowSpan 1~24).
	layout?: LayoutSpec;
}

export interface LayoutSpec {
	colSpan?: number;
	rowSpan?: number;
}

export interface DashboardResponse {
	stockCode: string;
	periodKind: PeriodKind;
	cards: Record<string, RechartsSpec>;
	order: string[];
}

// 기업분석 3 탭 (financial / quant / viewer). 옛 6 탭 (portfolio/valuation/
// governance/peer/lifecycle/macro) 은 financial 안의 분석 방법론별 view 로 흡수.
// quant = 가격 시계열 + 기술/모멘텀/변동성/베타/예측/백테스트 (재무 알파 X).
export type AnalysisTab = 'financial' | 'quant' | 'viewer';

// 재무제표분석 7 분석 방법론 — 같은 회사를 그레이엄·린치·S&P·Sloan 식
// 다른 학파 시각으로 보는 lens. legacy 6 (performance/...) 은 redirect 용.
export type FinancialSubCategory =
	| 'story'
	| 'dupont'
	| 'value'
	| 'growth'
	| 'credit'
	| 'quality'
	| 'snowflake'
	// legacy (redirect)
	| 'performance'
	| 'capitalStructure'
	| 'cashflow'
	| 'risk'
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

// 회사 헤더 메타 — kindlist parquet 단일 룩업 (corpName + 시장 + 섹터 + 제품 + 블로그).
// 첫 페인트에서 회사명 받는 SSOT. fetchDashboard 로 dashboard 전체 빌드해서 corpName
// 한 글자 뽑던 회귀 차단용 (P-DASH-V2).
export interface CompanyBlogPost {
	title: string;
	slug: string;
	url: string;
}

export interface CompanyMeta {
	stockCode: string;
	corpName: string;
	market: string;
	sector: string;
	products: string[];
	blogPosts: CompanyBlogPost[];
}

export function fetchCompanyMeta(stockCode: string): Promise<CompanyMeta> {
	return fetchJson<CompanyMeta>(`/api/company/${stockCode}/meta`);
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
	colCount: number;
	layout: PackedCard[];
	cards: Record<string, RechartsSpec>;
	// eager 외 카드 — frontend 가 viewport 진입 시 fetchCard 로 spec 받음.
	lazyKeys?: string[];
}

export function fetchTabLayout(
	tab: AnalysisTab,
	stockCode: string,
	view: string | null = null,
	periodKind: PeriodKind = 'annual',
	nPeriods = 40,
	layoutOnly = false,
	eagerN = 6,
): Promise<TabLayoutResponse> {
	const qs = new URLSearchParams({ periodKind, nPeriods: String(nPeriods), eagerN: String(eagerN) });
	if (view) qs.set('view', view);
	if (layoutOnly) qs.set('layoutOnly', 'true');
	return fetchJson<TabLayoutResponse>(`/api/viz/layout/${tab}/${stockCode}?${qs}`);
}

// ── 공시뷰어 panel grid (panel SSOT — 항목 × 기간 wide) ──
// 서버는 panel wide 를 JSON 직렬화만(pass-through), 프론트가 격자를 직접 렌더.
// diff/timeline/캡션은 순수 UI (인접 period 셀 비교 + window slice).

export interface PanelTocBlock {
	blockLeaf: string;
	rowCount: number;
}

export interface PanelTocSection {
	sectionLeaf: string;
	sectionKey: string; // `${chapter}␟${sectionLeaf}` — 동명 sectionLeaf 충돌 방지
	rowCount: number;
	blocks: PanelTocBlock[];
}

export interface PanelTocChapter {
	chapter: string;
	sections: PanelTocSection[];
}

export interface PanelTocResponse {
	stockCode: string;
	corpName: string;
	chapters: PanelTocChapter[];
	periods: string[]; // 전체 기간 축 (최신좌측) — timeline SSOT
}

export interface PanelRow {
	chapter: string;
	sectionLeaf: string;
	blockLeaf: string;
	disclosureKey: string | null; // null = narrative 행
	scope: string | null;
	blockType: 'text' | 'table';
	cells: Record<string, string>; // period → 셀 본문 (raw DART XML, tag=True)
}

export interface PanelGridResponse {
	stockCode: string;
	corpName: string;
	chapter: string | null;
	sectionLeaf: string | null;
	sectionKey: string;
	periods: string[];
	rows: PanelRow[];
	dartUrlByPeriod?: Record<string, string | null>;
}

export interface PanelInitResponse {
	stockCode: string;
	corpName: string;
	toc: PanelTocResponse;
	firstChapter: string | null;
	firstSectionKey: string | null;
	grid: PanelGridResponse | null;
}

export function fetchPanelInit(stockCode: string): Promise<PanelInitResponse> {
	return fetchJson<PanelInitResponse>(`/api/company/${stockCode}/panel/init`);
}

export function fetchPanelToc(stockCode: string): Promise<PanelTocResponse> {
	return fetchJson<PanelTocResponse>(`/api/company/${stockCode}/panel/toc`);
}

export function fetchPanelGrid(
	stockCode: string,
	sectionKey: string,
	periods?: string[],
	block?: string,
): Promise<PanelGridResponse> {
	const qs = new URLSearchParams({ section: sectionKey });
	if (periods?.length) qs.set('periods', periods.join(','));
	if (block) qs.set('block', block);
	return fetchJson<PanelGridResponse>(`/api/company/${stockCode}/panel?${qs}`);
}
