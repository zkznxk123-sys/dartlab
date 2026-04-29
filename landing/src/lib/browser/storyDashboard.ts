import { loadJson } from '$lib/data/dartlabData';
import type {
	LiveCompanyBundle,
	LiveCompanyChange,
	LiveCompanyDocExcerpt,
	LiveCompanyReportFact,
	StatementDashboard,
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

export interface StoryManifest {
	schemaVersion: number;
	actHeaders: Record<string, { title: string; question: string }>;
	sections: StoryManifestSection[];
	blocks: StoryManifestBlock[];
	reportTypes: Record<string, StoryManifestReportType>;
	templates: Record<string, { description: string; emphasize: string[]; keyQuestions: string[]; actFocus: Record<string, string> }>;
}

export interface StoryMetric {
	label: string;
	value: string;
	tone?: 'good' | 'bad' | 'neutral';
}

export interface StoryDashboardBlock {
	key: string;
	label: string;
	description: string;
	type: 'metrics' | 'flags' | 'narrative' | 'evidence';
	emphasized: boolean;
	metrics: StoryMetric[];
	flags: string[];
	text: string;
	evidenceCount: number;
}

export interface StoryDashboardSectionView {
	id: string;
	key: string;
	title: string;
	actTitle: string;
	question: string;
	summary: string;
	blocks: StoryDashboardBlock[];
}

export interface StoryDashboardView {
	template: string;
	templateDescription: string;
	focusQuestions: string[];
	sections: StoryDashboardSectionView[];
}

const SECTION_IDS: Record<string, string> = {
	종합평가: 'story-score',
	수익구조: 'story-revenue',
	안정성: 'story-stability',
	가치평가: 'story-value',
	매크로: 'story-macro',
	storyValidation: 'story-validation'
};

const CURATED_KEYS: Record<string, string[]> = {
	종합평가: ['scorecard', 'summaryFlags', 'creditScore', 'peerPosition'],
	수익구조: ['profile', 'segmentComposition', 'growth', 'marginTrend'],
	안정성: ['leverageTrend', 'coverageTrend', 'distressScore', 'stabilityFlags'],
	가치평가: ['valuationSynthesis', 'priceTarget', 'relativeValuation', 'valuationFlags'],
	매크로: ['macroCycle', 'companyCyclePosition', 'macroRates', 'macroFlags'],
	storyValidation: ['storyPlausibility', 'storyPrecedents', 'plausibilityBand', 'valuationSins']
};

const BLOCK_COPY: Record<string, { label: string; description: string }> = {
	scorecard: { label: '재무 판정판', description: '외형, 마진, 재무위험, 현금창출을 한 줄로 압축합니다.' },
	summaryFlags: { label: '즉시 확인할 신호', description: '숫자만 보면 놓치는 위험과 강점을 먼저 뽑습니다.' },
	creditScore: { label: '채무 감당력', description: '부채비율과 현금흐름으로 재무 압박을 봅니다.' },
	peerPosition: { label: '업종 내 위치', description: '산업지도에서 이 회사가 맡는 역할과 국면입니다.' },
	profile: { label: '사업 모델', description: '무엇을 팔아 매출과 이익을 만드는지 봅니다.' },
	segmentComposition: { label: '매출-이익 연결', description: '매출 규모가 영업이익으로 얼마나 남는지 확인합니다.' },
	growth: { label: '성장 속도', description: '최근 외형 성장과 수익성의 방향을 같이 봅니다.' },
	marginTrend: { label: '마진 구조', description: '매출에서 영업이익, 순이익까지 떨어지는 폭입니다.' },
	leverageTrend: { label: '자본 구조', description: '자산을 부채와 자본이 어떻게 떠받치는지 봅니다.' },
	coverageTrend: { label: '이자 부담', description: '영업이익과 현금흐름으로 금융비용 여력을 봅니다.' },
	distressScore: { label: '위험 압력', description: '레버리지와 현금 부족 신호를 먼저 걸러냅니다.' },
	stabilityFlags: { label: '안정성 경고', description: 'BS와 CF에서 바로 확인해야 할 항목입니다.' },
	valuationSynthesis: { label: '가격 감각', description: '현재 가격 배수와 재무 흐름을 같이 봅니다.' },
	priceTarget: { label: '가격 기준선', description: '가격이 실적 흐름을 얼마나 선반영했는지 봅니다.' },
	relativeValuation: { label: '상대 배수', description: 'PER, PBR, 배당수익률로 시장의 기대를 읽습니다.' },
	valuationFlags: { label: '밸류 리스크', description: '싸 보이는 이유와 비싸 보이는 이유를 분리합니다.' },
	macroCycle: { label: '산업 사이클', description: '매크로와 업황이 회사 실적에 주는 압력입니다.' },
	companyCyclePosition: { label: '회사 국면', description: '산업 안에서 현재 위치와 역할을 봅니다.' },
	macroRates: { label: '금리 민감도', description: '부채와 밸류에이션에 영향을 주는 금리 조건입니다.' },
	macroFlags: { label: '외부 변수', description: '회사 밖에서 실적을 흔드는 변수를 정리합니다.' },
	storyPlausibility: { label: '스토리 검증', description: '재무제표, 정기보고서, 원문이 같은 방향인지 봅니다.' },
	storyPrecedents: { label: '공시 변화', description: '과거 원문 변화와 현재 숫자의 연결입니다.' },
	plausibilityBand: { label: '근거 밀도', description: '판단을 뒷받침하는 report/docs 연결 정도입니다.' },
	valuationSins: { label: '판단 오류 방지', description: '숫자 하나로 결론내리는 오류를 막습니다.' }
};

export async function loadStoryManifest(fetchFn: typeof fetch): Promise<StoryManifest | null> {
	return await loadJson<StoryManifest>('story/manifest.json', {
		fetchFn,
		preferLocal: true,
		required: false
	});
}

export function buildStoryDashboardView(input: {
	manifest: StoryManifest | null;
	company: LiveCompanyBundle | null;
	dashboards: Record<StatementKey, StatementDashboard>;
	facts: LiveCompanyReportFact[];
	docs: LiveCompanyDocExcerpt[];
	changes: LiveCompanyChange[];
}): StoryDashboardView {
	const manifest = input.manifest ?? fallbackManifest();
	const reportType = manifest.reportTypes.dashboard;
	const template = detectBrowserTemplate(input.company, input.dashboards);
	const templateInfo = manifest.templates[template];
	const blockMeta = new Map(manifest.blocks.map((block) => [block.key, block]));
	const sectionMeta = new Map(manifest.sections.map((section) => [section.key, section]));
	const templateEmphasis = new Set(templateInfo?.emphasize ?? []);
	const reportEmphasis = new Set(reportType.emphasize);

	return {
		template,
		templateDescription: templateInfo?.description ?? 'story dashboard',
		focusQuestions: reportType.focusQuestions,
		sections: reportType.sectionOrder.map((key) => {
			const section = sectionMeta.get(key) ?? fallbackSection(key);
			const act = manifest.actHeaders[String(section.act)] ?? { title: section.title, question: '' };
			const keys = selectKeys(section, reportEmphasis, templateEmphasis);
			const blocks = keys.map((blockKey) =>
				buildBlock(blockMeta.get(blockKey), blockKey, section.key, input, reportEmphasis, templateEmphasis)
			);
			return {
				id: SECTION_IDS[key] ?? key,
				key,
				title: section.title,
				actTitle: act.title,
				question: act.question,
				summary: buildSectionSummary(key, blocks, input),
				blocks
			};
		})
	};
}

function selectKeys(
	section: StoryManifestSection,
	reportEmphasis: Set<string>,
	templateEmphasis: Set<string>
): string[] {
	const curated = CURATED_KEYS[section.key] ?? [];
	const fromStory = section.keys.filter((key) => reportEmphasis.has(key) || templateEmphasis.has(key));
	return Array.from(new Set([...curated, ...fromStory])).slice(0, 6);
}

function buildBlock(
	meta: StoryManifestBlock | undefined,
	key: string,
	sectionKey: string,
	input: {
		company: LiveCompanyBundle | null;
		dashboards: Record<StatementKey, StatementDashboard>;
		facts: LiveCompanyReportFact[];
		docs: LiveCompanyDocExcerpt[];
		changes: LiveCompanyChange[];
	},
	reportEmphasis: Set<string>,
	templateEmphasis: Set<string>
): StoryDashboardBlock {
	const copy = BLOCK_COPY[key];
	const label = copy?.label ?? meta?.label ?? key;
	const metrics = metricsForBlock(key, sectionKey, input);
	const flags = flagsForBlock(key, sectionKey, input);
	const evidenceCount = evidenceCountForBlock(key, sectionKey, input);
	return {
		key,
		label,
		description: copy?.description ?? meta?.description ?? '',
		type: metrics.length ? 'metrics' : flags.length ? 'flags' : evidenceCount ? 'evidence' : 'narrative',
		emphasized: reportEmphasis.has(key) || templateEmphasis.has(key),
		metrics,
		flags,
		text: narrativeForBlock(key, sectionKey, input),
		evidenceCount
	};
}

function metricsForBlock(
	key: string,
	sectionKey: string,
	input: { company: LiveCompanyBundle | null; dashboards: Record<StatementKey, StatementDashboard> }
): StoryMetric[] {
	const summary = input.company?.summary;
	const price = input.company?.price;
	const is = input.dashboards.IS.metrics;
	const bs = input.dashboards.BS.metrics;
	const cf = input.dashboards.CF.metrics;
	const find = (items: StoryMetric[], label: string, value: string, tone: StoryMetric['tone'] = 'neutral') => [
		...items,
		{ label, value, tone }
	];

	if (key === 'scorecard') {
		let out: StoryMetric[] = [];
		out = find(out, '매출', displayMetric(is, 'revenue', summary?.revenue), toneByNumber(summary?.revenue, 0, false));
		out = find(out, '영업이익률', displayMetric(is, 'opMargin', summary?.opMargin), toneByNumber(summary?.opMargin, 8, false));
		out = find(out, '부채비율', displayMetric(bs, 'debtRatio', summary?.debtRatio), toneByDebt(summary?.debtRatio));
		out = find(out, 'FCF', displayMetric(cf, 'fcf', null), toneByNumber(cf.find((m) => m.key === 'fcf')?.value, 0, false));
		return out;
	}
	if (key === 'marginTrend' || sectionKey === '수익구조') {
		return [
			{ label: '매출', value: displayMetric(is, 'revenue', summary?.revenue) },
			{ label: '영업이익', value: displayMetric(is, 'op', summary?.op) },
			{ label: '순이익', value: displayMetric(is, 'net', summary?.net) },
			{ label: '영업이익률', value: displayMetric(is, 'opMargin', summary?.opMargin) }
		];
	}
	if (key === 'leverageTrend' || key === 'coverageTrend' || sectionKey === '안정성') {
		return [
			{ label: '총자산', value: displayMetric(bs, 'assets', null) },
			{ label: '총부채', value: displayMetric(bs, 'liabilities', null) },
			{ label: '총자본', value: displayMetric(bs, 'equity', null) },
			{ label: '부채비율', value: displayMetric(bs, 'debtRatio', summary?.debtRatio) }
		];
	}
	if (sectionKey === '가치평가') {
		return [
			{ label: '현재가', value: price?.currentPrice ? `₩${Math.round(price.currentPrice).toLocaleString('ko-KR')}` : '—' },
			{ label: 'PER', value: price?.per ? `${price.per.toFixed(2)}x` : '—' },
			{ label: 'PBR', value: price?.pbr ? `${price.pbr.toFixed(2)}x` : '—' },
			{ label: '배당수익률', value: price?.dividendYield ? `${price.dividendYield.toFixed(1)}%` : '—' }
		];
	}
	if (sectionKey === '매크로') {
		return [
			{ label: '산업', value: input.company?.companyMeta?.ego?.industry ?? '—' },
			{ label: '역할', value: input.company?.companyMeta?.ego?.role ?? '—' },
			{ label: '단계', value: input.company?.companyMeta?.ego?.stage ?? '—' }
		];
	}
	return [];
}

function flagsForBlock(
	key: string,
	sectionKey: string,
	input: { company: LiveCompanyBundle | null; changes: LiveCompanyChange[] }
): string[] {
	const out: string[] = [];
	const debtRatio = input.company?.summary?.debtRatio;
	const opMargin = input.company?.summary?.opMargin;
	const revenue = input.company?.summary?.revenue;
	const op = input.company?.summary?.op;
	if ((key === 'summaryFlags' || sectionKey === '종합평가') && opMargin != null) {
		if (opMargin >= 15) out.push('영업이익률이 높아 제품 믹스와 가격 결정력이 핵심입니다.');
		else if (opMargin >= 8) out.push('마진은 양호하지만 비용 변동이 이익을 얼마나 흔드는지 봐야 합니다.');
		else out.push('영업이익률이 낮아 비용구조와 일회성 비용 확인이 필요합니다.');
	}
	if ((key === 'stabilityFlags' || sectionKey === '안정성') && debtRatio != null && debtRatio > 200) {
		out.push(`부채비율 ${debtRatio.toFixed(1)}%는 BS 우선 점검 구간입니다.`);
	}
	if ((key === 'summaryFlags' || sectionKey === '종합평가') && revenue != null && op != null && revenue > 0) {
		out.push(`매출 ${displayMetric([], 'revenue', revenue)} 중 영업이익은 ${displayMetric([], 'op', op)}입니다.`);
	}
	for (const change of input.changes.slice(0, 2)) {
		if (sectionKey === 'storyValidation') out.push(`${change.sectionTitle} 공시 변화 감지`);
	}
	return out;
}

function evidenceCountForBlock(
	_key: string,
	sectionKey: string,
	input: { facts: LiveCompanyReportFact[]; docs: LiveCompanyDocExcerpt[]; changes: LiveCompanyChange[] }
): number {
	if (sectionKey === 'storyValidation') return input.docs.length + input.changes.length;
	if (sectionKey === '수익구조') return input.docs.filter((doc) => /사업|제품|매출/.test(doc.title)).length;
	if (sectionKey === '안정성') return input.facts.filter((fact) => /사채|감사|audit|bond/i.test(fact.key)).length;
	return 0;
}

function narrativeForBlock(
	key: string,
	sectionKey: string,
	input: { company: LiveCompanyBundle | null; docs: LiveCompanyDocExcerpt[] }
): string {
	const name = input.company?.companyMeta?.ego?.corpName ?? input.company?.stockCode ?? '회사';
	if (key === 'profile') return input.company?.companyMeta?.aiInsight?.narrative ?? `${name}의 매출 원천과 비용 구조를 먼저 잡습니다.`;
	if (sectionKey === 'storyValidation') {
		const doc = input.docs[0];
		return doc ? `${doc.title} 원문과 정기보고서 팩트를 함께 대조합니다.` : '원문 근거를 불러오는 중입니다.';
	}
	if (sectionKey === '종합평가') return `${name}의 투자 판단을 수익성, 레버리지, 현금창출 순서로 좁힙니다.`;
	if (sectionKey === '수익구조') return `${name}이 돈을 버는 방식이 매출 성장인지, 마진 개선인지 분리합니다.`;
	if (sectionKey === '안정성') return `${name}의 부채 부담이 영업현금으로 감당 가능한지 봅니다.`;
	if (sectionKey === '가치평가') return `${name}의 가격 배수가 현재 이익 체력과 맞는지 확인합니다.`;
	if (sectionKey === '매크로') return `${name}의 업황 민감도와 산업지도 위치를 같이 봅니다.`;
	return `${name}의 ${sectionKey} 판단 근거를 정리합니다.`;
}

function buildSectionSummary(
	key: string,
	blocks: StoryDashboardBlock[],
	input: { company: LiveCompanyBundle | null; dashboards: Record<StatementKey, StatementDashboard> }
): string {
	const summary = input.company?.summary;
	if (key === '종합평가') return `매출 ${displayMetric(input.dashboards.IS.metrics, 'revenue', summary?.revenue)}, 영업이익률 ${displayMetric(input.dashboards.IS.metrics, 'opMargin', summary?.opMargin)} 기준의 한 페이지 판단입니다.`;
	if (key === '수익구조') return 'IS와 사업 원문을 같이 보며 외형 성장, 마진, 수익원을 연결합니다.';
	if (key === '안정성') return 'BS 기반 자본 구조와 현금흐름으로 부채 감당력을 확인합니다.';
	if (key === '가치평가') return '가격 배수와 story의 성장/위험 근거를 같은 화면에서 비교합니다.';
	if (key === '매크로') return '산업지도와 매크로 블록을 회사의 현재 국면에 연결합니다.';
	if (key === 'storyValidation') return '재무제표, 정기보고서, 사업보고서 원문이 같은 이야기를 말하는지 대조합니다.';
	return blocks[0]?.text ?? '';
}

function displayMetric(
	metrics: Array<{ key: string; display: string }>,
	key: string,
	fallback: number | null | undefined
): string {
	const display = metrics.find((metric) => metric.key === key)?.display;
	if (display && display !== '데이터 없음') return display;
	if (fallback == null || !Number.isFinite(fallback)) return '—';
	if (Math.abs(fallback) > 1e10) return `${(fallback / 1e12).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`;
	return `${fallback.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}`;
}

function toneByDebt(value: number | null | undefined): StoryMetric['tone'] {
	if (value == null || !Number.isFinite(value)) return 'neutral';
	if (value >= 200) return 'bad';
	if (value <= 100) return 'good';
	return 'neutral';
}

function toneByNumber(value: number | null | undefined, threshold: number, lowerIsBetter: boolean): StoryMetric['tone'] {
	if (value == null || !Number.isFinite(value)) return 'neutral';
	if (lowerIsBetter) return value <= threshold ? 'good' : 'bad';
	return value >= threshold ? 'good' : 'bad';
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

function fallbackManifest(): StoryManifest {
	return {
		schemaVersion: 1,
		actHeaders: {},
		sections: ['종합평가', '수익구조', '안정성', '가치평가', '매크로', 'storyValidation'].map(fallbackSection),
		blocks: [],
		reportTypes: {
			dashboard: {
				key: 'dashboard',
				label: '대시보드',
				description: '한 페이지 회사 스냅샷',
				sectionOrder: ['종합평가', '수익구조', '안정성', '가치평가', '매크로', 'storyValidation'],
				emphasize: ['scorecard', 'marginTrend', 'leverageTrend'],
				focusQuestions: [],
				detail: false
			}
		},
		templates: {}
	};
}

function fallbackSection(key: string): StoryManifestSection {
	return { key, partId: '', title: key, act: 0, keys: CURATED_KEYS[key] ?? [], helper: '', aiGuide: '' };
}
