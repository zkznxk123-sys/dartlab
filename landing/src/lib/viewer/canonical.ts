// panel canonical L1 TOC — 회사 챕터 드리프트를 정부표준 14 노드로 흡수 (브라우저 readWide).
//
// Python `providers/dart/panel/canonical/{canonicalData,__init__}.py` 1:1 포팅.
// DART XML 은 era 별로 챕터 III~XII 를 "II. 사업의 내용" 아래로 mis-nesting 해 chapter(SECTION-1)가
// 붕괴한다. sectionPath(전 깊이 truth)의 가장 깊은 canonical 매치 원소가 진짜 챕터 → 복원.
// 매핑 SSOT = CANONICAL_L1 (Python 운영자 수동 관리분과 동기). 미매칭은 원본 보존(honest).

export type CanonNode = readonly [id: string, label: string, keywords: readonly string[]];

// 정부표준 14 서사노드 (고정 순서 = chapter rank) + 드리프트 흡수 키워드.
export const CANONICAL_L1: readonly CanonNode[] = [
	['cover', '【 대표이사 등의 확인 】', ['대표이사']],
	['L1_company', 'I. 회사의 개요', ['회사의개요', '회사개요']],
	['L2_business', 'II. 사업의 내용', ['사업의내용']],
	// III 정부표준 하위 절 전부 — 배당·증권발행은 옛 era 가 III 모챕터 없이 top-level 로 실어 챕터로 새던 것(흡수).
	['L3_finance', 'III. 재무에 관한 사항', ['재무에관한사항', '첨부재무제표', '첨부연결재무제표', '재무제표', '요약재무', '배당에관한사항', '증권의발행']],
	['L4_mda', 'IV. 이사의 경영진단 및 분석의견', ['경영진단', '분석의견']],
	['L5_audit', 'V. 회계감사인의 감사의견 등', ['감사의견', '감사보고서', '내부회계관리', '외부감사']],
	['L6_board', 'VI. 이사회 등 회사의 기관에 관한 사항', ['이사회', '회사의기관']],
	['L7_shareholder', 'VII. 주주에 관한 사항', ['주주에관한']],
	['L8_officer', 'VIII. 임원 및 직원 등에 관한 사항', ['임원및직원', '임원·직원', '임원직원']],
	['L9_affiliate', 'IX. 계열회사 등에 관한 사항', ['계열회사']],
	['L10_related', 'X. 대주주 등과의 거래내용', ['대주주', '이해관계자']],
	['L11_investor', 'XI. 그 밖에 투자자 보호를 위하여 필요한 사항', ['투자자보호', '그밖에투자자']],
	['L12_detail', 'XII. 상세표', ['상세표']],
	['expert', '【 전문가의 확인 】', ['전문가']]
];

// canonical 라벨 → 정부 문서순서(rank). list index = rank.
export const CANONICAL_RANK: Record<string, number> = Object.fromEntries(
	CANONICAL_L1.map(([, label], i) => [label, i])
);

// 표지·서명 확인서 노드 — 보고서 본문 아닌 인증 페이지(cover=.jpg 서명, expert="해당사항 없음"). navigable TOC
// 제외하되 panel 데이터엔 보존. canonicalData.CERT_NODE_IDS 1:1.
const CERT_NODE_IDS = new Set(['cover', 'expert']);
// navigable 보고서 챕터(I~XII) 라벨 화이트리스트 — cert 제외. buildToc 가 이 집합으로 TOC 챕터를 거른다
// (표지/확인서·front-matter('')·미분류 stray 비노출). canonicalData.REPORT_CHAPTER_LABELS 1:1.
export const REPORT_CHAPTER_LABELS = new Set(
	CANONICAL_L1.filter(([id]) => !CERT_NODE_IDS.has(id)).map(([, label]) => label)
);
// chapter 가 navigable 보고서 챕터(DART I~XII)인가. EDGAR(form 챕터)는 buildToc 가 market-aware 로 별도 판정.
export function isReportChapter(chapter: string | null | undefined): boolean {
	return chapter != null && REPORT_CHAPTER_LABELS.has(chapter);
}

const SECTION_SEP = '␟'; // SECTION-N 경로 구분자 (walker._SECTION_SEP 동일)
const ROMAN_RE = /^\s*[IVXLCDM]+\s*\.\s*/; // 로마숫자 머리 ("III. ")
const WS_RE = /\s+/g; // 전 공백

// chapter/sectionPath 원소 정규화 — 로마숫자 머리 + 전 공백 제거 (키워드 매칭 축).
function norm(s: string | null | undefined): string {
	return (s ?? '').replace(ROMAN_RE, '').replace(WS_RE, '');
}

// 단일 원소(chapter/sectionPath 원소) → canonical L1 라벨 또는 null (CANONICAL_L1 순서 첫 키워드 매치).
function canonLabel(element: string | null | undefined): string | null {
	const n = norm(element);
	for (const [, label, kws] of CANONICAL_L1) {
		for (const kw of kws) {
			if (n.includes(kw.replace(WS_RE, ''))) return label;
		}
	}
	return null;
}

// 드리프트·붕괴 chapter → canonical L1 라벨. sectionPath 깊은 canonical 원소 우선 → chapter fallback → 원본.
// Python canonicalChapterExpr 1:1: sectionPath split → 원소별 canonical → drop_nulls → last(deepest) →
// (없으면) chapter 직접 매치 → (없으면) 원본 chapter(honest).
export function canonicalChapter(chapter: string | null | undefined, sectionPath: string | null | undefined): string {
	let deepest: string | null = null;
	for (const e of (sectionPath ?? '').split(SECTION_SEP)) {
		const lbl = canonLabel(e);
		if (lbl !== null) deepest = lbl; // last non-null = deepest
	}
	if (deepest !== null) return deepest;
	const fromChapter = canonLabel(chapter);
	if (fromChapter !== null) return fromChapter;
	return chapter ?? '';
}

// canonical 라벨(이미 접힌 chapter) → 정부 문서순서 rank (미등재는 null → 정렬 말미).
export function canonicalRank(label: string | null | undefined): number | null {
	if (label != null && label in CANONICAL_RANK) return CANONICAL_RANK[label];
	return null;
}
