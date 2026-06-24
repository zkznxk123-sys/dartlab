import { describe, it, expect } from 'vitest';
import { toNum, parseNoteRows, toComposition, dropTotals, detectUnitMult, currentPeriodTables, isCostPlausible, costCategory, cleanCostRows } from './noteTableParse';

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
	it('같은 항목 중복 표 = first-wins (중복 합산 안 함)', () => {
		const rows = parseNoteRows([COST_XML, COST_XML]); // 동일 표 2번
		expect(new Map(rows.map((r) => [r.name, r.amount])).get('종업원급여')).toBe(65836829); // 2배 아님
	});
	// 삼성 등 XBRL 태깅 — 셀이 <TD> 아닌 <TE>, 총계행='성격별 비용'(실측 005930), 재고변동(음수)
	const TE_XML =
		'<TABLE><THEAD><TR><TH>　</TH><TH>공시금액</TH></TR></THEAD><TBODY>' +
		'<TR><TE COLSPAN="2">성격별 비용</TE><TE ALIGN="RIGHT">76,640,647</TE></TR>' +
		'<TR><TE>제품과 재공품의 감소(증가)</TE><TE>(2,633,697)</TE></TR>' +
		'<TR><TE>원재료 등의 사용액 및 상품 매입액</TE><TE>40,000,000</TE></TR>' +
		'<TR><TE>종업원급여</TE><TE>15,000,000</TE></TR>' +
		'<TR><TE>감가상각비</TE><TE>12,000,000</TE></TR></TBODY></TABLE>';
	it('XBRL <TE> 셀 + 성격별 비용 총계행 제외 + 음수항목(재고)은 보존(파싱)·composition 제외', () => {
		const rows = parseNoteRows([TE_XML]);
		const m = new Map(rows.map((r) => [r.name, r.amount]));
		expect(m.has('성격별 비용')).toBe(false);
		expect(m.get('제품과 재공품의 감소(증가)')).toBe(-2633697); // 음수 보존(dropTotals signed 검출용)
		expect(m.get('원재료 등의 사용액 및 상품 매입액')).toBe(40000000);
		const comp = toComposition(rows);
		expect(comp).not.toBeNull();
		expect(comp!.items[0]!.name).toBe('원재료 등의 사용액 및 상품 매입액'); // 음수 재고변동 제외, 원재료 최대
	});
});

describe('dropTotals — 라벨 안 걸린 총계 구조적 제거 (signed-sum ~0%)', () => {
	it("'총 영업비용'식 미라벨 총계(=양수합−재고변동) 제거", () => {
		// LG화학 실측 구조: 재고변동(음수) + 컴포넌트 + 총영업비용(=정확한 signed 합)
		const rows = [
			{ name: '제품과 재공품의 변동', amount: -653750 },
			{ name: '원재료와 소모품의 사용', amount: 5116987 },
			{ name: '종업원급여', amount: 1386137 },
			{ name: '기타 비용', amount: 2660327 },
			{ name: '영업비용계', amount: 5116987 - 653750 + 1386137 + 2660327 } // = 8509701 (정확한 합)
		];
		const clean = dropTotals(rows);
		expect(clean.find((r) => r.name === '영업비용계')).toBeUndefined();
		expect(clean.length).toBe(4);
	});
	it('~50% 인 실 컴포넌트는 오검출 안 함 (잔차 0.5% 초과)', () => {
		// COST_XML: 원재료 50.5% (잔차 1.9% > 0.5%) — 총계로 오인하면 안 됨
		const rows = parseNoteRows([COST_XML]);
		const clean = dropTotals(rows);
		expect(clean.find((r) => r.name === '원재료와 상품의 매입액')).toBeDefined();
		expect(clean.length).toBe(5);
	});
});

describe('detectUnitMult — 단위 검출', () => {
	it('백만원 → 1e6', () => expect(detectUnitMult(['<TD>비용의 성격별 분류 (단위 : 백만원)</TD>'])).toBe(1e6));
	it('천원 → 1e3 (셀트리온식)', () => expect(detectUnitMult(['(단위 : 천원)'])).toBe(1e3));
	it('억원 → 1e8', () => expect(detectUnitMult(['단위 억원'])).toBe(1e8));
	it('미검출 = 백만원 기본', () => expect(detectUnitMult(['<TD>원재료</TD>'])).toBe(1e6));
});

describe('currentPeriodTables — 당기 블록만(전기 마커 전까지)', () => {
	it('당기표 모으고 전분기 마커에서 중단(전기표 제외)', () => {
		const frags = [
			{ leafType: 'text', contentRaw: '<TD>비용의 성격별 분류 당분기 (단위 : 백만원)</TD>' },
			{ leafType: 'table', contentRaw: COST_XML }, // 당기
			{ leafType: 'text', contentRaw: '<TD>전분기 (단위 : 백만원)</TD>' }, // 마커 → 중단
			{ leafType: 'table', contentRaw: COST_XML } // 전기 — 제외돼야
		];
		expect(currentPeriodTables(frags).length).toBe(1);
	});
	it('전기 마커 없으면 전 table (단일기간/통합표)', () => {
		const frags = [
			{ leafType: 'table', contentRaw: COST_XML },
			{ leafType: 'text', contentRaw: '<TD>(*) 주석 설명</TD>' }
		];
		expect(currentPeriodTables(frags).length).toBe(1);
	});
});

describe('costCategory — 의미 버킷 + 산업특수 passthrough', () => {
	it('의미 버킷 매핑 (이름 변경·조각 흡수)', () => {
		expect(costCategory('원재료와 소모품의 사용')).toBe('원재료·상품');
		expect(costCategory('원재료 및 상품 사용액')).toBe('원재료·상품'); // 상품↔소모품 둘 다 원재료·상품
		expect(costCategory('종업원급여(주석 24)')).toBe('인건비');
		expect(costCategory('퇴직급여')).toBe('인건비'); // 인건비로 통합
		expect(costCategory('감가상각비, 무형자산상각비')).toBe('감가상각');
		expect(costCategory('지급수수료')).toBe('용역·수수료');
	});
	it('기타류 → 기타', () => {
		expect(costCategory('기타비용')).toBe('기타');
		expect(costCategory('기타 비용')).toBe('기타');
	});
	it('산업특수 라인은 passthrough(공백제거 키)', () => {
		expect(costCategory('구입전력비')).toBe('구입전력비'); // 한전 — 의미버킷에 안 묻힘
		expect(costCategory('망 접속비')).toBe('망접속비'); // KT
	});
});

describe('isCostPlausible — 잡음(자본/손익소계/날짜/문구) 방어', () => {
	it('비용 라인 형태 통과', () => {
		expect(isCostPlausible('구입전력비')).toBe(true);
		expect(isCostPlausible('세금과공과')).toBe(true);
		expect(isCostPlausible('임차료 및 사용료')).toBe(true);
		expect(isCostPlausible('기타비용')).toBe(true);
	});
	it('형태부터 비-비용(날짜·문구·손익) 차단', () => {
		expect(isCostPlausible('2016.12.31')).toBe(false); // 날짜
		expect(isCostPlausible('한 시점에 이행되는 수행의무')).toBe(false); // 수익인식 문구
		expect(isCostPlausible('지분법손익')).toBe(false); // 익 — 비용 접미사 아님
	});
	// '법인세비용차감전순이익'(비용 포함)·'보통주자본금'(금 접미사)은 형태론 통과 → cleanCostRows 의 NON_COST 가 차단(아래)
});

describe('cleanCostRows — 정제(비-비용 드롭 + 구조총계 + 재고제외 + 비용형태만)', () => {
	it('자본구조·손익소계·재고변동·총계 제거 후 비용만', () => {
		const rows = [
			{ name: '보통주자본금', amount: 482403125000 }, // 자본 누수
			{ name: '법인세비용차감전순이익', amount: 999 }, // 손익소계
			{ name: '제품과 재공품의 감소(증가)', amount: 571892 }, // 재고변동(양수여도 제외)
			{ name: '원재료 등의 사용액', amount: 93861545 },
			{ name: '종업원급여', amount: 15000000 },
			{ name: '감가상각비', amount: 12000000 }
		];
		const clean = cleanCostRows(rows);
		const names = clean.map((r) => r.name);
		expect(names).toContain('원재료 등의 사용액');
		expect(names).toContain('종업원급여');
		expect(names).not.toContain('보통주자본금');
		expect(names).not.toContain('법인세비용차감전순이익');
		expect(names).not.toContain('제품과 재공품의 감소(증가)');
		expect(clean.length).toBe(3);
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
