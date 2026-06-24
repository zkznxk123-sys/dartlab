// KRW 단위 SSOT 단위테스트 — per-value(fmtKrwFromJo)·시리즈 축(pickKrwUnit) 의 "0.0조 붕괴 없음" 가드.
import { describe, it, expect } from 'vitest';
import { fmtKrw, fmtKrwFromEok, fmtKrwFromJo, pickKrwUnit } from './krw';

describe('fmtKrw — 자연 단위 선택(0.X조 회피)', () => {
	it('1조↑=조, 1억↑=억, 1만↑=만, 그 미만=콤마', () => {
		expect(fmtKrw(1.283e15)).toBe('1,283조');
		expect(fmtKrw(8.5e11)).toBe('8,500억'); // 0.85조 → 억으로(0.9조 아님)
		expect(fmtKrw(2.1e8)).toBe('2.1억');
		expect(fmtKrw(120000)).toBe('12만');
		expect(fmtKrw(0)).toBe('0');
	});
	it('음수·결측 안전', () => {
		expect(fmtKrw(-8.5e11)).toBe('-8,500억');
		expect(fmtKrw(null)).toBe('—');
		expect(fmtKrw(NaN)).toBe('—');
	});
});

describe('fmtKrwFromJo — 조 단위 입력은 0.0조로 뭉개지지 않는다', () => {
	it('작은 값도 제 단위(억)로', () => {
		expect(fmtKrwFromJo(0.0864)).toBe('864억'); // 864억 — "0.0조" 아님
		expect(fmtKrwFromJo(0.032)).toBe('320억');
		expect(fmtKrwFromJo(50)).toBe('50조');
		expect(fmtKrwFromJo(2.72)).toBe('2.7조');
	});
	it('억 raw 헬퍼와 일관', () => {
		expect(fmtKrwFromJo(0.0864)).toBe(fmtKrwFromEok(864));
	});
});

describe('pickKrwUnit — 시리즈 공통 단위(최빈 단위 통일)', () => {
	it('전부 조(대기업)는 조 유지', () => {
		const s = pickKrwUnit([50, 8.64, 6.2], { from: '조' });
		expect(s.unit).toBe('조');
		expect(s.scale).toBe(1);
		expect(s.fmt(50)).toBe('50');
		expect(s.fmt(8.64)).toBe('8.6');
	});
	it('전부 1조 미만이면 억으로 — 0.0 범벅 차단', () => {
		const s = pickKrwUnit([0.8, 0.03, 0.15], { from: '조' });
		expect(s.unit).toBe('억');
		expect(s.scale).toBe(1e4);
		expect(s.fmt(0.8)).toBe('8,000'); // 8,000억
		expect(s.fmt(0.03)).toBe('300'); // 300억 — 0.0 아님
	});
	it('손익 혼합(매출 조 + 이익 억) — 억이 지배하면 전부 억(매출도 억으로)', () => {
		// 매출 5.9·4.0(조) + 영업익 0.3·0.9 + 순익 0.4·0.8 + 판관비 0.2·0.3(억) → 억 다수.
		const s = pickKrwUnit([5.9, 4.0, 0.3, 0.9, 0.4, 0.8, 0.2, 0.3], { from: '조' });
		expect(s.unit).toBe('억');
		expect(s.fmt(5.9)).toBe('59,000'); // 매출도 억으로 — 혼합 없음
		expect(s.fmt(0.3)).toBe('3,000'); // 영업익 3,000억
	});
	it('통화 아닌 단위(%·배·일)는 항등', () => {
		const s = pickKrwUnit([12.3, 4.4], { from: '%' });
		expect(s.unit).toBe('%');
		expect(s.scale).toBe(1);
		expect(s.fmt(12.3)).toBe('12.3');
	});
	it('빈/결측 배열도 안전', () => {
		const s = pickKrwUnit([null, undefined, NaN], { from: '조' });
		expect(s.scale).toBeGreaterThan(0);
		expect(s.fmt(0)).toBe('0');
	});
});
