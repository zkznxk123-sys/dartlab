// sectionKey ({chapter}␟{sectionLeaf}) — 동명 sectionLeaf 의 chapter 간 충돌 방지.
// Python `companyApi.sectionKeyFor`/`splitSectionKey` 1:1.

const SEP = '␟';

export function sectionKeyFor(chapter: string, sectionLeaf: string): string {
	return `${chapter}${SEP}${sectionLeaf}`;
}

export function splitSectionKey(sectionKey: string): [string | null, string] {
	const i = sectionKey.indexOf(SEP);
	if (i >= 0) return [sectionKey.slice(0, i), sectionKey.slice(i + 1)];
	return [null, sectionKey];
}
