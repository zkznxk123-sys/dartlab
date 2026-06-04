// 공시뷰어 공유 키/상수 — pipeline·toc·orchestrator 공통 단일 출처(순환참조 방지).

import spineData from './spineData.json';

export const SEP = '␟'; // rowIdentity/sectionKey 구분자 (Python ␟)
export const sectionKeyFor = (chapter: string, sectionLeaf: string): string => `${chapter}${SEP}${sectionLeaf}`;

// 정부 서식 척추(SPINE, XBRL 기반) — rowIdentity → spineOrder. Python panel.spine.SPINE 1:1 (spineBuilder 생성물).
export const SPINE_ORDER = spineData as Record<string, number>;

// rowIdentity — keyed=disclosureKey / narrative=NARR::{canonicalChapter}␟{sectionLeaf} (mapper.rowIdentity 1:1).
export function spineOrderFor(disclosureKey: string | null, chapter: string, sectionLeaf: string): number | null {
	const id = disclosureKey ?? `NARR::${chapter}${SEP}${sectionLeaf}`;
	return id in SPINE_ORDER ? SPINE_ORDER[id] : null;
}

// 제목 정규화 — 괄호·중점·공백 제거 (Python NOTE_TITLE_NORM_PATTERN). alignNotes·narrativeCore 공통.
export const NOTE_TITLE_NORM = /[()·\s]/g;
