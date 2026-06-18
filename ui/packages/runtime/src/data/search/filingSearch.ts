// 전역 공시 본문 검색 — 질의어 postings + top-k meta 만 HTTP range fetch(서버리스·exact BM25).
// 공통배선: 퍼블릭·로컬 동일 코어(DataCore)·동일 경로(hf 통파일 / hfRange 조각). 인덱스 sidecar는
// fieldIndex.saveShardedSegment 산출(postings/terms/docLengths/meta.bin + main_stems.json + search_meta.json).
// 검증(_attempts/filingPostingsFetch): byte-range fetch BM25 = full BM25 overlap 1.0000(exact).
// 회사 인덱스(universe/query)는 별개 feature(census A-11) — 본 포트는 queryFilings(공시 코퍼스)만 구현.
import type { DataCore } from '../fetch/request';
import type { SearchPort, FilingHit, FilingSearchQuery } from '@dartlab/ui-contracts';

const K1 = 1.5;
const B = 0.75;
const HANGUL = /[가-힣]+/g;
const ASCII = /[A-Za-z]{2,20}/g;

// searchIndex.ts/tokenizeContent 와 byte-parity: 한글 음절 bigram + 영문 소문자(숫자 제외).
function tokenizeBigram(text: string): string[] {
	if (!text) return [];
	const out: string[] = [];
	for (const m of text.matchAll(HANGUL)) {
		const run = m[0];
		if (run.length === 1) out.push(run);
		else for (let i = 0; i < run.length - 1; i++) out.push(run.slice(i, i + 2));
	}
	for (const m of text.matchAll(ASCII)) out.push(m[0].toLowerCase());
	return out;
}

// LEB128 unsigned varint — count 개 디코드(값 < 2^31 보장: docId<~5M, tf 소). 반환 (값, 다음 pos).
function readVarints(bytes: Uint8Array, pos: number, count: number): number[] {
	const vals = new Array<number>(count);
	for (let n = 0; n < count; n++) {
		let shift = 0;
		let val = 0;
		let byte: number;
		do {
			byte = bytes[pos++] ?? 0;
			val |= (byte & 0x7f) << shift;
			shift += 7;
		} while (byte & 0x80);
		vals[n] = val >>> 0;
	}
	return vals;
}

interface MetaCard {
	rcept_no?: string;
	corp_name?: string;
	stock_code?: string;
	report_nm?: string;
	rcept_dt?: string;
	source?: string;
	sourceRef?: string;
	snippet?: string;
}

interface SearchStats {
	stemDict: Record<string, number>;
	terms: Uint32Array; // stemId 별 (byteStart, gapLen, tfLen, df)
	docLengths: Uint32Array;
	metaOffsets: BigUint64Array; // doc 별 meta.bin byte offset (nDocs+1)
	nDocs: number;
	avgDocLength: number;
}

export interface FilingSearchOptions {
	/** 인덱스 tier (배포 경로 dart/contentIndex/{tier}). 기본 lite. */
	tier?: string;
}

export function createSearchPort(core: DataCore, opts: FilingSearchOptions = {}): SearchPort {
	const dir = `dart/contentIndex/${opts.tier ?? 'lite'}`;
	let statsP: Promise<SearchStats> | null = null;

	async function loadStats(): Promise<SearchStats> {
		// stats blob = 콜드 1회(이후 캐시). 통파일은 hf(프록시 엣지캐시), 조각만 hfRange.
		const ab = (path: string) => core.request<ArrayBuffer>({ origin: 'hf', path, parse: (r) => r.arrayBuffer() });
		const [stemDict, termsBuf, dlBuf, moBuf, meta] = await Promise.all([
			core.request<Record<string, number>>({ origin: 'hf', path: `${dir}/main_stems.json`, parse: (r) => r.json() }),
			ab(`${dir}/main.terms.bin`),
			ab(`${dir}/main.docLengths.bin`),
			ab(`${dir}/main.metaOffsets.bin`),
			core.request<{ nDocs: number; avgDocLength: number }>({ origin: 'hf', path: `${dir}/main.search_meta.json`, parse: (r) => r.json() })
		]);
		return {
			stemDict,
			terms: new Uint32Array(termsBuf),
			docLengths: new Uint32Array(dlBuf),
			metaOffsets: new BigUint64Array(moBuf),
			nDocs: meta.nDocs,
			avgDocLength: Math.max(meta.avgDocLength, 1)
		};
	}

	async function queryFilings(input: FilingSearchQuery): Promise<FilingHit[]> {
		const text = (input.text ?? '').trim();
		if (!text) return [];
		const stats = await (statsP ??= loadStats());
		const { stemDict, terms, docLengths, nDocs, avgDocLength } = stats;

		const seen = new Set<string>();
		const sids: number[] = [];
		for (const tok of tokenizeBigram(text)) {
			if (seen.has(tok)) continue;
			seen.add(tok);
			const sid = stemDict[tok];
			if (sid !== undefined) sids.push(sid);
		}
		if (!sids.length) return [];

		// 질의어 term postings 조각만 병렬 range fetch(1 RTT wave) → exact BM25 누적.
		const scores = new Map<number, number>();
		await Promise.all(
			sids.map(async (sid) => {
				const byteStart = terms[sid * 4] ?? 0;
				const gapLen = terms[sid * 4 + 1] ?? 0;
				const tfLen = terms[sid * 4 + 2] ?? 0;
				const df = terms[sid * 4 + 3] ?? 0;
				if (!df) return;
				const buf = await core.requestBytes({ path: `${dir}/main.postings.bin`, start: byteStart, len: gapLen + tfLen });
				const u8 = new Uint8Array(buf);
				const gaps = readVarints(u8, 0, df);
				const tfs = readVarints(u8, gapLen, df);
				const idf = Math.log((nDocs - df + 0.5) / (df + 0.5) + 1.0);
				let docId = 0;
				for (let i = 0; i < df; i++) {
					docId += gaps[i] ?? 0; // 첫 gap=절대 docId, 이후 delta → cumsum
					const tf = tfs[i] ?? 0;
					const dl = docLengths[docId] || avgDocLength;
					const norm = (tf * (K1 + 1)) / (tf + K1 * (1 - B + (B * dl) / avgDocLength));
					scores.set(docId, (scores.get(docId) ?? 0) + idf * norm);
				}
			})
		);
		if (!scores.size) return [];

		const limit = Math.max(1, input.limit ?? 10);
		const top = [...scores.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit);

		// top-k doc meta 만 range fetch(doc-keyed meta.bin) → FilingHit.
		const hits = await Promise.all(
			top.map(async ([docId, score]) => {
				const o0 = Number(stats.metaOffsets[docId]);
				const o1 = Number(stats.metaOffsets[docId + 1]);
				const buf = await core.requestBytes({ path: `${dir}/main.meta.bin`, start: o0, len: o1 - o0 });
				const card = JSON.parse(new TextDecoder().decode(buf)) as MetaCard;
				return {
					rceptNo: card.rcept_no ?? '',
					corpName: card.corp_name ?? '',
					stockCode: card.stock_code ?? '',
					reportNm: (card.report_nm ?? '').trim(),
					rceptDt: card.rcept_dt ?? '',
					snippet: card.snippet ?? '',
					source: card.source ?? '',
					sourceRef: card.sourceRef ?? '',
					score
				} satisfies FilingHit;
			})
		);
		return hits;
	}

	const companyIndexUnwired = (): never => {
		throw new Error('[search] universe/query(회사 인덱스)는 별도 feature(census A-11) — 이 경로는 미배선. queryFilings(공시 본문)만 구현됨.');
	};
	return { universe: companyIndexUnwired, query: companyIndexUnwired, queryFilings };
}
