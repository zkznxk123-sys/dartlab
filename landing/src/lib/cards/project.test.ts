// 카드 투영 단위테스트 — projectBlock 8 변종 매핑·pending/skip 정직 카드·미매핑 fail-loud·
// narration 신규합성 0(모델값 그대로). fixture 만으로 런타임 비의존 검증.
import { describe, it, expect } from 'vitest';
import type { ReportModel, ReportBlock, ReportSection } from '$lib/report/model';
import { projectBlock, projectReport, projectResult } from './project';

function model(overrides: Partial<ReportModel> = {}): ReportModel {
	return {
		stockCode: '005930',
		corpName: '삼성전자',
		asOf: '2025-03-31',
		dataBasis: 'FY2024 (연간)',
		perspectiveKey: 'earningsPower',
		perspectiveLabel: '수익성',
		conclusion: '영업이익률이 회복 국면에 있다.',
		headlineKpis: [
			{ label: '매출', value: '300조' },
			{ label: '영업이익률', value: '12.3%' }
		],
		narrativeOverview: '개요',
		keyFindings: [],
		sections: [],
		closing: [{ label: '종합', engine: 'story', line: '구조적 회복이 관건이다.' }],
		provenance: { engines: {}, note: '' },
		assumptionsNote: '',
		qualityLabel: 'verified',
		focusQuestions: [],
		...overrides
	};
}

const HEAD = { heading: '재무분석', sub: '수익성' };

describe('projectBlock — 8 변종 명시 매핑', () => {
	it('line/bars/share/metrics/flags/table(시계열) → 카드', () => {
		expect(projectBlock({ type: 'line', series: [1, 2, 3] }, HEAD)?.kind).toBe('line');
		expect(projectBlock({ type: 'bars', rows: [{ label: 'a', value: 1, display: '1' }] }, HEAD)?.kind).toBe('bars');
		expect(
			projectBlock({ type: 'share', rows: [{ year: '2024', segs: [] }], legend: [] }, HEAD)?.kind
		).toBe('share');
		expect(projectBlock({ type: 'metrics', metrics: [{ label: 'a', value: '1' }] }, HEAD)?.kind).toBe('kpis');
		expect(projectBlock({ type: 'flags', kind: 'warning', flags: ['x'] }, HEAD)?.kind).toBe('flags');
		const ts: ReportBlock = { type: 'table', data: [{ 항목: '매출', '2022': '1', '2023': '2', '2024': '3' }] };
		expect(projectBlock(ts, HEAD)?.kind).toBe('table');
	});
	it('heading·짧은 text·비시계열 table → 명시 skip(null)', () => {
		expect(projectBlock({ type: 'heading', title: 'x' }, HEAD)).toBeNull();
		expect(projectBlock({ type: 'text', text: '짧음' }, HEAD)).toBeNull();
		expect(projectBlock({ type: 'table', data: [{ 항목: '매출', 값: '1' }] }, HEAD)).toBeNull();
	});
	it('충분히 긴 text → narrative', () => {
		const c = projectBlock({ type: 'text', text: '영업이익률이 3년 연속 개선되어 구조적 회복 신호로 읽힌다.' }, HEAD);
		expect(c?.kind).toBe('narrative');
	});
	it('미매핑 변종 → fail-loud(throw, silent drop 금지)', () => {
		expect(() => projectBlock({ type: 'bogus' } as unknown as ReportBlock, HEAD)).toThrow(/미매핑/);
	});
});

describe('projectReport — 덱 구조 + 정직', () => {
	const sec: ReportSection = {
		key: 'profit',
		title: '재무분석 -- 수익성은 지속되는가',
		sourceEngine: 'analysis',
		blocks: [
			{ type: 'heading', title: '추세' },
			{ type: 'line', series: [10, 11, 12], xLabels: ['22', '24'] },
			{ type: 'flags', kind: 'opportunity', flags: ['신규 라인 가동'] }
		]
	};
	it('cover → kpis → finChart → 섹션카드 → closing 순서', () => {
		const deck = projectReport(model({ sections: [sec] }), { heroUrl: 'https://x/h.webp' });
		const kinds = deck.cards.map((c) => c.kind);
		expect(kinds[0]).toBe('cover');
		expect(kinds).toContain('kpis');
		expect(kinds).toContain('finChart');
		expect(kinds).toContain('line');
		expect(kinds).toContain('flags');
		expect(kinds.at(-1)).toBe('closing');
		// heading 블록은 슬라이드가 안 됨(접힘).
		expect(deck.cards.filter((c) => c.kind === 'line')[0]).toMatchObject({ heading: '재무분석', sub: '수익성은 지속되는가' });
	});
	it('cover 는 모델값 그대로(신규 숫자 합성 0)', () => {
		const deck = projectReport(model());
		const cover = deck.cards[0];
		expect(cover.kind === 'cover' && cover.conclusion).toBe('영업이익률이 회복 국면에 있다.');
		expect(cover.kind === 'cover' && cover.heroUrl).toBeUndefined(); // hero 없으면 폴백(undefined)
	});
	it('hero 부재 시에도 덱 렌더 가능(빈 화면 금지) — cover+finChart 최소', () => {
		const deck = projectReport(model({ headlineKpis: [], sections: [] }));
		expect(deck.cards.length).toBeGreaterThanOrEqual(2); // cover + finChart(+closing)
		expect(deck.cards.some((c) => c.kind === 'finChart')).toBe(true);
	});
});

describe('pending/skip — 정직 빈 카드', () => {
	it('pending 관점 → empty 카드', () => {
		const deck = projectReport(model({ pending: true }));
		expect(deck.cards.map((c) => c.kind)).toEqual(['cover', 'empty']);
	});
	it('ReportSkipped → empty 카드(broken img 아님)', () => {
		const deck = projectResult({ skipped: true, stockCode: '999999', reason: '데이터 없음' }, '수익성');
		expect(deck.cards).toEqual([{ kind: 'empty', reason: '데이터 없음' }]);
	});
});
