import { describe, it, expect } from 'vitest';
import { toNum, parseNoteRows, toComposition } from './noteTableParse';

describe('toNum — DART 숫자 셀 파싱', () => {
	it('콤마·단위 제거', () => expect(toNum('2,556,130,638')).toBe(2556130638));
	it('괄호 = 음수', () => expect(toNum('(59,967,423)')).toBe(-59967423));
	it('단위어/원 제거', () => expect(toNum('1,029 천원')).toBe(1029));
	it('항목명(텍스트) = null', () => expect(toNum('원재료 및 상품매입액')).toBeNull());
	it('헤더(당분기) = null', () => expect(toNum('당분기')).toBeNull());
	it('빈/대시 = null', () => { expect(toNum('')).toBeNull(); expect(toNum('-')).toBeNull(); });
});

// 실측 005740 구조: [구분, 당분기, 전분기] 3컬럼 + 합계행
const COST_XML =
	'<TABLE><TBODY>' +
	'<TR><TD>구 분</TD><TD>당분기</TD><TD>전분기</TD></TR>' +
	'<TR><TD>원재료와 상품의 매입액</TD><TD ALIGN="RIGHT">124,452,797</TD><TD>110,000,000</TD></TR>' +
	'<TR><TD>종업원급여</TD><TD>65,836,829</TD><TD>60,000,000</TD></TR>' +
	'<TR><TD>기타비용</TD><TD>35,135,824</TD><TD>30,000,000</TD></TR>' +
	'<TR><TD>감가상각비</TD><TD>11,311,669</TD><TD>10,000,000</TD></TR>' +
	'<TR><TD>운반비</TD><TD>9,805,571</TD><TD>9,000,000</TD></TR>' +
	'<TR><TD>합 계</TD><TD>246,542,690</TD><TD>219,000,000</TD></TR>' +
	'</TBODY></TABLE>';

describe('parseNoteRows — 표 조각 → (항목,금액) 행', () => {
	it('데이터 행만 추출 (헤더·합계행 제외, 당기 컬럼)', () => {
		const rows = parseNoteRows([COST_XML]);
		const m = new Map(rows.map((r) => [r.name, r.amount]));
		expect(rows.length).toBe(5); // 구분(헤더)·합계 제외
		expect(m.get('원재료와 상품의 매입액')).toBe(124452797);
		expect(m.get('종업원급여')).toBe(65836829);
		expect(m.has('합 계')).toBe(false);
		expect(m.has('구 분')).toBe(false);
	});
	it('1컬럼 flattened(001250식: 항목 금액 항목 금액) 도 행 단위면 추출', () => {
		const xml = '<TABLE><TR><TD>공시금액</TD></TR>' +
			'<TR><TD>재화의 사용</TD><TD>1,029,785,079</TD></TR>' +
			'<TR><TD>종업원급여비용</TD><TD>17,371,656</TD></TR>' +
			'<TR><TD>감가상각비</TD><TD>3,867,984</TD></TR></TABLE>';
		const rows = parseNoteRows([xml]);
		expect(rows.length).toBe(3); // 공시금액(합계행 토큰) 제외
		expect(new Map(rows.map((r) => [r.name, r.amount])).get('재화의 사용')).toBe(1029785079);
	});
	it('조각 여러 개 병합 (당기 표 + 각주 표)', () => {
		const rows = parseNoteRows(['<TABLE><TR><TD>(단위: 원)</TD></TR></TABLE>', COST_XML, '<TABLE><TR><TD>(주1) 합산 금액</TD></TR></TABLE>']);
		expect(rows.length).toBe(5);
	});
});

describe('toComposition — 구성 비중', () => {
	it('금액 desc·비중% (원재료 ~50%)', () => {
		const comp = toComposition(parseNoteRows([COST_XML]));
		expect(comp).not.toBeNull();
		expect(comp!.items[0]!.name).toBe('원재료와 상품의 매입액');
		expect(comp!.items[0]!.pct).toBeCloseTo(50.5, 0);
		const sum = comp!.items.reduce((a, i) => a + i.pct, 0);
		expect(sum).toBeCloseTo(100, 1);
	});
	it('상위 topN + 기타 롤업', () => {
		const comp = toComposition(parseNoteRows([COST_XML]), 3);
		expect(comp!.items.length).toBe(4); // 상위3 + 기타
		expect(comp!.items[3]!.name).toMatch(/^기타 \(2\)$/);
	});
	it('유효 항목 <3 → null (비정형 → 원문 폴백)', () => {
		expect(toComposition([{ name: 'a', amount: 100 }, { name: 'b', amount: 50 }])).toBeNull();
	});
});
