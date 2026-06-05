import type { CompanyFinancePeriodRow } from '$lib/scan/financeLiteRuntime';

export type FinanceSignalTone = 'good' | 'bad' | 'neutral' | 'watch' | 'missing';

export interface FinanceSignal {
	id: string;
	label: string;
	value: string;
	detail: string;
	tone: FinanceSignalTone;
	periodLabel: string | null;
	series: Array<number | null>;
}

export interface FinanceSignalSummary {
	periodLabel: string | null;
	comparisonLabel: string | null;
	signals: FinanceSignal[];
	notes: string[];
	coverage: {
		available: number;
		total: number;
	};
}

type AccountId =
	| 'sales'
	| 'operating_profit'
	| 'net_income'
	| 'operating_cashflow'
	| 'current_assets'
	| 'current_liabilities'
	| 'noncurrent_liabilities'
	| 'total_stockholders_equity';

const SIGNAL_TOTAL = 6;

export function buildFinanceSignalSummary(periods: CompanyFinancePeriodRow[]): FinanceSignalSummary {
	const sorted = periods
		.filter((period) => period.year && Number.isFinite(Number(period.year)) && period.quarter >= 1 && period.quarter <= 4)
		.slice()
		.sort((a, b) => periodRank(a) - periodRank(b));
	const latest = sorted.at(-1) ?? null;
	const priorSameQuarter = latest ? sorted.find((period) => period.year === String(Number(latest.year) - 1) && period.quarter === latest.quarter) ?? null : null;
	const previous = latest ? sorted.slice(0, -1).at(-1) ?? null : null;
	const comparison = priorSameQuarter ?? previous;
	const comparisonKind = priorSameQuarter ? '전년 동기' : previous ? '전기' : null;
	const signals = [
		salesGrowthSignal(latest, comparison, comparisonKind, sorted),
		marginSignal('opMargin', '영업이익률', latest, sorted, 'operating_profit', 10, 3),
		marginSignal('netMargin', '순이익률', latest, sorted, 'net_income', 8, 0),
		cashConversionSignal(latest, sorted),
		debtRatioSignal(latest, sorted),
		currentRatioSignal(latest, sorted)
	];
	const missing = signals.filter((signal) => signal.tone === 'missing').length;
	const notes: string[] = [];
	if (!latest) {
		notes.push('finance-lite 기간 데이터 없음');
	} else {
		notes.push(`${latest.label} 분기 단독값 기준`);
		if (!priorSameQuarter && previous) notes.push(`전년 동기 없음 · ${previous.label} 전기 비교`);
		if (!comparison) notes.push('비교 기간 없음');
	}
	if (missing > 0) notes.push(`${missing}개 신호는 계정 결손 또는 분모 0으로 보류`);
	return {
		periodLabel: latest?.label ?? null,
		comparisonLabel: comparison?.label ?? null,
		signals,
		notes,
		coverage: {
			available: SIGNAL_TOTAL - missing,
			total: SIGNAL_TOTAL
		}
	};
}

function salesGrowthSignal(
	latest: CompanyFinancePeriodRow | null,
	comparison: CompanyFinancePeriodRow | null,
	comparisonKind: string | null,
	periods: CompanyFinancePeriodRow[]
): FinanceSignal {
	const curr = valueOf(latest, 'sales');
	const prev = valueOf(comparison, 'sales');
	const growth = percentChange(curr, prev);
	return signal({
		id: 'salesGrowth',
		label: '매출 성장',
		value: formatPct(growth, true),
		detail: growth == null ? '비교 불가' : `${comparisonKind ?? '비교'} ${comparison?.label ?? ''}`.trim(),
		tone: growthTone(growth),
		periodLabel: latest?.label ?? null,
		series: periods.map((period) => valueOf(period, 'sales'))
	});
}

function marginSignal(
	id: string,
	label: string,
	latest: CompanyFinancePeriodRow | null,
	periods: CompanyFinancePeriodRow[],
	accountId: 'operating_profit' | 'net_income',
	goodAt: number,
	watchAt: number
): FinanceSignal {
	const margin = ratio(valueOf(latest, accountId), valueOf(latest, 'sales'), { positiveDenominator: true });
	return signal({
		id,
		label,
		value: formatPct(margin),
		detail: margin == null ? '매출 또는 이익 결손' : `${latest?.label ?? ''} 매출 대비`.trim(),
		tone: marginTone(margin, goodAt, watchAt),
		periodLabel: latest?.label ?? null,
		series: periods.map((period) => ratio(valueOf(period, accountId), valueOf(period, 'sales'), { positiveDenominator: true }))
	});
}

function cashConversionSignal(latest: CompanyFinancePeriodRow | null, periods: CompanyFinancePeriodRow[]): FinanceSignal {
	const net = valueOf(latest, 'net_income');
	const cash = valueOf(latest, 'operating_cashflow');
	const conversion = net != null && net > 0 ? ratio(cash, net, { positiveDenominator: true }) : null;
	return signal({
		id: 'cashConversion',
		label: '이익 현금화',
		value: formatPct(conversion),
		detail: conversion == null ? '순이익 양수일 때만 계산' : `${latest?.label ?? ''} 영업CF/순이익`.trim(),
		tone: cashTone(conversion),
		periodLabel: latest?.label ?? null,
		series: periods.map((period) => {
			const periodNet = valueOf(period, 'net_income');
			return periodNet != null && periodNet > 0 ? ratio(valueOf(period, 'operating_cashflow'), periodNet, { positiveDenominator: true }) : null;
		})
	});
}

function debtRatioSignal(latest: CompanyFinancePeriodRow | null, periods: CompanyFinancePeriodRow[]): FinanceSignal {
	const equity = valueOf(latest, 'total_stockholders_equity');
	if (equity != null && equity <= 0) {
		return signal({
			id: 'debtRatio',
			label: '부채비율',
			value: '자본≤0',
			detail: `${latest?.label ?? ''} 자본총계 0 이하`.trim(),
			tone: 'bad',
			periodLabel: latest?.label ?? null,
			series: periods.map((period) => debtRatio(period))
		});
	}
	const debt = debtRatio(latest);
	return signal({
		id: 'debtRatio',
		label: '부채비율',
		value: formatPct(debt),
		detail: debt == null ? '부채 또는 자본 결손' : `${latest?.label ?? ''} 총부채/자본`.trim(),
		tone: debtTone(debt),
		periodLabel: latest?.label ?? null,
		series: periods.map((period) => debtRatio(period))
	});
}

function currentRatioSignal(latest: CompanyFinancePeriodRow | null, periods: CompanyFinancePeriodRow[]): FinanceSignal {
	const current = ratio(valueOf(latest, 'current_assets'), valueOf(latest, 'current_liabilities'), { positiveDenominator: true });
	return signal({
		id: 'currentRatio',
		label: '유동비율',
		value: formatPct(current),
		detail: current == null ? '유동자산 또는 유동부채 결손' : `${latest?.label ?? ''} 유동자산/유동부채`.trim(),
		tone: currentTone(current),
		periodLabel: latest?.label ?? null,
		series: periods.map((period) => ratio(valueOf(period, 'current_assets'), valueOf(period, 'current_liabilities'), { positiveDenominator: true }))
	});
}

function debtRatio(period: CompanyFinancePeriodRow | null): number | null {
	const current = valueOf(period, 'current_liabilities');
	const noncurrent = valueOf(period, 'noncurrent_liabilities');
	const equity = valueOf(period, 'total_stockholders_equity');
	if (current == null || noncurrent == null) return null;
	return ratio(current + noncurrent, equity, { positiveDenominator: true });
}

function signal(input: FinanceSignal): FinanceSignal {
	return input;
}

function valueOf(period: CompanyFinancePeriodRow | null | undefined, accountId: AccountId): number | null {
	const value = period?.values[accountId];
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function percentChange(curr: number | null, prev: number | null): number | null {
	if (curr == null || prev == null || prev <= 0) return null;
	return (curr / prev - 1) * 100;
}

function ratio(
	numerator: number | null,
	denominator: number | null,
	{ positiveDenominator = false }: { positiveDenominator?: boolean } = {}
): number | null {
	if (numerator == null || denominator == null || denominator === 0) return null;
	if (positiveDenominator && denominator <= 0) return null;
	return (numerator / denominator) * 100;
}

function growthTone(value: number | null): FinanceSignalTone {
	if (value == null) return 'missing';
	if (value >= 5) return 'good';
	if (value >= 0) return 'watch';
	return 'bad';
}

function marginTone(value: number | null, goodAt: number, watchAt: number): FinanceSignalTone {
	if (value == null) return 'missing';
	if (value < 0) return 'bad';
	if (value >= goodAt) return 'good';
	if (value >= watchAt) return 'neutral';
	return 'watch';
}

function cashTone(value: number | null): FinanceSignalTone {
	if (value == null) return 'missing';
	if (value >= 100) return 'good';
	if (value >= 60) return 'watch';
	return 'bad';
}

function debtTone(value: number | null): FinanceSignalTone {
	if (value == null) return 'missing';
	if (value <= 100) return 'good';
	if (value <= 200) return 'watch';
	return 'bad';
}

function currentTone(value: number | null): FinanceSignalTone {
	if (value == null) return 'missing';
	if (value >= 150) return 'good';
	if (value >= 100) return 'watch';
	return 'bad';
}

function formatPct(value: number | null, withSign = false): string {
	if (value == null || !Number.isFinite(value)) return '—';
	const sign = withSign && value > 0 ? '+' : '';
	return `${sign}${value.toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

function periodRank(period: CompanyFinancePeriodRow): number {
	return Number(period.year) * 4 + period.quarter;
}
