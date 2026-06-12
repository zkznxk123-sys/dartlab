import type { PanelGridResponse, PanelRow } from '@/features/dashboard/api/client';

const HANGUL_RE = /[가-힣]+/g;
const ASCII_RE = /[A-Za-z]{2,24}/g;
const TAG_RE = /<[^>]+>/g;
const ENTITY_RE = /&[a-zA-Z#0-9]+;/g;
const WS_RE = /\s+/g;
const SECTION_KEY_SEP = '␟';

const SYNONYMS: Record<string, string[]> = {
	부채: ['차입금', '사채', '우발부채', '지급보증', '리스부채'],
	차입금: ['사채', '단기차입', '장기차입', 'borrowings'],
	위험: ['리스크', '불확실성', '위험요인'],
	소송: ['계류', '손해배상', '분쟁', '피소', '제소'],
	배당: ['배당금', '현금배당', '현물배당', '배당성향'],
	자사주: ['자기주식', '자기주식취득', '자기주식소각'],
	스톡옵션: ['주식매수선택권', '주식기준보상'],
	감사인: ['감사의견', '감사보고서', '내부회계관리', '외부감사'],
	특수관계자: ['특수관계', '이해관계자', '관계기업', '종속기업'],
	손상: ['손상차손', '영업권', '회수가능액'],
	합병: ['인수', '사업결합', '분할'],
	증자: ['유상증자', '무상증자', '신주발행'],
	전환사채: ['신주인수권부사채', '교환사채'],
	리스: ['리스부채', '사용권자산', '운용리스', '금융리스'],
	충당부채: ['우발부채', '복구충당', '판매보증'],
	파생: ['파생상품', '선도', '스왑', '헤지'],
	매출: ['매출액', '영업수익'],
	순이익: ['당기순이익'],
	현금흐름: ['영업활동현금흐름'],
};

const STOP_WORDS = new Set([
	'연간만',
	'연간',
	'켜고',
	'근거',
	'근거로',
	'근거를',
	'이동',
	'이동해서',
	'최근',
	'내용',
	'숫자',
	'숫자를',
	'기간',
	'기간과',
	'함께',
	'요약',
	'요약해줘',
	'알려줘',
	'찾아줘',
	'보여줘',
	'설명',
	'관련',
	'공시',
	'화면',
	'위치',
]);

const AMOUNT_RE = /(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s?(조|억)(?=\s*원|[\s,.)\]]|$)/g;
const AMOUNT_QUERY_RE = /(\d[\d,]*(?:\.\d+)?)\s*(조|억)\s*(?:원\s*)?(이상|초과|넘는|넘게|이하|미만|미달)/;
const UNIT_MULT: Record<string, number> = { 조: 1e12, 억: 1e8 };

export interface ViewerIndexedRow {
	sectionKey: string;
	rowIndex: number;
	chapter: string;
	section: string;
	block: string;
	scope: string;
	blockType: PanelRow['blockType'];
	cells: Record<string, string>;
	tf: Map<string, number>;
	len: number;
	maxAmount: number;
}

export interface ViewerSearchIndex {
	rows: ViewerIndexedRow[];
	postings: Map<string, number[]>;
	df: Map<string, number>;
	avgdl: number;
	periods: string[];
	vocab: number;
}

export interface ViewerSearchHit {
	sectionKey: string;
	rowIndex: number;
	chapter: string;
	section: string;
	block: string;
	scope: string;
	period: string;
	score: number;
	snippet: string;
	matchKind: 'text' | 'table' | 'amount';
	matchedTerms: string[];
	stale: boolean;
}

interface BuildAccumulator {
	rows: ViewerIndexedRow[];
	postings: Map<string, number[]>;
	df: Map<string, number>;
	totalLen: number;
	sectionCounts: Map<string, number>;
}

interface AmountConstraint {
	min?: number;
	max?: number;
}

export function sectionKeyFor(row: Pick<PanelRow, 'chapter' | 'sectionLeaf'>): string {
	return `${row.chapter}${SECTION_KEY_SEP}${row.sectionLeaf}`;
}

export function plainText(raw: string): string {
	return raw.replace(TAG_RE, ' ').replace(ENTITY_RE, ' ').replace(WS_RE, ' ').trim();
}

export function tokenizeBigram(text: string): string[] {
	const out: string[] = [];
	const hg = text.match(HANGUL_RE);
	if (hg) {
		for (const run of hg) {
			if (run.length === 1) out.push(run);
			else for (let i = 0; i < run.length - 1; i++) out.push(run.slice(i, i + 2));
		}
	}
	const ascii = text.match(ASCII_RE);
	if (ascii) {
		for (const w of ascii) out.push(w.toLowerCase());
	}
	return out;
}

export function maxAmountKrw(text: string): number {
	let max = 0;
	AMOUNT_RE.lastIndex = 0;
	let match: RegExpExecArray | null;
	while ((match = AMOUNT_RE.exec(text)) !== null) {
		if (text.slice(Math.max(0, match.index - 2), match.index).includes('제')) continue;
		if (match[2] === '조') {
			const tail = text.slice(match.index + match[0].length, match.index + match[0].length + 14);
			if (!/^\s*원/.test(tail) && !/^\s*[\d,]+\s*억/.test(tail)) continue;
		}
		const value = Number.parseFloat(match[1].replace(/,/g, '')) * UNIT_MULT[match[2] as keyof typeof UNIT_MULT];
		if (value > max) max = value;
	}
	return max;
}

function parseConstraint(query: string): { constraint: AmountConstraint | null; residual: string } {
	const match = query.match(AMOUNT_QUERY_RE);
	if (!match || match.index === undefined) return { constraint: null, residual: query };
	const value = Number.parseFloat(match[1].replace(/,/g, '')) * UNIT_MULT[match[2] as keyof typeof UNIT_MULT];
	const isMin = match[3] === '이상' || match[3] === '초과' || match[3] === '넘는' || match[3] === '넘게';
	const residual = `${query.slice(0, match.index)} ${query.slice(match.index + match[0].length)}`.replace(/\s+/g, ' ').trim();
	return { constraint: isMin ? { min: value } : { max: value }, residual };
}

function amountOk(amount: number, constraint: AmountConstraint): boolean {
	return amount > 0 && (constraint.min === undefined || amount >= constraint.min) && (constraint.max === undefined || amount <= constraint.max);
}

function queryWords(query: string): string[] {
	return query.toLowerCase().match(/[가-힣a-z0-9]{2,}/g) ?? [];
}

function importantWords(query: string): string[] {
	return queryWords(query).filter((word) => !STOP_WORDS.has(word));
}

function expandQuery(query: string): { weights: Map<string, number>; added: string[]; important: string[] } {
	const weights = new Map<string, number>();
	const important = importantWords(query);
	const weightedSource = important.length ? important.join(' ') : query;
	for (const token of tokenizeBigram(weightedSource)) weights.set(token, 1);
	const added: string[] = [];
	const words = queryWords(query);
	for (const [key, syns] of Object.entries(SYNONYMS)) {
		const lowerKey = key.toLowerCase();
		if (!words.some((w) => w === lowerKey || w.startsWith(lowerKey))) continue;
		for (const syn of syns) {
			for (const bg of tokenizeBigram(syn)) weights.set(bg, Math.max(weights.get(bg) ?? 0, 0.5));
			added.push(syn);
		}
	}
	return { weights, added, important };
}

function surfaceNeedlesFromImportant(important: string[], added: string[], fallbackQuery: string): string[] {
	const needles = new Set<string>();
	const sources = important.length || added.length ? [...important, ...added] : [fallbackQuery];
	for (const source of sources) {
		for (const m of source.matchAll(/[가-힣A-Za-z0-9]{2,}/g)) {
			const word = m[0].toLowerCase();
			if (!STOP_WORDS.has(word)) needles.add(word);
		}
	}
	return [...needles].sort((a, b) => b.length - a.length);
}

function yieldToMain(): Promise<void> {
	return new Promise((resolve) => {
		const channel = new MessageChannel();
		channel.port1.onmessage = () => {
			channel.port1.close();
			channel.port2.close();
			resolve();
		};
		channel.port2.postMessage(null);
	});
}

function indexRow(acc: BuildAccumulator, row: PanelRow, periods: string[]): void {
	const sectionKey = sectionKeyFor(row);
	const rowIndex = acc.sectionCounts.get(sectionKey) ?? 0;
	acc.sectionCounts.set(sectionKey, rowIndex + 1);

	const cells: Record<string, string> = {};
	for (const period of periods) {
		const raw = row.cells[period];
		if (raw) cells[period] = plainText(raw);
	}
	if (Object.keys(cells).length === 0) return;

	const label = `${row.chapter} ${row.sectionLeaf} ${row.blockLeaf}`;
	const body = row.blockType === 'table' ? '' : Object.values(cells).map((v) => v.slice(0, 4000)).join(' ');
	const tokens = tokenizeBigram(`${label} ${body}`);
	const tf = new Map<string, number>();
	for (const token of tokens) tf.set(token, (tf.get(token) ?? 0) + 1);

	const pos = acc.rows.length;
	for (const token of tf.keys()) {
		let posting = acc.postings.get(token);
		if (!posting) acc.postings.set(token, (posting = []));
		posting.push(pos);
		acc.df.set(token, (acc.df.get(token) ?? 0) + 1);
	}

	const len = tokens.length || 1;
	acc.totalLen += len;
	acc.rows.push({
		sectionKey,
		rowIndex,
		chapter: row.chapter,
		section: row.sectionLeaf,
		block: row.blockLeaf,
		scope: row.scope ?? '',
		blockType: row.blockType,
		cells,
		tf,
		len,
		maxAmount: maxAmountKrw(Object.values(cells).join(' ')),
	});
}

export async function buildViewerSearchIndex(grid: PanelGridResponse, chunkRows = 96): Promise<ViewerSearchIndex> {
	const acc: BuildAccumulator = {
		rows: [],
		postings: new Map(),
		df: new Map(),
		totalLen: 0,
		sectionCounts: new Map(),
	};
	let since = 0;
	for (const row of grid.rows) {
		indexRow(acc, row, grid.periods);
		if (++since >= chunkRows) {
			since = 0;
			await yieldToMain();
		}
	}
	return {
		rows: acc.rows,
		postings: acc.postings,
		df: acc.df,
		avgdl: acc.totalLen / Math.max(1, acc.rows.length),
		periods: grid.periods,
		vocab: acc.df.size,
	};
}

function evidencePeriod(row: ViewerIndexedRow, periods: string[], needles: string[]): { period: string; rank: number; stale: boolean; matchedTerms: string[] } {
	let firstNonEmpty = -1;
	for (let i = 0; i < periods.length; i++) {
		const period = periods[i];
		const cell = row.cells[period];
		if (!cell) continue;
		if (firstNonEmpty < 0) firstNonEmpty = i;
		const lower = cell.toLowerCase();
		const matchedTerms = needles.filter((needle) => lower.includes(needle));
		if (matchedTerms.length) return { period, rank: i, stale: i > firstNonEmpty, matchedTerms };
	}
	const rank = firstNonEmpty >= 0 ? firstNonEmpty : 0;
	return { period: periods[rank] ?? '', rank, stale: false, matchedTerms: [] };
}

function snippetAt(text: string, needles: string[]): string {
	const lower = text.toLowerCase();
	let bestAt = Number.POSITIVE_INFINITY;
	for (const needle of needles) {
		const at = lower.indexOf(needle);
		if (at >= 0) bestAt = Math.min(bestAt, at);
	}
	if (Number.isFinite(bestAt)) {
		return text.slice(Math.max(0, bestAt - 34), Math.min(text.length, bestAt + 96));
	}
	return text.slice(0, 120);
}

function labelBoost(row: ViewerIndexedRow, needles: string[], important: string[]): number {
	const hay = `${row.chapter} ${row.section} ${row.block}`.toLowerCase();
	let score = 0;
	for (const word of important) {
		if (hay.includes(word)) score += 4;
	}
	for (const needle of needles) {
		if (needle.length >= 2 && hay.includes(needle)) score += 2;
	}
	return score;
}

function rowSurface(row: ViewerIndexedRow): string {
	return `${row.chapter} ${row.section} ${row.block} ${Object.values(row.cells).join(' ')}`.toLowerCase();
}

function rowMatchesSurface(row: ViewerIndexedRow, needles: string[], important: string[]): boolean {
	if (!needles.length && !important.length) return true;
	const hay = rowSurface(row);
	return [...needles, ...important].some((needle) => needle.length >= 2 && hay.includes(needle));
}

export function searchViewerIndex(idx: ViewerSearchIndex, query: string, topK = 8): { hits: ViewerSearchHit[]; added: string[] } {
	const { constraint, residual } = parseConstraint(query);
	const { weights, added, important } = expandQuery(constraint ? residual : query);
	const scores = new Map<number, number>();
	const rowCount = idx.rows.length;
	const needles = surfaceNeedlesFromImportant(important, added, residual || query);

	for (const [term, weight] of weights) {
		const df = idx.df.get(term) ?? 0;
		if (!df) continue;
		const idf = Math.log((rowCount - df + 0.5) / (df + 0.5) + 1);
		for (const pos of idx.postings.get(term) ?? []) {
			const row = idx.rows[pos];
			const tf = row.tf.get(term) ?? 0;
			const denom = tf + 1.5 * (1 - 0.75 + 0.75 * (row.len / idx.avgdl));
			if (denom > 0) scores.set(pos, (scores.get(pos) ?? 0) + weight * idf * ((tf * 2.5) / denom));
		}
	}

	let ranked: Array<[number, number]>;
	if (scores.size) {
		ranked = [...scores.entries()]
			.filter(([pos]) => !constraint || amountOk(idx.rows[pos].maxAmount, constraint))
			.map(([pos, score]) => {
				const ep = evidencePeriod(idx.rows[pos], idx.periods, needles);
				return [pos, (score + labelBoost(idx.rows[pos], needles, important)) / (1 + ep.rank * 0.08)] as [number, number];
			})
			.sort((a, b) => b[1] - a[1]);
	} else if (constraint) {
		const amountRows = idx.rows
			.map((row, pos) => [pos, row.maxAmount] as [number, number])
			.filter(([pos, amount]) => amountOk(amount, constraint) && rowMatchesSurface(idx.rows[pos], needles, important));
		const fallbackRows = amountRows.length
			? amountRows
			: idx.rows.map((row, pos) => [pos, row.maxAmount] as [number, number]).filter(([, amount]) => amountOk(amount, constraint));
		ranked = fallbackRows
			.map(([pos, amount]) => [pos, amount + labelBoost(idx.rows[pos], needles, important) * 1e12] as [number, number])
			.sort((a, b) => b[1] - a[1]);
	} else {
		return { hits: [], added };
	}

	const seen = new Set<string>();
	const hits: ViewerSearchHit[] = [];
	for (const [pos, score] of ranked) {
		const row = idx.rows[pos];
		const dedupeKey = `${row.sectionKey}${SECTION_KEY_SEP}${row.block}`;
		if (seen.has(dedupeKey)) continue;
		seen.add(dedupeKey);
		const ep = evidencePeriod(row, idx.periods, needles);
		const cell = row.cells[ep.period] ?? '';
		hits.push({
			sectionKey: row.sectionKey,
			rowIndex: row.rowIndex,
			chapter: row.chapter,
			section: row.section,
			block: row.block,
			scope: row.scope,
			period: ep.period,
			score,
			snippet: snippetAt(cell, needles),
			matchKind: constraint && amountOk(row.maxAmount, constraint) ? 'amount' : row.blockType === 'table' ? 'table' : 'text',
			matchedTerms: ep.matchedTerms.slice(0, 8),
			stale: ep.stale,
		});
		if (hits.length >= topK) break;
	}
	return { hits, added };
}
