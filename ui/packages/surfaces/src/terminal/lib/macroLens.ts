import { MACRO_ATTRIBUTION, MACRO_SERIES, type MacroLatest, type MacroSeriesDef } from '@dartlab/ui-contracts';
import type { CoMover } from './coMovement';
import type { Company, MacroFile, MacroSide, Tailwind, Tone } from './types';

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
	status: 'qualitativeOnly' | 'blocked';
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
	evidenceGates: MacroEvidenceGateView[];
	falsifiers: MacroFalsifierView[];
	scenarios: MacroScenarioView[];
	sourceRefs: string[];
	missing: MacroMissingView[];
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
	const staleAfter = def.src === 'fred' ? 10 : def.id === 'BASE_RATE' ? 65 : 75;
	if (lag > staleAfter) return { status: 'stale', daysLag: lag, label: `stale ${lag}d` };
	if (lag > staleAfter * 0.65) return { status: 'watch', daysLag: lag, label: `watch ${lag}d` };
	return { status: 'fresh', daysLag: lag, label: `fresh ${lag}d` };
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

function buildEdges(co: Company, drivers: MacroDriverView[]): MacroTransmissionEdgeView[] {
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

function buildFalsifiers(coMovers: CoMover[], drivers: MacroDriverView[], macro: MacroFile | null): MacroFalsifierView[] {
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
	out.push({
		id: 'company-evidence',
		type: 'missingCompanyEvidence',
		label: '회사 고유 노출은 정성 단계',
		severity: 'warning',
		detail: '해외매출·FX손익·차입 만기·원재료 비중이 공개 surface로 표준화되기 전까지 beta 숫자는 표시하지 않는다.',
		sourceRef: 'analysis.macroExposure pending'
	});
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

function buildExposureQuality(): MacroExposureQualityView {
	return {
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

function buildMissing(args: { macro: MacroFile | null; macroLatest: MacroLatest[]; edges: MacroTransmissionEdgeView[]; coMovers: CoMover[] }): MacroMissingView[] {
	const out: MacroMissingView[] = [];
	if (!args.macro) out.push({ id: 'macro-json', status: 'missing', reason: 'macro regime artifact unavailable', sourceRef: 'dashboards/macro.json' });
	if (!args.macroLatest.length) out.push({ id: 'macro-latest', status: 'missing', reason: 'macro latest observations unavailable', sourceRef: 'macro/{fred,ecos}/observations.parquet' });
	if (!args.edges.length) out.push({ id: 'transmission-edge', status: 'notWiredYet', reason: 'sector transmission edge unavailable for this company', sourceRef: 'Macro Lens EDGE_TEMPLATES' });
	if (!args.coMovers.length) out.push({ id: 'co-movement', status: 'partial', reason: 'overlap sample insufficient or chart co-movement not calculated', sourceRef: 'terminal coMovement' });
	return out;
}

function buildEvidenceGates(args: {
	asOf: string | null;
	drivers: MacroDriverView[];
	topPressures: MacroDriverView[];
	edges: MacroTransmissionEdgeView[];
	exposureQuality: MacroExposureQualityView;
}): MacroEvidenceGateView[] {
	const top = args.topPressures.length ? args.topPressures : args.drivers.slice(0, 3);
	const stale = top.filter((d) => d.freshness.status === 'stale');
	const watch = top.filter((d) => d.freshness.status === 'watch');
	const observed = args.edges.filter((e) => e.evidenceLevel === 'observed' && e.confidence !== 'blocked');
	const candidates = args.drivers.filter((d) => d.coMovement?.status === 'candidate');
	const coWindows = candidates.map((d) => `${d.id}:${d.coMovement?.window ?? 'window?'}`);
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
			sourceRef: 'macro transmission edge template',
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
			value: '정성',
			detailKr: '회귀 잠금',
			detailEn: 'regression locked',
			status: 'blocked',
			sourceRef: args.exposureQuality.sourceRef,
			blocks: args.exposureQuality.missingEvidence
		},
		{
			id: 'quant',
			labelKr: '민감도',
			labelEn: 'Beta',
			value: 'LOCK',
			detailKr: 'nObs/R² 없음',
			detailEn: 'no nObs/R²',
			status: 'blocked',
			sourceRef: args.exposureQuality.sourceRef,
			blocks: [args.exposureQuality.blockedReason]
		}
	];
}

export function buildMacroLensSnapshot(args: {
	co: Company;
	macro: MacroFile | null;
	macroLatest: MacroLatest[];
	sectorTailwinds: { id: string; kr: string; en: string; blended: number }[];
	coMovers: CoMover[];
}): MacroLensSnapshot {
	const { co, macro, macroLatest, sectorTailwinds, coMovers } = args;
	const drivers = buildDrivers(macroLatest, co.industry, coMovers);
	const priorityRank = { high: 0, medium: 1, low: 2, blocked: 3 };
	const topPressures = [...drivers]
		.filter((d) => d.relevance !== 'context' && d.pressureLevel !== 'blocked')
		.sort((a, b) => priorityRank[a.pressureLevel] - priorityRank[b.pressureLevel])
		.slice(0, 3);
	const edges = buildEdges(co, drivers);
	const checkpoints = buildCheckpoints(co);
	const scenarios = buildScenarios(drivers, edges);
	const falsifiers = buildFalsifiers(coMovers, drivers, macro);
	const exposureQuality = buildExposureQuality();
	const marketPhase = {
		kr: phaseView('KR', macro?.kr),
		us: phaseView('US', macro?.us)
	};
	const missing = buildMissing({ macro, macroLatest, edges, coMovers });
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
		evidenceGates: buildEvidenceGates({ asOf: macro?.asOf ?? null, drivers, topPressures, edges, exposureQuality }),
		falsifiers,
		scenarios,
		sourceRefs: [
			MACRO_ATTRIBUTION,
			'dashboards/macro.json',
			'macro/{fred,ecos}/observations.parquet',
			'terminal Company snapshot',
			'coMovement: monthly stock return vs macro diff',
			...drivers.slice(0, 8).map((d) => `${d.id}: ${d.sourceLineage}`)
		],
		missing
	};
}

export function macroDefOf(id: string): MacroSeriesDef | null {
	return MACRO_SERIES.find((s) => s.id === id) ?? null;
}
