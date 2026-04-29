import { loadJson } from '$lib/data/dartlabData';
import type {
	LiveCompanyBundle,
	LiveCompanyChange,
	LiveCompanyDocExcerpt,
	LiveCompanyReportFact,
	StatementDashboard,
	StatementGroupRow,
	StatementKey
} from './companyLive';

export interface StoryManifestBlock {
	key: string;
	label: string;
	section: string;
	description: string;
}

export interface StoryManifestSection {
	key: string;
	partId: string;
	title: string;
	act: number;
	keys: string[];
	helper: string;
	aiGuide: string;
}

export interface StoryManifestReportType {
	key: string;
	label: string;
	description: string;
	sectionOrder: string[];
	emphasize: string[];
	focusQuestions: string[];
	detail: boolean;
}

export interface StoryManifestDashboardQuestion {
	id: string;
	question: string;
	tocLabel: string;
	sectionKeys: string[];
	blockKeys: string[];
	statementKeys: StatementKey[];
	evidenceTopics: Array<'finance' | 'report' | 'docs' | 'map' | 'price' | 'macro' | 'peer'>;
	vizKeys: string[];
}

export interface StoryManifestVizIntent {
	key: string;
	chartType: string;
	title: string;
	purpose: StoryVizSpec['purpose'];
	statement: string;
	component?: string;
	periodMode?: string;
	compareMode?: string;
	requiredMetricIds?: string[];
	evidenceTopics: string[];
	blockKeys: string[];
}

export interface StoryManifest {
	schemaVersion: number;
	source: string;
	actHeaders: Record<string, { title: string; question: string }>;
	sections: StoryManifestSection[];
	blocks: StoryManifestBlock[];
	reportTypes: Record<string, StoryManifestReportType>;
	templates: Record<
		string,
		{ description: string; emphasize: string[]; keyQuestions: string[]; actFocus: Record<string, string> }
	>;
	dashboardQuestions?: StoryManifestDashboardQuestion[];
	vizIntents?: StoryManifestVizIntent[];
}

export interface StoryMetric {
	label: string;
	value: string;
	tone?: 'good' | 'bad' | 'neutral';
	sparkValues?: Array<number | null>;
}

export interface StoryVizSpec {
	chartType: 'combo' | 'bar' | 'line' | 'radar' | 'waterfall' | 'heatmap' | 'sparkline' | 'pie';
	title: string;
	series: Array<Record<string, unknown>>;
	categories: string[];
	options: Record<string, unknown>;
	meta: {
		source: string;
		stockCode?: string;
		corpName?: string;
		sectionKey?: string;
		blockKey?: string;
		statement?: 'IS' | 'BS' | 'CF' | 'REPORT' | 'DOCS' | 'PRICE' | 'MACRO' | 'PEER';
	};
	purpose?: 'trend' | 'composition' | 'bridge' | 'comparison' | 'risk' | 'valuation' | 'evidence';
	evidenceIds?: string[];
}

export interface StoryDashboardBlock {
	key: string;
	label: string;
	section: string;
	description: string;
	emphasized: boolean;
}

export interface StoryDashboardSectionView {
	id: string;
	question: string;
	tocLabel: string;
	sectionKeys: string[];
	statementKeys: StatementKey[];
	evidenceTopics: string[];
	metrics: StoryMetric[];
	charts: StoryVizSpec[];
	blocks: StoryDashboardBlock[];
	summary: string;
	evidenceCount: number;
}

export interface StoryDashboardView {
	template: string;
	templateDescription: string;
	focusQuestions: string[];
	sections: StoryDashboardSectionView[];
}

interface StoryDashboardBuildInput {
	manifest: StoryManifest | null;
	company: LiveCompanyBundle | null;
	dashboards: Record<StatementKey, StatementDashboard>;
	facts: LiveCompanyReportFact[];
	docs: LiveCompanyDocExcerpt[];
	changes: LiveCompanyChange[];
}

const COLORS = ['#ea4647', '#fb923c', '#3b82f6', '#22c55e', '#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899'];

const GRADE_SCORE: Record<string, number> = {
	A: 100,
	B: 80,
	C: 60,
	D: 40,
	E: 20,
	F: 10,
	우수: 100,
	양호: 80,
	보통: 60,
	저수익: 40,
	적자: 10,
	고성장: 100,
	성장: 80,
	정체: 60,
	급감: 40,
	역성장: 10,
	안전: 100,
	관찰: 60,
	주의: 40,
	고위험: 10,
	위험: 10,
	안정: 100,
	경고: 40,
	취약: 10
};

export async function loadStoryManifest(fetchFn: typeof fetch): Promise<StoryManifest | null> {
	return await loadJson<StoryManifest>('story/manifest.json', {
		fetchFn,
		preferLocal: true,
		required: false
	});
}

export function buildStoryDashboardView(input: StoryDashboardBuildInput): StoryDashboardView {
	const manifest = input.manifest;
	const questions = manifest?.dashboardQuestions ?? [];
	const reportType = manifest?.reportTypes?.dashboard;
	const template = detectBrowserTemplate(input.company, input.dashboards);
	const templateInfo = manifest?.templates?.[template];
	const blockMeta = new Map((manifest?.blocks ?? []).map((block) => [block.key, block]));
	const intentMeta = new Map((manifest?.vizIntents ?? []).map((intent) => [intent.key, intent]));
	const templateEmphasis = new Set(templateInfo?.emphasize ?? []);
	const reportEmphasis = new Set(reportType?.emphasize ?? []);

	return {
		template,
		templateDescription: templateInfo?.description ?? '질문형 company dashboard',
		focusQuestions: reportType?.focusQuestions ?? questions.map((question) => question.question),
		sections: questions.map((question) => {
			const blocks = question.blockKeys.map((blockKey) => {
				const meta = blockMeta.get(blockKey);
				return {
					key: blockKey,
					label: meta?.label ?? blockKey,
					section: meta?.section ?? question.sectionKeys[0] ?? '',
					description: meta?.description ?? '',
					emphasized: reportEmphasis.has(blockKey) || templateEmphasis.has(blockKey)
				};
			});
			const charts = question.vizKeys
				.map((key) => buildVizSpec(key, intentMeta.get(key), question, input))
				.filter((chart): chart is StoryVizSpec => chart != null);
			const metrics = metricsForQuestion(question, input);
			return {
				id: `q-${question.id}`,
				question: question.question,
				tocLabel: question.tocLabel,
				sectionKeys: question.sectionKeys,
				statementKeys: question.statementKeys,
				evidenceTopics: question.evidenceTopics,
				metrics,
				charts,
				blocks,
				summary: buildQuestionSummary(question, metrics, charts, input),
				evidenceCount: evidenceCountForQuestion(question, input)
			};
		})
	};
}

export function buildStatementVizSpecs(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string } = {}
): StoryVizSpec[] {
	if (dashboard.topic === 'IS') {
		return [buildIsRevenueProfit(dashboard, context), buildIsMarginTrend(dashboard, context)].filter(
			(chart): chart is StoryVizSpec => chart != null
		);
	}
	if (dashboard.topic === 'BS') {
		return [
			buildBsCapitalStructure(dashboard, context),
			buildBsAssetComposition(dashboard, context),
			buildBsDebtRatioTrend(dashboard, context)
		].filter((chart): chart is StoryVizSpec => chart != null);
	}
	return [buildCfSignedFlow(dashboard, context), buildCfWaterfall(dashboard, context)].filter(
		(chart): chart is StoryVizSpec => chart != null
	);
}

function buildVizSpec(
	key: string,
	intent: StoryManifestVizIntent | undefined,
	question: StoryManifestDashboardQuestion,
	input: {
		company: LiveCompanyBundle | null;
		dashboards: Record<StatementKey, StatementDashboard>;
		facts: LiveCompanyReportFact[];
		docs: LiveCompanyDocExcerpt[];
		changes: LiveCompanyChange[];
	}
): StoryVizSpec | null {
	const context = {
		stockCode: input.company?.stockCode,
		corpName: input.company?.companyMeta?.ego?.corpName ?? input.company?.stockCode
	};
	const attach = (spec: StoryVizSpec | null): StoryVizSpec | null => {
		if (!spec) return null;
		return {
			...spec,
			title: intent?.title ?? spec.title,
			purpose: intent?.purpose ?? spec.purpose,
			meta: {
				...spec.meta,
				sectionKey: question.sectionKeys[0],
				blockKey: question.blockKeys[0]
			}
		};
	};

	if (key === 'kpi_sparklines') return attach(buildKpiSparklines(input.dashboards, context));
	if (key === 'is_revenue_profit') return attach(buildIsRevenueProfit(input.dashboards.IS, context));
	if (key === 'is_margin_trend') return attach(buildIsMarginTrend(input.dashboards.IS, context));
	if (key === 'bs_capital_structure') return attach(buildBsCapitalStructure(input.dashboards.BS, context));
	if (key === 'bs_asset_composition') return attach(buildBsAssetComposition(input.dashboards.BS, context));
	if (key === 'bs_debt_ratio_trend') return attach(buildBsDebtRatioTrend(input.dashboards.BS, context));
	if (key === 'cf_signed_flow') return attach(buildCfSignedFlow(input.dashboards.CF, context));
	if (key === 'cf_waterfall') return attach(buildCfWaterfall(input.dashboards.CF, context));
	if (key === 'valuation_multiples') return attach(buildValuationMultiples(input.company, context));
	if (key === 'peer_position_radar') return attach(buildPeerRadar(input.company, context));
	if (key === 'report_evidence_heatmap') return attach(buildReportEvidenceHeatmap(input, context));
	return null;
}

function metricsForQuestion(
	question: StoryManifestDashboardQuestion,
	input: StoryDashboardBuildInput
): StoryMetric[] {
	const is = input.dashboards.IS;
	const bs = input.dashboards.BS;
	const cf = input.dashboards.CF;
	const price = input.company?.price;

	if (question.id === 'overview') {
		return [
			metricFromDashboard(is, 'revenue'),
			metricFromDashboard(is, 'opMargin'),
			metricFromDashboard(bs, 'debtRatio'),
			metricFromDashboard(cf, 'fcf'),
			{ label: 'PER/PBR', value: `${fmtMul(price?.per)} / ${fmtMul(price?.pbr)}`, tone: 'neutral' }
		].filter(Boolean) as StoryMetric[];
	}
	if (question.id === 'business' || question.id === 'profit') {
		return [
			metricFromDashboard(is, 'revenue'),
			metricFromDashboard(is, 'revenueYoy'),
			metricFromDashboard(is, 'op'),
			metricFromDashboard(is, 'opMargin'),
			metricFromDashboard(is, 'netMargin')
		].filter(Boolean) as StoryMetric[];
	}
	if (question.id === 'cash') {
		return [
			metricFromDashboard(cf, 'ocf'),
			metricFromDashboard(cf, 'fcf'),
			metricFromDashboard(cf, 'icf'),
			metricFromDashboard(cf, 'financingCf')
		].filter(Boolean) as StoryMetric[];
	}
	if (question.id === 'stability') {
		return [
			metricFromDashboard(bs, 'assets'),
			metricFromDashboard(bs, 'liabilities'),
			metricFromDashboard(bs, 'equity'),
			metricFromDashboard(bs, 'debtRatio')
		].filter(Boolean) as StoryMetric[];
	}
	if (question.id === 'allocation') {
		return [
			metricFromDashboard(bs, 'cash'),
			metricFromDashboard(bs, 'inventory'),
			metricFromDashboard(cf, 'fcf'),
			metricFromDashboard(cf, 'dividendPaid')
		].filter(Boolean) as StoryMetric[];
	}
	if (question.id === 'valuation') {
		return [
			{ label: '현재가', value: fmtPrice(price?.currentPrice), tone: 'neutral' },
			{ label: 'PER', value: fmtMul(price?.per), tone: 'neutral' },
			{ label: 'PBR', value: fmtMul(price?.pbr), tone: 'neutral' },
			{ label: '배당수익률', value: price?.dividendYield == null ? '데이터 없음' : `${price.dividendYield.toFixed(1)}%`, tone: 'neutral' }
		];
	}
	return [
		{ label: '정기보고서', value: `${evidenceCountByTopic('report', input)}개`, tone: 'neutral' },
		{ label: '원문 발췌', value: `${evidenceCountByTopic('docs', input)}개`, tone: 'neutral' }
	];
}

function metricFromDashboard(dashboard: StatementDashboard, key: string): StoryMetric | null {
	const metric = dashboard.metrics.find((item) => item.key === key);
	if (!metric) return null;
	const rowValues = rowSeries(dashboard, key);
	return {
		label: metric.label,
		value: metric.display,
		tone: metric.tone,
		sparkValues: rowValues.length ? rowValues : undefined
	};
}

function buildQuestionSummary(
	question: StoryManifestDashboardQuestion,
	metrics: StoryMetric[],
	charts: StoryVizSpec[],
	input: { facts: LiveCompanyReportFact[]; docs: LiveCompanyDocExcerpt[]; changes: LiveCompanyChange[] }
): string {
	const metricText = metrics
		.slice(0, 3)
		.map((metric) => `${metric.label} ${metric.value}`)
		.join(' · ');
	const visualText = charts.length ? `시각화 ${charts.length}개` : '시각화 대기';
	const evidenceText = `근거 ${evidenceCountForQuestion(question, input)}개`;
	return [metricText, visualText, evidenceText].filter(Boolean).join(' · ');
}

function evidenceCountForQuestion(
	question: StoryManifestDashboardQuestion,
	input: { facts: LiveCompanyReportFact[]; docs: LiveCompanyDocExcerpt[]; changes: LiveCompanyChange[] }
): number {
	return question.evidenceTopics.reduce((total, topic) => total + evidenceCountByTopic(topic, input), 0);
}

function evidenceCountByTopic(
	topic: string,
	input: { facts?: LiveCompanyReportFact[]; docs?: LiveCompanyDocExcerpt[]; changes?: LiveCompanyChange[] }
): number {
	if (topic === 'report') return input.facts?.length ?? 0;
	if (topic === 'docs') return input.docs?.length ?? 0;
	if (topic === 'finance') return 1;
	if (topic === 'price') return 1;
	if (topic === 'map' || topic === 'peer' || topic === 'macro') return 1;
	return input.changes?.length ?? 0;
}

function buildKpiSparklines(
	dashboards: Record<StatementKey, StatementDashboard>,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const items = [
		sparkMetric('매출(조)', rowSeries(dashboards.IS, 'revenue'), 1e12),
		sparkMetric('영업이익(조)', rowSeries(dashboards.IS, 'op'), 1e12),
		sparkMetric('순이익(조)', rowSeries(dashboards.IS, 'net'), 1e12),
		sparkMetric('부채비율(%)', metricSeries(dashboards.BS, 'debtRatio')),
		sparkMetric('FCF(조)', metricSeries(dashboards.CF, 'fcf'), 1e12)
	].filter((item): item is { field: string; values: Array<number | null>; latest: number | null; trend: string } => item != null);
	if (!items.length) return null;
	return {
		chartType: 'sparkline',
		title: '핵심 지표 5년 흐름',
		series: [{ category: '핵심 지표', metrics: items }],
		categories: dashboards.IS.periods,
		options: {},
		purpose: 'trend',
		evidenceIds: ['finance:IS', 'finance:BS', 'finance:CF'],
		meta: baseMeta('finance', 'IS', context)
	};
}

function buildIsRevenueProfit(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const series = [
		chartSeries('매출', rowSeries(dashboard, 'revenue'), 'bar', COLORS[2]),
		chartSeries('영업이익', rowSeries(dashboard, 'op'), 'bar', COLORS[0]),
		chartSeries('순이익', rowSeries(dashboard, 'net'), 'bar', COLORS[3])
	].filter((item): item is Record<string, unknown> => item != null);
	if (!series.length) return null;
	return {
		chartType: 'combo',
		title: '매출과 이익 흐름',
		series,
		categories: dashboard.periods,
		options: { unit: '원' },
		purpose: 'trend',
		evidenceIds: ['finance:IS'],
		meta: baseMeta('finance', 'IS', context)
	};
}

function buildIsMarginTrend(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const series = [
		chartSeries('영업이익률', metricSeries(dashboard, 'opMargin'), 'line', COLORS[0]),
		chartSeries('순이익률', metricSeries(dashboard, 'netMargin'), 'line', COLORS[3])
	].filter((item): item is Record<string, unknown> => item != null);
	if (!series.length) return null;
	return {
		chartType: 'line',
		title: '영업이익률과 순이익률',
		series,
		categories: dashboard.periods,
		options: { unit: '%' },
		purpose: 'trend',
		evidenceIds: ['finance:IS'],
		meta: baseMeta('finance', 'IS', context)
	};
}

function buildBsCapitalStructure(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const series = [
		chartSeries('부채', rowSeries(dashboard, 'liabilities'), 'bar', COLORS[2]),
		chartSeries('자본', rowSeries(dashboard, 'equity'), 'bar', COLORS[3])
	].filter((item): item is Record<string, unknown> => item != null);
	if (!series.length) return null;
	return {
		chartType: 'bar',
		title: '자산 = 부채 + 자본',
		series,
		categories: dashboard.periods,
		options: { unit: '원', stacked: true },
		purpose: 'composition',
		evidenceIds: ['finance:BS'],
		meta: baseMeta('finance', 'BS', context)
	};
}

function buildBsAssetComposition(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const series = [
		chartSeries('현금', rowSeries(dashboard, 'cash'), 'bar', COLORS[3]),
		chartSeries('매출채권', rowSeries(dashboard, 'receivables'), 'bar', COLORS[2]),
		chartSeries('재고', rowSeries(dashboard, 'inventory'), 'bar', COLORS[6]),
		chartSeries('유형자산', rowSeries(dashboard, 'tangible'), 'bar', COLORS[0]),
		chartSeries('무형자산', rowSeries(dashboard, 'intangible'), 'bar', COLORS[4])
	].filter((item): item is Record<string, unknown> => item != null);
	if (!series.length) return null;
	return {
		chartType: 'bar',
		title: '자산 구성',
		series,
		categories: dashboard.periods,
		options: { unit: '원', stacked: true },
		purpose: 'composition',
		evidenceIds: ['finance:BS'],
		meta: baseMeta('finance', 'BS', context)
	};
}

function buildBsDebtRatioTrend(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const series = chartSeries('부채비율', metricSeries(dashboard, 'debtRatio'), 'line', COLORS[0]);
	if (!series) return null;
	return {
		chartType: 'line',
		title: '부채비율 추이',
		series: [series],
		categories: dashboard.periods,
		options: { unit: '%' },
		purpose: 'risk',
		evidenceIds: ['finance:BS'],
		meta: baseMeta('finance', 'BS', context)
	};
}

function buildCfSignedFlow(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const series = [
		chartSeries('영업CF', rowSeries(dashboard, 'ocf'), 'bar', COLORS[3]),
		chartSeries('투자CF', rowSeries(dashboard, 'icf'), 'bar', COLORS[2]),
		chartSeries('재무CF', rowSeries(dashboard, 'financingCf'), 'bar', COLORS[4]),
		chartSeries('FCF', metricSeries(dashboard, 'fcf'), 'line', COLORS[0])
	].filter((item): item is Record<string, unknown> => item != null);
	if (!series.length) return null;
	return {
		chartType: 'combo',
		title: '영업/투자/재무/FCF 흐름',
		series,
		categories: dashboard.periods,
		options: { unit: '원' },
		purpose: 'bridge',
		evidenceIds: ['finance:CF'],
		meta: baseMeta('finance', 'CF', context)
	};
}

function buildCfWaterfall(
	dashboard: StatementDashboard,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const rows = [
		['기초현금', latest(rowSeries(dashboard, 'cash'))],
		['영업CF', latest(rowSeries(dashboard, 'ocf'))],
		['투자CF', latest(rowSeries(dashboard, 'icf'))],
		['재무CF', latest(rowSeries(dashboard, 'financingCf'))],
		['기말현금', latest(rowSeries(dashboard, 'closingCash'))]
	] as Array<[string, number | null]>;
	if (!rows.some(([, value]) => value != null)) return null;
	return {
		chartType: 'waterfall',
		title: '최신 현금흐름 브릿지',
		series: [{ name: '현금흐름', data: rows.map(([, value]) => value), color: COLORS[3] }],
		categories: rows.map(([label]) => label),
		options: { unit: '원' },
		purpose: 'bridge',
		evidenceIds: ['finance:CF'],
		meta: baseMeta('finance', 'CF', context)
	};
}

function buildValuationMultiples(
	company: LiveCompanyBundle | null,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const price = company?.price;
	const values = [price?.per ?? null, price?.pbr ?? null, price?.dividendYield ?? null];
	if (!values.some((value) => value != null && Number.isFinite(value))) return null;
	return {
		chartType: 'bar',
		title: '시장 가격 배수',
		series: [{ name: '배수/수익률', data: values, color: COLORS[0], type: 'bar' }],
		categories: ['PER', 'PBR', '배당수익률'],
		options: { unit: '배/%' },
		purpose: 'valuation',
		evidenceIds: ['price:snapshot'],
		meta: baseMeta('price', 'PRICE', context)
	};
}

function buildPeerRadar(
	company: LiveCompanyBundle | null,
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const ego = company?.companyMeta?.ego;
	const grades = [ego?.profGrade, ego?.growthGrade, ego?.debtGrade, ego?.qualGrade, ego?.govGrade];
	const values = grades.map((grade) => (grade ? GRADE_SCORE[String(grade)] : null));
	if (!values.some((value) => value != null)) return null;
	return {
		chartType: 'radar',
		title: '업종 내 위치',
		series: [{ name: context.corpName ?? '회사', data: values.map((value) => value ?? 50), color: COLORS[0] }],
		categories: ['수익성', '성장', '안정성', '품질', '지배구조'],
		options: { maxValue: 100, unit: '점' },
		purpose: 'comparison',
		evidenceIds: ['map:companyMeta'],
		meta: baseMeta('map', 'PEER', context)
	};
}

function buildReportEvidenceHeatmap(
	input: { facts: LiveCompanyReportFact[]; docs: LiveCompanyDocExcerpt[]; changes: LiveCompanyChange[] },
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec | null {
	const data = [
		{ topic: '정기보고서', value: input.facts.length, intensity: input.facts.length >= 4 ? 'high' : input.facts.length ? 'medium' : 'low' },
		{ topic: '원문', value: input.docs.length, intensity: input.docs.length >= 8 ? 'high' : input.docs.length ? 'medium' : 'low' },
		{ topic: '공시변화', value: input.changes.length, intensity: input.changes.length >= 4 ? 'high' : input.changes.length ? 'medium' : 'low' }
	];
	if (!data.some((item) => item.value > 0)) return null;
	return {
		chartType: 'heatmap',
		title: '보고서/원문 근거 밀도',
		series: [{ name: '근거', data }],
		categories: data.map((item) => item.topic),
		options: { colorScale: { low: '#263145', medium: '#fb923c', high: '#ea4647' } },
		purpose: 'evidence',
		evidenceIds: ['report:facts', 'docs:excerpts'],
		meta: baseMeta('report', 'REPORT', context)
	};
}

function baseMeta(
	source: string,
	statement: StoryVizSpec['meta']['statement'],
	context: { stockCode?: string; corpName?: string }
): StoryVizSpec['meta'] {
	return {
		source,
		stockCode: context.stockCode,
		corpName: context.corpName,
		statement
	};
}

function chartSeries(
	name: string,
	values: Array<number | null>,
	type: 'bar' | 'line',
	color: string
): Record<string, unknown> | null {
	if (!values.some((value) => value != null && Number.isFinite(value))) return null;
	return { name, data: values, type, color };
}

function sparkMetric(field: string, values: Array<number | null>, scale = 1) {
	const scaledValues = values.map((value) => (value == null || !Number.isFinite(value) ? null : value / scale));
	if (!scaledValues.some((value) => value != null && Number.isFinite(value))) return null;
	const nums = scaledValues.filter((value): value is number => value != null && Number.isFinite(value));
	const last = nums.at(-1) ?? null;
	const prev = nums.at(-2) ?? null;
	const trend = last == null || prev == null ? 'neutral' : last > prev ? 'up' : last < prev ? 'down' : 'neutral';
	return { field, values: scaledValues, latest: last, trend };
}

function metricSeries(dashboard: StatementDashboard, key: string): Array<number | null> {
	if (key === 'opMargin') return ratioSeries(dashboard, 'op', 'revenue');
	if (key === 'netMargin') return ratioSeries(dashboard, 'net', 'revenue');
	if (key === 'debtRatio') return ratioSeries(dashboard, 'liabilities', 'equity');
	if (key === 'fcf') {
		const ocf = rowSeries(dashboard, 'ocf');
		const capex = rowSeries(dashboard, 'capex');
		const icf = rowSeries(dashboard, 'icf');
		const len = Math.max(ocf.length, capex.length, icf.length);
		return Array.from({ length: len }, (_, i) => {
			if (ocf[i] == null) return null;
			if (capex[i] != null) return ocf[i]! + capex[i]!;
			if (icf[i] != null) return ocf[i]! + icf[i]!;
			return null;
		});
	}
	const row = rowSeries(dashboard, key);
	if (row.length) return row;
	const metric = dashboard.metrics.find((item) => item.key === key);
	if (!metric) return [];
	return dashboard.periods.map((_, i) => (i === dashboard.periods.length - 1 ? metric.value : null));
}

function ratioSeries(dashboard: StatementDashboard, numeratorKey: string, denominatorKey: string): Array<number | null> {
	const numerator = rowSeries(dashboard, numeratorKey);
	const denominator = rowSeries(dashboard, denominatorKey);
	const len = Math.max(numerator.length, denominator.length);
	return Array.from({ length: len }, (_, i) =>
		numerator[i] != null && denominator[i] ? (numerator[i]! / denominator[i]!) * 100 : null
	);
}

function rowSeries(dashboard: StatementDashboard, key: string): Array<number | null> {
	const item = row(dashboard, key);
	return item?.values.map(numberOrNull) ?? [];
}

function row(dashboard: StatementDashboard, key: string): StatementGroupRow | null {
	for (const group of dashboard.groups) {
		const found = group.rows.find((item) => item.key === key);
		if (found) return found;
	}
	return null;
}

function latest(values: Array<number | null>): number | null {
	for (let i = values.length - 1; i >= 0; i -= 1) {
		const value = values[i];
		if (value != null && Number.isFinite(value)) return value;
	}
	return null;
}

function numberOrNull(value: unknown): number | null {
	if (typeof value === 'number') return Number.isFinite(value) ? value : null;
	if (typeof value === 'string' && value.trim()) {
		const parsed = Number(value.replace(/,/g, ''));
		return Number.isFinite(parsed) ? parsed : null;
	}
	return null;
}

function fmtPrice(value: number | null | undefined): string {
	if (value == null || !Number.isFinite(value)) return '데이터 없음';
	return `₩${Math.round(value).toLocaleString('ko-KR')}`;
}

function fmtMul(value: number | null | undefined): string {
	if (value == null || !Number.isFinite(value)) return '데이터 없음';
	return `${value.toFixed(2)}x`;
}

function detectBrowserTemplate(
	company: LiveCompanyBundle | null,
	dashboards: Record<StatementKey, StatementDashboard>
): string {
	const stage = company?.companyMeta?.ego?.stage;
	if (stage && /성장/.test(stage)) return '성장';
	const revenueMetric = dashboards.IS.metrics.find((m) => m.key === 'revenueYoy');
	if ((revenueMetric?.value ?? 0) > 15) return '성장';
	const cash = dashboards.BS.metrics.find((m) => m.key === 'cash')?.value;
	const assets = dashboards.BS.metrics.find((m) => m.key === 'assets')?.value;
	if (cash && assets && cash / assets > 0.2) return '현금부자';
	return '사이클';
}
