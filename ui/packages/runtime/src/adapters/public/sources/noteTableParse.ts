// 정기보고서 주석 표 파서 — panel 파케 contentRaw(DART XML 표)를 (항목, 금액) 행으로 파싱·병합.
// 주석은 조각 테이블(헤딩·단위·당기/전기·각주)로 분리돼 있어, 데이터 행(항목명+숫자)만 골라 항목별 병합한다.
// 비용 성격별·부문 같은 *정형 숫자표*만 대상 — 우발부채/특수관계자(서술 혼합)는 파싱 폴백(원문 발췌, 별도).
// 순수 함수(렌더 0). Python 프로토타입(전 universe 실측) 동형 — 검증된 정규식 파싱.
// 정확성 4가지(전 universe 실측): ① <TD>·<TE>(XBRL 태깅) 셀 모두, ② 당기 블록만(전기/전분기 마커 전까지 —
// currentPeriodTables), ③ 라벨 총계행 + signed-sum 구조적 총계 제거(계(*)·총영업비용 등 라벨 누락 방어),
// ④ 단위(백만원/천원/억원) 검출 → 원 환산.

import type { CompositionItem, NoteComposition } from '@dartlab/ui-contracts';

export interface NoteRow {
	name: string;
	amount: number; // 당기 = 첫 숫자 컬럼 (원 환산 전 raw — 호출측이 detectUnitMult 곱해 원으로)
}

const stripTags = (s: string): string =>
	(s || '')
		.replace(/<[^>]+>/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();

// '2,556,130,638' → 2556130638 · '(59,967,423)' → -59967423(괄호=음수) · 단위어/공백 제거.
// 숫자가 아니면 null(항목명·헤더 셀 구분용).
export function toNum(raw: string): number | null {
	const x = (raw || '').trim();
	const neg = x.startsWith('(') && x.endsWith(')');
	const cleaned = x.replace(/[(),원천백만\s%]/g, '');
	if (!/^-?\d+$/.test(cleaned)) return null;
	const v = Number(cleaned);
	if (!Number.isFinite(v)) return null;
	return neg ? -v : v;
}

// 라벨로 잡는 총계/헤더행 — '합계/총계/소계/공시금액/성격별 비용/총 영업비용', 그리고 바닥 '계'·'계(*)'(삼성 등).
// (라벨 누락 총계는 dropTotals 의 구조적 검출이 추가로 방어)
const TOTAL_ROW = /합\s*계|총\s*계|소\s*계|공시금액|성격별\s*비용|영업비용|^계(?:\s|\(|\*|$)/;

// '전기/전분기/전반기' 비교기간 마커(짧은 라벨, 숫자 없음) — 당기 블록 끝 경계.
const PRIOR_MARKER = /^전\s*(기|분기|반기)/;

/** 단위어 → 원 환산 배수. 표 머리 '(단위 : 백만원)' 류에서 검출(대부분 백만원, 일부 천원). 미검출 = 백만원(최빈) 기본. */
export function detectUnitMult(texts: string[]): number {
	for (const t of texts) {
		const m = (t || '').match(/단위\s*[:：]?\s*([십백천만억]*\s*원)/);
		if (m && m[1]) {
			const u = m[1].replace(/\s/g, '');
			if (u.includes('십억')) return 1e9;
			if (u.includes('백만')) return 1e6;
			if (u.includes('억')) return 1e8;
			if (u.includes('천')) return 1e3;
			return 1; // '원'
		}
	}
	return 1e6; // 백만원 최빈 기본
}

/** 문서순 프래그먼트(text/table 혼재)에서 *당기 블록* 의 table contentRaw 만 — 첫 '전기/전분기' 마커 프래그먼트
 * 전까지. DART 주석은 당기표 → '전기(단위:...)' 라벨 → 전기표 순. 마커 전까지만 모아 당기/전기 혼입을 막는다.
 * 마커는 짧은 라벨(<25자·4자리 숫자 없음)로 식별 — 데이터 행이 든 표(숫자 큼)는 마커로 오인하지 않는다. */
export function currentPeriodTables(frags: { leafType: string; contentRaw: string }[]): string[] {
	const out: string[] = [];
	for (const f of frags) {
		const plain = stripTags(f.contentRaw);
		if (PRIOR_MARKER.test(plain) && plain.length < 25 && !/\d{4,}/.test(plain)) break;
		if (f.leafType === 'table') out.push(f.contentRaw);
	}
	return out;
}

/** DART XML 표 조각들에서 (항목, 금액=첫 숫자 컬럼) 행을 파싱. 합계행(라벨)·헤더행·숫자명행 제외, 음수 유지
 * (구조적 총계검출용). 같은 항목명 중복 시 first-wins(당기 블록은 보통 1표 — 호출측이 currentPeriodTables 로
 * 당기만 넘기는 것을 권장). */
export function parseNoteRows(contents: string[]): NoteRow[] {
	const merged = new Map<string, number>();
	for (const xml of contents) {
		const trMatches = xml.match(/<TR[^>]*>[\s\S]*?<\/TR>/gi);
		if (!trMatches) continue;
		for (const tr of trMatches) {
			// DART XML 셀 = <TD>(평문) 또는 <TE>(XBRL 태깅 — 삼성 등 대형사 다수). 둘 다 매칭. <TH>(헤더)는 제외.
			const cellMatches = tr.match(/<T[DE][^>]*>[\s\S]*?<\/T[DE]>/gi);
			if (!cellMatches || cellMatches.length < 2) continue;
			const cells = cellMatches.map((c) => stripTags(c.replace(/^<T[DE][^>]*>/i, '').replace(/<\/T[DE]>$/i, '')));
			const name = cells[0]?.trim() ?? '';
			if (!name || toNum(name) != null) continue; // 빈/숫자 첫셀 = 데이터 항목 아님
			if (TOTAL_ROW.test(name)) continue; // 라벨 총계행 = 분모로 따로(컴포넌트 아님)
			if (merged.has(name)) continue; // first-wins (당기 블록 중복 표 방어)
			let amount: number | null = null;
			for (let i = 1; i < cells.length; i++) {
				const c = cells[i];
				if (c == null) continue;
				amount = toNum(c);
				if (amount != null) break;
			}
			if (amount == null) continue;
			merged.set(name, amount);
		}
	}
	return [...merged.entries()].map(([name, amount]) => ({ name, amount }));
}

/** 라벨로 안 잡힌 총계행 구조적 제거 — 절댓값 최댓값 행이 *나머지 signed 합* 과 0.5% 이내로 같으면 = 총계
 * (총계는 정의상 컴포넌트 합과 정확히 일치 → 잔차 ~0%; 실 컴포넌트는 ~50% 라도 잔차가 큼). 반복(중첩 소계).
 * signed 합이라 LG화학 '총 영업비용'=양수합−재고변동(음수) 같은 케이스도 정확히 잡힌다. */
export function dropTotals(rows: NoteRow[]): NoteRow[] {
	let items = rows.slice();
	for (let pass = 0; pass < 3 && items.length >= 3; pass++) {
		let mi = 0;
		for (let i = 1; i < items.length; i++) if (Math.abs(items[i]!.amount) > Math.abs(items[mi]!.amount)) mi = i;
		const mv = items[mi]!.amount;
		let rest = 0;
		for (let i = 0; i < items.length; i++) if (i !== mi) rest += items[i]!.amount;
		if (mv !== 0 && Math.abs(mv - rest) / Math.abs(mv) < 0.005) {
			items = items.filter((_, i) => i !== mi);
		} else break;
	}
	return items;
}

// ── 비용 성격별 정제·분류 — panel 블록 오라벨(자본구조·손익소계가 비용블록에 섞임)과 회사별 라인 변경에 강건. ──
// 의미 카테고리 버킷 — 이름 변경·조각화에 안정(상품↔소모품, 와↔및, 각주꼬리 흡수, 급여+퇴직+복리 = 인건비).
// 미매칭 산업특수 라인(구입전력비·망접속비 등)은 자기명칭 유지(passthrough) — 의미 버킷팅으로 안 묻음.
const COST_CANON: [RegExp, string][] = [
	[/원재료|부재료|재료|소모품|상품|매입|저장품/, '원재료·상품'],
	[/급여|상여|임금|인건|노무|종업원|퇴직|복리후생/, '인건비'],
	[/감가상각|상각/, '감가상각'],
	[/운반|화물|물류|하역|보관|용선|운송/, '운반·물류'],
	[/광고|선전|판촉|마케팅/, '광고·판촉'],
	[/지급수수료|수수료|용역|외주|가공|협력|위탁/, '용역·수수료']
];
export const COST_SEMANTIC_LABELS = new Set<string>([...COST_CANON.map(([, l]) => l), '기타']);

// 비용 아님 — 자본구조·손익계산서 소계·지분법·수익인식 문구·날짜. panel 블록 오라벨로 섞여든 비-비용 행 하드 드롭.
const NON_COST = /수권주식|발행주식|주당금액|자본금|주식수|액면|법인세|차감전|순이익|순손익|계속사업|세전|총포괄|매출액|매출총이익|당기순|영업이익|영업손익|지분법|수행의무|시점에이행|기간에걸쳐/;
// 재고·재공품 변동 = 원가 타이밍 조정(지출 아님) — composition 제외(단 dropTotals signed 검출엔 유지하려 parse 단계엔 남김).
const INVENTORY = /재고자산.*변동|재공품|제품.*변동|재고.*증감|미착품/;

const normName = (name: string): string => name.replace(/\([^)]*\)/g, '').replace(/\s+/g, '');

function isNonCost(name: string): boolean {
	return NON_COST.test(name.replace(/\s+/g, '')) || /^\d{4}[.\-/]/.test(name.trim());
}

/** 비용 라인 형태인가 — canon 버킷 매치 OR 비용성 접미사(비/료/금/액/과) OR '비용' 포함 OR 기타류. 아니면 드롭(잡음 방어). */
export function isCostPlausible(name: string): boolean {
	const n = normName(name);
	if (!n || n.length > 24) return false;
	if (/^(기타|잡비|잡손실)/.test(n)) return true;
	if (COST_CANON.some(([re]) => re.test(n))) return true;
	return /[비료금액과]$/.test(n) || n.includes('비용');
}

/** 비용 성격별 라인 → 그룹 키. 의미 버킷(인건비·감가상각 등) 매치면 라벨, 미매칭 산업특수는 공백제거 키(passthrough), 기타류 → '기타'. */
export function costCategory(name: string): string {
	const n = normName(name);
	if (/^(기타|잡비|잡손실)/.test(n)) return '기타';
	for (const [re, label] of COST_CANON) if (re.test(n)) return label;
	return n; // passthrough 키(공백제거) — 표시명은 호출측이 원본 latest 로
}

/** parseNoteRows 결과 → 비용 composition 입력으로 정제: 비-비용 하드드롭 → 구조적 총계 제거 → 양수·재고제외·비용형태만. */
export function cleanCostRows(rows: NoteRow[]): NoteRow[] {
	const base = rows.filter((r) => !isNonCost(r.name)); // 자본/손익소계 드롭(총계검출 왜곡 방지)
	const clean = dropTotals(base);
	return clean.filter((r) => r.amount > 0 && !INVENTORY.test(normName(r.name)) && isCostPlausible(r.name));
}

/** (항목,금액) 행 → 비용 구성(composition): cleanCostRows 정제 후 금액 desc, 상위 topN + '기타 (N)' 롤업, 비중%.
 * 유효 비용 항목 <3 이면 null(파싱 실패/비정형 → 호출측이 원문 발췌 폴백). 항목명은 원본 유지(스냅샷 정밀 디테일). */
export function toComposition(rows: NoteRow[], topN = 6): NoteComposition | null {
	const pos = cleanCostRows(rows);
	if (pos.length < 3) return null;
	const total = pos.reduce((a, r) => a + r.amount, 0);
	if (total <= 0) return null;
	const sorted = [...pos].sort((a, b) => b.amount - a.amount);
	const top = sorted.slice(0, topN);
	const rest = sorted.slice(topN);
	const items: CompositionItem[] = top.map((r) => ({ name: r.name, amount: r.amount, pct: (r.amount / total) * 100 }));
	if (rest.length) {
		const restAmt = rest.reduce((a, r) => a + r.amount, 0);
		items.push({ name: `기타 (${rest.length})`, amount: restAmt, pct: (restAmt / total) * 100 });
	}
	return { items, total };
}
