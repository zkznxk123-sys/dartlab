// anchorNarrativeToSpine — narrative 섹션 라벨을 SPINE(최신 필링 골격=핵) 등재 라벨로 통일. Python read 1:1.
// anchorLatest 가 keyed 만 통일하므로 narrative(배당·증권·기타재무) era 변종("6.배당" vs "6.배당 등", 옛 "6.기타재무"
// vs 현행 "8.기타재무")이 잔존 → 같은 chapter·제목코어의 SPINE 등재 라벨로 덮어써 통일(화이트리스트 bounded, 자유 fuzzy 0).

import { NOTE_TITLE_NORM, SEP, SPINE_ORDER } from '../keys';
import type { LeafRow } from '../types';

const NARR_NUM_RE = /^\s*\d+(-\d+)?\.?\s*/; // 선행 절 번호
const NARR_ETC_RE = /\s*등\s*$/; // 후행 '등'(era 변종)

export function narrativeCore(leaf: string): string {
	return (leaf ?? '').replace(NARR_NUM_RE, '').trim().replace(NARR_ETC_RE, '').replace(NOTE_TITLE_NORM, '');
}

// SPINE_ORDER 키(NARR::{chapter}␟{sectionLeaf})에서 {chapter␟코어 → 정식 sectionLeaf} 룩업 (첫 등장 우선).
const SPINE_NARR_MAP: Record<string, string> = (() => {
	const m: Record<string, string> = {};
	for (const ident of Object.keys(SPINE_ORDER)) {
		if (!ident.startsWith('NARR::')) continue;
		const body = ident.slice('NARR::'.length);
		const i = body.indexOf(SEP);
		if (i < 0) continue;
		const chap = body.slice(0, i);
		const leaf = body.slice(i + 1);
		const key = `${chap}${SEP}${narrativeCore(leaf)}`;
		if (!(key in m)) m[key] = leaf;
	}
	return m;
})();

export function anchorNarrativeToSpineRow(r: LeafRow): void {
	if (r.disclosureKey != null) return; // keyed 불변 (anchorLatest 담당)
	const canon = SPINE_NARR_MAP[`${r.chapter ?? ''}${SEP}${narrativeCore(r.sectionLeaf ?? '')}`];
	if (canon != null) r.sectionLeaf = canon;
}
