// AccentText 헬퍼 — 기존 SNS 캐러셀 AccentText.tsx 와 동일 규약(`[[구절]]`=강조).
import { describe, it, expect } from 'vitest';
import { accentParts } from './theme';

describe('accentParts — [[구절]] 강조 분해', () => {
	it('마커 안은 accent, 밖은 일반', () => {
		expect(accentParts('본업 [[현금]]이 받친다')).toEqual([
			{ text: '본업 ', accent: false },
			{ text: '현금', accent: true },
			{ text: '이 받친다', accent: false }
		]);
	});
	it('마커 없으면 통째로 일반', () => {
		expect(accentParts('강조 없음')).toEqual([{ text: '강조 없음', accent: false }]);
	});
	it('빈/널 안전', () => {
		expect(accentParts('')).toEqual([]);
	});
});
