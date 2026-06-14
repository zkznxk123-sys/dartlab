// DartLab Terminal — raw data file shapes + built Company shape.
// 스키마는 landing/static 의 실데이터에서 검증 (finance/macro/meta/prices/search-index/ecosystem/quarters/industryStats).
// 가짜 필드 없음 — cf.opening/closing 는 실데이터에서 null 이라 표면에 노출하지 않는다.

export type Num = number | null;
// ui/shared/chart 의 ChartSpec (loose — 차트 컴포넌트는 @ts-nocheck spec 객체 수신).
export type ChartSpec = Record<string, unknown>;
export type Lang = 'kr' | 'en';
export type Tone = 'up' | 'down' | 'good' | 'warn' | 'neutral';
export type Prov = 'real' | 'derived' | 'wire';

// ───────────────────────── raw files ─────────────────────────
export interface FinanceCompany {
	is: { sales: Num[]; op: Num[]; net: Num[]; opMargin: Num[] };
	bs: {
		assets?: Record<string, Num[]>;
		liab?: Record<string, Num[]>;
		equity?: Record<string, Num[]>;
		totals: {
			totalAsset: Num[];
			totalLiab: Num[];
			totalEquity: Num[];
			currAsset: Num[];
			currLiab: Num[];
		};
	};
	cf: { op: Num; inv: Num; fin: Num; opening: Num; closing: Num; fx: Num };
	ratios: { roe: Num[]; debtRatio: Num[] };
}
export interface FinanceFile {
	version?: string;
	years: string[];
	companies: Record<string, FinanceCompany>;
}

export interface QuartersCompany {
	is: { sales: Num[]; op: Num[]; net: Num[] };
	cf?: { ocf: Num[]; icf: Num[] };
	bs?: { totals?: Record<string, Num[]> };
}
export interface QuartersFile {
	periods: string[];
	companies: Record<string, QuartersCompany>;
}

export interface MacroQuadrant {
	quadrant: string;
	quadrantLabel: string;
	growth: string;
	inflation?: string;
	assetImplication: Record<string, string>;
	description: string;
}
export interface MacroSide {
	phase: string;
	phaseLabel: string;
	quadrant?: MacroQuadrant; // 빌더 입력 부족(cycle 결측) 시 부재 가능 — 소비처 옵셔널 접근 강제
}
export interface TailwindEntry {
	kr: number;
	us: number;
	blended: number;
}
export interface MacroFile {
	version?: string;
	asOf?: string;
	kr: MacroSide;
	us: MacroSide;
	sectorTailwind: Record<string, TailwindEntry>;
}

export interface BlogEntry {
	slug: string;
	title: string;
	date: string;
	readTime?: number | string;
	excerpt?: string;
}
export interface MetaFile {
	version?: string;
	blog?: Record<string, BlogEntry>;
}

export interface PriceRow {
	currentPrice: number;
	marketCap: number;
	return1m: Num;
	return3m: Num;
	return1y: Num;
	volatility1y: Num;
	week52High: Num;
	week52Low: Num;
	volumeAvg30d: Num;
	foreignPct: Num;
	beta: Num;
	priceUpdated: string;
}
export interface PricesFile {
	count?: number;
	data: Record<string, PriceRow>;
}

export interface IndexRow {
	stockCode: string;
	corpName: string;
	industry: string;
	stage?: string;
	revenue: Num;
}

export interface EcoNode {
	id: string;
	label?: string;
	industry: string;
	industryName?: string;
	market?: string;
	stageName?: string;
	role?: string;
	revenue?: Num;
	marketShare?: Num;
	roe?: Num;
	opMargin?: Num;
	netMargin?: Num;
	roa?: Num;
	debtRatio?: Num;
	icr?: Num;
	currentRatio?: Num;
	assetTurnover?: Num;
	ccc?: Num;
	accrualRatio?: Num;
	revCagr?: Num;
	netIncomeCagr?: Num;
	industryRank?: Num;
	industryPeerCount?: Num;
	holderPct?: Num;
	holderChange?: Num;
	empCount?: Num;
	profGrade?: string;
	growthGrade?: string;
	govGrade?: string;
	qualGrade?: string;
	liqGrade?: string;
	auditRisk?: string;
	stability?: string;
	cfPattern?: string;
	roeDelta?: Num;
	opMarginDelta?: Num;
	debtRatioDelta?: Num;
	revenueYoyPct?: Num;
	deltaYear?: string | null;
}
export interface EcosystemFile {
	version?: string;
	nodes: EcoNode[];
	industries?: unknown[];
	industryFlows?: unknown[];
}

export interface IndustryDistribution {
	p10?: number;
	p25?: number;
	median?: number;
	p75?: number;
	p90?: number;
	mean?: number;
	n?: number;
}
export interface IndustryStat {
	id?: string;
	name?: string;
	distribution?: Record<string, IndustryDistribution>;
}
export type IndustryStatsFile = Record<string, IndustryStat> | { industries?: IndustryStat[] };

export interface RawData {
	finance: FinanceFile;
	macro: MacroFile | null;
	meta: MetaFile | null;
	prices: PricesFile;
	index: IndexRow[];
	eco: EcosystemFile | null;
	quarters: QuartersFile | null;
	// 업종 분포 통계(p10~p90 밴드) — map 이 쓰던 자산. public 셸은 로드, local 단일사 브리지는 null(정직). 필수=공동배선 강제.
	industryStats: IndustryStatsFile | null;
}

// ───────────────────────── built company ─────────────────────────
export interface Bilingual {
	kr: string;
	en: string;
}
export interface StatementRow {
	kr: string;
	en: string;
	id: string;
	pct?: boolean;
	vals: Num[];
}
export interface Statement {
	periods: string[];
	rows: StatementRow[];
}
export interface RatioRow {
	kr: string;
	en: string;
	id: string;
	v: string;
	tone: Tone;
}
export interface GradeChip {
	key: string;
	kr: string;
	en: string;
	v: string;
	tone: Tone;
	color: string;
}
export interface RadarAxis {
	kr: string;
	en: string;
	s: Num;
}
export interface ChangeRow {
	kr: string;
	en: string;
	v: Num;
	unit: string;
	invert?: boolean;
}
export interface CreditTrack {
	kr: string;
	en: string;
	score: number;
}
export interface Credit {
	grade: string;
	healthScore: number;
	pd: string;
	tone: Tone;
	tracks: CreditTrack[];
	basis: { debtRatio: Num; curr: Num; opm: Num };
}
export interface RiskFlag {
	lv: 'red' | 'yellow' | 'green';
	kr: string;
	en: string;
	d: string;
}
export interface PercentileMetric {
	kr: string;
	en: string;
	v: Num;
	p: number;
	unit: string;
	// 업종 분포 밴드(industryStats) — public 만 실데이터, local(단일사 seed)·분포 부재 = null(다이얼로그 생략).
	// p10~p90 5분위점 = 분포곡선(skew 반영, 정규가정 아님)·회사 위치 마커 렌더용.
	band: { p10: number; p25: number; median: number; p75: number; p90: number } | null;
}
export interface Valuation {
	per: Num;
	pbr: Num;
	perMed: Num;
	pbrMed: Num;
	fairLow: Num;
	fairHigh: Num;
	fairMid: Num;
	upside: Num;
	last: number;
	perPos: string | null;
}
export interface Tailwind {
	key: string;
	kr: string;
	blended: number;
	krScore: number;
	usScore: number;
	label: string;
	tone: Tone;
}
export interface Verdict {
	composite: number;
	band: { kr: string; en: string; tone: Tone };
	strengths: Bilingual[];
	concerns: Bilingual[];
	riskRed: number;
	riskYellow: number;
}
export interface Peer {
	code: string;
	name: string;
	revenue: Num;
	self: boolean;
}
export interface TrendSeries {
	periods: string[];
	sales: Num[];
	op: Num[];
	net: Num[];
	opMargin: Num[];
	freq: 'annual' | 'quarter';
}
export interface AnalysisTrack {
	kr: string;
	en: string;
	verdict: Bilingual;
	tone: Tone;
	delta: string;
}
// ui/web 재무카드 포팅 — finance.json 5Y 에서 계산
export interface StackSeg {
	kr: string;
	v: number;
	color: string;
}
export interface Financials {
	years: string[]; // 오래된→최신
	opMargin: Num[];
	netMargin: Num[];
	roe: Num[];
	assetTurn: Num[]; // 매출/자산 (회전)
	equityMult: Num[]; // 자산/자본
	deRatio: Num[]; // 부채/자본 %
	currRatio: Num[]; // 유동자산/유동부채 %
	dupont: { netMargin: Num; assetTurn: Num; equityMult: Num; roe: Num }; // 최신
	assetMix: StackSeg[]; // 최신 자산 구성
	fundMix: StackSeg[]; // 최신 부채+자본 구성
	cf: { op: Num; inv: Num; fin: Num; fcf: Num };
}
export interface Company {
	code: string;
	marketLabel: string;
	name: Bilingual;
	sector: Bilingual;
	stage: string;
	role: string;
	eco: EcoNode;
	grades: GradeChip[];
	radar: RadarAxis[];
	changes: ChangeRow[];
	price: {
		last: number;
		mktcap: string;
		mktcapRaw: number; // 원 — 캔들 최신가 기준 시총 보정용
		ret1m: Num;
		ret3m: Num;
		ret1y: Num;
		vol1y: Num;
		hi52: Num;
		lo52: Num;
		vol: Num;
		asOf: string;
	};
	fundamentals: { per: Num; pbr: Num; psr: Num; npm: Num; roe: Num; opm: Num; dr: Num };
	financials: Financials;
	trendAnnual: TrendSeries;
	trendQuarter: TrendSeries | null;
	income: Statement;
	balance: Statement;
	cashflow: Statement;
	ratios: RatioRow[];
	credit: Credit;
	analysis: { summary: Bilingual; tracks: AnalysisTrack[] };
	peers: Peer[];
	story: { title: string; date: string; readTime?: number | string; slug: string } | null;
	percentile: { industry: string; n: number; metrics: PercentileMetric[] } | null;
	valuation: Valuation | null;
	risks: RiskFlag[];
	tailwind: Tailwind | null;
	verdict: Verdict;
}
