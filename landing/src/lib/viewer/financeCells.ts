// 재무제표 셀(항목) 단위 회사 비교 — 엔진 `compare(topic="bs"/"is"…)` 의 브라우저 미러.
// panel 본문(PanelRow.cells = XBRL 태그 raw)을 native DOMParser(application/xml)로 파싱해 acode×값
// 셀을 뽑고, acode 로 회사 간 정렬 + 원 환산. cell.py/build/cell.py 1:1 포팅(실 Chromium byte-parity PASS).
//
// ★text/html 금지 — HTML table-model 이 비표준 <TR>/<TE> 를 foster-parent 해 셀 누락. application/xml 필수.

import type { PanelBundle, PanelRow } from './types';

// ── ACONTEXT 디코드 (build/cell.py decodeAcontext 1:1, 순수 regex) ──
const PERIOD_RE = /^(BP|P|C)FY(\d{4})([de])(FY|FQA|FQQ|FQ|HYA|HYQ|HY|TQA|TQQ|TQ)$/;
const AXIS_PREFIXES = new Set(['ifrs-full', 'dart']);
const MARKER_QUARTER: Record<string, number> = { FY: 4, FQ: 1, HY: 2, TQ: 3 };
const UNIT_RE = /단위\s*[:：]\s*(백만원|천원|원)/;
const UNIT_SCALE: Record<string, number> = { 백만원: 1_000_000, 천원: 1_000, 원: 1 };
// 재무 5표 disclosureKey — 셀모드 화이트리스트(엔진 CELL_STATEMENTS 동형).
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
		} else buf.push(s);
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

// 한 statement contentRaw(XBRL 태그) → RawCell[]. application/xml DOMParser.
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

// freq 마스크 (cell.py _freqMask 1:1).
function freqMatch(c: RawCell, freq: 'quarter' | 'year' | 'ytd'): boolean {
	if (freq === 'year') return c.ctxMode === 'Y' || (c.ctxMode === 'A' && c.ctxQuarter === 4);
	if (freq === 'quarter')
		return (c.ctxFlow === 'd' && c.ctxMode === 'Q') || (c.ctxFlow === 'e' && (c.ctxMode === 'A' || c.ctxMode === 'Y'));
	return c.ctxMode === 'A' || c.ctxMode === 'Y'; // ytd
}
function cellPeriod(c: RawCell, freq: 'quarter' | 'year' | 'ytd'): string {
	return freq === 'year' ? String(c.ctxYear) : `${c.ctxYear}Q${c.ctxQuarter}`;
}

const UNIT_ALL_RE = /단위\s*[:：]\s*(백만원|천원|원)/g;
const _BIG_NUM_RE = />\s*\(?\s*[△-]?\s*([\d,]{7,})/g; // TE 본문의 큰 금액(자릿수 단서)

// 단위 배율(원 기준) — 표머리 캡션(백만원/천원)을 우선 신뢰(본문 EPS '단위:원' 오염 무시),
// 캡션이 없으면 magnitude 로 원/비원 판정. 엔진 _detectUnitScale 의 브라우저 보강(에이전트 단위 검증).
function detectUnitScale(rows: PanelRow[], period: string): number {
	let captionUnit: string | null = null; // 백만원/천원만 (원은 EPS 오염 가능 → magnitude 로 확인)
	let maxRaw = 0;
	for (const r of rows) {
		const c = r.cells?.[period];
		if (!c) continue;
		if (!captionUnit) {
			for (const m of c.matchAll(UNIT_ALL_RE)) {
				if (m[1] === '백만원' || m[1] === '천원') {
					captionUnit = m[1];
					break;
				}
			}
		}
		for (const m of c.matchAll(_BIG_NUM_RE)) {
			const n = parseFloat(m[1].replace(/,/g, ''));
			if (isFinite(n) && n > maxRaw) maxRaw = n;
		}
	}
	if (captionUnit) return UNIT_SCALE[captionUnit]; // 표머리 단위 신뢰
	// 백만원/천원 캡션 부재 → magnitude: 1e12 초과(13자리+) = 원, 아니면 백만원(DART 표준).
	// (백만원 회사가 1e12 백만원=100경 원 값을 가질 수 없으므로 원/백만원 분리는 확실. 천원은 캡션 의존.)
	return maxRaw > 1e12 ? 1 : 1_000_000;
}

export interface FinanceRow {
	acode: string;
	label: string;
	values: (number | null)[]; // 회사 index → 원 환산값 (null=honest-gap)
}

// 한 회사의 재무 섹션 → {acode: (label, 원환산값)} (locked period 의 freq 컨텍스트, depth-1).
function companyFinance(
	rows: PanelRow[],
	period: string,
	freq: 'quarter' | 'year' | 'ytd'
): Map<string, { label: string; value: number }> {
	const scale = detectUnitScale(rows, period);
	const targetYear = parseInt(period.slice(0, 4), 10);
	const targetQ = period.length > 5 ? parseInt(period[5], 10) : null;
	const out = new Map<string, { label: string; value: number }>();
	for (const r of rows) {
		const content = r.cells?.[period];
		if (!content || !content.includes('ACODE=')) continue;
		for (const c of parseCells(content)) {
			if (!freqMatch(c, freq) || c.axisPath.includes('|')) continue; // depth-1 라인아이템만
			if (c.ctxYear !== targetYear) continue;
			if (targetQ !== null && freq !== 'year' && c.ctxQuarter !== targetQ) continue;
			if (out.has(c.acode)) continue; // 첫 등장(상위 라인) 우선
			const num = parseNum(c.valueRaw);
			if (num !== null) out.set(c.acode, { label: c.label, value: num * scale });
		}
	}
	return out;
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

// N개 bundle 의 재무 섹션을 acode 로 정렬 — 행=acode·label, 회사별 원 환산값. honest-gap null.
export function alignFinance(
	bundles: PanelBundle[],
	sectionKey: string,
	period: string,
	freq: 'quarter' | 'year' | 'ytd' = 'quarter'
): FinanceRow[] {
	const n = bundles.length;
	const per = bundles.map((b) => companyFinance(b.gridBySection.get(sectionKey) ?? [], period, freq));
	const order: string[] = [];
	const reprLabel = new Map<string, string>();
	for (const m of per) {
		for (const [ac, { label }] of m) {
			if (!reprLabel.has(ac)) {
				reprLabel.set(ac, label);
				order.push(ac);
			}
		}
	}
	return order.map((ac) => ({
		acode: ac,
		label: reprLabel.get(ac) || ac,
		values: per.map((m) => m.get(ac)?.value ?? null)
	}));
}

// 섹션이 재무 셀모드 대상인가 — 섹션의 어떤 행이 재무 5표 disclosureKey 인가(화이트리스트, 오감지 차단).
export function isFinanceSection(rows: PanelRow[]): boolean {
	return rows.some((r) => r.disclosureKey != null && FIN_STATEMENTS.has(r.disclosureKey));
}
