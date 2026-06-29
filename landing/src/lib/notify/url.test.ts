import { describe, it, expect } from 'vitest';
import { safeNotificationUrl } from './url';

const BASE = '/dartlab';
const ORIGIN = 'https://eddmpython.github.io';

describe('safeNotificationUrl', () => {
	it('app-path 에 BASE 접두 (라운드4 blocker 닫음)', () => {
		expect(safeNotificationUrl(BASE, '/blog/everything-about-dart', ORIGIN)).toBe('/dartlab/blog/everything-about-dart');
	});

	it('카드 라우트 querystring 보존', () => {
		expect(safeNotificationUrl(BASE, '/cards?post=my-issue', ORIGIN)).toBe('/dartlab/cards?post=my-issue');
	});

	it('url 없으면 홈', () => {
		expect(safeNotificationUrl(BASE, undefined, ORIGIN)).toBe('/dartlab/');
		expect(safeNotificationUrl(BASE, '', ORIGIN)).toBe('/dartlab/');
	});

	it('외부 절대 URL 도 우리 origin 밖으로 못 나감(피싱 차단)', () => {
		// base 접두로 절대 URL 이 우리 origin 의 상대경로로 흡수됨 → 최악이 우리 도메인의 404(외부 호스트 도달 0).
		const out = safeNotificationUrl(BASE, 'https://evil.com/steal', ORIGIN);
		expect(out.startsWith('/dartlab')).toBe(true);
		expect(new URL(out, ORIGIN).origin).toBe(ORIGIN); // 핵심 불변: origin 고정
	});

	it('protocol-relative //evil.com 도 우리 origin 고정', () => {
		const out = safeNotificationUrl(BASE, '//evil.com/x', ORIGIN);
		expect(new URL(out, ORIGIN).origin).toBe(ORIGIN);
	});

	it('javascript: 스킴은 path 로 흡수(스킴 탈출 불가)', () => {
		const out = safeNotificationUrl(BASE, 'javascript:alert(1)', ORIGIN);
		expect(out.startsWith('/dartlab')).toBe(true);
		expect(out.startsWith('javascript:')).toBe(false);
	});
});
