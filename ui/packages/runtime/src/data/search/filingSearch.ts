// 전역 공시 본문 검색 — 질의어 postings + top-k meta 만 HTTP range fetch(서버리스·exact BM25).
// 공통배선: 퍼블릭·로컬 동일 코어(DataCore)·동일 경로(hf 통파일 / hfRange 조각). 인덱스 sidecar는
// fieldIndex.saveShardedSegment 산출(postings/terms/docLengths/meta.bin + main_stems.json + search_meta.json).
// 검증(_attempts/filingPostingsFetch): byte-range fetch BM25 = full BM25 overlap 1.0000(exact).
// 회사 인덱스(universe/query)는 별개 feature(census A-11) — 본 포트는 queryFilings(공시 코퍼스)만 구현.
//
// ★배포 layout: 인덱스 파일은 flat 경로가 아니라 run-scoped staging 에 있고, flat `manifest.json` 이
// 안정 pointer(`fileSources`: 파일명→staging 경로)다(publishIndex.manifestPointer 모델). 그래서 항상
// manifest 를 먼저 읽어 fileSources 로 각 파일을 resolve 한다 — CI 가 새 빌드를 publish 하면 pointer 만
// 갈아끼워도 다음 세션이 자동 추종(공통배선이 publish SSOT 와 일치). fileSources 부재 시 flat fallback.
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

interface SegmentStats {
	segment: string; // 'main' | 'delta'
	stemDict: Record<string, number>;
	terms: Uint32Array; // stemId 별 (byteStart, gapLen, tfLen, df)
	docLengths: Uint32Array;
	metaOffsets: BigUint64Array; // doc 별 meta.bin byte offset (nDocs+1)
	nDocs: number;
	avgDocLength: number;
	postingsPath: string; // resolve 된 postings.bin 경로(range fetch)
	metaPath: string; // resolve 된 meta.bin 경로(range fetch)
}

export interface FilingSearchOptions {
	/** 인덱스 tier. 기본 ``full``(flat ``dart/contentIndex/`` — 전체 코퍼스, range-fetch 라 클라 비용 동일).
	 *  그 외 tier 는 ``dart/contentIndex/{tier}/`` 서브디렉터리(예 lite). 둘 다 manifest pointer 경유. */
	tier?: string;
}

export function createSearchPort(core: DataCore, opts: FilingSearchOptions = {}): SearchPort {
	const tier = opts.tier ?? 'full';
	const prefix = tier === 'full' ? 'dart/contentIndex' : `dart/contentIndex/${tier}`;
	const manifestPath = `${prefix}/manifest.json`;
	let segmentsP: Promise<SegmentStats[]> | null = null;

	// flat `manifest.json`(pointer)을 1회 읽어 fileSources(파일명→staging 경로)를 노출.
	// resolve: 파일명→경로(없으면 flat fallback). has: 파일이 게시됐는지(delta 세그먼트 존재 판정용).
	async function loadManifest(): Promise<{ resolve: (name: string) => string; has: (name: string) => boolean }> {
		let fileSources: Record<string, string> = {};
		try {
			const manifest = await core.request<{ fileSources?: Record<string, string> }>({
				origin: 'hf',
				path: manifestPath,
				parse: (r) => r.json()
			});
			if (manifest && typeof manifest.fileSources === 'object' && manifest.fileSources) fileSources = manifest.fileSources;
		} catch {
			// manifest 부재(404)·파싱 실패 → flat fallback(전환기/직접배포 호환). 세그먼트 fetch 가 정직히 실패한다.
		}
		return {
			resolve: (name: string) => fileSources[name] ?? `${prefix}/${name}`,
			has: (name: string) => name in fileSources
		};
	}

	async function loadSegment(seg: string, resolve: (name: string) => string): Promise<SegmentStats> {
		// stats blob = 콜드 1회(이후 캐시). 통파일은 hf(프록시 엣지캐시), 조각만 hfRange. 경로는 pointer resolve.
		const ab = (name: string) => core.request<ArrayBuffer>({ origin: 'hf', path: resolve(name), parse: (r) => r.arrayBuffer() });
		const [stemDict, termsBuf, dlBuf, moBuf, meta] = await Promise.all([
			core.request<Record<string, number>>({ origin: 'hf', path: resolve(`${seg}_stems.json`), parse: (r) => r.json() }),
			ab(`${seg}.terms.bin`),
			ab(`${seg}.docLengths.bin`),
			ab(`${seg}.metaOffsets.bin`),
			core.request<{ nDocs: number; avgDocLength: number }>({ origin: 'hf', path: resolve(`${seg}.search_meta.json`), parse: (r) => r.json() })
		]);
		return {
			segment: seg,
			stemDict,
			terms: new Uint32Array(termsBuf),
			docLengths: new Uint32Array(dlBuf),
			metaOffsets: new BigUint64Array(moBuf),
			nDocs: meta.nDocs,
			avgDocLength: Math.max(meta.avgDocLength, 1),
			postingsPath: resolve(`${seg}.postings.bin`),
			metaPath: resolve(`${seg}.meta.bin`)
		};
	}

	// main(항상) + delta(증분 sidecar 게시됐을 때만) — 파이썬 _getSegments 미러. 신규 공시는 delta 에 있다.
	async function loadSegments(): Promise<SegmentStats[]> {
		const { resolve, has } = await loadManifest();
		const names = ['main', ...(has('delta.postings.bin') ? ['delta'] : [])];
		return Promise.all(names.map((seg) => loadSegment(seg, resolve)));
	}

	// 세그먼트 1개 BM25 — 질의어 postings 조각만 병렬 range fetch(1 RTT wave). 각 세그먼트 자기 idf·nDocs
	// (파이썬 _scoreBM25 per-segment 미러 — delta 는 작아 합산 idf 와의 차이 무시 가능).
	async function scoreSegment(seg: SegmentStats, tokens: string[]): Promise<Map<number, number>> {
		const scores = new Map<number, number>();
		const seen = new Set<string>();
		const sids: number[] = [];
		for (const tok of tokens) {
			if (seen.has(tok)) continue;
			seen.add(tok);
			const sid = seg.stemDict[tok];
			if (sid !== undefined) sids.push(sid);
		}
		if (!sids.length) return scores;
		await Promise.all(
			sids.map(async (sid) => {
				const byteStart = seg.terms[sid * 4] ?? 0;
				const gapLen = seg.terms[sid * 4 + 1] ?? 0;
				const tfLen = seg.terms[sid * 4 + 2] ?? 0;
				const df = seg.terms[sid * 4 + 3] ?? 0;
				if (!df) return;
				const buf = await core.requestBytes({ path: seg.postingsPath, start: byteStart, len: gapLen + tfLen });
				const u8 = new Uint8Array(buf);
				const gaps = readVarints(u8, 0, df);
				const tfs = readVarints(u8, gapLen, df);
				const idf = Math.log((seg.nDocs - df + 0.5) / (df + 0.5) + 1.0);
				let docId = 0;
				for (let i = 0; i < df; i++) {
					docId += gaps[i] ?? 0; // 첫 gap=절대 docId, 이후 delta → cumsum
					const tf = tfs[i] ?? 0;
					const dl = seg.docLengths[docId] || seg.avgDocLength;
					const norm = (tf * (K1 + 1)) / (tf + K1 * (1 - B + (B * dl) / seg.avgDocLength));
					scores.set(docId, (scores.get(docId) ?? 0) + idf * norm);
				}
			})
		);
		return scores;
	}

	async function fetchHit(seg: SegmentStats, docId: number, score: number): Promise<FilingHit> {
		const o0 = Number(seg.metaOffsets[docId]);
		const o1 = Number(seg.metaOffsets[docId + 1]);
		const buf = await core.requestBytes({ path: seg.metaPath, start: o0, len: o1 - o0 });
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
	}

	async function queryFilings(input: FilingSearchQuery): Promise<FilingHit[]> {
		const text = (input.text ?? '').trim();
		if (!text) return [];
		const tokens = tokenizeBigram(text);
		if (!tokens.length) return [];
		const segs = await (segmentsP ??= loadSegments());
		const limit = Math.max(1, input.limit ?? 10);

		// 세그먼트별 독립 BM25 → 후보 (세그먼트, docId, score) 통합. 파이썬 searchContent: delta 먼저·main 병합.
		const scored = await Promise.all(segs.map((seg) => scoreSegment(seg, tokens).then((scores) => ({ seg, scores }))));
		const cands: { seg: SegmentStats; docId: number; score: number }[] = [];
		for (const { seg, scores } of scored) for (const [docId, score] of scores) if (score > 0) cands.push({ seg, docId, score });
		if (!cands.length) return [];

		// 점수 내림차순(동점이면 delta 우선 — 신규/정정본). dedup 버퍼로 top(limit*2)만 meta range fetch.
		cands.sort((a, b) => b.score - a.score || (a.seg.segment === 'delta' ? -1 : 1));
		const picked = cands.slice(0, limit * 2);
		const metas = await Promise.all(picked.map((c) => fetchHit(c.seg, c.docId, c.score)));

		// 같은 공시(rceptNo)가 main·delta 양쪽에 있으면 1건만 — 정렬상 delta/고득점이 앞서 채택(파이썬 deltaRcepts skip 근사).
		const out: FilingHit[] = [];
		const seenRcept = new Set<string>();
		for (const hit of metas) {
			if (hit.rceptNo) {
				if (seenRcept.has(hit.rceptNo)) continue;
				seenRcept.add(hit.rceptNo);
			}
			out.push(hit);
			if (out.length >= limit) break;
		}
		return out;
	}

	const companyIndexUnwired = (): never => {
		throw new Error('[search] universe/query(회사 인덱스)는 별도 feature(census A-11) — 이 경로는 미배선. queryFilings(공시 본문)만 구현됨.');
	};
	return { universe: companyIndexUnwired, query: companyIndexUnwired, queryFilings };
}
