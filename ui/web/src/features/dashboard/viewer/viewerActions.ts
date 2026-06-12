import type { ViewerSearchHit } from './searchIndex';

export type ViewerAction =
	| { kind: 'navigateCompany'; code: string; carryQuestion?: string }
	| { kind: 'focusEvidence'; hit: ViewerSearchHit }
	| { kind: 'setSection'; sectionKey: string }
	| { kind: 'setPeriod'; period: string }
	| { kind: 'shiftWindow'; direction: 'newer' | 'older' }
	| { kind: 'setCols'; count: 3 | 6 | 9 }
	| { kind: 'toggleAnnual' };

export interface ViewerActionApi {
	navigateCompany: (code: string, carryQuestion?: string) => void;
	focusEvidence: (hit: ViewerSearchHit) => void;
	setSection: (sectionKey: string) => void;
	setPeriod: (period: string) => void;
	moveNewer: () => void;
	moveOlder: () => void;
	setCols: (count: 3 | 6 | 9) => void;
	toggleAnnual: () => void;
	hasSection: (sectionKey: string) => boolean;
	hasPeriod: (period: string) => boolean;
	knownCode: (code: string) => boolean;
}

export interface ViewerActionResult {
	ok: boolean;
	reason?: string;
}

export function executeViewerAction(action: ViewerAction, api: ViewerActionApi): ViewerActionResult {
	switch (action.kind) {
		case 'navigateCompany':
			if (!api.knownCode(action.code)) return { ok: false, reason: `unknown code: ${action.code}` };
			api.navigateCompany(action.code, action.carryQuestion);
			return { ok: true };
		case 'focusEvidence':
			if (!action.hit.sectionKey) return { ok: false, reason: 'missing section' };
			api.focusEvidence(action.hit);
			return { ok: true };
		case 'setSection':
			if (!api.hasSection(action.sectionKey)) return { ok: false, reason: `missing section: ${action.sectionKey}` };
			api.setSection(action.sectionKey);
			return { ok: true };
		case 'setPeriod':
			if (!api.hasPeriod(action.period)) return { ok: false, reason: `missing period: ${action.period}` };
			api.setPeriod(action.period);
			return { ok: true };
		case 'shiftWindow':
			if (action.direction === 'newer') api.moveNewer();
			else api.moveOlder();
			return { ok: true };
		case 'setCols':
			api.setCols(action.count);
			return { ok: true };
		case 'toggleAnnual':
			api.toggleAnnual();
			return { ok: true };
	}
}

const YEAR_RE = /(20\d{2})/;
const COL_RE = /(3|6|9)\s*(개|열|기간|분기|년)?/;
const OLDER_RE = /이전|과거|옛|older|뒤로/;
const NEWER_RE = /최신|최근|newer|앞으로/;
const ANNUAL_RE = /연간만|사업보고서|연간\s*필터/;

export function deriveViewerActions(input: {
	question: string;
	hits: ViewerSearchHit[];
	periods: string[];
	targetCode?: string | null;
}): ViewerAction[] {
	const q = input.question;
	const actions: ViewerAction[] = [];
	if (input.targetCode) return [{ kind: 'navigateCompany', code: input.targetCode, carryQuestion: q }];

	const col = q.match(COL_RE)?.[1];
	if (col === '3' || col === '6' || col === '9') actions.push({ kind: 'setCols', count: Number(col) as 3 | 6 | 9 });
	if (ANNUAL_RE.test(q)) actions.push({ kind: 'toggleAnnual' });
	if (OLDER_RE.test(q)) actions.push({ kind: 'shiftWindow', direction: 'older' });
	if (NEWER_RE.test(q)) actions.push({ kind: 'shiftWindow', direction: 'newer' });

	const year = q.match(YEAR_RE)?.[1];
	if (year) {
		const period = input.periods.find((p) => p.startsWith(year));
		if (period) actions.push({ kind: 'setPeriod', period });
	}

	const topHit = input.hits[0];
	if (topHit) actions.push({ kind: 'focusEvidence', hit: topHit });
	return actions;
}
