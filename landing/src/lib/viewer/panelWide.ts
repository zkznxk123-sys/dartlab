// 브라우저 readWide — panel long(flat 16-col) 하나에서 항목×기간 wide 를 온더플라이 계산.
//
// Python `panel.read.readWide` + `companyApi.buildToc/buildPanelGrid` 1:1 포팅(파생 artifact 0).
// 파이프라인: scope → anchorLatest(라벨통일) → dedupKeyed → canonicalChapter → leafSeq → collapse →
// pivot → order. 제외: alignNotes(주석 build-time 정렬·panel 이미 정렬), _stripExpr(뷰어 tag=True raw),
// SPINE 정밀정렬(v1 은 _skel blockOrder fallback). hyparquet 으로 HF panel 직접 read.

import { canonicalChapter, canonicalRank } from './canonical';
import { marketForCode, viewerUrl } from './dartUrl';
import spineData from './spineData.json';
import type { PanelBundle, PanelRow, PanelTocBlock, PanelTocChapter, PanelTocResponse, PanelTocSection } from './types';

// 정부 서식 척추(SPINE, XBRL 기반) — rowIdentity → spineOrder. Python panel.spine.SPINE 1:1 (spineBuilder 생성물).
const SPINE_ORDER = spineData as Record<string, number>;
// rowIdentity — keyed=disclosureKey / narrative=NARR::{canonicalChapter}␟{sectionLeaf} (mapper.rowIdentity 1:1).
function spineOrderFor(disclosureKey: string | null, chapter: string, sectionLeaf: string): number | null {
	const id = disclosureKey ?? `NARR::${chapter}${SEP}${sectionLeaf}`;
	return id in SPINE_ORDER ? SPINE_ORDER[id] : null;
}

// panel parquet 한 leaf 행 (필요 컬럼). 브라우저 read 컬럼 목록은 panelLoad.READ_COLUMNS.
export interface LeafRow {
	chapter: string | null;
	sectionLeaf: string | null;
	sectionPath: string | null;
	blockLeaf: string | null;
	leafType: string | null;
	disclosureKey: string | null;
	xbrlClass: string | null;
	blockOrder: number | null;
	contentRaw: string | null;
	period: string | null;
	rceptNo: string | null;
}

// scope 파생 (scopeExpr): xbrlClass 에 "_S" → standalone, else consolidated(null 포함).
function scopeOf(xbrlClass: string | null): string {
	return xbrlClass != null && xbrlClass.includes('_S') ? 'standalone' : 'consolidated';
}

// period 최신순(내림차순) — "YYYYQn" 문자열 정렬.
function sortPeriodsDesc(periods: string[]): string[] {
	return [...periods].sort((a, b) => (a < b ? 1 : a > b ? -1 : 0));
}

const SEP = '␟'; // ␟
const sectionKeyFor = (chapter: string, sectionLeaf: string): string => `${chapter}${SEP}${sectionLeaf}`;

// (첨부) 물리 재무첨부((첨부)연결재무제표·(첨부)재무제표) → 정규 재무섹션 흡수 (read.py absorbAttached 1:1).
// sectionPath(공백제거)에서 감지 → chapter→III, sectionLeaf→연결 "2."/별도 "4." (주석은 3./5.). 섹션 위치는
// 정규(XBRL) 행이 잡게 흡수행 blockOrder 를 크게 밀어 _skel 뒤로(섹션 앞으로 끌림 차단).
function absorbAttachedRow(r: LeafRow): void {
	const path = (r.sectionPath ?? '').replace(/\s+/g, '');
	if (!(path.includes('(첨부)') && path.includes('재무제표'))) return;
	const consol = path.includes('연결');
	const note = (r.sectionLeaf ?? '').includes('주석');
	r.chapter = 'III. 재무에 관한 사항';
	r.sectionLeaf = note ? (consol ? '3. 연결재무제표 주석' : '5. 재무제표 주석') : consol ? '2. 연결재무제표' : '4. 재무제표';
	if (r.blockOrder != null) r.blockOrder += 1_000_000;
}

// 섹션 번호 정렬키 — "2. …"→2, "7-1. …"→[7,1]. 번호 없으면 null(nulls_last). orderBySpine _secNum/_secSub 1:1.
function sectionNum(sectionLeaf: string): [number | null, number] {
	const m = /^\s*(\d+)/.exec(sectionLeaf);
	const sub = /^\s*\d+\s*-\s*(\d+)/.exec(sectionLeaf);
	return [m ? parseInt(m[1], 10) : null, sub ? parseInt(sub[1], 10) : 0];
}

// ── alignNotes: 옛 split 주석행(null key) → (scope,정규화제목) 표준 NT_ 정렬 (회사 own 뼈대 우선, 전역 fallback) ──
const NOTE_TITLE_NORM = /[()·\s]/g; // Python NOTE_TITLE_NORM_PATTERN
const SUFFIX_CAP = /[-–―]\s*(연결|별도)\s*$/; // native 접미사 scope
const SUFFIX_STRIP = /\s*[-–―]\s*(연결|별도)\s*$/; // 접미사 제거

function alignNotes(rows: LeafRow[], noteTaxonomy: Record<string, string>): void {
	const meta = rows.map((r) => {
		const bl = r.blockLeaf ?? '';
		const m = bl.match(SUFFIX_CAP);
		const suf = m ? m[1] : null;
		const bare = bl.replace(SUFFIX_STRIP, '');
		const secMark = (r.chapter ?? '') + (r.sectionLeaf ?? '');
		const scope = suf === '연결' ? 'consolidated' : suf === '별도' ? 'standalone' : secMark.includes('연결') ? 'consolidated' : 'standalone';
		const title = bare.replace(NOTE_TITLE_NORM, '');
		return { key: scope + '|' + title, titleLen: [...title].length, isNote: (r.sectionLeaf ?? '').includes('주석') };
	});
	// 자기 native NT_ 주석 뼈대 — ownStd(_U 제외 표준) + own(전체, fallback). 첫 등장 우선.
	const ownStd = new Map<string, string>();
	const own = new Map<string, string>();
	for (let i = 0; i < rows.length; i++) {
		const dk = rows[i].disclosureKey;
		if (dk == null || !dk.startsWith('NT_') || meta[i].titleLen <= 1) continue;
		const k = meta[i].key;
		if (!own.has(k)) own.set(k, dk);
		if (!dk.includes('_U') && !ownStd.has(k)) ownStd.set(k, dk);
	}
	// 부여 — Python when/then 순서: 주석&표준 → 표준 / 기존키 보존 / 주석&own / 주석&전역.
	for (let i = 0; i < rows.length; i++) {
		const r = rows[i];
		const { key, isNote } = meta[i];
		if (isNote && ownStd.has(key)) r.disclosureKey = ownStd.get(key)!;
		else if (r.disclosureKey != null) continue;
		else if (isNote && own.has(key)) r.disclosureKey = own.get(key)!;
		else if (isNote && noteTaxonomy[key] != null) r.disclosureKey = noteTaxonomy[key];
	}
}

// ── anchorLatest: scope era-안정 + keyed 라벨 최신통일 (narrative 보존) ──
function anchorLatest(rows: LeafRow[]): void {
	// scope 부착.
	for (const r of rows) (r as LeafRow & { scope: string }).scope = scopeOf(r.xbrlClass);
	const anchorKey = (r: LeafRow) => r.disclosureKey ?? r.xbrlClass;

	// scope era-안정 — anchorKey & xbrlClass 보유 행의 최신 period scope 를 같은 anchorKey 전 era 에 전파.
	const scopeByAnchor = new Map<string, { period: string; scope: string }>();
	for (const r of rows) {
		const ak = anchorKey(r);
		if (ak == null || r.xbrlClass == null) continue;
		const cur = scopeByAnchor.get(ak);
		const p = r.period ?? '';
		if (!cur || p > cur.period) scopeByAnchor.set(ak, { period: p, scope: scopeOf(r.xbrlClass) });
	}
	for (const r of rows) {
		const ak = anchorKey(r);
		if (ak != null) {
			const s = scopeByAnchor.get(ak);
			if (s) (r as LeafRow & { scope: string }).scope = s.scope;
		}
	}

	// keyed 라벨 통일 — (anchorKey, scope) 최신 period 라벨. 같은 period 면 (첨부) 먼저 → canonical 채택.
	type Label = { chapter: string | null; sectionLeaf: string | null; blockLeaf: string | null };
	const labelByGroup = new Map<string, { period: string; attach: boolean; label: Label }>();
	for (const r of rows) {
		const ak = anchorKey(r);
		if (ak == null) continue;
		const scope = (r as LeafRow & { scope: string }).scope;
		const gk = ak + SEP + scope;
		const p = r.period ?? '';
		const attach = (r.chapter ?? '').includes('(첨부)');
		const cur = labelByGroup.get(gk);
		// sort period asc + attach 먼저(desc) → last = (최신 period, 비첨부). 즉 최신 우선, 동 period 면 비첨부.
		const better = !cur || p > cur.period || (p === cur.period && cur.attach && !attach);
		if (better) labelByGroup.set(gk, { period: p, attach, label: { chapter: r.chapter, sectionLeaf: r.sectionLeaf, blockLeaf: r.blockLeaf } });
	}
	for (const r of rows) {
		const ak = anchorKey(r);
		if (ak == null) continue;
		const scope = (r as LeafRow & { scope: string }).scope;
		const g = labelByGroup.get(ak + SEP + scope);
		if (g) {
			if (g.label.chapter != null) r.chapter = g.label.chapter;
			if (g.label.sectionLeaf != null) r.sectionLeaf = g.label.sectionLeaf;
			if (g.label.blockLeaf != null) r.blockLeaf = g.label.blockLeaf;
		}
	}
}

// ── dedupKeyed: keyed 행 (disclosureKey,scope,leafType,period) 당 1개 (xbrlClass 있음·긴 본문 우선) ──
function dedupKeyed(rows: LeafRow[]): LeafRow[] {
	const seen = new Map<string, LeafRow>();
	const out: LeafRow[] = [];
	for (const r of rows) {
		if (r.disclosureKey == null) {
			out.push(r); // narrative 보존
			continue;
		}
		const scope = (r as LeafRow & { scope: string }).scope;
		const k = [r.disclosureKey, scope, r.leafType ?? '', r.period ?? ''].join(SEP);
		const prev = seen.get(k);
		if (!prev) {
			seen.set(k, r);
			out.push(r);
			continue;
		}
		// 우선: xbrlClass 있음 > 없음, 그다음 본문 길이.
		const score = (x: LeafRow) => [x.xbrlClass != null ? 1 : 0, (x.contentRaw ?? '').length];
		const [pa, pb] = score(prev);
		const [ca, cb] = score(r);
		if (ca > pa || (ca === pa && cb > pb)) {
			const idx = out.indexOf(prev);
			if (idx >= 0) out[idx] = r;
			seen.set(k, r);
		}
	}
	return out;
}

// ── 핵심: leaf 행들 → PanelBundle (순수, 로컬 parity 테스트 가능) ──
export function buildPanelBundle(
	leafRows: LeafRow[],
	opts: { code: string; corpName?: string; noteTaxonomy?: Record<string, string> }
): PanelBundle {
	const rows = leafRows.slice(); // 빈 content 도 leafSeq 랭킹·뼈대에 포함 (Python readWide 와 동일, 빈셀은 출력서 제외)
	const market = marketForCode(opts.code);
	const empty: PanelBundle = {
		stockCode: opts.code,
		corpName: opts.corpName ?? '',
		toc: { stockCode: opts.code, corpName: opts.corpName ?? '', chapters: [], periods: [] },
		periods: [],
		gridBySection: new Map(),
		dartUrlByPeriod: {}
	};
	if (rows.length === 0) return empty;

	// corpName — panel 에 회사명 컬럼 없음(corp=코드). opt 로만 주입, 없으면 빈값(라우트가 코드로 표기).
	const corpName = opts.corpName ?? '';

	alignNotes(rows, opts.noteTaxonomy ?? {});
	anchorLatest(rows);
	const deduped = dedupKeyed(rows);

	// canonicalChapter (sectionPath 깊은 canonical 원소 우선) + (첨부) 물리 재무첨부 흡수.
	for (const r of deduped) {
		r.chapter = canonicalChapter(r.chapter, r.sectionPath);
		absorbAttachedRow(r);
	}

	// leafSeq — narrative(disclosureKey null) 는 (chapter,sectionLeaf,leafType,period) 내 blockOrder ordinal rank, keyed=0.
	const seqGroups = new Map<string, LeafRow[]>();
	for (const r of deduped) {
		if (r.disclosureKey != null) {
			(r as LeafRow & { leafSeq: number }).leafSeq = 0;
			continue;
		}
		const gk = [r.chapter ?? '', r.sectionLeaf ?? '', r.leafType ?? '', r.period ?? ''].join(SEP);
		let arr = seqGroups.get(gk);
		if (!arr) seqGroups.set(gk, (arr = []));
		arr.push(r);
	}
	for (const arr of seqGroups.values()) {
		arr.sort((a, b) => (a.blockOrder ?? 0) - (b.blockOrder ?? 0));
		arr.forEach((r, i) => ((r as LeafRow & { leafSeq: number }).leafSeq = i + 1));
	}

	// collapse — indexKey(=[chapter,sectionLeaf,blockLeaf,leafType,disclosureKey,scope,leafSeq]) × period.
	interface Agg {
		chapter: string; sectionLeaf: string; blockLeaf: string; leafType: string;
		disclosureKey: string | null; scope: string | null; leafSeq: number;
		cellParts: Map<string, { bo: number; text: string }[]>; // period → leaves
	}
	const aggs = new Map<string, Agg>();
	const periodSet = new Set<string>();
	for (const r of deduped) {
		const scope = (r as LeafRow & { scope: string }).scope;
		const leafSeq = (r as LeafRow & { leafSeq: number }).leafSeq;
		const chapter = r.chapter ?? '';
		const sectionLeaf = r.sectionLeaf ?? '';
		const blockLeaf = r.blockLeaf ?? '';
		const leafType = r.leafType ?? '';
		const period = r.period ?? '';
		periodSet.add(period);
		const ik = [chapter, sectionLeaf, blockLeaf, leafType, r.disclosureKey ?? ' ', scope ?? '', leafSeq].join(SEP);
		let a = aggs.get(ik);
		if (!a) aggs.set(ik, (a = { chapter, sectionLeaf, blockLeaf, leafType, disclosureKey: r.disclosureKey, scope, leafSeq, cellParts: new Map() }));
		let parts = a.cellParts.get(period);
		if (!parts) a.cellParts.set(period, (parts = []));
		parts.push({ bo: r.blockOrder ?? 0, text: r.contentRaw ?? '' });
	}

	const periods = sortPeriodsDesc([...periodSet]);
	const q4 = periods.filter((p) => p.endsWith('Q4'));
	const latestP = (q4.length ? q4 : periods).reduce((m, p) => (p > m ? p : m), '');

	// 각 agg → cells(join by blockOrder) + skeleton(_skel=latestP _bo, _skelOld=마지막 period _bo).
	interface Built extends Agg { cells: Record<string, string>; skel: number | null; skelOld: number | null; canonRank: number | null; spOrder: number | null; secNum: number | null; secSub: number; }
	const built: Built[] = [];
	for (const a of aggs.values()) {
		const cells: Record<string, string> = {};
		let skel: number | null = null;
		let skelOld: number | null = null;
		let lastPeriodSeen = '';
		const periodKeys = [...a.cellParts.keys()].sort();
		for (const p of periodKeys) {
			const parts = a.cellParts.get(p)!.slice().sort((x, y) => x.bo - y.bo);
			const joined = parts.map((x) => x.text).join('');
			if (joined) cells[p] = joined; // 빈셀 제외(serializePanelRows 동일)
			const minBo = parts.reduce((m, x) => Math.min(m, x.bo), Infinity);
			if (p === latestP) skel = minBo;
			if (p >= lastPeriodSeen) { lastPeriodSeen = p; skelOld = minBo; } // 마지막(최대) period 의 _bo
		}
		const [secNum, secSub] = sectionNum(a.sectionLeaf);
		built.push({
			...a,
			cells,
			skel,
			skelOld,
			canonRank: canonicalRank(a.chapter),
			spOrder: spineOrderFor(a.disclosureKey, a.chapter, a.sectionLeaf),
			secNum,
			secSub
		});
	}

	// order — [_canonRank, _secNum(절 번호), _secSub, _spOrder(XBRL 척추), _skel, _skelOld, leafSeq] nulls_last (orderBySpine 1:1).
	const nl = (v: number | null) => (v == null ? Infinity : v);
	built.sort((x, y) =>
		nl(x.canonRank) - nl(y.canonRank) ||
		nl(x.secNum) - nl(y.secNum) ||
		x.secSub - y.secSub ||
		nl(x.spOrder) - nl(y.spOrder) ||
		nl(x.skel) - nl(y.skel) ||
		nl(x.skelOld) - nl(y.skelOld) ||
		x.leafSeq - y.leafSeq
	);

	// PanelRow + gridBySection (빈셀 행 제외 = serializePanelRows 동일).
	const gridBySection = new Map<string, PanelRow[]>();
	for (const b of built) {
		if (Object.keys(b.cells).length === 0) continue; // 본문 0 행 skip
		const row: PanelRow = {
			chapter: b.chapter,
			sectionLeaf: b.sectionLeaf,
			blockLeaf: b.blockLeaf,
			disclosureKey: b.disclosureKey,
			scope: b.scope,
			blockType: Object.values(b.cells).some((v) => v.includes('<TABLE')) ? 'table' : 'text',
			cells: b.cells
		};
		const sk = sectionKeyFor(b.chapter, b.sectionLeaf);
		let arr = gridBySection.get(sk);
		if (!arr) gridBySection.set(sk, (arr = []));
		arr.push(row);
	}

	const toc = buildToc(opts.code, corpName, built, periods);

	// dartUrlByPeriod — period 별 첫 rceptNo (leafRows 원본).
	const rceptByPeriod = new Map<string, string>();
	for (const r of leafRows) {
		if (r.period && r.rceptNo && !rceptByPeriod.has(r.period)) rceptByPeriod.set(r.period, r.rceptNo);
	}
	const dartUrlByPeriod: Record<string, string | null> = {};
	for (const p of periods) dartUrlByPeriod[p] = viewerUrl(market, rceptByPeriod.get(p) ?? null);

	return { stockCode: opts.code, corpName, toc, periods, gridBySection, dartUrlByPeriod };
}

// TOC — chapter > sectionLeaf > blockLeaf 트리 (정렬된 built 순서 first-appearance). buildToc 1:1.
function buildToc(
	code: string,
	corpName: string,
	built: { chapter: string; sectionLeaf: string; blockLeaf: string }[],
	periods: string[]
): PanelTocResponse {
	const order: string[] = []; // chapter first-appearance
	const chMap = new Map<string, PanelTocChapter>();
	const secMap = new Map<string, PanelTocSection>();
	for (const b of built) {
		const chapter = b.chapter;
		if (!chapter) continue;
		let ch = chMap.get(chapter);
		if (!ch) { ch = { chapter, sections: [] }; chMap.set(chapter, ch); order.push(chapter); }
		const sectionLeaf = b.sectionLeaf;
		if (!sectionLeaf || sectionLeaf === chapter) continue; // 빈 절/chapter 헤더 행 제외
		const sk = sectionKeyFor(chapter, sectionLeaf);
		let sec = secMap.get(sk);
		if (!sec) { sec = { sectionLeaf, sectionKey: sk, rowCount: 0, blocks: [] }; secMap.set(sk, sec); ch.sections.push(sec); }
		sec.rowCount++;
		const blockLeaf = b.blockLeaf;
		if (!blockLeaf) continue; // narrative anchor 행(blockLeaf 없음) 은 chip 제외
		const block: PanelTocBlock | undefined = sec.blocks.find((x) => x.blockLeaf === blockLeaf);
		if (block) block.rowCount++;
		else sec.blocks.push({ blockLeaf, rowCount: 1 });
	}
	// 섹션 ≥1 인 chapter 만 (Python buildToc `if sections:`).
	const chapters = order.map((c) => chMap.get(c)!).filter((ch) => ch.sections.length > 0);
	return { stockCode: code, corpName, chapters, periods };
}
