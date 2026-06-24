// 정기보고서 주석 표 파서 — panel 파케 contentRaw(DART XML 표)를 (항목, 금액) 행으로 파싱·병합.
// 주석은 조각 테이블(헤딩·단위·당기/전기·각주)로 분리돼 있어, 데이터 행(항목명+숫자)만 골라 항목별 병합한다.
// 비용 성격별·부문 같은 *정형 숫자표*만 대상 — 우발부채/특수관계자(서술 혼합)는 파싱 폴백(원문 발췌, 별도).
// 순수 함수(렌더 0). Python 프로토타입(전 universe 실측) 동형 — 검증된 정규식 파싱.

import type { CompositionItem, NoteComposition } from '@dartlab/ui-contracts';

export interface NoteRow {
	name: string;
	amount: number; // 원 (당기 = 첫 숫자 컬럼)
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

const TOTAL_ROW = /합\s*계|총\s*계|소\s*계|공시금액|성격별\s*비용\s*합계/;

/** DART XML 표 조각들에서 (항목, 금액=첫 숫자 컬럼) 행을 파싱·항목별 병합. 합계행·헤더행·숫자명행 제외.
 * 당기/전기 분리표는 항목명으로 자연 병합(같은 이름 += , 단 분리표는 보통 같은 항목이라 첫 표 당기만 채택되도록
 * 호출측이 연결 우선 1벌만 넘기는 것을 권장 — 여기선 단순 합산이라 동일항목 중복 시 합쳐짐에 유의). */
export function parseNoteRows(contents: string[]): NoteRow[] {
	const merged = new Map<string, number>();
	for (const xml of contents) {
		const trMatches = xml.match(/<TR[^>]*>[\s\S]*?<\/TR>/gi);
		if (!trMatches) continue;
		for (const tr of trMatches) {
			const tdMatches = tr.match(/<TD[^>]*>[\s\S]*?<\/TD>/gi);
			if (!tdMatches || tdMatches.length < 2) continue;
			const cells = tdMatches.map((td) => stripTags(td.replace(/^<TD[^>]*>/i, '').replace(/<\/TD>$/i, '')));
			const name = cells[0]?.trim() ?? '';
			if (!name || toNum(name) != null) continue; // 빈/숫자 첫셀 = 데이터 항목 아님
			if (TOTAL_ROW.test(name)) continue; // 합계행 = 분모로 따로(컴포넌트 아님)
			let amount: number | null = null;
			for (let i = 1; i < cells.length; i++) {
				const c = cells[i];
				if (c == null) continue;
				amount = toNum(c);
				if (amount != null) break;
			}
			if (amount == null) continue;
			merged.set(name, (merged.get(name) ?? 0) + amount);
		}
	}
	return [...merged.entries()].map(([name, amount]) => ({ name, amount }));
}

/** (항목,금액) 행 → 구성(composition): 양수 항목만, 금액 desc, 상위 topN + '기타 (N)' 롤업, 비중% 계산.
 * 유효 항목 <3 이면 null(파싱 실패/비정형 → 호출측이 원문 발췌 폴백). */
export function toComposition(rows: NoteRow[], topN = 6): NoteComposition | null {
	const pos = rows.filter((r) => r.amount > 0);
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
