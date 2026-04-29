import { fmtKrw, fmtPrice } from '$lib/format/krw';
import { fmtMul, fmtPct } from '$lib/format/pct';
import type {
	LiveCompanyBundle,
	LiveCompanyChange,
	LiveCompanyDocExcerpt,
	LiveCompanyReportFact,
	StatementDashboard,
	StatementGroupRow,
	StatementKey
} from './companyLive';
import type { StoryManifest, StoryManifestDashboardQuestion } from './storyDashboard';

export type PeriodMode = 'Q' | 'TTM' | 'Y';
export type Tone = 'good' | 'bad' | 'neutral' | 'watch' | 'missing';
export type FinancialChartKind =
	| 'small-multiples'
	| 'lines'
	| 'stacked-share'
	| 'signed-bars'
	| 'waterfall'
	| 'matrix'
	| 'valuation';

export interface DashboardSeries {
	id: string;
	label: string;
	values: Array<number | null>;
	unit: string;
	color: string;
	type?: 'bar' | 'line';
}

export interface DashboardMetric {
	id: string;
	label: string;
	value: string;
	raw: number | null;
	unit: string;
	delta: string;
	deltaTone: Tone;
	tone: Tone;
	period: string | null;
	series: Array<number | null>;
	note?: string;
}

export interface FinancialChart {
	id: string;
	title: string;
	subtitle: string;
	kind: FinancialChartKind;
	categories: string[];
	series: DashboardSeries[];
	unit: string;
	sourceLabel: string;
	emptyLabel?: string;
}

export interface FinancialTableRow {
	key: string;
	label: string;
	unit: string;
	values: Array<number | string | null>;
	yoy: number | null;
	source: string;
	raw?: StatementGroupRow;
}

export interface FinancialTableGroup {
	key: string;
	label: string;
	periods: string[];
	rows: FinancialTableRow[];
	statement: StatementKey;
}

export interface EvidenceLink {
	label: string;
	value: string;
	topic: 'finance' | 'report' | 'docs' | 'price' | 'map' | 'peer';
}

export interface DashboardQuestionView {
	id: string;
	question: string;
	tocLabel: string;
	answer: string;
	metrics: DashboardMetric[];
	charts: FinancialChart[];
	tableGroups: FinancialTableGroup[];
	evidenceLinks: EvidenceLink[];
	statementKeys: StatementKey[];
}

export interface CompanyDashboardView {
	title: string;
	subtitle: string;
	tags: string[];
	latestPeriod: string | null;
	periodMode: PeriodMode;
	kpis: DashboardMetric[];
	questions: DashboardQuestionView[];
	statementPanels: FinancialTableGroup[];
	forbiddenLabels: string[];
}

interface BuildCompanyDashboardInput {
	manifest: StoryManifest | null;
	company: LiveCompanyBundle | null;
	dashboards: Record<StatementKey, StatementDashboard>;
	facts: LiveCompanyReportFact[];
	docs: LiveCompanyDocExcerpt[];
	changes: LiveCompanyChange[];
	periodMode: PeriodMode;
}

const DEFAULT_QUESTIONS: StoryManifestDashboardQuestion[] = [
	{
		id: 'overview',
		question: '한눈에 결론은 무엇인가?',
		tocLabel: '결론',
		sectionKeys: ['종합평가'],
		blockKeys: ['scorecard', 'summaryFlags', 'creditScore', 'peerPosition'],
		statementKeys: ['IS', 'BS', 'CF'],
		evidenceTopics: ['finance', 'report', 'docs', 'map', 'price', 'peer'],
		vizKeys: ['kpi_sparklines', 'peer_position_radar']
	},
	{
		id: 'business',
		question: '이 회사는 무엇으로 돈을 버나?',
		tocLabel: '수익원',
		sectionKeys: ['수익구조'],
		blockKeys: ['profile', 'segmentComposition', 'growth', 'concentration', 'revenueQuality'],
		statementKeys: ['IS'],
		evidenceTopics: ['finance', 'docs', 'map'],
		vizKeys: ['is_revenue_profit', 'report_evidence_matrix']
	},
	{
		id: 'profit',
		question: '번 돈은 얼마나 남나?',
		tocLabel: '수익성',
		sectionKeys: ['수익성', '비용구조'],
		blockKeys: ['marginTrend', 'returnTrend', 'costBreakdown', 'profitabilityFlags'],
		statementKeys: ['IS'],
		evidenceTopics: ['finance', 'docs'],
		vizKeys: ['is_margin_trend', 'is_revenue_profit']
	},
	{
		id: 'cash',
		question: '이익은 현금으로 바뀌나?',
		tocLabel: '현금',
		sectionKeys: ['현금흐름', '이익품질'],
		blockKeys: ['cashFlowOverview', 'cashQuality', 'ocfDecomposition', 'accrualAnalysis'],
		statementKeys: ['IS', 'CF'],
		evidenceTopics: ['finance', 'report', 'docs'],
		vizKeys: ['cf_signed_flow', 'cf_waterfall']
	},
	{
		id: 'stability',
		question: '자산과 부채 구조는 안전한가?',
		tocLabel: '안정성',
		sectionKeys: ['안정성', '자금조달'],
		blockKeys: ['leverageTrend', 'coverageTrend', 'distressScore', 'fundingSources'],
		statementKeys: ['BS', 'CF'],
		evidenceTopics: ['finance', 'report', 'docs'],
		vizKeys: ['bs_capital_structure', 'bs_debt_ratio_trend']
	},
	{
		id: 'allocation',
		question: '번 돈은 어디에 묶이고 어디에 재투자되나?',
		tocLabel: '자산배치',
		sectionKeys: ['자본배분', '자산구조'],
		blockKeys: ['assetStructure', 'workingCapital', 'capexPattern', 'fcfUsage', 'reinvestment', 'dividendPolicy'],
		statementKeys: ['BS', 'CF'],
		evidenceTopics: ['finance', 'report', 'docs'],
		vizKeys: ['bs_asset_composition', 'capital_allocation_flow']
	},
	{
		id: 'valuation',
		question: '현재 가격은 무엇을 반영하나?',
		tocLabel: '가격',
		sectionKeys: ['가치평가', '비교분석', '시장분석'],
		blockKeys: ['valuationSynthesis', 'relativeValuation', 'priceTarget', 'peerPosition'],
		statementKeys: ['IS', 'BS', 'CF'],
		evidenceTopics: ['finance', 'price', 'peer', 'macro'],
		vizKeys: ['valuation_multiples', 'peer_position_radar']
	},
	{
		id: 'evidence',
		question: '보고서와 원문은 숫자를 뒷받침하나?',
		tocLabel: '근거',
		sectionKeys: ['storyValidation', '공시변화', '지배구조'],
		blockKeys: ['storyPrecedents', 'plausibilityBand', 'valuationSins', 'disclosureChangeSummary'],
		statementKeys: ['IS', 'BS', 'CF'],
		evidenceTopics: ['finance', 'report', 'docs'],
		vizKeys: ['report_evidence_matrix']
	}
];

const COLORS = {
	revenue: '#60a5fa',
	op: '#fb923c',
	net: '#34d399',
	margin: '#fbbf24',
	bad: '#ea4647',
	cash: '#38bdf8',
	receivables: '#818cf8',
	inventory: '#fbbf24',
	tangible: '#fb923c',
	intangible: '#c084fc',
	other: '#64748b',
	liabilities: '#ea4647',
	equity: '#34d399',
	ocf: '#34d399',
	icf: '#60a5fa',
	financing: '#c084fc',
	fcf: '#fb923c',
	price: '#f8fafc'
};

export function buildCompanyDashboardView(input: BuildCompanyDashboardInput): CompanyDashboardView {
	const questions = dashboardQuestions(input.manifest);
	const ctx = makeContext(input);
	const kpis = buildKpis(ctx);
	const questionViews = questions.map((question) => buildQuestionView(question, ctx));
	const ego = input.company?.companyMeta?.ego;
	const tags = [input.company?.stockCode, ego?.market, ego?.industry, ego?.stage, ego?.role]
		.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
		.slice(0, 5);

	return {
		title: ego?.corpName ?? input.company?.stockCode ?? 'Company',
		subtitle: [ego?.industry, ego?.role].filter(Boolean).join(' · ') || '재무제표와 보고서 근거 기반 분석',
		tags,
		latestPeriod: latestPeriod(input.dashboards),
		periodMode: input.periodMode,
		kpis,
		questions: questionViews,
		statementPanels: statementTableGroups(input.dashboards),
		forbiddenLabels: ['제1막', '제6막', 'HF', 'HuggingFace']
	};
}

function dashboardQuestions(manifest: StoryManifest | null): StoryManifestDashboardQuestion[] {
	const qs = manifest?.dashboardQuestions;
	if (qs?.length === 8) return qs;
	return DEFAULT_QUESTIONS;
}

function makeContext(input: BuildCompanyDashboardInput) {
	return {
		...input,
		price: input.company?.price ?? null,
		ego: input.company?.companyMeta?.ego ?? null
	};
}

function buildKpis(ctx: ReturnType<typeof makeContext>): DashboardMetric[] {
	const revenue = normalizedSeries(ctx.dashboards.IS, 'revenue', ctx.periodMode, 'flow');
	const op = normalizedSeries(ctx.dashboards.IS, 'op', ctx.periodMode, 'flow');
	const net = normalizedSeries(ctx.dashboards.IS, 'net', ctx.periodMode, 'flow');
	const opMargin = ratioSeries(op.values, revenue.values);
	const equity = normalizedSeries(ctx.dashboards.BS, 'equity', ctx.periodMode, 'stock');
	const roe = ratioSeries(net.values, equity.values);
	const liabilities = normalizedSeries(ctx.dashboards.BS, 'liabilities', ctx.periodMode, 'stock');
	const debtRatio = ratioSeries(liabilities.values, equity.values);
	const ocf = normalizedSeries(ctx.dashboards.CF, 'ocf', ctx.periodMode, 'flow');
	const fcf = fcfSeries(ctx.dashboards.CF, ctx.periodMode);

	return [
		metric('revenue', '매출', revenue.values, revenue.categories, 'KRW', 'amount', ctx.periodMode),
		metric('op', '영업이익', op.values, op.categories, 'KRW', 'amount', ctx.periodMode),
		metric('net', '순이익', net.values, net.categories, 'KRW', 'amount', ctx.periodMode),
		metric('opMargin', '영업이익률', opMargin, revenue.categories, '%', 'pct', ctx.periodMode, {
			watchAbsAbove: 100
		}),
		metric('roe', 'ROE', roe, equity.categories, '%', 'pct', ctx.periodMode, { watchAbsAbove: 100 }),
		metric('debtRatio', '부채비율', debtRatio, equity.categories, '%', 'pct', ctx.periodMode),
		combinedMetric('cashflow', 'OCF/FCF', ocf.values, fcf.values, ocf.categories, ctx.periodMode),
		{
			id: 'valuation',
			label: 'PER/PBR',
			value: `${fmtMul(ctx.price?.per)} / ${fmtMul(ctx.price?.pbr)}`,
			raw: ctx.price?.per ?? null,
			unit: 'x',
			delta: ctx.price?.dividendYield == null ? '' : `배당 ${fmtPct(ctx.price.dividendYield)}`,
			deltaTone: 'neutral',
			tone: ctx.price?.per == null && ctx.price?.pbr == null ? 'missing' : 'neutral',
			period: ctx.price?.snapshotAt ?? null,
			series: [],
			note: ctx.price?.currentPrice ? fmtPrice(ctx.price.currentPrice) : undefined
		}
	];
}

function buildQuestionView(
	question: StoryManifestDashboardQuestion,
	ctx: ReturnType<typeof makeContext>
): DashboardQuestionView {
	const charts = chartsForQuestion(question.id, ctx);
	const metrics = metricsForQuestion(question.id, ctx);
	const tableGroups = tableGroupsForQuestion(question.id, ctx.dashboards);
	const evidenceLinks = evidenceLinksForQuestion(question, ctx);

	return {
		id: `q-${question.id}`,
		question: question.question,
		tocLabel: question.tocLabel,
		answer: answerForQuestion(question.id, metrics, ctx),
		metrics,
		charts,
		tableGroups,
		evidenceLinks,
		statementKeys: question.statementKeys
	};
}

function metricsForQuestion(id: string, ctx: ReturnType<typeof makeContext>): DashboardMetric[] {
	const kpis = buildKpis(ctx);
	const byId = new Map(kpis.map((item) => [item.id, item]));
	if (id === 'overview') return pick(byId, ['revenue', 'opMargin', 'debtRatio', 'cashflow', 'valuation']);
	if (id === 'business') return pick(byId, ['revenue', 'op', 'net', 'opMargin']);
	if (id === 'profit') return pick(byId, ['op', 'net', 'opMargin', 'roe']);
	if (id === 'cash') return pick(byId, ['net', 'cashflow']);
	if (id === 'stability') return pick(byId, ['debtRatio']);
	if (id === 'allocation') return allocationMetrics(ctx);
	if (id === 'valuation') return pick(byId, ['valuation', 'revenue', 'opMargin', 'roe']);
	return [
		textMetric('reportFacts', '정기보고서', `${ctx.facts.length}개`, ctx.facts.length ? 'neutral' : 'missing'),
		textMetric('docs', '원문 발췌', `${ctx.docs.length}개`, ctx.docs.length ? 'neutral' : 'missing'),
		textMetric('changes', '공시 변화', `${ctx.changes.length}개`, ctx.changes.length ? 'watch' : 'neutral')
	];
}

function allocationMetrics(ctx: ReturnType<typeof makeContext>): DashboardMetric[] {
	const assets = latestValue(normalizedSeries(ctx.dashboards.BS, 'assets', ctx.periodMode, 'stock').values);
	const cash = latestValue(normalizedSeries(ctx.dashboards.BS, 'cash', ctx.periodMode, 'stock').values);
	const inventory = latestValue(normalizedSeries(ctx.dashboards.BS, 'inventory', ctx.periodMode, 'stock').values);
	const tangible = latestValue(normalizedSeries(ctx.dashboards.BS, 'tangible', ctx.periodMode, 'stock').values);
	const fcf = latestValue(fcfSeries(ctx.dashboards.CF, ctx.periodMode).values);
	return [
		singleMetric('cashShare', '현금/자산', ratio(cash, assets), '%'),
		singleMetric('inventoryShare', '재고/자산', ratio(inventory, assets), '%'),
		singleMetric('tangibleShare', '유형자산/자산', ratio(tangible, assets), '%'),
		singleMetric('fcfLatest', 'FCF', fcf, 'KRW')
	];
}

function chartsForQuestion(id: string, ctx: ReturnType<typeof makeContext>): FinancialChart[] {
	if (id === 'overview') return [isSmallMultiples(ctx), fundingChart(ctx)].filter(Boolean) as FinancialChart[];
	if (id === 'business') return [isSmallMultiples(ctx), evidenceMatrix(ctx)].filter(Boolean) as FinancialChart[];
	if (id === 'profit') return [marginChart(ctx), isSmallMultiples(ctx)].filter(Boolean) as FinancialChart[];
	if (id === 'cash') return [cashFlowChart(ctx), cashWaterfall(ctx)].filter(Boolean) as FinancialChart[];
	if (id === 'stability') return [fundingChart(ctx), debtRatioChart(ctx)].filter(Boolean) as FinancialChart[];
	if (id === 'allocation') return [assetMixChart(ctx), capitalAllocationChart(ctx)].filter(Boolean) as FinancialChart[];
	if (id === 'valuation') return [valuationChart(ctx), marginChart(ctx)].filter(Boolean) as FinancialChart[];
	return [evidenceMatrix(ctx)].filter(Boolean) as FinancialChart[];
}

function isSmallMultiples(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const revenue = normalizedSeries(ctx.dashboards.IS, 'revenue', ctx.periodMode, 'flow');
	const op = normalizedSeries(ctx.dashboards.IS, 'op', ctx.periodMode, 'flow');
	const net = normalizedSeries(ctx.dashboards.IS, 'net', ctx.periodMode, 'flow');
	if (!hasAny([revenue.values, op.values, net.values])) return null;
	return {
		id: 'is-small-multiples',
		title: '매출과 이익을 같은 축에 뭉개지 않고 본다',
		subtitle: '매출, 영업이익, 순이익을 각각의 높이로 비교하고 마진은 별도 차트에서 본다.',
		kind: 'small-multiples',
		categories: revenue.categories,
		series: [
			series('revenue', '매출', revenue.values, 'KRW', COLORS.revenue, 'bar'),
			series('op', '영업이익', op.values, 'KRW', COLORS.op, 'bar'),
			series('net', '순이익', net.values, 'KRW', COLORS.net, 'bar')
		],
		unit: 'KRW',
		sourceLabel: ctx.dashboards.IS.quality.sourceLabel,
		emptyLabel: 'IS 데이터 없음'
	};
}

function marginChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const revenue = normalizedSeries(ctx.dashboards.IS, 'revenue', ctx.periodMode, 'flow');
	const op = normalizedSeries(ctx.dashboards.IS, 'op', ctx.periodMode, 'flow');
	const net = normalizedSeries(ctx.dashboards.IS, 'net', ctx.periodMode, 'flow');
	const opMargin = ratioSeries(op.values, revenue.values);
	const netMargin = ratioSeries(net.values, revenue.values);
	if (!hasAny([opMargin, netMargin])) return null;
	return {
		id: 'is-margin-lines',
		title: '얼마나 남는가',
		subtitle: '마진은 매출 규모와 분리해서 보며, 100% 초과 값은 구조 확인 대상으로 둔다.',
		kind: 'lines',
		categories: revenue.categories,
		series: [
			series('opMargin', '영업이익률', opMargin, '%', COLORS.op, 'line'),
			series('netMargin', '순이익률', netMargin, '%', COLORS.net, 'line')
		],
		unit: '%',
		sourceLabel: ctx.dashboards.IS.quality.sourceLabel
	};
}

function fundingChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const liab = normalizedSeries(ctx.dashboards.BS, 'liabilities', ctx.periodMode, 'stock');
	const equity = normalizedSeries(ctx.dashboards.BS, 'equity', ctx.periodMode, 'stock');
	if (!hasAny([liab.values, equity.values])) return null;
	return {
		id: 'bs-funding',
		title: '자산은 부채와 자본으로 조달된다',
		subtitle: '부채와 자본의 비중을 같은 100% 기준에서 비교한다.',
		kind: 'stacked-share',
		categories: liab.categories,
		series: [
			series('liabilities', '부채', liab.values, 'KRW', COLORS.liabilities, 'bar'),
			series('equity', '자본', equity.values, 'KRW', COLORS.equity, 'bar')
		],
		unit: 'KRW',
		sourceLabel: ctx.dashboards.BS.quality.sourceLabel
	};
}

function debtRatioChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const liab = normalizedSeries(ctx.dashboards.BS, 'liabilities', ctx.periodMode, 'stock');
	const equity = normalizedSeries(ctx.dashboards.BS, 'equity', ctx.periodMode, 'stock');
	const debtRatio = ratioSeries(liab.values, equity.values);
	if (!hasAny([debtRatio])) return null;
	return {
		id: 'bs-debt-ratio',
		title: '레버리지 압력',
		subtitle: '부채비율 추이를 보고 자금조달 부담이 커지는지 확인한다.',
		kind: 'lines',
		categories: liab.categories,
		series: [series('debtRatio', '부채비율', debtRatio, '%', COLORS.bad, 'line')],
		unit: '%',
		sourceLabel: ctx.dashboards.BS.quality.sourceLabel
	};
}

function assetMixChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const bs = ctx.dashboards.BS;
	const assets = normalizedSeries(bs, 'assets', ctx.periodMode, 'stock');
	const cash = normalizedSeries(bs, 'cash', ctx.periodMode, 'stock');
	const receivables = normalizedSeries(bs, 'receivables', ctx.periodMode, 'stock');
	const inventory = normalizedSeries(bs, 'inventory', ctx.periodMode, 'stock');
	const tangible = normalizedSeries(bs, 'tangible', ctx.periodMode, 'stock');
	const intangible = normalizedSeries(bs, 'intangible', ctx.periodMode, 'stock');
	const other = residualSeries(assets.values, [
		cash.values,
		receivables.values,
		inventory.values,
		tangible.values,
		intangible.values
	]);
	if (!hasAny([assets.values, cash.values, receivables.values, inventory.values, tangible.values, intangible.values, other])) {
		return null;
	}
	return {
		id: 'bs-asset-mix',
		title: '총자산은 어디에 묶여 있나',
		subtitle: '현금, 채권, 재고, 유형·무형자산과 잔여 자산을 같은 총자산 기준으로 비교한다.',
		kind: 'stacked-share',
		categories: assets.categories,
		series: [
			series('cash', '현금', cash.values, 'KRW', COLORS.cash, 'bar'),
			series('receivables', '매출채권', receivables.values, 'KRW', COLORS.receivables, 'bar'),
			series('inventory', '재고', inventory.values, 'KRW', COLORS.inventory, 'bar'),
			series('tangible', '유형자산', tangible.values, 'KRW', COLORS.tangible, 'bar'),
			series('intangible', '무형자산', intangible.values, 'KRW', COLORS.intangible, 'bar'),
			series('otherAssets', '기타/비영업', other, 'KRW', COLORS.other, 'bar')
		],
		unit: 'KRW',
		sourceLabel: bs.quality.sourceLabel
	};
}

function cashFlowChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const ocf = normalizedSeries(ctx.dashboards.CF, 'ocf', ctx.periodMode, 'flow');
	const icf = normalizedSeries(ctx.dashboards.CF, 'icf', ctx.periodMode, 'flow');
	const fin = normalizedSeries(ctx.dashboards.CF, 'financingCf', ctx.periodMode, 'flow');
	const fcf = fcfSeries(ctx.dashboards.CF, ctx.periodMode);
	if (!hasAny([ocf.values, icf.values, fin.values, fcf.values])) return null;
	return {
		id: 'cf-signed',
		title: '현금흐름은 0축 기준으로 본다',
		subtitle: '영업CF, 투자CF, 재무CF, FCF를 signed bar로 나눠 현금 창출과 사용을 분리한다.',
		kind: 'signed-bars',
		categories: ocf.categories,
		series: [
			series('ocf', '영업CF', ocf.values, 'KRW', COLORS.ocf, 'bar'),
			series('icf', '투자CF', icf.values, 'KRW', COLORS.icf, 'bar'),
			series('financingCf', '재무CF', fin.values, 'KRW', COLORS.financing, 'bar'),
			series('fcf', 'FCF', fcf.values, 'KRW', COLORS.fcf, 'bar')
		],
		unit: 'KRW',
		sourceLabel: ctx.dashboards.CF.quality.sourceLabel
	};
}

function cashWaterfall(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const cf = ctx.dashboards.CF;
	const ocf = latestValue(normalizedSeries(cf, 'ocf', ctx.periodMode, 'flow').values);
	const icf = latestValue(normalizedSeries(cf, 'icf', ctx.periodMode, 'flow').values);
	const fin = latestValue(normalizedSeries(cf, 'financingCf', ctx.periodMode, 'flow').values);
	const closing = latestValue(normalizedSeries(cf, 'closingCash', ctx.periodMode, 'stock').values);
	const values = [ocf, icf, fin, closing];
	if (!values.some(isFiniteNumber)) return null;
	return {
		id: 'cf-waterfall',
		title: '최신 현금 브릿지',
		subtitle: '영업, 투자, 재무활동이 기말현금에 어떻게 이어지는지 본다.',
		kind: 'waterfall',
		categories: ['영업CF', '투자CF', '재무CF', '기말현금'],
		series: [series('waterfall', '현금흐름', values, 'KRW', COLORS.ocf, 'bar')],
		unit: 'KRW',
		sourceLabel: cf.quality.sourceLabel
	};
}

function capitalAllocationChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const cf = ctx.dashboards.CF;
	const fcf = fcfSeries(cf, ctx.periodMode);
	const capex = normalizedSeries(cf, 'capex', ctx.periodMode, 'flow');
	const dividend = normalizedSeries(cf, 'dividendPaid', ctx.periodMode, 'flow');
	const financing = normalizedSeries(cf, 'financingCf', ctx.periodMode, 'flow');
	if (!hasAny([fcf.values, capex.values, dividend.values, financing.values])) return null;
	return {
		id: 'capital-allocation',
		title: 'FCF 이후 어디로 갔나',
		subtitle: '투자, 배당, 재무CF를 FCF와 비교해 자본배분 방향을 본다.',
		kind: 'signed-bars',
		categories: fcf.categories,
		series: [
			series('fcf', 'FCF', fcf.values, 'KRW', COLORS.fcf, 'bar'),
			series('capex', 'CAPEX', capex.values, 'KRW', COLORS.tangible, 'bar'),
			series('dividendPaid', '배당', dividend.values, 'KRW', COLORS.net, 'bar'),
			series('financingCf', '재무CF', financing.values, 'KRW', COLORS.financing, 'bar')
		],
		unit: 'KRW',
		sourceLabel: cf.quality.sourceLabel
	};
}

function valuationChart(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const values = [ctx.price?.per ?? null, ctx.price?.pbr ?? null, ctx.price?.dividendYield ?? null];
	if (!values.some(isFiniteNumber)) return null;
	return {
		id: 'valuation-bars',
		title: '가격은 어떤 배수를 말하나',
		subtitle: 'PER, PBR, 배당수익률을 실적과 함께 해석한다.',
		kind: 'valuation',
		categories: ['PER', 'PBR', '배당수익률'],
		series: [series('valuation', '시장가격', values, 'x/%', COLORS.price, 'bar')],
		unit: 'x/%',
		sourceLabel: '시장가격'
	};
}

function evidenceMatrix(ctx: ReturnType<typeof makeContext>): FinancialChart | null {
	const values = [ctx.facts.length, ctx.docs.length, ctx.changes.length];
	return {
		id: 'evidence-matrix',
		title: '숫자와 원문 근거 연결',
		subtitle: '정기보고서, 사업보고서 원문, 공시 변화를 같은 근거 레이어로 묶는다.',
		kind: 'matrix',
		categories: ['정기보고서', '원문', '공시변화'],
		series: [series('evidence', '근거', values, 'count', COLORS.fcf, 'bar')],
		unit: 'count',
		sourceLabel: '근거'
	};
}

function tableGroupsForQuestion(
	id: string,
	dashboards: Record<StatementKey, StatementDashboard>
): FinancialTableGroup[] {
	if (id === 'business' || id === 'profit') return groupsFor(dashboards.IS, ['revenue', 'cost', 'profit']);
	if (id === 'cash') return groupsFor(dashboards.CF, ['operating', 'investing', 'financing']);
	if (id === 'stability') return groupsFor(dashboards.BS, ['liabilities', 'equity']);
	if (id === 'allocation') return [...groupsFor(dashboards.BS, ['assets']), ...groupsFor(dashboards.CF, ['investing', 'financing'])];
	if (id === 'valuation') return [...groupsFor(dashboards.IS, ['revenue', 'profit']), ...groupsFor(dashboards.BS, ['equity'])];
	if (id === 'evidence') return [];
	return [...groupsFor(dashboards.IS, ['revenue', 'profit']), ...groupsFor(dashboards.BS, ['assets', 'liabilities']), ...groupsFor(dashboards.CF, ['operating'])];
}

function statementTableGroups(dashboards: Record<StatementKey, StatementDashboard>): FinancialTableGroup[] {
	return [dashboards.IS, dashboards.BS, dashboards.CF].flatMap((dashboard) =>
		dashboard.groups.map((group) => ({
			key: `${dashboard.topic}-${group.key}`,
			label: `${dashboard.topic} · ${group.label}`,
			periods: dashboard.periods,
			statement: dashboard.topic,
			rows: group.rows.map(toFinancialRow)
		}))
	);
}

function groupsFor(dashboard: StatementDashboard, keys: string[]): FinancialTableGroup[] {
	return dashboard.groups
		.filter((group) => keys.includes(group.key) && group.rows.length)
		.map((group) => ({
			key: `${dashboard.topic}-${group.key}`,
			label: `${dashboard.topic} · ${group.label}`,
			periods: dashboard.periods,
			statement: dashboard.topic,
			rows: group.rows.map(toFinancialRow)
		}));
}

function toFinancialRow(row: StatementGroupRow): FinancialTableRow {
	return {
		key: row.key,
		label: row.label,
		unit: row.unit,
		values: row.values,
		yoy: row.yoy,
		source: row.source,
		raw: row
	};
}

function evidenceLinksForQuestion(
	question: StoryManifestDashboardQuestion,
	ctx: ReturnType<typeof makeContext>
): EvidenceLink[] {
	return question.evidenceTopics.slice(0, 4).map((topic) => {
		if (topic === 'finance') return { topic, label: '재무제표', value: 'IS/BS/CF' };
		if (topic === 'report') return { topic, label: '정기보고서', value: `${ctx.facts.length}개` };
		if (topic === 'docs') return { topic, label: '사업보고서 원문', value: `${ctx.docs.length}개` };
		if (topic === 'price') return { topic, label: '시장가격', value: ctx.price?.currentPrice ? fmtPrice(ctx.price.currentPrice) : '대기' };
		if (topic === 'peer') return { topic, label: '비교군', value: ctx.ego?.industry ?? '대기' };
		return { topic: topic as EvidenceLink['topic'], label: '산업지도', value: '연결' };
	});
}

function answerForQuestion(id: string, metrics: DashboardMetric[], ctx: ReturnType<typeof makeContext>): string {
	const get = (key: string) => metrics.find((metric) => metric.id === key)?.value ?? '—';
	if (id === 'overview') return `매출 ${get('revenue')}, 영업이익률 ${get('opMargin')}, 부채비율 ${get('debtRatio')}을 먼저 본다.`;
	if (id === 'business') return `수익원은 매출 규모와 이익 동행 여부로 판정한다. 최신 매출은 ${get('revenue')}이다.`;
	if (id === 'profit') return `남는 돈은 마진과 ROE를 분리해서 본다. 영업이익률은 ${get('opMargin')}이다.`;
	if (id === 'cash') return `순이익과 OCF/FCF가 같은 방향인지 확인한다. ${get('cashflow')} 기준이다.`;
	if (id === 'stability') return `부채와 자본의 조달 비중, 부채비율 추이가 안전성의 출발점이다.`;
	if (id === 'allocation') return `총자산 안에서 현금, 채권, 재고, 유형·무형자산, 기타/비영업 자산이 어디에 묶였는지 본다.`;
	if (id === 'valuation') return `시장가격은 ${ctx.price?.currentPrice ? fmtPrice(ctx.price.currentPrice) : '가격 대기'}와 배수로 실적을 얼마나 반영했는지 본다.`;
	return `정기보고서 ${ctx.facts.length}개, 원문 ${ctx.docs.length}개, 공시 변화 ${ctx.changes.length}개를 숫자와 연결한다.`;
}

function pick(map: Map<string, DashboardMetric>, ids: string[]): DashboardMetric[] {
	return ids.map((id) => map.get(id)).filter((item): item is DashboardMetric => item != null);
}

function textMetric(id: string, label: string, value: string, tone: Tone): DashboardMetric {
	return { id, label, value, raw: null, unit: 'count', delta: '', deltaTone: 'neutral', tone, period: null, series: [] };
}

function singleMetric(id: string, label: string, value: number | null, unit: string): DashboardMetric {
	return {
		id,
		label,
		value: formatValue(value, unit),
		raw: value,
		unit,
		delta: '',
		deltaTone: 'neutral',
		tone: value == null ? 'missing' : value < 0 ? 'bad' : 'neutral',
		period: null,
		series: []
	};
}

function combinedMetric(
	id: string,
	label: string,
	leftValues: Array<number | null>,
	rightValues: Array<number | null>,
	categories: string[],
	periodMode: PeriodMode
): DashboardMetric {
	const left = latestValue(leftValues);
	const right = latestValue(rightValues);
	return {
		id,
		label,
		value: `${formatValue(left, 'KRW')} / ${formatValue(right, 'KRW')}`,
		raw: right,
		unit: 'KRW',
		delta: deltaText(rightValues, periodMode),
		deltaTone: deltaTone(deltaNumber(rightValues, periodMode)),
		tone: right == null ? 'missing' : right >= 0 ? 'good' : 'bad',
		period: latestCategory(categories, rightValues),
		series: rightValues
	};
}

function metric(
	id: string,
	label: string,
	values: Array<number | null>,
	categories: string[],
	unit: string,
	kind: 'amount' | 'pct',
	periodMode: PeriodMode,
	options: { watchAbsAbove?: number } = {}
): DashboardMetric {
	const latest = latestValue(values);
	const delta = deltaNumber(values, periodMode);
	const tone: Tone =
		latest == null
			? 'missing'
			: options.watchAbsAbove != null && Math.abs(latest) > options.watchAbsAbove
				? 'watch'
				: kind === 'amount'
					? latest >= 0
						? 'neutral'
						: 'bad'
					: 'neutral';
	return {
		id,
		label,
		value: formatValue(latest, unit),
		raw: latest,
		unit,
		delta: deltaText(values, periodMode),
		deltaTone: tone === 'watch' ? 'watch' : deltaTone(delta),
		tone,
		period: latestCategory(categories, values),
		series: values,
		note: tone === 'watch' ? '구조 확인' : undefined
	};
}

function normalizedSeries(
	dashboard: StatementDashboard,
	key: string,
	periodMode: PeriodMode,
	accountType: 'flow' | 'stock'
): { values: Array<number | null>; categories: string[] } {
	const values = rowValues(dashboard, key);
	const categories = dashboard.periods;
	if (periodMode === 'TTM' && accountType === 'flow') {
		return { values: rollingSum(values, 4), categories };
	}
	return { values, categories };
}

function fcfSeries(dashboard: StatementDashboard, periodMode: PeriodMode): { values: Array<number | null>; categories: string[] } {
	const explicitValues = groupRowValues(dashboard, 'fcf');
	if (explicitValues?.some(isFiniteNumber)) {
		return {
			values: periodMode === 'TTM' ? rollingSum(explicitValues, 4) : explicitValues,
			categories: dashboard.periods
		};
	}
	const ocf = normalizedSeries(dashboard, 'ocf', periodMode, 'flow');
	const capex = normalizedSeries(dashboard, 'capex', periodMode, 'flow');
	const icf = normalizedSeries(dashboard, 'icf', periodMode, 'flow');
	const values = ocf.values.map((value, i) => {
		if (!isFiniteNumber(value)) return null;
		if (isFiniteNumber(capex.values[i])) return value + capex.values[i]!;
		if (isFiniteNumber(icf.values[i])) return value + icf.values[i]!;
		return null;
	});
	return { values, categories: ocf.categories };
}

function rowValues(dashboard: StatementDashboard, key: string): Array<number | null> {
	const groupValues = groupRowValues(dashboard, key);
	if (groupValues) return groupValues;
	const metric = dashboard.metrics.find((item) => item.key === key);
	if (metric) return dashboard.periods.map((_, i) => (i === dashboard.periods.length - 1 ? metric.value : null));
	return [];
}

function groupRowValues(dashboard: StatementDashboard, key: string): Array<number | null> | null {
	for (const group of dashboard.groups) {
		const row = group.rows.find((item) => item.key === key);
		if (row) return row.values.map((value) => normalizeUnitValue(numberOrNull(value), row.unit));
	}
	return null;
}

function normalizeUnitValue(value: number | null, unit: string): number | null {
	if (value == null) return null;
	if (unit === '조원') return value * 1e12;
	if (unit === '억원') return value * 1e8;
	return value;
}

function residualSeries(total: Array<number | null>, parts: Array<Array<number | null>>): Array<number | null> {
	return total.map((value, i) => {
		if (!isFiniteNumber(value)) return null;
		let known = 0;
		let hasPart = false;
		for (const part of parts) {
			if (isFiniteNumber(part[i])) {
				known += part[i]!;
				hasPart = true;
			}
		}
		if (!hasPart) return null;
		const residual = value - known;
		return residual >= 0 ? residual : null;
	});
}

function ratioSeries(numerator: Array<number | null>, denominator: Array<number | null>): Array<number | null> {
	const len = Math.max(numerator.length, denominator.length);
	return Array.from({ length: len }, (_, i) => ratio(numerator[i], denominator[i]));
}

function ratio(numerator: number | null | undefined, denominator: number | null | undefined): number | null {
	if (!isFiniteNumber(numerator) || !isFiniteNumber(denominator) || denominator === 0) return null;
	return (numerator / denominator) * 100;
}

function rollingSum(values: Array<number | null>, window: number): Array<number | null> {
	return values.map((_, i) => {
		if (i < window - 1) return null;
		const slice = values.slice(i - window + 1, i + 1);
		return slice.every(isFiniteNumber) ? slice.reduce((sum, value) => sum + value!, 0) : null;
	});
}

function latestValue(values: Array<number | null>): number | null {
	for (let i = values.length - 1; i >= 0; i -= 1) {
		if (isFiniteNumber(values[i])) return values[i]!;
	}
	return null;
}

function latestCategory(categories: string[], values: Array<number | null>): string | null {
	for (let i = values.length - 1; i >= 0; i -= 1) {
		if (isFiniteNumber(values[i])) return categories[i] ?? null;
	}
	return null;
}

function deltaNumber(values: Array<number | null>, periodMode: PeriodMode): number | null {
	const latestIndex = lastFiniteIndex(values);
	if (latestIndex < 0) return null;
	const compareIndex = periodMode === 'Q' || periodMode === 'TTM' ? latestIndex - 4 : latestIndex - 1;
	const fallbackIndex = latestIndex - 1;
	const base = isFiniteNumber(values[compareIndex]) ? values[compareIndex] : values[fallbackIndex];
	const latest = values[latestIndex];
	if (!isFiniteNumber(latest) || !isFiniteNumber(base) || base === 0) return null;
	return ((latest - base) / Math.abs(base)) * 100;
}

function deltaText(values: Array<number | null>, periodMode: PeriodMode): string {
	const delta = deltaNumber(values, periodMode);
	if (delta == null) return '';
	const label = periodMode === 'Y' ? '전년' : 'YoY';
	return `${label} ${fmtPct(delta, { withSign: true })}`;
}

function deltaTone(value: number | null): Tone {
	if (value == null) return 'neutral';
	if (value > 0.001) return 'good';
	if (value < -0.001) return 'bad';
	return 'neutral';
}

function lastFiniteIndex(values: Array<number | null>): number {
	for (let i = values.length - 1; i >= 0; i -= 1) {
		if (isFiniteNumber(values[i])) return i;
	}
	return -1;
}

function series(
	id: string,
	label: string,
	values: Array<number | null>,
	unit: string,
	color: string,
	type: 'bar' | 'line'
): DashboardSeries {
	return { id, label, values, unit, color, type };
}

function hasAny(groups: Array<Array<number | null>>): boolean {
	return groups.some((group) => group.some(isFiniteNumber));
}

function formatValue(value: number | null | undefined, unit: string): string {
	if (!isFiniteNumber(value)) return '—';
	if (unit === '%') return fmtPct(value);
	if (unit === 'x') return fmtMul(value);
	if (unit === 'KRW') return fmtKrw(value);
	if (unit === '조원') return `${value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`;
	if (unit === 'count') return `${Math.round(value).toLocaleString('ko-KR')}개`;
	return value.toLocaleString('ko-KR', { maximumFractionDigits: 1 });
}

export function formatTableValue(value: number | string | null, unit: string): string {
	if (typeof value === 'string') return value || '—';
	const num = numberOrNull(value);
	if (num == null) return '—';
	return formatValue(num, unit);
}

function numberOrNull(value: unknown): number | null {
	if (typeof value === 'number' && Number.isFinite(value)) return value;
	if (typeof value === 'string' && value.trim()) {
		const parsed = Number(value.replace(/,/g, ''));
		return Number.isFinite(parsed) ? parsed : null;
	}
	return null;
}

function isFiniteNumber(value: unknown): value is number {
	return typeof value === 'number' && Number.isFinite(value);
}

function latestPeriod(dashboards: Record<StatementKey, StatementDashboard>): string | null {
	return dashboards.IS.periods.at(-1) ?? dashboards.BS.periods.at(-1) ?? dashboards.CF.periods.at(-1) ?? null;
}
