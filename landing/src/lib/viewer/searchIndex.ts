// 공시뷰어 인-페이지 검색 — gridBySection(브라우저 보유) 위 BM25 역인덱스. 서버·임베딩·LLM 0.
//
// 설계: 한국어 음절 bigram(조사 변형 흡수, 형태소 0) + BM25 + 큐레이션 동의어확장. 표(blockType='table')는
// 라벨만 인덱싱(거대표 13MB 본문 폭주 차단 — 표는 라벨/섹션으로 찾음). 빌드는 타임슬라이싱(메인스레드 비차단).
// 실측 검증: tests/_attempts/viewerSearch/ (삼성·SK·카카오 진짜 panel, 빌드 0.76s·쿼리 0.3ms). README 참조.

import type { PanelBundle, PanelRow } from './types';

const HANGUL = /[가-힣]+/g;
const ASCII = /[A-Za-z]{2,20}/g;
const TAG = /<[^>]+>/g;
const ENT = /&[a-zA-Z#0-9]+;/g;
const WS = /\s+/g;

// 한국어 음절 bigram + ascii 단어 (숫자 제외 = vocab 오염 차단). 가-힣 은 BMP 라 surrogate 무관.
export function tokenizeBigram(text: string): string[] {
	const out: string[] = [];
	const hg = text.match(HANGUL);
	if (hg) {
		for (const run of hg) {
			if (run.length === 1) out.push(run);
			else for (let i = 0; i < run.length - 1; i++) out.push(run.slice(i, i + 2));
		}
	}
	const ac = text.match(ASCII);
	if (ac) for (const w of ac) out.push(w.toLowerCase());
	return out;
}

// 검색용 경량 평문화 — 태그·엔티티→공백, 공백 1회 정규화. (cell.ts stripInlineTags 는 캡션파싱용 6패스라
// 대량 인덱싱엔 과함 — 실측 2배 느림. 인덱싱은 단일라인 평문이면 충분.)
function strip(raw: string): string {
	return raw.replace(TAG, ' ').replace(ENT, ' ').replace(WS, ' ').trim();
}

// 큐레이션 동의어 — dartlab `ngramIndex._L0_INFORMAL`(43키) + 공시 도메인 상식 시드. 운영자 수동 관리.
// PMI/공기행렬 자동발굴 금지(단일회사 코퍼스 동어반복 인공물 — project_unified_search_table §8 격하).
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
	전환사채: ['전환사채', '신주인수권부사채', '교환사채'],
	리스: ['리스부채', '사용권자산', '운용리스', '금융리스'],
	충당부채: ['충당부채', '우발부채', '복구충당', '판매보증'],
	파생: ['파생상품', '선도', '스왑', '헤지']
};

export interface IndexedRow {
	sectionKey: string;
	rowIndex: number; // gridBySection.get(sectionKey) 내 index (PanelMatrix 행 i 와 정렬 → glow 타깃)
	chapter: string;
	section: string;
	block: string;
	scope: string;
	cells: Record<string, string>; // period → 평문 셀 (스니펫·hit period 용)
	tf: Map<string, number>;
	len: number;
}

export interface SearchIndex {
	rows: IndexedRow[];
	postings: Map<string, number[]>;
	df: Map<string, number>;
	avgdl: number;
	vocab: number;
}

export interface SearchHit {
	sectionKey: string;
	rowIndex: number;
	chapter: string;
	section: string;
	block: string;
	scope: string;
	period: string;
	score: number;
	snippet: string;
}

export interface BuildOpts {
	/** 표 행 본문도 토큰화할지. 기본 false = 표는 라벨만(거대표 폭주 차단, 표는 라벨로 찾음). */
	tableBody?: boolean;
	/** 셀당 토큰화 상한 글자수(거대 텍스트셀 방어). 기본 4000. */
	cellCap?: number;
}

interface Acc {
	rows: IndexedRow[];
	postings: Map<string, number[]>;
	df: Map<string, number>;
	totalLen: number;
}

// 한 행(PanelRow) → acc 누적. buildIndex/buildIndexChunked 공용 (parity 보장).
function indexRow(acc: Acc, sectionKey: string, rowIndex: number, r: PanelRow, opts: Required<BuildOpts>): void {
	const cells: Record<string, string> = {};
	for (const [p, raw] of Object.entries(r.cells)) {
		if (raw) cells[p] = strip(raw);
	}
	if (Object.keys(cells).length === 0) return;
	const label = `${r.chapter} ${r.sectionLeaf} ${r.blockLeaf}`;
	const skipBody = !opts.tableBody && r.blockType === 'table';
	const bodyText = skipBody
		? ''
		: Object.values(cells)
				.map((c) => (c.length > opts.cellCap ? c.slice(0, opts.cellCap) : c))
				.join(' ');
	const toks = tokenizeBigram(label + ' ' + bodyText);
	const tf = new Map<string, number>();
	for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
	const idx = acc.rows.length;
	for (const t of tf.keys()) {
		let lst = acc.postings.get(t);
		if (!lst) acc.postings.set(t, (lst = []));
		lst.push(idx);
		acc.df.set(t, (acc.df.get(t) ?? 0) + 1);
	}
	const len = toks.length || 1;
	acc.totalLen += len;
	acc.rows.push({
		sectionKey,
		rowIndex,
		chapter: r.chapter,
		section: r.sectionLeaf,
		block: r.blockLeaf,
		scope: r.scope ?? '',
		cells,
		tf,
		len
	});
}

function finalize(acc: Acc): SearchIndex {
	return {
		rows: acc.rows,
		postings: acc.postings,
		df: acc.df,
		avgdl: acc.totalLen / Math.max(1, acc.rows.length),
		vocab: acc.df.size
	};
}

function defaults(opts: BuildOpts): Required<BuildOpts> {
	return { tableBody: opts.tableBody ?? false, cellCap: opts.cellCap ?? 4000 };
}

/** 동기 빌드 — 작은 회사·테스트용. 큰 회사는 buildIndexChunked 권장. */
export function buildIndex(bundle: PanelBundle, opts: BuildOpts = {}): SearchIndex {
	const o = defaults(opts);
	const acc: Acc = { rows: [], postings: new Map(), df: new Map(), totalLen: 0 };
	for (const [sectionKey, prows] of bundle.gridBySection) {
		for (let i = 0; i < prows.length; i++) indexRow(acc, sectionKey, i, prows[i], o);
	}
	return finalize(acc);
}

// MessageChannel 기반 yield-to-main (setTimeout 4ms clamp 회피, 진짜 macrotask 양보 = 렌더 비차단).
function yieldToMain(): Promise<void> {
	return new Promise((resolve) => {
		const ch = new MessageChannel();
		ch.port1.onmessage = () => resolve();
		ch.port2.postMessage(null);
	});
}

/**
 * 타임슬라이싱 빌드 — 섹션 묶음마다 메인스레드에 양보(잼 0). 결과는 buildIndex 와 동일(parity).
 * 거대표 회사(카카오 1.4s)도 16ms 프레임 안 넘게 끊어 빌드.
 */
export async function buildIndexChunked(bundle: PanelBundle, opts: BuildOpts = {}, chunkSections = 8): Promise<SearchIndex> {
	const o = defaults(opts);
	const acc: Acc = { rows: [], postings: new Map(), df: new Map(), totalLen: 0 };
	let since = 0;
	for (const [sectionKey, prows] of bundle.gridBySection) {
		for (let i = 0; i < prows.length; i++) indexRow(acc, sectionKey, i, prows[i], o);
		if (++since >= chunkSections) {
			since = 0;
			await yieldToMain();
		}
	}
	return finalize(acc);
}

const K1 = 1.5;
const B = 0.75;

/** 쿼리 → bigram 가중치 + 적용된 동의어 목록(칩 노출용). */
export function expandQuery(query: string, expand = true): { weights: Map<string, number>; added: string[] } {
	const weights = new Map<string, number>();
	for (const t of tokenizeBigram(query)) weights.set(t, 1.0);
	const added: string[] = [];
	if (expand) {
		const qns = query.replace(/\s+/g, '');
		for (const [key, syns] of Object.entries(SYNONYMS)) {
			if (qns.includes(key)) {
				for (const syn of syns) {
					for (const bg of tokenizeBigram(syn)) weights.set(bg, Math.max(weights.get(bg) ?? 0, 0.5));
					added.push(syn);
				}
			}
		}
	}
	return { weights, added };
}

export function search(idx: SearchIndex, query: string, opts: { expand?: boolean; topK?: number } = {}): { hits: SearchHit[]; added: string[] } {
	const { weights, added } = expandQuery(query, opts.expand ?? true);
	const n = idx.rows.length;
	if (n === 0 || weights.size === 0) return { hits: [], added };
	const scores = new Map<number, number>();
	for (const [term, qw] of weights) {
		const d = idx.df.get(term) ?? 0;
		if (d <= 0) continue;
		const idf = Math.log((n - d + 0.5) / (d + 0.5) + 1.0);
		const postings = idx.postings.get(term);
		if (!postings) continue;
		for (const pos of postings) {
			const row = idx.rows[pos];
			const tf = row.tf.get(term) ?? 0;
			const denom = tf + K1 * (1 - B + B * (row.len / idx.avgdl));
			if (denom > 0) scores.set(pos, (scores.get(pos) ?? 0) + (qw * idf * (tf * (K1 + 1))) / denom);
		}
	}
	const top = [...scores.entries()].sort((a, b) => b[1] - a[1]).slice(0, opts.topK ?? 8);
	const firstTok = (query.trim().split(/\s+/)[0] ?? '').replace(/[^가-힣A-Za-z]/g, '');
	const hits: SearchHit[] = top.map(([pos, sc]) => {
		const row = idx.rows[pos];
		const periodsDesc = Object.keys(row.cells).sort().reverse();
		let hitP = periodsDesc[0] ?? '';
		let snippet = '';
		if (firstTok.length >= 2) {
			for (const p of periodsDesc) {
				const at = row.cells[p].indexOf(firstTok);
				if (at >= 0) {
					hitP = p;
					snippet = row.cells[p].slice(Math.max(0, at - 28), at + 52);
					break;
				}
			}
		}
		if (!snippet) snippet = (row.cells[hitP] ?? '').slice(0, 72);
		return {
			sectionKey: row.sectionKey,
			rowIndex: row.rowIndex,
			chapter: row.chapter,
			section: row.section,
			block: row.block,
			scope: row.scope,
			period: hitP,
			score: sc,
			snippet
		};
	});
	return { hits, added };
}
