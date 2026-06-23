// 시장 뉴스 source 정규화 단위 테스트 — 날짜(Date 객체/문자열/epoch-days) 정규화·url dedup·제목/url
// 필수 필터·date 내림차순 정렬을 네트워크 없이 검증(normalizeMarketNews 순수 함수).
// url 은 dedup 키·passthrough 일 뿐이라 비-URL 플레이스홀더 사용(checkUiDataWiring rule 2: http(s) 리터럴 금지).
import { describe, it, expect } from 'vitest';
import { normalizeMarketNews } from './marketNewsSource';

function row(o: Partial<Record<string, unknown>>): Record<string, unknown> {
	return { date: '', title: '', url: '', source: '', ...o };
}

describe('normalizeMarketNews', () => {
	it('Date 객체·문자열·epoch-days 를 모두 YYYY-MM-DD 로 정규화', () => {
		const out = normalizeMarketNews([
			row({ date: new Date(Date.UTC(2026, 5, 12)), title: 'A', url: 'art-a' }), // Date 객체
			row({ date: '2026-06-11', title: 'B', url: 'art-b' }), // 문자열
			row({ date: 20250, title: 'C', url: 'art-c' }) // epoch-days(20089=2025-01-01, +161=2025-06-11)
		]);
		expect(out[0]?.date).toBe('2026-06-12');
		expect(out[1]?.date).toBe('2026-06-11');
		expect(out[2]?.date).toBe('2025-06-11');
	});

	it('url dedup(keep-first) + 제목·url 빈 행 제외', () => {
		const out = normalizeMarketNews([
			row({ date: '2026-06-10', title: '같은URL 1', url: 'dup' }),
			row({ date: '2026-06-10', title: '같은URL 2', url: 'dup' }), // dedup
			row({ date: '2026-06-09', title: '', url: 'notitle' }), // 제목 없음 제외
			row({ date: '2026-06-08', title: 'url 없음', url: '' }) // url 없음 제외
		]);
		expect(out.map((n) => n.url)).toEqual(['dup']);
		expect(out[0]?.title).toBe('같은URL 1'); // keep-first
	});

	it('date 내림차순 정렬(여러 shard 병합 후 시간순)', () => {
		const out = normalizeMarketNews([
			row({ date: '2026-06-08', title: 'old', url: 'a1' }),
			row({ date: '2026-06-12', title: 'new', url: 'a2' }),
			row({ date: '2026-06-10', title: 'mid', url: 'a3' })
		]);
		expect(out.map((n) => n.title)).toEqual(['new', 'mid', 'old']);
	});

	it('필드 매핑·trim', () => {
		const out = normalizeMarketNews([row({ date: '2026-06-12', title: '  제목  ', url: 'art-x', source: '  연합  ' })]);
		expect(out[0]).toEqual({ date: '2026-06-12', title: '제목', source: '연합', url: 'art-x' });
	});
});
