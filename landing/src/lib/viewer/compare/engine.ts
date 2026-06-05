// Compare module entrypoint for viewer surfaces.
// Routes/components should call this instead of composing row/finance branches themselves.

import type { PanelBundle } from '../types';
import { alignFinance, isFinanceSection } from './financeCompare';
import { compareRows } from './rowCompare';
import type { CompareBoard, FinanceFreq } from './types';

export interface BuildCompareBoardOptions {
	sectionKey: string;
	period: string;
	freq?: FinanceFreq;
	scope?: string | null;
}

function freqForPeriod(bundle: PanelBundle | undefined, period: string): FinanceFreq {
	return bundle?.periodKind[period] === 'annual' ? 'year' : 'quarter';
}

export function buildCompareBoard(bundles: PanelBundle[], opts: BuildCompareBoardOptions): CompareBoard {
	const referenceRows = bundles[0]?.gridBySection.get(opts.sectionKey) ?? [];
	if (isFinanceSection(referenceRows)) {
		const freq = opts.freq ?? freqForPeriod(bundles[0], opts.period);
		const finance = alignFinance(bundles, opts.sectionKey, opts.period, freq, opts.scope);
		return {
			mode: 'finance',
			rows: [],
			financeRows: finance.rows,
			financeUnits: finance.units,
			diagnostics: finance.diagnostics
		};
	}
	const row = compareRows(bundles, opts.sectionKey, opts.period);
	return {
		mode: 'row',
		rows: row.rows,
		financeRows: null,
		financeUnits: null,
		diagnostics: row.diagnostics
	};
}
