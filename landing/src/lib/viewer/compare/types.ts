// Viewer compare model — browser mirror of Python `dartlab.compare`.
// Pure data contracts only; Svelte components consume this through the compare module.

export const COMPARE_SEP = '␟';

export type ShareClass = 'shared' | 'partial' | 'solo';
export type FinanceFreq = 'quarter' | 'year' | 'ytd';
export type UnitConfidence = 'caption' | 'magnitude';

export interface CompareCompany {
	code: string;
	corpName: string;
}

export interface CompareDiagnostics {
	mode: 'row' | 'finance';
	period: string;
	freq?: FinanceFreq;
	scope?: string | null;
	rowCount: number;
	sharedRows: number;
	partialRows: number;
	soloRows: number;
	narrativePolicy?: 'company-row';
	unitWarnings?: number;
}

export interface AlignedRow {
	alignKey: string;
	label: string; // gutter/self-identifying label = blockLeaf || sectionLeaf || disclosureKey
	disclosureKey: string | null;
	scope: string | null;
	leafType: string;
	blockType: 'text' | 'table';
	cells: (string | null)[]; // company index -> cell body; null = honest-gap
	shareClass: ShareClass;
}

export interface UnitInfo {
	scale: number;
	label: string;
	confidence: UnitConfidence;
}

export interface FinanceRow {
	acode: string;
	label: string;
	depth: number; // 들여쓰기 깊이(순수 구조) — IS 본류 균일 1, 리프 2+
	isTotal: boolean; // 총계 강조 — depth 와 분리(IS 당기순이익/총포괄손익은 depth 1 + true)
	values: (number | null)[]; // company index -> KRW-normalized value; null = honest-gap
}

export interface FinanceCompare {
	rows: FinanceRow[];
	units: UnitInfo[]; // company index -> source unit metadata
	diagnostics: CompareDiagnostics;
}

export interface CompareBoard {
	mode: 'row' | 'finance';
	rows: AlignedRow[];
	financeRows: FinanceRow[] | null;
	financeUnits: UnitInfo[] | null;
	diagnostics: CompareDiagnostics;
}
