// Finance cell-mode compare — browser mirror of Python compare(topic="bs"/"is"/...).
// Rows align by acode; values are normalized to KRW with source-unit diagnostics.

import type { PanelBundle, PanelRow } from '../types';
import { accountDepth, accountIsTotal } from '../finance/financePivot';
import type { CompareDiagnostics, FinanceCompare, FinanceFreq, FinanceRow, UnitInfo } from './types';

const PERIOD_RE = /^(BP|P|C)FY(\d{4})([de])(FY|FQA|FQQ|FQ|HYA|HYQ|HY|TQA|TQQ|TQ)$/;
const AXIS_PREFIXES = new Set(['ifrs-full', 'dart']);
const MARKER_QUARTER: Record<string, number> = { FY: 4, FQ: 1, HY: 2, TQ: 3 };
const UNIT_RE = /단위\s*[:：]?\s*[(]?\s*(백만원|천원|원)/;
const UNIT_SCALE: Record<string, number> = { 백만원: 1_000_000, 천원: 1_000, 원: 1 };
const UNIT_LABEL: Record<number, string> = { 1_000_000: '백만원', 1_000: '천원', 1: '원' };
const BIG_NUM_RE = />\s*\(?\s*[△-]?\s*([\d,]{7,})/g;

// Financial statement disclosure keys present in viewer PanelRow data.
export const FIN_STATEMENTS = new Set(['BS', 'IS1', 'IS2', 'IS3', 'CF', 'EF']);

function markerToQuarterMode(marker: string): [number, string] {
	if (marker === 'FY') return [4, 'Y'];
	const base = marker.slice(0, 2);
	const suffix = marker.slice(2);
	const mode = suffix === 'A' || suffix === 'Q' ? suffix : 'P';
	return [MARKER_QUARTER[base], mode];
}

function axisMembers(segs: string[]): string[] {
	const tokens: string[] = [];
	let buf: string[] = [];
	for (const s of segs) {
		if (AXIS_PREFIXES.has(s) || s.startsWith('entity')) {
			if (buf.length) tokens.push(buf.join('_'));
			buf = [s];
		} else {
			buf.push(s);
		}
	}
	if (buf.length) tokens.push(buf.join('_'));
	return tokens
		.filter((t) => t.endsWith('Member'))
		.map((m) =>
			m.startsWith('ifrs-full_') ? m.slice('ifrs-full_'.length) : m.startsWith('dart_') ? m.slice('dart_'.length) : m
		);
}

function decodeAcontext(ctx: string): [number, string, number, string, string] | null {
	if (!ctx) return null;
	const parts = ctx.split('_');
	const m = PERIOD_RE.exec(parts[0]);
	if (!m) return null;
	const ctxYear = parseInt(m[2], 10);
	const ctxFlow = m[3];
	const [ctxQuarter, ctxMode] = markerToQuarterMode(m[4]);
	const axisPath = axisMembers(parts.slice(1)).join('|');
	return [ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath];
}

interface RawCell {
	acode: string;
	label: string;
	ctxYear: number;
	ctxFlow: string;
	ctxQuarter: number;
	ctxMode: string;
	axisPath: string;
	valueRaw: string;
}

function teText(el: Element): string {
	return (el.textContent || '').trim();
}

function rowLabel(tes: Element[]): string {
	for (const te of tes) {
		const ac = (te.getAttribute('ACODE') || '').trim();
		if (!ac) {
			const t = teText(te);
			if (t) return t;
		}
	}
	return '';
}

function parseCells(contentRaw: string): RawCell[] {
	if (!contentRaw || !contentRaw.includes('ACODE=')) return [];
	const doc = new DOMParser().parseFromString('<root>' + contentRaw + '</root>', 'application/xml');
	const out: RawCell[] = [];
	for (const tr of Array.from(doc.querySelectorAll('TR'))) {
		const tes = Array.from(tr.querySelectorAll('TE'));
		if (!tes.length) continue;
		const label = rowLabel(tes);
		for (const te of tes) {
			const actx = (te.getAttribute('ACONTEXT') || '').trim();
			const acode = (te.getAttribute('ACODE') || '').trim();
			if (!actx || !acode) continue;
			const dec = decodeAcontext(actx);
			if (!dec) continue;
			const [ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath] = dec;
			out.push({ acode, label, ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath, valueRaw: teText(te) });
		}
	}
	return out;
}

function freqMatch(c: RawCell, freq: FinanceFreq): boolean {
	if (freq === 'year') return c.ctxMode === 'Y' || (c.ctxMode === 'A' && c.ctxQuarter === 4);
	if (freq === 'quarter')
		return (c.ctxFlow === 'd' && c.ctxMode === 'Q') || (c.ctxFlow === 'e' && (c.ctxMode === 'A' || c.ctxMode === 'Y'));
	return c.ctxMode === 'A' || c.ctxMode === 'Y';
}

function captionUnit(content: string): UnitInfo | null {
	const acodeAt = content.indexOf('ACODE=');
	const captionArea = acodeAt >= 0 ? content.slice(0, acodeAt) : content;
	const m = UNIT_RE.exec(captionArea);
	if (!m) return null;
	const scale = UNIT_SCALE[m[1]];
	return { scale, label: UNIT_LABEL[scale], confidence: 'caption' };
}

// Unit detection is scoped to the locked period and caption area only.
// Body labels like EPS "(단위:원)" are after ACODE cells and must not define the table unit.
export function detectFinanceUnit(rows: PanelRow[], period: string): UnitInfo {
	let maxRaw = 0;
	for (const r of rows) {
		const content = r.cells?.[period];
		if (!content) continue;
		const unit = captionUnit(content);
		if (unit) return unit;
		for (const g of content.matchAll(BIG_NUM_RE)) {
			const n = parseFloat(g[1].replace(/,/g, ''));
			if (isFinite(n) && n > maxRaw) maxRaw = n;
		}
	}
	const scale = maxRaw > 1e12 ? 1 : 1_000_000;
	return { scale, label: UNIT_LABEL[scale], confidence: 'magnitude' };
}

function parseNum(s: string): number | null {
	if (!s) return null;
	let t = s.replace(/,/g, '').trim();
	let neg = false;
	if (/^\(.*\)$/.test(t) || t.startsWith('△') || t.startsWith('-')) {
		neg = true;
		t = t.replace(/[()△-]/g, '');
	}
	const n = parseFloat(t);
	if (!isFinite(n)) return null;
	return neg ? -n : n;
}

function targetScope(rows: PanelRow[]): string | null {
	return rows.find((r) => r.scope)?.scope ?? null;
}

function companyFinance(
	rows: PanelRow[],
	period: string,
	freq: FinanceFreq,
	scope: string | null
): { cells: Map<string, { label: string; value: number }>; unit: UnitInfo } {
	const scopedRows = scope ? rows.filter((r) => r.scope === scope || r.scope == null) : rows;
	const unit = detectFinanceUnit(scopedRows, period);
	const targetYear = parseInt(period.slice(0, 4), 10);
	const targetQ = period.length > 5 ? parseInt(period[5], 10) : null;
	const out = new Map<string, { label: string; value: number }>();
	for (const r of scopedRows) {
		const content = r.cells?.[period];
		if (!content || !content.includes('ACODE=')) continue;
		for (const c of parseCells(content)) {
			if (!freqMatch(c, freq) || c.axisPath.includes('|')) continue;
			if (c.ctxYear !== targetYear) continue;
			if (targetQ !== null && freq !== 'year' && c.ctxQuarter !== targetQ) continue;
			if (out.has(c.acode)) continue;
			const num = parseNum(c.valueRaw);
			if (num !== null) out.set(c.acode, { label: c.label, value: num * unit.scale });
		}
	}
	return { cells: out, unit };
}

export function alignFinance(
	bundles: PanelBundle[],
	sectionKey: string,
	period: string,
	freq: FinanceFreq = 'quarter',
	scopeOverride?: string | null
): FinanceCompare {
	const referenceRows = bundles[0]?.gridBySection.get(sectionKey) ?? [];
	const scope = scopeOverride ?? targetScope(referenceRows);
	const per = bundles.map((b) => companyFinance(b.gridBySection.get(sectionKey) ?? [], period, freq, scope));
	const order: string[] = [];
	const reprLabel = new Map<string, string>();
	for (const { cells } of per) {
		for (const [ac, { label }] of cells) {
			if (!reprLabel.has(ac)) {
				reprLabel.set(ac, label);
				order.push(ac);
			}
		}
	}
	const rows: FinanceRow[] = order.map((ac) => ({
		acode: ac,
		label: reprLabel.get(ac) || ac,
		depth: accountDepth(ac),
		isTotal: accountIsTotal(ac),
		values: per.map((p) => p.cells.get(ac)?.value ?? null)
	}));
	const sharedRows = rows.filter((r) => r.values.every((v) => v != null)).length;
	const partialRows = rows.filter((r) => r.values.filter((v) => v != null).length > 1 && r.values.some((v) => v == null)).length;
	const diagnostics: CompareDiagnostics = {
		mode: 'finance',
		period,
		freq,
		scope,
		rowCount: rows.length,
		sharedRows,
		partialRows,
		soloRows: rows.length - sharedRows - partialRows,
		unitWarnings: per.filter((p) => p.unit.confidence === 'magnitude').length
	};
	return { rows, units: per.map((p) => p.unit), diagnostics };
}

export function isFinanceSection(rows: PanelRow[]): boolean {
	return rows.some((r) => r.disclosureKey != null && FIN_STATEMENTS.has(r.disclosureKey));
}
