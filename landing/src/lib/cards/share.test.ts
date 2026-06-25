import { describe, it, expect } from 'vitest';
import { cardShareUrl } from './share';

// 이번 변경 검증: SHARE_BASE 기본값 = 배포된 cardShare 워커(env 미설정 시).
describe('cardShareUrl', () => {
	it('워커 base 기본값 → /c/<slug> 리치 OG 링크', () => {
		expect(cardShareUrl('2026-06-korea-macro')).toBe(
			'https://dartlab-card-share.eddmpython.workers.dev/c/2026-06-korea-macro'
		);
	});
	it('슬러그 URL 인코딩', () => {
		expect(cardShareUrl('a/b?x')).toBe('https://dartlab-card-share.eddmpython.workers.dev/c/a%2Fb%3Fx');
	});
});
