// 회사 워크스페이스 재무 판단 신호 순수 모델 검증.
// 실행: cd landing && npx tsx _scripts/companyFinanceSignalCheck.mts
import { buildFinanceSignalSummary } from '../src/lib/company/financeSignalModel.ts';
import type { CompanyFinancePeriodRow } from '../src/lib/scan/financeLiteRuntime.ts';

let fail = 0;

function eq(got: unknown, expected: unknown, label: string): void {
	if (JSON.stringify(got) !== JSON.stringify(expected)) {
		fail += 1;
		console.log('FAIL', label, '\n  got', JSON.stringify(got), '\n  exp', JSON.stringify(expected));
	}
}

function period(periodId: string, values: CompanyFinancePeriodRow['values']): CompanyFinancePeriodRow {
	const year = periodId.slice(0, 4);
	const quarter = Number(periodId.slice(5, 6));
	return {
		period: periodId,
		label: `${year.slice(2)}.${quarter}Q`,
		year,
		quarter,
		values
	};
}

const healthy = buildFinanceSignalSummary([
	period('2023Q4', {
		sales: 1000,
		operating_profit: 80,
		net_income: 60,
		operating_cashflow: 50,
		current_assets: 350,
		current_liabilities: 200,
		noncurrent_liabilities: 220,
		total_stockholders_equity: 600
	}),
	period('2024Q4', {
		sales: 1200,
		operating_profit: 180,
		net_income: 120,
		operating_cashflow: 150,
		current_assets: 500,
		current_liabilities: 250,
		noncurrent_liabilities: 200,
		total_stockholders_equity: 600
	})
]);

eq(healthy.periodLabel, '24.4Q', 'latest period');
eq(healthy.comparisonLabel, '23.4Q', 'same-quarter comparison');
eq(healthy.coverage, { available: 6, total: 6 }, 'coverage all available');
eq(healthy.signals.map((s) => [s.id, s.value, s.tone]), [
	['salesGrowth', '+20.0%', 'good'],
	['opMargin', '15.0%', 'good'],
	['netMargin', '10.0%', 'good'],
	['cashConversion', '125.0%', 'good'],
	['debtRatio', '75.0%', 'good'],
	['currentRatio', '200.0%', 'good']
], 'healthy signal values');

const guarded = buildFinanceSignalSummary([
	period('2023Q4', {
		sales: 0,
		operating_profit: 10,
		net_income: 10,
		operating_cashflow: 5,
		current_assets: 100,
		current_liabilities: 0,
		total_stockholders_equity: 100
	}),
	period('2024Q4', {
		sales: 100,
		operating_profit: -5,
		net_income: -20,
		operating_cashflow: 10,
		current_assets: 100,
		current_liabilities: 80,
		total_stockholders_equity: -1
	})
]);

eq(guarded.signals.find((s) => s.id === 'salesGrowth')?.tone, 'missing', 'zero prior sales withheld');
eq(guarded.signals.find((s) => s.id === 'opMargin')?.tone, 'bad', 'negative operating margin');
eq(guarded.signals.find((s) => s.id === 'cashConversion')?.tone, 'missing', 'negative net income withheld');
eq(guarded.signals.find((s) => s.id === 'debtRatio')?.value, '자본≤0', 'non-positive equity flagged');
eq(guarded.signals.find((s) => s.id === 'currentRatio')?.value, '125.0%', 'current ratio from available pair');

const empty = buildFinanceSignalSummary([]);
eq(empty.coverage, { available: 0, total: 6 }, 'empty coverage');
eq(empty.notes[0], 'finance-lite 기간 데이터 없음', 'empty note');

console.log(fail === 0 ? 'companyFinanceSignalCheck: ALL OK' : `companyFinanceSignalCheck: ${fail} FAIL`);
process.exit(fail === 0 ? 0 : 1);
