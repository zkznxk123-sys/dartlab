import { MACRO_ATTRIBUTION, MACRO_SERIES, type MacroLatest, type MacroSeriesDef } from '@dartlab/ui-contracts';
import type { CoMover } from './coMovement';
import type { Company, MacroExposureIndicatorPayload, MacroExposureQualityPayload, MacroFile, MacroSide, MacroTransmissionEdge, MacroTransmissionPayload, Tailwind, Tone } from './types';
import { EDGE_SECTOR_TO_TAILWIND, CURRENT_MACRO_EDGE_SECTOR_KEYS, classifyTailwind, hasNegativeTailwind } from './macroMappings';

export type MacroLensTab = 'regime' | 'drivers' | 'transmission' | 'scenario' | 'sources';
export type MacroMarket = 'KR' | 'US' | 'GLOBAL';
export type MacroChannel = 'revenue' | 'margin' | 'balanceSheet' | 'cashFlow' | 'valuation';

export interface MacroDriverView {
	id: string;
	label: string;
	group: string;
	seriesId: string;
	unit: string;
	source: 'ECOS' | 'FRED';
	value: string;
	change: string;
	asOf: string;
	spark: number[];
	directionSemantics: string;
	defaultLagMonths: number | null;
	relevance: 'primary' | 'secondary' | 'context';
	pressureLevel: 'high' | 'medium' | 'low' | 'blocked';
	pressureReason: string;
	coMovement: {
		corr: number;
		n: number;
		window: string;
		label: string;
		status: 'candidate' | 'unstable' | 'missing';
	} | null;
	freshness: {
		status: 'fresh' | 'watch' | 'stale' | 'unknown';
		daysLag: number | null;
		label: string;
	};
	transform: string;
	sourceLineage: string;
	qualityHint: string;
}

export interface MacroTransmissionEdgeView {
	id: string;
	driverId: string;
	driverLabel: string;
	market: MacroMarket;
	sectorKey: string;
	sectorLabel: string;
	channel: MacroChannel;
	financialLine: string;
	valuationLever: 'discountRate' | 'growth' | 'margin' | 'multiple' | 'riskPremium';
	sign: 'positive' | 'negative' | 'mixed' | 'unknown';
	lagMonths: [number, number] | null;
	confidence: 'high' | 'medium' | 'low' | 'blocked';
	evidenceLevel: 'observed' | 'sectorPrior' | 'template';
	requiredCompanyEvidence: string[];
	sourceRefs: string[];
	note: string;
}

export interface MacroCheckpointView {
	id: string;
	label: string;
	value: string;
	tone: Tone;
	reason: string;
	source: string;
}

export interface MacroFalsifierView {
	id: string;
	type: 'coMovement' | 'quality' | 'missingCompanyEvidence' | 'staleData';
	driverId?: string;
	label: string;
	severity: 'info' | 'warning' | 'blocker';
	detail: string;
	sourceRef: string;
}

export interface MacroScenarioView {
	id: string;
	label: string;
	driverId: string;
	shock: string;
	firstBreak: string;
	expectedDirection: string;
	impactedFinancialLine: string;
	valuationLever: string;
	falsifier: string;
	requiredEvidence: string[];
	nextSurface: string;
	readiness: {
		status: 'ready' | 'needsEvidence' | 'blocked';
		reason: string;
	};
}

export interface MacroExposureQualityView {
	method: string | null;
	modelVersion: string | null;
	targetMetric: string | null;
	minObs: number | null;
	status: 'quantCandidate' | 'qualitativeOnly' | 'blocked';
	reason: string;
	blockedReason: string;
	missingEvidence: string[];
	sourceRef: string;
	nObs: number | null;
	rSquared: number | null;
	window: string | null;
	frequency: 'monthly' | 'quarterly' | 'annual' | null;
	lagMonths: number | null;
	coverage: 'company' | 'sectorOnly' | 'missing';
}

export interface MacroExposureIndicatorView {
	method: string | null;
	modelVersion: string | null;
	targetMetric: string | null;
	minObs: number | null;
	label: string;
	seriesId: string;
	axis: string;
	rSquared: number | null;
	nObs: number | null;
	window: string | null;
	frequency: 'monthly' | 'quarterly' | 'annual' | null;
	lagMonths: number | null;
	coverage: 'company' | 'sectorOnly' | 'missing';
	sourceRef: string;
	sourceRefs: string[];
	latestChange: number | null;
	impact: string;
}

export interface MacroReleaseView {
	driverId: string;
	label: string;
	source: 'ECOS' | 'FRED';
	frequency: string;
	lastObservation: string;
	nextCheck: string;
	daysLag: number | null;
	staleAfterDays: number;
	status: 'fresh' | 'watch' | 'stale' | 'unknown';
	sourceRef: string;
}

export interface MacroSourcePacketView {
	driverId: string;
	label: string;
	seriesId: string;
	source: 'ECOS' | 'FRED';
	unit: string;
	frequency: string;
	asOf: string;
	value: string;
	change: string;
	transform: string;
	status: 'fresh' | 'watch' | 'stale' | 'unknown' | 'missing';
	artifactPath: string;
	sourceRef: string;
	lineage: string;
	qualityHint: string;
}

export interface MacroContributionComponentView {
	id: string;
	label: string;
	value: number;
	detail: string;
	status: 'ok' | 'watch' | 'blocked';
	sourceRef: string;
}

export interface MacroContributionView {
	driverId: string;
	label: string;
	summary: string;
	components: MacroContributionComponentView[];
	sourceRef: string;
}

export interface MacroCoMovePointView {
	ym: string;
	x: number;
	y: number;
	px: number;
	py: number;
	latest: boolean;
	label: string;
}

export interface MacroCoMoveGateView {
	driverId: string;
	label: string;
	corr: number | null;
	n: number | null;
	window: string;
	status: 'candidate' | 'unstable' | 'missing';
	sourceRef: string;
	detail: string;
	points: MacroCoMovePointView[];
	displayedPoints: number;
	lagLabel: string;
	formula: string;
	limitations: string[];
	xZero: number;
	yZero: number;
	xRange: string;
	yRange: string;
}

export interface MacroEvidenceGateView {
	id: 'macroData' | 'path' | 'comove' | 'company' | 'quant';
	labelKr: string;
	labelEn: string;
	value: string;
	detailKr: string;
	detailEn: string;
	status: 'ok' | 'watch' | 'blocked';
	sourceRef: string;
	blocks: string[];
}

export interface MacroMissingView {
	id: string;
	status: 'missing' | 'partial' | 'notWiredYet' | 'staleRisk';
	reason: string;
	sourceRef: string;
}

export interface MacroLensSnapshot {
	asOf: {
		macro: string | null;
		price: string | null;
		finance: string | null;
	};
	company: {
		code: string;
		name: string;
		sector: string;
		industry: string;
	};
	marketPhase: {
		kr: MacroPhaseView | null;
		us: MacroPhaseView | null;
	};
	drivers: MacroDriverView[];
	topPressures: MacroDriverView[];
	transmissionEdges: MacroTransmissionEdgeView[];
	companyCheckpoints: MacroCheckpointView[];
	sectorBinding: {
		tailwind: Tailwind | null;
		top: { id: string; kr: string; en: string; blended: number }[];
		bottom: { id: string; kr: string; en: string; blended: number }[];
	};
	exposureQuality: MacroExposureQualityView;
	exposureIndicators: MacroExposureIndicatorView[];
	releaseRail: MacroReleaseView[];
	sourcePackets: MacroSourcePacketView[];
	contributionStacks: MacroContributionView[];
	coMoveGates: MacroCoMoveGateView[];
	evidenceGates: MacroEvidenceGateView[];
	falsifiers: MacroFalsifierView[];
	scenarios: MacroScenarioView[];
	sourceRefs: string[];
	missing: MacroMissingView[];
	glance?: MacroGlanceView;
	macroPath?: MacroPathView;
	marketOnly?: boolean;
}

export interface MacroPhaseView {
	market: 'KR' | 'US';
	phase: string;
	label: string;
	quadrant: string;
	growth: string;
	inflation: string;
	description: string;
}

export interface RegimeQuadrantCellView {
	key: 'stagflation' | 'reflation' | 'deflation' | 'goldilocks';
	labelKr: string;
	labelEn: string;
	growth: 'rising' | 'falling';
	inflation: 'rising' | 'falling';
}

export interface RegimeMarketView {
	market: 'KR' | 'US';
	cellKey: RegimeQuadrantCellView['key'] | null;
	phase: string;
	phaseLabel: string;
	quadrantLabel: string;
	growth: string;
	inflation: string;
	confidence: string | null;
	hasQuadrant: boolean;
	lensConflict: boolean;
	transitionLabel: string;
	hasTransitionProgress: boolean;
	assets: { key: string; labelKr: string; labelEn: string; weight: string; tone: 'ow' | 'uw' | 'nu' }[];
	description: string;
}

export interface RegimeQuadrantView {
	asOf: string | null;
	cells: RegimeQuadrantCellView[];
	markets: RegimeMarketView[];
	freshness: {
		status: 'fresh' | 'watch' | 'stale' | 'unknown';
		label: string;
		daysLag: number | null;
	};
	lensConflict: boolean;
}

export interface MacroPathSectorNode {
	key: string;
	labelKr: string;
	labelEn: string;
	industryId: string | null;
	tailwindKey: string | null;
	blended: number | null;
	tailwindLabelKr: string;
	tailwindLabelEn: string;
	tone: Tone;
	missingTailwind: boolean;
	active: boolean;
}

export interface MacroPathLinkView {
	id: string;
	driverId: string;
	driverLabel: string;
	channel: MacroChannel;
	channelLabelKr: string;
	channelLabelEn: string;
	sectorKeys: string[];
	sectorNodes: MacroPathSectorNode[];
	market: MacroMarket;
	sign: 'positive' | 'negative' | 'mixed' | 'unknown';
	signLabel: string;
	evidenceLevel: 'observed' | 'sectorPrior' | 'template';
	evidenceLabel: 'OBS' | 'PRIOR' | 'TPL';
	confidence: 'high' | 'medium' | 'low' | 'blocked';
	styleClass: string;
	signClass: string;
	opacity: number;
	financialLine: string;
	valuationLever: string;
	lagLabel: string;
	note: string;
	sourceRefs: string[];
	active: boolean;
	allSector: boolean;
}

export interface MacroPathView {
	asOf: string | null;
	mode: 'compact' | 'full';
	driverNodes: { id: string; label: string; market: MacroMarket; freshnessStatus: string }[];
	channelNodes: { id: MacroChannel; labelKr: string; labelEn: string }[];
	sectorNodes: MacroPathSectorNode[];
	links: MacroPathLinkView[];
	allSectorLinks: MacroPathLinkView[];
	missing: MacroMissingView[];
	coverageKeys: string[];
	hasNegativeTailwind: boolean;
	captionKr: string;
	captionEn: string;
}

export interface MacroGlanceView {
	asOf: string | null;
	regime: RegimeQuadrantView;
	path: MacroPathView;
	sectorTailwinds: { id: string; kr: string; en: string; blended: number; tailwindKey?: string }[];
}

interface EdgeTemplate {
	driverId: string;
	market: MacroMarket;
	sectors: string[];
	channel: MacroChannel;
	financialLine: string;
	valuationLever: MacroTransmissionEdgeView['valuationLever'];
	sign: MacroTransmissionEdgeView['sign'];
	lagMonths: [number, number] | null;
	confidence: MacroTransmissionEdgeView['confidence'];
	evidenceLevel: MacroTransmissionEdgeView['evidenceLevel'];
	requiredCompanyEvidence: string[];
	note: string;
}

const DRIVER_SEMANTICS: Record<string, { direction: string; lag: number | null }> = {
	USDKRW: { direction: '상승은 원화 약세. 수출 환산매출과 수입원가가 동시에 움직인다.', lag: 1 },
	BASE_RATE: { direction: '상승은 차입비용과 할인율 상승 압력으로 전파될 수 있다.', lag: 6 },
	FEDFUNDS: { direction: '상승은 글로벌 할인율·달러 유동성 압력으로 전파될 수 있다.', lag: 6 },
	DGS10: { direction: '상승은 장기 할인율과 multiple 압박으로 전파될 수 있다.', lag: 3 },
	CPI: { direction: '상승은 가격전가와 비용압박을 동시에 확인해야 한다.', lag: 3 },
	CPIAUCSL: { direction: '상승은 미국 긴축·수요 둔화 압력으로 전파될 수 있다.', lag: 3 },
	EXPORT: { direction: '상승은 외부수요와 국내 제조업 매출 환경을 보여준다.', lag: 1 },
	IPI: { direction: '상승은 생산·가동률 환경 개선 신호다.', lag: 1 },
	CLI: { direction: '상승은 경기 선행 모멘텀 개선 신호다.', lag: 3 },
	BAMLH0A0HYM2: { direction: '상승은 신용위험과 자금조달 압력 확대 신호다.', lag: 3 },
	NFCI: { direction: '상승은 금융여건 긴축 신호다.', lag: 3 },
	VIXCLS: { direction: '상승은 위험회피와 equity risk premium 확대 신호다.', lag: 0 },
	DCOILWTICO: { direction: '상승은 에너지 매출 증가 요인, 제조 원가 상승 요인일 수 있다.', lag: 1 },
	PCOPPUSDM: { direction: '상승은 글로벌 제조·전기화 수요와 원가 압력을 동시에 시사한다.', lag: 1 },
	PPI_SEMI: { direction: '상승은 반도체 제품가격 환경 개선 또는 원가 전가 신호다.', lag: 1 },
	PPI_CHEM: { direction: '상승은 화학 제품가격과 원가 전가력을 동시에 확인해야 한다.', lag: 1 },
	PPI_STEEL: { direction: '상승은 철강 판가와 수요 환경을 함께 본다.', lag: 1 },
	PPI_AUTO: { direction: '상승은 자동차 판가·원가 전가력을 함께 본다.', lag: 1 },
	PPI_DISPLAY: { direction: '상승은 디스플레이 가격 환경 개선 신호다.', lag: 1 },
	PPI_ELEC: { direction: '상승은 전기전자 판가와 부품 원가를 함께 본다.', lag: 1 },
	PPI_OIL: { direction: '상승은 정유·석화 판가와 원재료 원가를 동시에 확인하게 만든다.', lag: 1 }
};

const SECTOR_DRIVER: Record<string, string[]> = {
	semiconductor: ['PPI_SEMI', 'USDKRW', 'EXPORT', 'DCOILWTICO', 'BAMLH0A0HYM2'],
	auto: ['PPI_AUTO', 'USDKRW', 'EXPORT', 'BASE_RATE', 'DCOILWTICO'],
	electronics: ['PPI_ELEC', 'USDKRW', 'EXPORT', 'DGS10'],
	chemical: ['PPI_CHEM', 'DCOILWTICO', 'USDKRW', 'EXPORT'],
	battery: ['PPI_CHEM', 'PCOPPUSDM', 'USDKRW', 'DGS10'],
	steel: ['PPI_STEEL', 'PCOPPUSDM', 'EXPORT', 'USDKRW'],
	shipbuilding: ['USDKRW', 'EXPORT', 'BASE_RATE', 'PPI_STEEL'],
	finance: ['BASE_RATE', 'DGS10', 'BAMLH0A0HYM2', 'NFCI'],
	construction: ['BASE_RATE', 'HOUSE_PRICE', 'BAMLH0A0HYM2'],
	realestate: ['BASE_RATE', 'HOUSE_PRICE', 'DGS10'],
	energy: ['DCOILWTICO', 'USDKRW', 'CPI'],
	retail: ['CPI', 'CSI', 'BASE_RATE'],
	cosmetics: ['USDKRW', 'EXPORT', 'CSI'],
	software: ['DGS10', 'FEDFUNDS', 'NASDAQCOM'],
	pharma: ['DGS10', 'FEDFUNDS', 'USDKRW'],
	telecom: ['BASE_RATE', 'CPI', 'DGS10'],
	food: ['CPI', 'DCOILWTICO', 'USDKRW'],
	logistics: ['DCOILWTICO', 'EXPORT', 'USDKRW']
};

const EDGE_TEMPLATES: EdgeTemplate[] = [
	{
		driverId: 'USDKRW',
		market: 'KR',
		sectors: ['semiconductor', 'auto', 'electronics', 'shipbuilding', 'chemical', 'battery', 'steel', 'cosmetics', 'logistics'],
		channel: 'revenue',
		financialLine: '매출 성장률 / 환산손익',
		valuationLever: 'growth',
		sign: 'mixed',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'sectorPrior',
		requiredCompanyEvidence: ['해외 매출 비중', '외화 매출·매입 통화', 'FX 손익 주석'],
		note: '원화 약세는 수출 환산매출에는 유리할 수 있지만 달러 원가·부채가 있으면 상쇄된다.'
	},
	{
		driverId: 'EXPORT',
		market: 'KR',
		sectors: ['semiconductor', 'auto', 'electronics', 'shipbuilding', 'chemical', 'steel', 'battery', 'logistics'],
		channel: 'revenue',
		financialLine: '매출 성장률 / 가동률',
		valuationLever: 'growth',
		sign: 'positive',
		lagMonths: [1, 6],
		confidence: 'medium',
		evidenceLevel: 'observed',
		requiredCompanyEvidence: ['수출·해외 법인 매출', '주요 제품 수요', '재고와 수주'],
		note: '수출 모멘텀은 제조업 매출 환경의 1차 driver다.'
	},
	{
		driverId: 'BASE_RATE',
		market: 'KR',
		sectors: ['all'],
		channel: 'balanceSheet',
		financialLine: '이자비용 / 차입 재조달',
		valuationLever: 'discountRate',
		sign: 'negative',
		lagMonths: [3, 12],
		confidence: 'medium',
		evidenceLevel: 'template',
		requiredCompanyEvidence: ['부채비율', '단기차입금', '이자보상배율', '차입금 만기'],
		note: '금리는 손익의 이자비용과 가치평가 할인율에 동시에 닿는다.'
	},
	{
		driverId: 'DGS10',
		market: 'US',
		sectors: ['software', 'pharma', 'battery', 'semiconductor', 'electronics', 'all'],
		channel: 'valuation',
		financialLine: 'multiple / 할인율',
		valuationLever: 'discountRate',
		sign: 'negative',
		lagMonths: [0, 6],
		confidence: 'low',
		evidenceLevel: 'template',
		requiredCompanyEvidence: ['장기 성장 기대', 'PER/PBR 위치', '현금흐름 기간 구조'],
		note: '장기금리는 성장주 multiple과 risk premium을 흔드는 공통 driver다.'
	},
	{
		driverId: 'BAMLH0A0HYM2',
		market: 'US',
		sectors: ['all'],
		channel: 'valuation',
		financialLine: '신용스프레드 / 위험프리미엄',
		valuationLever: 'riskPremium',
		sign: 'negative',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'observed',
		requiredCompanyEvidence: ['신용등급', '차입 의존도', '만기 구조'],
		note: 'HY spread 확대는 위험자산 전반의 요구수익률 상승 신호다.'
	},
	{
		driverId: 'DCOILWTICO',
		market: 'GLOBAL',
		sectors: ['energy', 'chemical', 'auto', 'logistics', 'food'],
		channel: 'margin',
		financialLine: '매출총이익률 / 원가율',
		valuationLever: 'margin',
		sign: 'mixed',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'sectorPrior',
		requiredCompanyEvidence: ['원재료 비중', '가격 전가력', '재고 회전', '연료비 비중'],
		note: '유가는 에너지 매출과 제조·물류 원가에 반대 방향으로 작용할 수 있다.'
	},
	{
		driverId: 'CPI',
		market: 'KR',
		sectors: ['retail', 'food', 'telecom', 'construction', 'all'],
		channel: 'margin',
		financialLine: '판가 / 비용 전가',
		valuationLever: 'margin',
		sign: 'mixed',
		lagMonths: [1, 6],
		confidence: 'low',
		evidenceLevel: 'template',
		requiredCompanyEvidence: ['가격 전가력', '원가 구조', '수요 탄력성'],
		note: '물가는 판가 인상 여지와 수요 둔화를 동시에 만든다.'
	},
	{
		driverId: 'PPI_SEMI',
		market: 'KR',
		sectors: ['semiconductor'],
		channel: 'margin',
		financialLine: '제품가격 / 영업이익률',
		valuationLever: 'margin',
		sign: 'positive',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'observed',
		requiredCompanyEvidence: ['제품 믹스', '재고 평가', '가동률'],
		note: '반도체 PPI는 제품가격 환경의 직접 proxy로 쓸 수 있다.'
	},
	{
		driverId: 'PPI_CHEM',
		market: 'KR',
		sectors: ['chemical', 'battery'],
		channel: 'margin',
		financialLine: '제품가격 / 스프레드',
		valuationLever: 'margin',
		sign: 'mixed',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'observed',
		requiredCompanyEvidence: ['원재료-제품 스프레드', '고객 전가력', '재고'],
		note: '화학 PPI는 판가와 원가 전가력을 함께 확인해야 한다.'
	},
	{
		driverId: 'PPI_STEEL',
		market: 'KR',
		sectors: ['steel', 'shipbuilding'],
		channel: 'margin',
		financialLine: '판가 / 원재료 스프레드',
		valuationLever: 'margin',
		sign: 'mixed',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'observed',
		requiredCompanyEvidence: ['철강재 매입·판매 구조', '장기계약 가격'],
		note: '철강 PPI는 철강사는 판가, 수요처는 원가로 전파된다.'
	},
	{
		driverId: 'PPI_AUTO',
		market: 'KR',
		sectors: ['auto'],
		channel: 'margin',
		financialLine: '판가 / 영업이익률',
		valuationLever: 'margin',
		sign: 'mixed',
		lagMonths: [0, 3],
		confidence: 'medium',
		evidenceLevel: 'observed',
		requiredCompanyEvidence: ['판매가격', '부품 원가', '인센티브', '환율'],
		note: '자동차 PPI는 가격 전가력과 수요 둔화를 같이 확인해야 한다.'
	}
];

const SCENARIOS: Omit<MacroScenarioView, 'readiness'>[] = [
	{ id: 'fx10', label: '원/달러 +10%', driverId: 'USDKRW', shock: 'USDKRW +10%', firstBreak: '수출 환산매출 또는 수입원가', expectedDirection: '수출 환산매출과 달러 원가가 동시에 움직임', impactedFinancialLine: '매출 성장률 / 매출총이익률', valuationLever: 'growth / margin', falsifier: '달러 원가·부채·헤지 정책 확인 전 방향 단정 금지', requiredEvidence: ['해외 매출 비중', '외화 원가', 'FX 손익'], nextSurface: '재무제표 분석 · 매출/원가/주석' },
	{ id: 'rate100', label: '기준금리 +100bp', driverId: 'BASE_RATE', shock: 'BASE_RATE +1.0%p', firstBreak: '이자비용과 할인율', expectedDirection: '차입 의존 기업에는 비용·할인율 상승 압력', impactedFinancialLine: '이자비용 / 순이익 / multiple', valuationLever: 'discountRate', falsifier: '순현금·고정금리 장기차입이면 약화', requiredEvidence: ['부채비율', '단기차입', '이자보상배율'], nextSurface: '재무제표 분석 · 안정성/현금흐름' },
	{ id: 'oil30', label: 'WTI +30%', driverId: 'DCOILWTICO', shock: 'WTI +30%', firstBreak: '원재료·연료비 또는 에너지 매출', expectedDirection: '에너지는 매출 증가 요인, 제조·물류는 원가 상승 요인 확인', impactedFinancialLine: '매출총이익률 / 원가율', valuationLever: 'margin', falsifier: '가격 전가·재고평가·원가 계약 확인 전 단정 금지', requiredEvidence: ['원재료 비중', '가격 전가력', '재고'], nextSurface: '재무제표 분석 · 마진/재고' },
	{ id: 'exportDown', label: '수출 YoY -10%', driverId: 'EXPORT', shock: 'EXPORT YoY -10%', firstBreak: '외부수요와 가동률', expectedDirection: '수출 제조업 매출·가동률 압박 가능', impactedFinancialLine: '매출 성장률 / 재고 / 가동률', valuationLever: 'growth', falsifier: '시장점유율·제품 믹스·단가가 반대 방향이면 약화', requiredEvidence: ['수출 매출', '수주', '재고'], nextSurface: '산업/동종업종 비교' },
	{ id: 'hy200', label: 'HY spread +200bp', driverId: 'BAMLH0A0HYM2', shock: 'HY spread +2.0%p', firstBreak: '위험프리미엄과 차입 접근성', expectedDirection: '레버리지 기업의 요구수익률·차입 접근성 압력', impactedFinancialLine: '신용스프레드 / 금융비용 / multiple', valuationLever: 'riskPremium', falsifier: '현금 보유·모회사 지원·만기 여유 확인 전 단정 금지', requiredEvidence: ['신용등급', '만기', '현금 보유'], nextSurface: '신용/리스크 경고등' }
];

const CORE_DRIVER_IDS = ['USDKRW', 'BASE_RATE', 'CPI', 'EXPORT', 'DGS10', 'BAMLH0A0HYM2', 'DCOILWTICO'];
const MS_DAY = 24 * 60 * 60 * 1000;
const REGIME_CELLS: RegimeQuadrantCellView[] = [
	{ key: 'stagflation', labelKr: '스태그플레이션', labelEn: 'Stagflation', growth: 'falling', inflation: 'rising' },
	{ key: 'reflation', labelKr: '리플레이션', labelEn: 'Reflation', growth: 'rising', inflation: 'rising' },
	{ key: 'deflation', labelKr: '디플레이션', labelEn: 'Deflation', growth: 'falling', inflation: 'falling' },
	{ key: 'goldilocks', labelKr: '골디락스', labelEn: 'Goldilocks', growth: 'rising', inflation: 'falling' }
];
const ASSET_ROWS = [
	{ key: 'equity', labelKr: '주식', labelEn: 'Equity' },
	{ key: 'bond', labelKr: '채권', labelEn: 'Bond' },
	{ key: 'commodity', labelKr: '원자재', labelEn: 'Comdty' },
	{ key: 'gold', labelKr: '금', labelEn: 'Gold' },
	{ key: 'tips', labelKr: '물가채', labelEn: 'TIPS' },
	{ key: 'cash', labelKr: '현금', labelEn: 'Cash' }
];
const CHANNEL_LABELS: Record<MacroChannel, { kr: string; en: string }> = {
	revenue: { kr: '매출', en: 'Sales' },
	margin: { kr: '마진', en: 'Margin' },
	balanceSheet: { kr: '차입', en: 'Debt' },
	cashFlow: { kr: '현금', en: 'Cash' },
	valuation: { kr: '밸류', en: 'Value' }
};

const fmtDate = (d?: string | null) => d ? (d.length === 8 ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` : d) : '—';

function fmtLatest(m: MacroLatest): string {
	const v = m.v.toLocaleString('en-US', { maximumFractionDigits: m.def.digits ?? 2 });
	const signed = m.def.yoy && m.v > 0 ? '+' + v : v;
	const u = m.def.unit;
	return u === 'pt' || u === '원' ? signed : u === '$' ? '$' + signed : u === '$/t' ? '$' + signed : signed + u;
}

function fmtChange(m: MacroLatest): string {
	if (m.chg == null) return '—';
	const v = Math.abs(m.chg).toLocaleString('en-US', { maximumFractionDigits: m.def.digits ?? 2 });
	return `${m.chg > 0 ? '+' : m.chg < 0 ? '-' : ''}${v}${m.def.unit === 'pt' || m.def.unit === '원' ? '' : m.def.unit}`;
}

function parseYmd(d?: string | null): number | null {
	if (!d || d.length < 8) return null;
	const t = Date.UTC(+d.slice(0, 4), +d.slice(4, 6) - 1, +d.slice(6, 8));
	return Number.isFinite(t) ? t : null;
}

function daysLag(d?: string | null): number | null {
	const t = parseYmd(d);
	if (t == null) return null;
	return Math.max(0, Math.floor((Date.now() - t) / MS_DAY));
}

function transformOf(def: MacroSeriesDef): string {
	if (def.yoy) return 'YoY + latest delta';
	if (def.unit === '%' || def.unit === '%p') return 'level + rate delta';
	if (def.unit === '원') return 'FX level + latest delta';
	if (def.unit === '$' || def.unit === '$/t') return 'commodity level + latest delta';
	return 'level + latest delta';
}

function freshnessOf(def: MacroSeriesDef, d: string): MacroDriverView['freshness'] {
	const lag = daysLag(d);
	if (lag == null) return { status: 'unknown', daysLag: null, label: '기준일 확인 필요' };
	const staleAfter = staleAfterDaysOf(def);
	if (lag > staleAfter) return { status: 'stale', daysLag: lag, label: `stale ${lag}d` };
	if (lag > staleAfter * 0.65) return { status: 'watch', daysLag: lag, label: `watch ${lag}d` };
	return { status: 'fresh', daysLag: lag, label: `fresh ${lag}d` };
}

function staleAfterDaysOf(def: MacroSeriesDef): number {
	if (def.src === 'fred') return 10;
	if (def.id === 'BASE_RATE') return 65;
	return 75;
}

function cadenceDaysOf(def: MacroSeriesDef): number {
	if (def.src === 'fred') return 7;
	if (def.id === 'BASE_RATE') return 60;
	return 35;
}

function frequencyOf(def: MacroSeriesDef): string {
	if (def.src === 'fred') return 'FRED rolling/daily check';
	if (def.id === 'BASE_RATE') return 'ECOS policy event';
	return def.yoy ? 'ECOS monthly YoY' : 'ECOS monthly';
}

function addDaysYmd(d: string, days: number): string {
	const t = parseYmd(d);
	if (t == null) return '—';
	const next = new Date(t + days * MS_DAY);
	const y = next.getUTCFullYear();
	const m = `${next.getUTCMonth() + 1}`.padStart(2, '0');
	const day = `${next.getUTCDate()}`.padStart(2, '0');
	return `${y}-${m}-${day}`;
}

function componentStatus(value: number): MacroContributionComponentView['status'] {
	return value >= 0.67 ? 'ok' : value >= 0.25 ? 'watch' : 'blocked';
}

function confidenceScore(edge: MacroTransmissionEdgeView | undefined): number {
	if (!edge || edge.confidence === 'blocked') return 0;
	const conf = edge.confidence === 'high' ? 1 : edge.confidence === 'medium' ? 0.72 : 0.42;
	const evidence = edge.evidenceLevel === 'observed' ? 1 : edge.evidenceLevel === 'sectorPrior' ? 0.65 : 0.38;
	return Math.min(1, conf * evidence);
}

function freshnessScore(status: MacroDriverView['freshness']['status']): number {
	return status === 'fresh' ? 1 : status === 'watch' ? 0.55 : status === 'unknown' ? 0.25 : 0.05;
}

function exposureQualityScore(q: MacroExposureQualityView): number {
	return q.status === 'quantCandidate' ? 0.86 : q.status === 'qualitativeOnly' ? 0.42 : 0.08;
}

function changeIntensity(m: MacroLatest): number {
	if (m.chg == null || !Number.isFinite(m.chg)) return 0;
	const abs = Math.abs(m.chg);
	const unit = m.def.unit;
	if (unit === '%' || unit === '%p') return Math.min(24, abs * 6);
	if (unit === '원') return Math.min(24, abs / 4);
	if (unit === '$') return Math.min(24, abs * 2.5);
	if (unit === '$/t') return Math.min(24, abs / 120);
	if (unit === 'pt') return Math.min(24, (abs / Math.max(1, Math.abs(m.v))) * 500);
	return Math.min(24, abs);
}

function signedValue(v: number, maximumFractionDigits = 2): string {
	const abs = Math.abs(v).toLocaleString('en-US', { maximumFractionDigits });
	return `${v > 0 ? '+' : v < 0 ? '-' : ''}${abs}`;
}

function paddedDomain(values: number[]): [number, number] {
	const finite = values.filter((v) => Number.isFinite(v));
	if (!finite.length) return [-1, 1];
	let lo = Math.min(0, ...finite);
	let hi = Math.max(0, ...finite);
	if (lo === hi) {
		const pad = Math.max(0.01, Math.abs(lo) * 0.12);
		return [lo - pad, hi + pad];
	}
	const pad = (hi - lo) * 0.08;
	return [lo - pad, hi + pad];
}

function domainPct(v: number, lo: number, hi: number): number {
	const span = hi - lo || 1;
	return Math.max(0, Math.min(100, ((v - lo) / span) * 100));
}

function buildCoMoveScatter(cm?: CoMover): Pick<MacroCoMoveGateView, 'points' | 'displayedPoints' | 'lagLabel' | 'formula' | 'limitations' | 'xZero' | 'yZero' | 'xRange' | 'yRange'> {
	const raw = (cm?.points ?? [])
		.filter((p) => Number.isFinite(p.macroDiff) && Number.isFinite(p.stockReturn))
		.slice(-72);
	const [xMin, xMax] = paddedDomain(raw.map((p) => p.macroDiff));
	const [yMin, yMax] = paddedDomain(raw.map((p) => p.stockReturn));
	return {
		points: raw.map((p, i) => ({
			ym: p.ym,
			x: p.macroDiff,
			y: p.stockReturn,
			px: domainPct(p.macroDiff, xMin, xMax),
			py: 100 - domainPct(p.stockReturn, yMin, yMax),
			latest: i === raw.length - 1,
			label: `${p.ym}: macro Δ ${signedValue(p.macroDiff, 2)} · stock ${signedValue(p.stockReturn * 100, 1)}%`
		})),
		displayedPoints: raw.length,
		lagLabel: 'lag 0M',
		formula: 'x=거시 월말값 1차차분 · y=종목 월수익률',
		limitations: ['월말 겹침 표본', '발표일·revision 미반영', 'outlier·우연상관 민감'],
		xZero: domainPct(0, xMin, xMax),
		yZero: 100 - domainPct(0, yMin, yMax),
		xRange: `${signedValue(xMin, 2)} to ${signedValue(xMax, 2)}`,
		yRange: `${signedValue(yMin * 100, 1)}% to ${signedValue(yMax * 100, 1)}%`
	};
}

function coMovementOf(cm?: CoMover): MacroDriverView['coMovement'] | null {
	if (!cm) return null;
	const abs = Math.abs(cm.corr);
	const status: NonNullable<MacroDriverView['coMovement']>['status'] = cm.n >= 24 && abs >= 0.45 ? 'candidate' : 'unstable';
	const sign = cm.corr > 0 ? '+' : '';
	return {
		corr: cm.corr,
		n: cm.n,
		window: `${cm.n}M overlap`,
		status,
		label: `${status === 'candidate' ? '탐색 후보' : '불안정'} corr ${sign}${cm.corr.toFixed(2)} · n=${cm.n}`
	};
}

function pressureLevel(relevance: MacroDriverView['relevance'], m: MacroLatest, coMovement: MacroDriverView['coMovement'] | null, freshness: MacroDriverView['freshness']): MacroDriverView['pressureLevel'] {
	if (freshness.status === 'stale') return 'blocked';
	if (relevance === 'primary' && coMovement?.status === 'candidate') return 'high';
	if (relevance === 'primary') return changeIntensity(m) >= 10 ? 'high' : 'medium';
	if (relevance === 'secondary' && coMovement?.status === 'candidate') return 'medium';
	if (relevance === 'secondary' && changeIntensity(m) >= 12) return 'medium';
	return 'low';
}

function pressureReason(relevance: MacroDriverView['relevance'], m: MacroLatest, coMovement: MacroDriverView['coMovement'] | null, freshness: MacroDriverView['freshness']): string {
	const rel = relevance === 'primary' ? '섹터 직접 driver' : relevance === 'secondary' ? '공통 매크로 driver' : '맥락 지표';
	const chg = m.chg == null ? '최근 변화 없음' : `최근 변화 ${fmtChange(m)}`;
	const co = coMovement ? coMovement.label : '동행상관 미확인';
	return `${rel} · ${chg} · ${co} · ${freshness.label}`;
}

function qualityHintOf(relevance: MacroDriverView['relevance'], coMovement: MacroDriverView['coMovement'] | null, freshness: MacroDriverView['freshness']): string {
	if (freshness.status === 'stale') return 'blocked: stale macro observation';
	if (coMovement?.status === 'candidate') return 'co-movement candidate; company evidence still required';
	if (relevance === 'primary') return 'sector path available; regression quality pending';
	if (relevance === 'secondary') return 'macro context; company-specific exposure pending';
	return 'context only';
}

function phaseView(market: 'KR' | 'US', side?: MacroSide): MacroPhaseView | null {
	if (!side) return null;
	const q = side.quadrant;
	return {
		market,
		phase: side.phase,
		label: side.phaseLabel || side.phase,
		quadrant: q?.quadrantLabel || q?.quadrant || '상세 없음',
		growth: q?.growth || '—',
		inflation: q?.inflation || '—',
		description: q?.description || '국면 상세 데이터 없음'
	};
}

function assetTone(weight?: string): 'ow' | 'uw' | 'nu' {
	return weight === 'overweight' ? 'ow' : weight === 'underweight' ? 'uw' : 'nu';
}

function cellFromSide(side?: MacroSide): RegimeQuadrantCellView['key'] | null {
	const q = side?.quadrant;
	const key = q?.quadrant;
	if (key === 'stagflation' || key === 'reflation' || key === 'deflation' || key === 'goldilocks') return key;
	const growth = q?.growth;
	const inflation = q?.inflation;
	if (growth === 'falling' && inflation === 'rising') return 'stagflation';
	if (growth === 'rising' && inflation === 'rising') return 'reflation';
	if (growth === 'falling' && inflation === 'falling') return 'deflation';
	if (growth === 'rising' && inflation === 'falling') return 'goldilocks';
	return null;
}

function transitionLabel(side?: MacroSide): { label: string; hasProgress: boolean } {
	const tr = side?.transition;
	if (!tr) return { label: '전이신호 미산출', hasProgress: false };
	const progress = typeof tr.progress === 'number' ? `${tr.progress}%` : '미확정';
	const from = tr.from || '?';
	const to = tr.to || '?';
	const triggered = tr.triggered?.length ?? 0;
	const pending = tr.pending?.length ?? 0;
	return { label: `${from}→${to} · ${progress} · ${triggered}/${triggered + pending} 신호`, hasProgress: typeof tr.progress === 'number' };
}

function freshnessFromAsOf(asOf?: string | null): RegimeQuadrantView['freshness'] {
	const lag = daysLag((asOf || '').replaceAll('-', ''));
	if (lag == null) return { status: 'unknown', label: 'asOf 없음', daysLag: null };
	if (lag > 10) return { status: 'stale', label: `${lag}일 경과`, daysLag: lag };
	if (lag > 5) return { status: 'watch', label: `${lag}일 경과`, daysLag: lag };
	return { status: 'fresh', label: `${lag}일`, daysLag: lag };
}

function buildRegimeMarket(market: 'KR' | 'US', side?: MacroSide): RegimeMarketView {
	const q = side?.quadrant;
	const cellKey = cellFromSide(side);
	const phase = side?.phase ?? 'unknown';
	const phaseLabel = side?.phaseLabel || phase;
	const quadrantLabel = q?.quadrantLabel || q?.quadrant || '국면 상세 데이터 없음';
	const tr = transitionLabel(side);
	return {
		market,
		cellKey,
		phase,
		phaseLabel,
		quadrantLabel,
		growth: q?.growth || '—',
		inflation: q?.inflation || '—',
		confidence: q?.confidence || side?.confidence || null,
		hasQuadrant: !!q,
		lensConflict: !!q && phase !== q.quadrant,
		transitionLabel: tr.label,
		hasTransitionProgress: tr.hasProgress,
		assets: ASSET_ROWS.map((asset) => ({
			...asset,
			weight: q?.assetImplication?.[asset.key] ?? 'neutral',
			tone: assetTone(q?.assetImplication?.[asset.key])
		})),
		description: q?.description || '국면 상세 데이터 없음'
	};
}

export function buildRegimeQuadrant(macro: MacroFile | null): RegimeQuadrantView {
	const markets = [buildRegimeMarket('KR', macro?.kr), buildRegimeMarket('US', macro?.us)];
	return {
		asOf: macro?.asOf ?? null,
		cells: REGIME_CELLS,
		markets,
		freshness: freshnessFromAsOf(macro?.asOf ?? null),
		lensConflict: markets.some((m) => m.lensConflict)
	};
}

function evidenceStyle(edge: MacroTransmissionEdge): { styleClass: string; opacity: number; label: 'OBS' | 'PRIOR' | 'TPL' } {
	if (edge.evidenceLevel === 'observed') return { styleClass: 'observed', opacity: 1, label: 'OBS' };
	if (edge.evidenceLevel === 'sectorPrior') return { styleClass: 'prior', opacity: 0.65, label: 'PRIOR' };
	return { styleClass: 'template', opacity: 0.45, label: 'TPL' };
}

function signClass(sign: MacroTransmissionEdge['sign']): string {
	return sign === 'positive' ? 'pos' : sign === 'negative' ? 'neg' : sign === 'mixed' ? 'mix' : 'unk';
}

function pathSectorNode(
	key: string,
	sectorTailwinds: { id: string; kr: string; en: string; blended: number; tailwindKey?: string }[],
	activeIndustryId?: string
): MacroPathSectorNode {
	const map = EDGE_SECTOR_TO_TAILWIND[key] ?? { industryId: null, tailwindKey: null, kr: key, en: key };
	const tw = map.tailwindKey ? sectorTailwinds.find((row) => row.tailwindKey === map.tailwindKey || row.id === map.industryId) : null;
	const cls = tw ? classifyTailwind(tw.blended) : null;
	return {
		key,
		labelKr: map.kr,
		labelEn: map.en,
		industryId: map.industryId,
		tailwindKey: map.tailwindKey,
		blended: tw?.blended ?? null,
		tailwindLabelKr: cls?.labelKr ?? 'tailwind 미산출',
		tailwindLabelEn: cls?.labelEn ?? 'tailwind missing',
		tone: cls?.tone ?? 'neutral',
		missingTailwind: !tw,
		active: !!activeIndustryId && map.industryId === activeIndustryId
	};
}

export function buildMacroPath(
	transmission: MacroTransmissionPayload | null | undefined,
	sectorTailwinds: { id: string; kr: string; en: string; blended: number; tailwindKey?: string }[],
	opts: { activeIndustryId?: string; mode?: 'compact' | 'full' } = {}
): MacroPathView {
	const mode = opts.mode ?? 'compact';
	const missing: MacroMissingView[] = [];
	if (!transmission?.edges?.length) {
		missing.push({ id: 'macro-path', status: 'missing', reason: 'macro.transmission edges unavailable', sourceRef: 'dashboards/macro.json#transmission' });
	}
	const driverById = new Map((transmission?.drivers ?? []).map((driver) => [driver.id, driver]));
	const sectorByKey = new Map<string, MacroPathSectorNode>();
	const links: MacroPathLinkView[] = [];
	const allSectorLinks: MacroPathLinkView[] = [];
	for (const edge of transmission?.edges ?? []) {
		const style = evidenceStyle(edge);
		const blocked = edge.confidence === 'blocked';
		const sectors = (edge.sectorKeys?.length ? edge.sectorKeys : ['unknown']);
		const allSector = sectors.length === 1 && sectors[0] === 'all';
		const sectorNodes = allSector
			? [pathSectorNode('all', sectorTailwinds, opts.activeIndustryId)]
			: sectors.map((key) => pathSectorNode(key, sectorTailwinds, opts.activeIndustryId));
		for (const node of sectorNodes) sectorByKey.set(node.key, node);
		const driver = driverById.get(edge.driverId);
		const channelLabel = CHANNEL_LABELS[edge.channel];
		const view: MacroPathLinkView = {
			id: edge.id,
			driverId: edge.driverId,
			driverLabel: driver?.labelKr ?? edge.driverId,
			channel: edge.channel,
			channelLabelKr: channelLabel?.kr ?? edge.channel,
			channelLabelEn: channelLabel?.en ?? edge.channel,
			sectorKeys: sectors,
			sectorNodes,
			market: edge.market,
			sign: edge.sign,
			signLabel: edge.sign === 'positive' ? '+' : edge.sign === 'negative' ? '-' : edge.sign === 'mixed' ? '±' : '?',
			evidenceLevel: edge.evidenceLevel,
			evidenceLabel: style.label,
			confidence: edge.confidence,
			styleClass: blocked ? 'blocked' : style.styleClass,
			signClass: blocked ? 'blocked' : signClass(edge.sign),
			opacity: blocked ? 0.3 : style.opacity,
			financialLine: edge.financialLine,
			valuationLever: edge.valuationLever,
			lagLabel: normalizeLag(edge.lagMonths) ? `${normalizeLag(edge.lagMonths)![0]}-${normalizeLag(edge.lagMonths)![1]}M` : '—',
			note: noteFromTransmission(edge),
			sourceRefs: edge.sourceRefs?.length ? edge.sourceRefs : [edge.sourceRef ?? `macro.transmission:edge:${edge.id}`],
			active: sectorNodes.some((node) => node.active),
			allSector
		};
		if (allSector) allSectorLinks.push(view);
		else links.push(view);
	}
	const sortedSectors = [...sectorByKey.values()].sort((a, b) => {
		if (a.key === 'all') return 1;
		if (b.key === 'all') return -1;
		if (a.blended == null && b.blended == null) return a.labelKr.localeCompare(b.labelKr);
		if (a.blended == null) return 1;
		if (b.blended == null) return -1;
		return b.blended - a.blended;
	});
	const negative = hasNegativeTailwind(sectorTailwinds);
	return {
		asOf: transmission?.asOf ?? null,
		mode,
		driverNodes: (transmission?.drivers ?? []).map((d) => ({
			id: d.id,
			label: d.labelKr ?? d.id,
			market: d.market,
			freshnessStatus: d.sourceLineage?.status ?? 'unknown'
		})),
		channelNodes: Object.entries(CHANNEL_LABELS).map(([id, label]) => ({ id: id as MacroChannel, labelKr: label.kr, labelEn: label.en })),
		sectorNodes: sortedSectors,
		links,
		allSectorLinks,
		missing: [...missing, ...((transmission?.missing ?? []) as MacroMissingView[])],
		coverageKeys: [...CURRENT_MACRO_EDGE_SECTOR_KEYS],
		hasNegativeTailwind: negative,
		captionKr: negative ? '음수 blended 섹터만 역풍으로 표시' : '전 섹터 약순풍 - 절대 역풍 없음',
		captionEn: negative ? 'Only negative blended sectors are headwind' : 'All sectors weak-positive - no absolute headwind'
	};
}

export function buildMacroGlanceView(
	macro: MacroFile | null,
	sectorTailwinds: { id: string; kr: string; en: string; blended: number; tailwindKey?: string }[],
	opts: { activeIndustryId?: string; mode?: 'compact' | 'full' } = {}
): MacroGlanceView {
	return {
		asOf: macro?.asOf ?? null,
		regime: buildRegimeQuadrant(macro),
		path: buildMacroPath(macro?.transmission ?? null, sectorTailwinds, opts),
		sectorTailwinds
	};
}

function toneFromValue(v: number | null, goodHigh = true): Tone {
	if (v == null) return 'neutral';
	if (goodHigh) return v >= 10 ? 'up' : v >= 3 ? 'good' : v >= 0 ? 'neutral' : 'warn';
	return v <= 80 ? 'up' : v <= 150 ? 'good' : v <= 250 ? 'warn' : 'down';
}

function buildCheckpoints(co: Company): MacroCheckpointView[] {
	const f = co.fundamentals;
	const cf = co.financials.cf;
	const fcf = cf.fcf;
	return [
		{
			id: 'sector',
			label: '섹터 전파',
			value: co.tailwind ? `${co.tailwind.label} ${co.tailwind.blended.toFixed(2)}` : '—',
			tone: co.tailwind?.tone ?? 'neutral',
			reason: '현재 macro sectorTailwind와 선택 업종의 방향',
			source: 'macro.sectorTailwind'
		},
		{
			id: 'margin',
			label: '마진 흡수력',
			value: f.opm == null ? '—' : `${f.opm.toFixed(1)}%`,
			tone: toneFromValue(f.opm),
			reason: '원가·환율 충격이 영업이익률에 흡수되는지 보는 1차 checkpoint',
			source: 'company.fundamentals.opm'
		},
		{
			id: 'debt',
			label: '금리 민감도',
			value: f.dr == null ? '—' : `${f.dr.toFixed(0)}%`,
			tone: toneFromValue(f.dr, false),
			reason: '금리와 신용스프레드 충격이 이자비용·재조달로 닿는 경로',
			source: 'company.fundamentals.dr'
		},
		{
			id: 'cashFlow',
			label: '현금흐름 흡수',
			value: fcf == null ? '—' : `${fcf.toFixed(2)}조`,
			tone: fcf == null ? 'neutral' : fcf > 0 ? 'good' : 'warn',
			reason: '마진·수요 충격이 실제 현금흐름을 잠식하는지 확인',
			source: 'company.financials.cf.fcf'
		},
		{
			id: 'valuation',
			label: '밸류 lever',
			value: co.valuation?.per == null ? '—' : `PER ${co.valuation.per.toFixed(1)}x`,
			tone: 'neutral',
			reason: '금리·성장률·마진 충격이 multiple 또는 할인율로 번역되는 위치',
			source: 'company.valuation'
		}
	];
}

function buildDrivers(latest: MacroLatest[], industry: string, coMovers: CoMover[]): MacroDriverView[] {
	const relevant = new Set(SECTOR_DRIVER[industry] ?? []);
	const latestById = new Map(latest.map((m) => [m.def.id, m]));
	const coById = new Map(coMovers.map((m) => [m.id, m]));
	const defs = MACRO_SERIES.filter((d) => latestById.has(d.id));
	return defs.map((def) => {
		const m = latestById.get(def.id)!;
		const meta = DRIVER_SEMANTICS[def.id] ?? { direction: '방향성 의미는 driver별 맥락과 같이 해석한다.', lag: null };
		const source: MacroDriverView['source'] = def.src === 'ecos' ? 'ECOS' : 'FRED';
		const relevance: MacroDriverView['relevance'] =
			relevant.has(def.id) ? 'primary' : CORE_DRIVER_IDS.includes(def.id) ? 'secondary' : 'context';
		const freshness = freshnessOf(def, m.d);
		const coMovement = coMovementOf(coById.get(def.id));
		const transform = transformOf(def);
		const level = pressureLevel(relevance, m, coMovement, freshness);
		return {
			id: def.id,
			label: def.kr,
			group: def.group ?? '기타',
			seriesId: def.id,
			unit: def.unit,
			source,
			value: fmtLatest(m),
			change: fmtChange(m),
			asOf: fmtDate(m.d),
			spark: m.spark,
			directionSemantics: meta.direction,
			defaultLagMonths: meta.lag,
			relevance,
			pressureLevel: level,
			pressureReason: pressureReason(relevance, m, coMovement, freshness),
			coMovement,
			freshness,
			transform,
			sourceLineage: `${source} · obs ${fmtDate(m.d)} · ${transform} · ${freshness.label}`,
			qualityHint: qualityHintOf(relevance, coMovement, freshness)
		};
	}).sort((a, b) => {
		const r = { primary: 0, secondary: 1, context: 2 };
		const p = { high: 0, medium: 1, low: 2, blocked: 3 };
		const ac = a.coMovement ? Math.abs(a.coMovement.corr) : 0;
		const bc = b.coMovement ? Math.abs(b.coMovement.corr) : 0;
		return r[a.relevance] - r[b.relevance] || p[a.pressureLevel] - p[b.pressureLevel] || bc - ac || a.group.localeCompare(b.group) || a.label.localeCompare(b.label);
	});
}

function normalizeLag(lag: number[] | [number, number] | null | undefined): [number, number] | null {
	if (!lag || lag.length < 2) return null;
	const start = Number(lag[0]);
	const end = Number(lag[1]);
	return Number.isFinite(start) && Number.isFinite(end) ? [start, end] : null;
}

function transmissionLineageOf(driver: MacroTransmissionPayload['drivers'][number]): string {
	const lineage = driver.sourceLineage;
	if (!lineage) return `${driver.source} · ${driver.sourceSeriesId} · ${driver.transform}`;
	const date = lineage.date ? fmtDate(lineage.date) : '—';
	return `${lineage.source} · ${lineage.sourceSeriesId} · obs ${date} · ${driver.transform} · ${lineage.status}`;
}

function applyTransmissionDriverLineage(drivers: MacroDriverView[], payload?: MacroTransmissionPayload | null): MacroDriverView[] {
	if (!payload?.drivers?.length) return drivers;
	const byId = new Map(payload.drivers.map((d) => [d.id, d]));
	return drivers.map((driver) => {
		const row = byId.get(driver.id);
		if (!row) return driver;
		const lineage = row.sourceLineage;
		return {
			...driver,
			source: row.source,
			seriesId: row.sourceSeriesId || driver.seriesId,
			unit: row.unit || driver.unit,
			group: row.group || driver.group,
			transform: row.transform || driver.transform,
			directionSemantics: row.directionSemantics || driver.directionSemantics,
			defaultLagMonths: normalizeLag(row.defaultLagMonths)?.[1] ?? driver.defaultLagMonths,
			asOf: lineage?.date ? fmtDate(lineage.date) : driver.asOf,
			sourceLineage: transmissionLineageOf(row),
			qualityHint: lineage?.status === 'missing' ? 'blocked: macro transmission lineage missing' : driver.qualityHint
		};
	});
}

function transmissionEdgeMatches(edge: MacroTransmissionEdge, sectorKey: string): boolean {
	const sectors = Array.isArray(edge.sectorKeys) ? edge.sectorKeys : [];
	return sectors.includes('all') || sectors.includes(sectorKey);
}

function noteFromTransmission(edge: MacroTransmissionEdge): string {
	const required = edge.requiredCompanyEvidence?.length ? `회사 증거: ${edge.requiredCompanyEvidence.slice(0, 3).join(' · ')}` : '회사 증거 필요';
	const falsifier = edge.falsifiers?.length ? `반증: ${edge.falsifiers[0]}` : '반증 조건은 source packet에서 확인';
	return `${required}. ${falsifier}.`;
}

function buildEdgesFromTransmission(co: Company, drivers: MacroDriverView[], payload?: MacroTransmissionPayload | null): MacroTransmissionEdgeView[] {
	if (!payload?.edges?.length) return [];
	const driverById = new Map(drivers.map((d) => [d.id, d]));
	const payloadDrivers = new Map(payload.drivers.map((d) => [d.id, d]));
	const sectorLabel = co.sector.kr || co.industry;
	return payload.edges
		.filter((e) => transmissionEdgeMatches(e, co.industry))
		.slice(0, 12)
		.map((e) => {
			const driver = driverById.get(e.driverId);
			const payloadDriver = payloadDrivers.get(e.driverId);
			const blocked = !driver || payloadDriver?.sourceLineage?.status === 'missing';
			const sourceRefs = [
				e.sourceRef ?? `macro.transmission:edge:${e.id}`,
				...(e.sourceRefs ?? []),
				payloadDriver ? transmissionLineageOf(payloadDriver) : `driver:${e.driverId}:missing`
			];
			return {
				id: e.id,
				driverId: e.driverId,
				driverLabel: driver?.label ?? payloadDriver?.labelKr ?? e.driverId,
				market: e.market,
				sectorKey: co.industry,
				sectorLabel,
				channel: e.channel,
				financialLine: e.financialLine,
				valuationLever: e.valuationLever,
				sign: e.sign,
				lagMonths: normalizeLag(e.lagMonths),
				confidence: blocked ? 'blocked' : e.confidence,
				evidenceLevel: e.evidenceLevel,
				requiredCompanyEvidence: e.requiredCompanyEvidence ?? [],
				sourceRefs,
				note: blocked ? `${noteFromTransmission(e)} 최신 driver 관측 lineage가 닫혀 있어 정량 claim은 잠근다.` : noteFromTransmission(e)
			};
		});
}

function buildMarketEdgesFromTransmission(drivers: MacroDriverView[], payload?: MacroTransmissionPayload | null): MacroTransmissionEdgeView[] {
	if (!payload?.edges?.length) return [];
	const driverById = new Map(drivers.map((d) => [d.id, d]));
	const payloadDrivers = new Map(payload.drivers.map((d) => [d.id, d]));
	return payload.edges.slice(0, 16).map((e) => {
		const driver = driverById.get(e.driverId);
		const payloadDriver = payloadDrivers.get(e.driverId);
		const blocked = !driver || payloadDriver?.sourceLineage?.status === 'missing';
		const sectorKeys = e.sectorKeys?.length ? e.sectorKeys : ['unknown'];
		const sectorLabels = sectorKeys.map((key) => EDGE_SECTOR_TO_TAILWIND[key]?.kr ?? key);
		const sourceRefs = [
			e.sourceRef ?? `macro.transmission:edge:${e.id}`,
			...(e.sourceRefs ?? []),
			payloadDriver ? transmissionLineageOf(payloadDriver) : `driver:${e.driverId}:missing`
		];
		return {
			id: e.id,
			driverId: e.driverId,
			driverLabel: driver?.label ?? payloadDriver?.labelKr ?? e.driverId,
			market: e.market,
			sectorKey: sectorKeys[0] ?? 'unknown',
			sectorLabel: sectorLabels.join(' · '),
			channel: e.channel,
			financialLine: e.financialLine,
			valuationLever: e.valuationLever,
			sign: e.sign,
			lagMonths: normalizeLag(e.lagMonths),
			confidence: blocked ? 'blocked' : e.confidence,
			evidenceLevel: e.evidenceLevel,
			requiredCompanyEvidence: e.requiredCompanyEvidence ?? [],
			sourceRefs,
			note: blocked ? `${noteFromTransmission(e)} 최신 driver 관측 lineage가 닫혀 있어 정량 claim은 잠근다.` : noteFromTransmission(e)
		};
	});
}

function buildEdges(co: Company, drivers: MacroDriverView[], payload?: MacroTransmissionPayload | null): MacroTransmissionEdgeView[] {
	const transmissionEdges = buildEdgesFromTransmission(co, drivers, payload);
	if (transmissionEdges.length) return transmissionEdges;
	const driverById = new Map(drivers.map((d) => [d.id, d]));
	const sectorLabel = co.sector.kr || co.industry;
	const selected = EDGE_TEMPLATES
		.filter((e) => e.sectors.includes('all') || e.sectors.includes(co.industry))
		.slice(0, 8);
	return selected.map((e, i) => {
		const driver = driverById.get(e.driverId);
		const blocked = !driver;
		return {
			id: `${e.driverId}-${e.channel}-${i}`,
			driverId: e.driverId,
			driverLabel: driver?.label ?? e.driverId,
			market: e.market,
			sectorKey: co.industry,
			sectorLabel,
			channel: e.channel,
			financialLine: e.financialLine,
			valuationLever: e.valuationLever,
			sign: e.sign,
			lagMonths: e.lagMonths,
			confidence: blocked ? 'blocked' : e.confidence,
			evidenceLevel: e.evidenceLevel,
			requiredCompanyEvidence: e.requiredCompanyEvidence,
			sourceRefs: [driver?.seriesId ?? e.driverId, blocked ? 'notWiredYet' : 'sector prior', 'company checkpoints'],
			note: blocked ? `${e.note} 최신 시계열이 MacroPort에 없어서 전파 edge는 차단 상태로만 표시한다.` : e.note
		};
	});
}

function buildFalsifiers(coMovers: CoMover[], drivers: MacroDriverView[], macro: MacroFile | null, exposureQuality: MacroExposureQualityView): MacroFalsifierView[] {
	const byId = new Map(drivers.map((d) => [d.id, d]));
	const out: MacroFalsifierView[] = [];
	for (const cm of coMovers.slice(0, 5)) {
		const d = byId.get(cm.id);
		if (!d) continue;
		const signal = d.coMovement;
		out.push({
			id: `co-${cm.id}`,
			type: 'coMovement',
			driverId: cm.id,
			label: `${d.label} ${signal?.label ?? `corr ${cm.corr > 0 ? '+' : ''}${cm.corr.toFixed(2)}`}`,
			severity: signal?.status === 'candidate' ? 'info' : 'warning',
			detail: `최근 겹친 ${cm.n}개월(${signal?.window ?? `${cm.n}M overlap`}) 월수익률과 거시 1차차분의 Pearson 상관. lag 안정성·회사 증거 전에는 인과나 beta로 승격하지 않는다.`,
			sourceRef: 'terminal coMovement'
		});
	}
	for (const d of drivers.filter((x) => x.freshness.status === 'stale').slice(0, 3)) {
		out.push({
			id: `stale-${d.id}`,
			type: 'staleData',
			driverId: d.id,
			label: `${d.label} 기준일 stale`,
			severity: 'warning',
			detail: `${d.sourceLineage}. 최신 국면 해석과 전파 경로 우선순위는 낮춰서 읽는다.`,
			sourceRef: d.sourceLineage
		});
	}
	if (!out.length) out.push({
		id: 'co-missing',
		type: 'coMovement',
		label: '동행상관 미계산',
		severity: 'warning',
		detail: '가격 월수익률과 거시 시계열의 겹친 표본이 부족하거나 아직 차트 계산 전이다.',
		sourceRef: 'terminal coMovement'
	});
	if (!macro?.asOf) out.push({
		id: 'macro-date',
		type: 'staleData',
		label: 'macro 기준일 없음',
		severity: 'warning',
		detail: 'macro.asOf가 없으면 최신 국면 해석으로 단정하지 않는다.',
		sourceRef: 'dashboards/macro.json'
	});
	if (exposureQuality.status === 'quantCandidate') {
		out.push({
			id: 'company-exposure-quality',
			type: 'quality',
			label: '회사 노출 품질 후보',
			severity: 'info',
			detail: `nObs ${exposureQuality.nObs ?? '—'}, R² ${exposureQuality.rSquared ?? '—'}, ${exposureQuality.window ?? 'window 없음'}. 정량 후보지만 추천·목표가로 번역하지 않는다.`,
			sourceRef: exposureQuality.sourceRef
		});
	} else {
		out.push({
			id: 'company-evidence',
			type: 'missingCompanyEvidence',
			label: exposureQuality.status === 'blocked' ? '회사 고유 노출 잠김' : '회사 고유 노출은 정성 단계',
			severity: exposureQuality.status === 'blocked' ? 'blocker' : 'warning',
			detail: exposureQuality.blockedReason || exposureQuality.reason,
			sourceRef: exposureQuality.sourceRef
		});
	}
	return out;
}

function buildScenarios(drivers: MacroDriverView[], edges: MacroTransmissionEdgeView[]): MacroScenarioView[] {
	const driverById = new Map(drivers.map((d) => [d.id, d]));
	const edgeByDriver = new Map(edges.map((e) => [e.driverId, e]));
	return SCENARIOS.map((s) => {
		const driver = driverById.get(s.driverId);
		const edge = edgeByDriver.get(s.driverId);
		const missing = edge?.requiredCompanyEvidence ?? s.requiredEvidence;
		const readiness: MacroScenarioView['readiness'] =
			!driver ? { status: 'blocked', reason: 'driver observation missing or not wired' } :
			edge?.confidence === 'blocked' ? { status: 'blocked', reason: 'transmission edge is not wired' } :
			driver.coMovement?.status === 'candidate' ? { status: 'needsEvidence', reason: 'co-movement exists; company evidence and regression quality pending' } :
			{ status: 'needsEvidence', reason: 'sector path only; company evidence required' };
		return {
			...s,
			requiredEvidence: missing,
			impactedFinancialLine: edge?.financialLine ?? s.impactedFinancialLine,
			valuationLever: edge?.valuationLever ?? s.valuationLever,
			readiness
		};
	}).slice(0, 5);
}

function normalizeExposureQuality(q: MacroExposureQualityPayload | undefined | null, code: string): MacroExposureQualityView | null {
	if (!q) return null;
	const status: MacroExposureQualityView['status'] =
		q.status === 'quantCandidate' || q.status === 'qualitativeOnly' || q.status === 'blocked'
			? q.status
			: 'blocked';
	return {
		method: q.method ?? null,
		modelVersion: q.modelVersion ?? null,
		targetMetric: q.targetMetric ?? null,
		minObs: typeof q.minObs === 'number' ? q.minObs : null,
		status,
		reason: q.reason || '회사 매출과 매크로 지표의 공개 품질 계약입니다.',
		blockedReason: q.blockedReason || (status === 'quantCandidate' ? '' : 'quality gate closed'),
		missingEvidence: Array.isArray(q.missingEvidence) ? q.missingEvidence : [],
		sourceRef: q.sourceRef || `analysis.macroExposure:${code}`,
		nObs: typeof q.nObs === 'number' ? q.nObs : null,
		rSquared: typeof q.rSquared === 'number' ? q.rSquared : null,
		window: q.window ?? null,
		frequency: q.frequency ?? null,
		lagMonths: typeof q.lagMonths === 'number' ? q.lagMonths : null,
		coverage: q.coverage ?? 'missing'
	};
}

function normalizeExposureIndicators(rows: MacroExposureIndicatorPayload[] | undefined | null): MacroExposureIndicatorView[] {
	if (!Array.isArray(rows)) return [];
	return rows.slice(0, 6).map((row) => ({
		method: row.method ?? null,
		modelVersion: row.modelVersion ?? null,
		targetMetric: row.targetMetric ?? null,
		minObs: typeof row.minObs === 'number' ? row.minObs : null,
		label: row.label || row.seriesId,
		seriesId: row.seriesId,
		axis: row.axis || 'macro',
		rSquared: typeof row.rSquared === 'number' ? row.rSquared : null,
		nObs: typeof row.nObs === 'number' ? row.nObs : null,
		window: row.window ?? null,
		frequency: row.frequency ?? null,
		lagMonths: typeof row.lagMonths === 'number' ? row.lagMonths : null,
		coverage: row.coverage ?? 'missing',
		sourceRef: row.sourceRef,
		sourceRefs: Array.isArray(row.sourceRefs) ? row.sourceRefs : [],
		latestChange: typeof row.latestChange === 'number' ? row.latestChange : null,
		impact: row.impact || '—'
	}));
}

function buildExposureQuality(co: Company): MacroExposureQualityView {
	const actual = normalizeExposureQuality(co.macroExposure?.exposureQuality, co.code);
	if (actual) return actual;
	return {
		method: null,
		modelVersion: null,
		targetMetric: null,
		minObs: null,
		status: 'qualitativeOnly',
		reason: '회사별 회귀/민감도는 nObs/R²/window/lag/coverage 공개 계약 전까지 정성 경로만 표시',
		blockedReason: 'nObs/R²/window/lag/coverage/sourceRef 공개 계약 전',
		missingEvidence: ['nObs', 'R²', 'window', 'lag', 'company exposure sourceRef'],
		sourceRef: 'analysis.macroExposure pending',
		nObs: null,
		rSquared: null,
		window: null,
		frequency: null,
		lagMonths: null,
		coverage: 'sectorOnly'
	};
}

function buildMissing(args: { macro: MacroFile | null; macroLatest: MacroLatest[]; edges: MacroTransmissionEdgeView[]; coMovers: CoMover[]; transmission?: MacroTransmissionPayload | null }): MacroMissingView[] {
	const out: MacroMissingView[] = [];
	if (!args.macro) out.push({ id: 'macro-json', status: 'missing', reason: 'macro regime artifact unavailable', sourceRef: 'dashboards/macro.json' });
	if (!args.macroLatest.length) out.push({ id: 'macro-latest', status: 'missing', reason: 'macro latest observations unavailable', sourceRef: 'macro/{fred,ecos}/observations.parquet' });
	if (!args.transmission) out.push({ id: 'macro-transmission', status: 'notWiredYet', reason: 'macro.transmission payload not present in macro artifact; using UI fallback templates', sourceRef: 'dashboards/macro.json#transmission' });
	if (!args.edges.length) out.push({ id: 'transmission-edge', status: 'notWiredYet', reason: 'sector transmission edge unavailable for this company', sourceRef: args.transmission ? 'dartlab://macro/transmission' : 'Macro Lens EDGE_TEMPLATES' });
	if (!args.coMovers.length) out.push({ id: 'co-movement', status: 'partial', reason: 'overlap sample insufficient or chart co-movement not calculated', sourceRef: 'terminal coMovement' });
	for (const m of args.transmission?.missing ?? []) out.push(m);
	return out;
}

function buildEvidenceGates(args: {
	asOf: string | null;
	drivers: MacroDriverView[];
	topPressures: MacroDriverView[];
	edges: MacroTransmissionEdgeView[];
	exposureQuality: MacroExposureQualityView;
	edgeSourceRef: string;
}): MacroEvidenceGateView[] {
	const top = args.topPressures.length ? args.topPressures : args.drivers.slice(0, 3);
	const stale = top.filter((d) => d.freshness.status === 'stale');
	const watch = top.filter((d) => d.freshness.status === 'watch');
	const observed = args.edges.filter((e) => e.evidenceLevel === 'observed' && e.confidence !== 'blocked');
	const candidates = args.drivers.filter((d) => d.coMovement?.status === 'candidate');
	const coWindows = candidates.map((d) => `${d.id}:${d.coMovement?.window ?? 'window?'}`);
	const companyHasEvidence = args.exposureQuality.coverage === 'company' && args.exposureQuality.nObs != null;
	const quantOpen = args.exposureQuality.status === 'quantCandidate';
	const qualityDetail = `nObs ${args.exposureQuality.nObs ?? '—'} · R² ${args.exposureQuality.rSquared ?? '—'} · ${args.exposureQuality.window ?? 'window 없음'}`;
	return [
		{
			id: 'macroData',
			labelKr: '시계열',
			labelEn: 'Series',
			value: stale.length ? 'STALE' : watch.length ? 'WATCH' : 'OK',
			detailKr: args.asOf ?? 'macro 기준일 없음',
			detailEn: args.asOf ?? 'macro asOf missing',
			status: stale.length ? 'blocked' : watch.length ? 'watch' : 'ok',
			sourceRef: 'dashboards/macro.json + macro observations',
			blocks: stale.map((d) => `${d.id}: ${d.freshness.label}`)
		},
		{
			id: 'path',
			labelKr: '경로',
			labelEn: 'Path',
			value: `${observed.length}/${args.edges.length}`,
			detailKr: '관측 edge',
			detailEn: 'observed edges',
			status: observed.length ? 'ok' : 'watch',
			sourceRef: args.edgeSourceRef,
			blocks: args.edges.filter((e) => e.confidence === 'blocked').map((e) => `${e.driverId}: ${e.sourceRefs.join(' · ')}`)
		},
		{
			id: 'comove',
			labelKr: '동행',
			labelEn: 'Co-move',
			value: candidates.length ? `${candidates.length}` : 'LOW',
			detailKr: candidates.length ? coWindows.join(', ') : '인과 아님',
			detailEn: candidates.length ? coWindows.join(', ') : 'not causal',
			status: candidates.length ? 'watch' : 'blocked',
			sourceRef: 'terminal coMovement',
			blocks: candidates.length ? [] : ['corr/n/window candidate absent']
		},
		{
			id: 'company',
			labelKr: '회사노출',
			labelEn: 'Company',
			value: companyHasEvidence ? 'OBS' : args.exposureQuality.coverage === 'sectorOnly' ? 'PRIOR' : 'LOCK',
			detailKr: companyHasEvidence ? qualityDetail : '회사 표본 없음',
			detailEn: companyHasEvidence ? qualityDetail : 'company sample absent',
			status: companyHasEvidence ? (quantOpen ? 'ok' : 'watch') : 'blocked',
			sourceRef: args.exposureQuality.sourceRef,
			blocks: args.exposureQuality.missingEvidence.length ? args.exposureQuality.missingEvidence : []
		},
		{
			id: 'quant',
			labelKr: '민감도',
			labelEn: 'Beta',
			value: quantOpen ? 'OPEN' : 'LOCK',
			detailKr: quantOpen ? qualityDetail : (args.exposureQuality.blockedReason || 'quality gate closed'),
			detailEn: quantOpen ? qualityDetail : (args.exposureQuality.blockedReason || 'quality gate closed'),
			status: quantOpen ? 'ok' : 'blocked',
			sourceRef: args.exposureQuality.sourceRef,
			blocks: quantOpen ? [] : [args.exposureQuality.blockedReason || 'quality gate closed']
		}
	];
}

function buildReleaseRail(drivers: MacroDriverView[]): MacroReleaseView[] {
	return drivers.slice(0, 10).map((driver) => {
		const def = macroDefOf(driver.id);
		const staleAfterDays = def ? staleAfterDaysOf(def) : 75;
		const cadenceDays = def ? cadenceDaysOf(def) : 35;
		return {
			driverId: driver.id,
			label: driver.label,
			source: driver.source,
			frequency: def ? frequencyOf(def) : 'unknown frequency',
			lastObservation: driver.asOf,
			nextCheck: addDaysYmd(driver.asOf.replaceAll('-', ''), cadenceDays),
			daysLag: driver.freshness.daysLag,
			staleAfterDays,
			status: driver.freshness.status,
			sourceRef: `${driver.source}:${driver.seriesId}:freshness-policy`
		};
	});
}

function buildSourcePackets(drivers: MacroDriverView[], payload?: MacroTransmissionPayload | null): MacroSourcePacketView[] {
	const payloadDrivers = new Map((payload?.drivers ?? []).map((d) => [d.id, d]));
	return drivers.slice(0, 16).map((driver) => {
		const def = macroDefOf(driver.id);
		const row = payloadDrivers.get(driver.id);
		const lineage = row?.sourceLineage;
		const artifactPath = lineage?.artifactPath || `macro/${driver.source === 'ECOS' ? 'ecos' : 'fred'}/observations.parquet`;
		const status = lineage?.status === 'missing' ? 'missing' : driver.freshness.status;
		return {
			driverId: driver.id,
			label: driver.label,
			seriesId: driver.seriesId,
			source: driver.source,
			unit: driver.unit,
			frequency: def ? frequencyOf(def) : 'unknown frequency',
			asOf: lineage?.date ? fmtDate(lineage.date) : driver.asOf,
			value: driver.value,
			change: driver.change,
			transform: driver.transform,
			status,
			artifactPath,
			sourceRef: `${artifactPath}#${driver.seriesId}`,
			lineage: driver.sourceLineage,
			qualityHint: driver.qualityHint
		};
	});
}

function buildContributionStacks(
	drivers: MacroDriverView[],
	edges: MacroTransmissionEdgeView[],
	latest: MacroLatest[],
	exposureQuality: MacroExposureQualityView
): MacroContributionView[] {
	const latestById = new Map(latest.map((m) => [m.def.id, m]));
	return drivers.slice(0, 10).map((driver) => {
		const macroLatest = latestById.get(driver.id);
		const edge = edges.find((e) => e.driverId === driver.id);
		const move = macroLatest ? Math.min(1, changeIntensity(macroLatest) / 24) : 0;
		const path = confidenceScore(edge);
		const co = driver.coMovement ? Math.min(1, Math.abs(driver.coMovement.corr)) : 0;
		const fresh = freshnessScore(driver.freshness.status);
		const company = exposureQualityScore(exposureQuality);
		const components: MacroContributionComponentView[] = [
			{
				id: 'move',
				label: '최근 변화',
				value: move,
				detail: macroLatest ? `${driver.change} · ${driver.asOf}` : 'latest observation missing',
				status: componentStatus(move),
				sourceRef: driver.sourceLineage
			},
			{
				id: 'path',
				label: '전파 경로',
				value: path,
				detail: edge ? `${edge.evidenceLevel} · ${edge.confidence} · ${edge.channel}` : 'mapped edge absent',
				status: componentStatus(path),
				sourceRef: edge?.sourceRefs[0] ?? 'macro.transmission edge missing'
			},
			{
				id: 'comove',
				label: '동행 후보',
				value: co,
				detail: driver.coMovement?.label ?? 'co-movement absent',
				status: driver.coMovement?.status === 'candidate' ? 'ok' : driver.coMovement ? 'watch' : 'blocked',
				sourceRef: 'terminal coMovement'
			},
			{
				id: 'freshness',
				label: '신선도',
				value: fresh,
				detail: driver.freshness.label,
				status: componentStatus(fresh),
				sourceRef: `${driver.source}:${driver.seriesId}:freshness-policy`
			},
			{
				id: 'company',
				label: '회사 품질',
				value: company,
				detail: `${exposureQuality.status} · nObs ${exposureQuality.nObs ?? '—'} · R² ${exposureQuality.rSquared ?? '—'}`,
				status: componentStatus(company),
				sourceRef: exposureQuality.sourceRef
			}
		];
		const open = components.filter((c) => c.status === 'ok').length;
		const watch = components.filter((c) => c.status === 'watch').length;
		return {
			driverId: driver.id,
			label: driver.label,
			summary: `${open} open · ${watch} watch · ${components.length - open - watch} locked`,
			components,
			sourceRef: `MacroLens:contributionStack:${driver.id}`
		};
	});
}

function buildCoMoveGates(drivers: MacroDriverView[], coMovers: CoMover[]): MacroCoMoveGateView[] {
	const coById = new Map(coMovers.map((m) => [m.id, m]));
	return drivers
		.filter((driver) => driver.relevance !== 'context')
		.slice(0, 10)
		.map((driver) => {
			const cm = coById.get(driver.id);
			const scatter = buildCoMoveScatter(cm);
			return {
				driverId: driver.id,
				label: driver.label,
				corr: driver.coMovement?.corr ?? null,
				n: driver.coMovement?.n ?? null,
				window: driver.coMovement?.window ?? 'overlap missing',
				status: driver.coMovement?.status ?? 'missing',
				sourceRef: 'terminal coMovement',
				detail: driver.coMovement
					? `${driver.coMovement.label}. 각 점은 월별 macro 1차차분(x)과 종목 월수익률(y)이다. 방향성 claim이나 beta가 아니라 동행 후보 gate다.`
					: '가격과 macro observation의 겹친 표본이 부족하다.',
				...scatter
			};
		});
}

export function buildMacroLensSnapshot(args: {
	co: Company;
	macro: MacroFile | null;
	transmission?: MacroTransmissionPayload | null;
	macroLatest: MacroLatest[];
	sectorTailwinds: { id: string; kr: string; en: string; blended: number; tailwindKey?: string }[];
	coMovers: CoMover[];
}): MacroLensSnapshot {
	const { co, macro, transmission = macro?.transmission ?? null, macroLatest, sectorTailwinds, coMovers } = args;
	const drivers = applyTransmissionDriverLineage(buildDrivers(macroLatest, co.industry, coMovers), transmission);
	const priorityRank = { high: 0, medium: 1, low: 2, blocked: 3 };
	const topPressures = [...drivers]
		.filter((d) => d.relevance !== 'context' && d.pressureLevel !== 'blocked')
		.sort((a, b) => priorityRank[a.pressureLevel] - priorityRank[b.pressureLevel])
		.slice(0, 3);
	const edges = buildEdges(co, drivers, transmission);
	const checkpoints = buildCheckpoints(co);
	const scenarios = buildScenarios(drivers, edges);
	const exposureQuality = buildExposureQuality(co);
	const exposureIndicators = normalizeExposureIndicators(co.macroExposure?.selected);
	const releaseRail = buildReleaseRail(drivers);
	const sourcePackets = buildSourcePackets(drivers, transmission);
	const contributionStacks = buildContributionStacks(drivers, edges, macroLatest, exposureQuality);
	const coMoveGates = buildCoMoveGates(drivers, coMovers);
	const falsifiers = buildFalsifiers(coMovers, drivers, macro, exposureQuality);
	const marketPhase = {
		kr: phaseView('KR', macro?.kr),
		us: phaseView('US', macro?.us)
	};
	const missing = buildMissing({ macro, macroLatest, edges, coMovers, transmission });
	const edgeSourceRef = transmission ? 'dartlab://macro/transmission' : 'macro transmission edge template';
	const financePeriod = co.trendQuarter?.periods.at(-1) ?? co.trendAnnual?.periods.at(-1) ?? null;
	return {
		asOf: {
			macro: macro?.asOf ?? null,
			price: co.price.asOf ?? null,
			finance: financePeriod
		},
		company: {
			code: co.code,
			name: co.name.kr,
			sector: co.sector.kr,
			industry: co.industry
		},
		marketPhase,
		drivers,
		topPressures: topPressures.length ? topPressures : drivers.slice(0, 3),
		transmissionEdges: edges,
		companyCheckpoints: checkpoints,
		sectorBinding: {
			tailwind: co.tailwind,
			top: sectorTailwinds.slice(0, 4),
			bottom: sectorTailwinds.length > 4 ? sectorTailwinds.slice(-4).reverse() : []
		},
		exposureQuality,
		exposureIndicators,
		releaseRail,
		sourcePackets,
		contributionStacks,
		coMoveGates,
		evidenceGates: buildEvidenceGates({ asOf: macro?.asOf ?? null, drivers, topPressures, edges, exposureQuality, edgeSourceRef }),
		falsifiers,
		scenarios,
		sourceRefs: [
			MACRO_ATTRIBUTION,
			'dashboards/macro.json',
			...(transmission?.sourceRefs ?? []),
			'macro/{fred,ecos}/observations.parquet',
			exposureQuality.sourceRef,
			'terminal Company snapshot',
			'coMovement: monthly stock return vs macro diff',
			...exposureIndicators.flatMap((x) => [x.sourceRef, ...x.sourceRefs]).filter(Boolean),
			...drivers.slice(0, 8).map((d) => `${d.id}: ${d.sourceLineage}`)
		],
		missing,
		glance: buildMacroGlanceView(macro, sectorTailwinds, { activeIndustryId: co.industry, mode: 'compact' }),
		macroPath: buildMacroPath(macro?.transmission ?? transmission, sectorTailwinds, { activeIndustryId: co.industry, mode: 'full' }),
		marketOnly: false
	};
}

function marketOnlyExposureQuality(): MacroExposureQualityView {
	return {
		method: null,
		modelVersion: null,
		targetMetric: null,
		minObs: null,
		status: 'blocked',
		reason: '종목을 선택하면 회사 노출 checkpoint를 계산한다.',
		blockedReason: 'company not selected',
		missingEvidence: ['company selection'],
		sourceRef: 'terminal macro market-only',
		nObs: null,
		rSquared: null,
		window: null,
		frequency: null,
		lagMonths: null,
		coverage: 'missing'
	};
}

function marketOnlyCheckpoints(): MacroCheckpointView[] {
	return [
		{ id: 'sector', label: '섹터 전파', value: '종목 선택 후', tone: 'neutral', reason: '회사 업종이 선택되면 해당 경로를 하이라이트한다.', source: 'company selection' },
		{ id: 'margin', label: '마진 흡수력', value: 'LOCK', tone: 'neutral', reason: '회사 재무제표 선택 전에는 계산하지 않는다.', source: 'company.fundamentals' },
		{ id: 'debt', label: '금리 민감도', value: 'LOCK', tone: 'neutral', reason: '차입·이자보상배율은 종목 선택 후 확인한다.', source: 'company.fundamentals' },
		{ id: 'cashFlow', label: '현금흐름 흡수', value: 'LOCK', tone: 'neutral', reason: '현금흐름 checkpoint는 종목 선택 후 확인한다.', source: 'company.financials' }
	];
}

export function buildMarketMacroLensSnapshot(args: {
	macro: MacroFile | null;
	macroLatest: MacroLatest[];
	sectorTailwinds: { id: string; kr: string; en: string; blended: number; tailwindKey?: string }[];
}): MacroLensSnapshot {
	const { macro, macroLatest, sectorTailwinds } = args;
	const transmission = macro?.transmission ?? null;
	const drivers = applyTransmissionDriverLineage(buildDrivers(macroLatest, '', []), transmission);
	const priorityRank = { high: 0, medium: 1, low: 2, blocked: 3 };
	const topPressures = [...drivers]
		.filter((d) => d.relevance !== 'context' && d.pressureLevel !== 'blocked')
		.sort((a, b) => priorityRank[a.pressureLevel] - priorityRank[b.pressureLevel])
		.slice(0, 3);
	const edges = buildMarketEdgesFromTransmission(drivers, transmission);
	const exposureQuality = marketOnlyExposureQuality();
	const releaseRail = buildReleaseRail(drivers);
	const sourcePackets = buildSourcePackets(drivers, transmission);
	const contributionStacks = buildContributionStacks(drivers, edges, macroLatest, exposureQuality);
	const coMoveGates = buildCoMoveGates(drivers, []);
	const marketPhase = {
		kr: phaseView('KR', macro?.kr),
		us: phaseView('US', macro?.us)
	};
	const missing = buildMissing({ macro, macroLatest, edges, coMovers: [], transmission });
	const edgeSourceRef = transmission ? 'dartlab://macro/transmission' : 'macro transmission missing';
	return {
		asOf: {
			macro: macro?.asOf ?? null,
			price: null,
			finance: null
		},
		company: {
			code: 'MARKET',
			name: 'Market Macro',
			sector: '종목 선택 전',
			industry: ''
		},
		marketPhase,
		drivers,
		topPressures: topPressures.length ? topPressures : drivers.slice(0, 3),
		transmissionEdges: edges,
		companyCheckpoints: marketOnlyCheckpoints(),
		sectorBinding: {
			tailwind: null,
			top: sectorTailwinds.slice(0, 4),
			bottom: sectorTailwinds.length > 4 ? sectorTailwinds.slice(-4).reverse() : []
		},
		exposureQuality,
		exposureIndicators: [],
		releaseRail,
		sourcePackets,
		contributionStacks,
		coMoveGates,
		evidenceGates: buildEvidenceGates({ asOf: macro?.asOf ?? null, drivers, topPressures, edges, exposureQuality, edgeSourceRef }),
		falsifiers: buildFalsifiers([], drivers, macro, exposureQuality),
		scenarios: buildScenarios(drivers, edges),
		sourceRefs: [
			MACRO_ATTRIBUTION,
			'dashboards/macro.json',
			...(transmission?.sourceRefs ?? []),
			'macro/{fred,ecos}/observations.parquet',
			'terminal macro market-only',
			...drivers.slice(0, 8).map((d) => `${d.id}: ${d.sourceLineage}`)
		],
		missing,
		glance: buildMacroGlanceView(macro, sectorTailwinds, { mode: 'compact' }),
		macroPath: buildMacroPath(transmission, sectorTailwinds, { mode: 'full' }),
		marketOnly: true
	};
}

export function macroDefOf(id: string): MacroSeriesDef | null {
	return MACRO_SERIES.find((s) => s.id === id) ?? null;
}
