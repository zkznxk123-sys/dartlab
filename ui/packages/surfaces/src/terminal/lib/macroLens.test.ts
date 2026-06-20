import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { MACRO_SERIES, type MacroLatest } from '@dartlab/ui-contracts';
import { CURRENT_MACRO_EDGE_SECTOR_KEYS, EDGE_SECTOR_TO_TAILWIND } from './macroMappings';
import {
	buildExposureMatrixRows,
	buildMacroGlanceView,
	buildMacroLensSnapshot,
	buildMacroPath,
	buildMarketMacroLensSnapshot,
	buildRegimeQuadrant,
	pickFocusCell,
	type MacroChannel,
	type MacroDriverView,
	type MacroExposureMatrixRow,
	type MacroTransmissionEdgeView
} from './macroLens';
import type { Company, MacroFile } from './types';

const macro = JSON.parse(
	readFileSync(new URL('../../../../../../landing/static/dashboards/macro.json', import.meta.url), 'utf8')
) as MacroFile;

const CHANNELS: MacroChannel[] = ['revenue', 'margin', 'balanceSheet', 'cashFlow', 'valuation'];

const sectorTailwinds = () =>
	Object.entries(EDGE_SECTOR_TO_TAILWIND).flatMap(([sectorKey, map]) => {
		const tailwindKey = map.tailwindKey;
		if (!tailwindKey) return [];
		const tw = macro.sectorTailwind[tailwindKey];
		if (!tw) return [];
		return [{
			id: map.industryId ?? sectorKey,
			kr: map.kr,
			en: map.en,
			tailwindKey,
			blended: tw.blended
		}];
	});

const macroLatest = (): MacroLatest[] =>
	(macro.transmission?.drivers ?? []).flatMap((driver) => {
		const def = MACRO_SERIES.find((series) => series.id === driver.id);
		if (!def) return [];
		const date = driver.sourceLineage?.date?.replaceAll('-', '') || '20260618';
		const value = driver.sourceLineage?.value ?? 1;
		return [{
			def,
			v: value,
			d: date,
			chg: 1,
			spark: [value - 2, value - 1, value]
		}];
	});

const cloneMacro = (): MacroFile => JSON.parse(JSON.stringify(macro)) as MacroFile;

const companyFixture = (overrides: Partial<Company> = {}): Company => ({
	code: '005930',
	marketLabel: 'KOSPI',
	name: { kr: '삼성전자', en: 'Samsung Electronics' },
	sector: { kr: '반도체', en: 'Semiconductor' },
	industry: 'semiconductor',
	stage: '',
	role: '',
	eco: { id: '005930', label: '삼성전자', industry: 'semiconductor' },
	grades: [],
	radar: [],
	changes: [],
	price: {
		last: 70000,
		mktcap: '0',
		mktcapRaw: 0,
		ret1m: null,
		ret3m: null,
		ret1y: null,
		vol1y: null,
		hi52: null,
		lo52: null,
		vol: null,
		asOf: '2026-06-18'
	},
	fundamentals: { per: null, pbr: null, psr: null, npm: null, roe: null, opm: 12, dr: 40 },
	financials: {
		years: [],
		sales: [],
		op: [],
		net: [],
		opMargin: [],
		netMargin: [],
		roe: [],
		assetTurn: [],
		equityMult: [],
		deRatio: [],
		currRatio: [],
		dupont: { netMargin: null, assetTurn: null, equityMult: null, roe: null },
		assetMix: [],
		fundMix: [],
		cf: { op: null, inv: null, fin: null, fcf: null }
	},
	trendAnnual: { periods: ['2025'], sales: [], op: [], net: [], opMargin: [], freq: 'annual' },
	trendQuarter: null,
	income: { periods: [], rows: [] },
	balance: { periods: [], rows: [] },
	cashflow: { periods: [], rows: [] },
	ratios: [],
	credit: { grade: 'NA', healthScore: 0, pd: '—', tone: 'neutral', tracks: [], basis: { debtRatio: null, curr: null, opm: null } },
	analysis: { summary: { kr: '', en: '' }, tracks: [] },
	macroExposure: null,
	peers: [],
	story: null,
	percentile: null,
	valuation: null,
	risks: [],
	riskCatalog: [],
	tailwind: null,
	verdict: { composite: 0, band: { kr: '', en: '', tone: 'neutral' }, strengths: [], concerns: [], riskRed: 0, riskYellow: 0 },
	...overrides
} as unknown as Company);

// 합성 driver/edge stub — buildExposureMatrixRows/pickFocusCell가 읽는 필드만 채운다(나머지 cast).
const mkDriver = (id: string, relevance: MacroDriverView['relevance'] = 'secondary'): MacroDriverView =>
	({ id, label: id, relevance } as unknown as MacroDriverView);
const mkEdge = (
	driverId: string,
	channel: MacroChannel,
	evidenceLevel: MacroTransmissionEdgeView['evidenceLevel'],
	confidence: MacroTransmissionEdgeView['confidence'] = 'medium',
	extra: Partial<MacroTransmissionEdgeView> = {}
): MacroTransmissionEdgeView =>
	({ id: `${driverId}-${channel}`, driverId, channel, evidenceLevel, confidence, financialLine: `${channel} line`, valuationLever: 'growth', sign: 'positive', lagMonths: [1, 6], ...extra } as unknown as MacroTransmissionEdgeView);

describe('macroLens builders — current macro v19 artifact (redesign)', () => {
	it('builds a 2x2 regime model without leaking raw coordinate signals', () => {
		const view = buildRegimeQuadrant(macro);
		expect(view.cells.map((cell) => cell.key).sort()).toEqual(['deflation', 'goldilocks', 'reflation', 'stagflation']);

		const kr = view.markets.find((market) => market.market === 'KR')!;
		const us = view.markets.find((market) => market.market === 'US')!;
		expect(kr.cellKey).toBe('stagflation');
		expect('growthSignal' in kr).toBe(false);
		expect('inflationSignal' in kr).toBe(false);
		expect(us.cellKey).toBe('reflation');
	});

	it('builds the macro transmission rail from macro.transmission without all-sector fanout', () => {
		const path = buildMacroPath(macro.transmission, sectorTailwinds(), { mode: 'full', activeIndustryId: 'logistics' });
		expect(path.mode).toBe('full');
		expect(path.links.length + path.allSectorLinks.length).toBe(macro.transmission!.edges.length);
		expect([...path.coverageKeys].sort()).toEqual([...CURRENT_MACRO_EDGE_SECTOR_KEYS].sort());
	});

	it('builds a market-only glance before a company is selected', () => {
		const view = buildMacroGlanceView(macro, sectorTailwinds(), { mode: 'compact' });
		expect(view.asOf).toBe('2026-06-18');
		expect(view.regime.markets).toHaveLength(2);
		expect(view.path.links.length).toBeGreaterThan(0);
		expect(view.sectorTailwinds.length).toBeGreaterThan(0);
	});
});

describe('macroLens snapshot — verdict layer removed, evidence gates kept', () => {
	it('produces no verdict layer and no single macro score', () => {
		const snapshot = buildMarketMacroLensSnapshot({
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds()
		});
		expect(snapshot.marketOnly).toBe(true);
		expect('verdict' in snapshot).toBe(false);
		// 단일 macro score / 방향점수 / /100 표면화 0 (verdict 부활 가드).
		const json = JSON.stringify(snapshot);
		expect(json).not.toContain('directionScore');
		expect(json).not.toContain('evidenceScore');
		expect(json).not.toContain('claimLevel');
	});

	it('blocks the macroData gate when a critical primary macro driver is stale', () => {
		const staleLatest = macroLatest().map((row) => row.def.id === 'USDKRW' ? { ...row, d: '20200101', chg: 35 } : row);
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro,
			macroLatest: staleLatest,
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const gate = snapshot.evidenceGates.find((g) => g.id === 'macroData');
		expect(gate?.status).toBe('blocked');
		expect(gate?.blocks.join(' ')).toContain('USDKRW');
	});

	it('preserves transmission edge falsifiers (no verdict needed)', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const fxEdge = snapshot.transmissionEdges.find((edge) => edge.driverId === 'USDKRW');
		expect(fxEdge?.falsifiers[0]).toContain('달러 원가');
	});

	it('blocks the quant gate when quantCandidate lacks required evidence fields', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture({
				macroExposure: {
					exposureQuality: {
						status: 'quantCandidate',
						reason: 'fixture invalid quant candidate',
						blockedReason: '',
						missingEvidence: [],
						sourceRef: 'test:macroExposure',
						nObs: null,
						rSquared: null,
						window: null,
						frequency: null,
						lagMonths: null,
						coverage: 'missing',
						minObs: 24,
						method: 'ols',
						modelVersion: 'test',
						targetMetric: 'sales'
					},
					selected: []
				}
			} as unknown as Partial<Company>),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		expect(snapshot.evidenceGates.find((g) => g.id === 'quant')?.status).toBe('blocked');
		expect(snapshot.evidenceGates.find((g) => g.id === 'quant')?.blocks.join(' ')).toContain('nObs missing');
	});

	it('hard-locks the path gate when macro.transmission is missing', () => {
		const noTransmission = cloneMacro();
		noTransmission.transmission = null;
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro: noTransmission,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		expect(snapshot.evidenceGates.find((g) => g.id === 'path')?.status).toBe('blocked');
	});

	it('drivers carry value/asOf/source for the Pulse strip (relevance != context)', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const pulse = snapshot.drivers.filter((d) => d.relevance !== 'context');
		expect(pulse.length).toBeGreaterThan(0);
		for (const d of pulse) {
			expect(typeof d.value).toBe('string');
			expect(d).toHaveProperty('asOf');
			expect(d).toHaveProperty('source');
		}
	});
});

describe('buildExposureMatrixRows — sparsity, cap 6, deterministic drop', () => {
	it('produces rows with cells.length === channels.length and filledCount', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const rows = buildExposureMatrixRows(snapshot.drivers, snapshot.topPressures, snapshot.transmissionEdges, CHANNELS);
		expect(rows.length).toBeLessThanOrEqual(6);
		for (const row of rows) {
			expect(row.cells).toHaveLength(CHANNELS.length);
			expect(row.filledCount).toBe(row.cells.filter(Boolean).length);
			for (const cell of row.cells) {
				if (cell) expect(['observed', 'sectorPrior', 'template']).toContain(cell.evidenceLevel);
			}
		}
	});

	it('caps at exactly 6 rows when 8 drivers are supplied', () => {
		const drivers = Array.from({ length: 8 }, (_, i) => mkDriver(`D${i}`));
		const edges = drivers.map((d, i) => mkEdge(d.id, CHANNELS[i % CHANNELS.length], 'template'));
		const rows = buildExposureMatrixRows(drivers, drivers, edges, CHANNELS);
		expect(rows).toHaveLength(6);
	});

	it('sorts by filledCount desc and, on equal filledCount, drops the last input row (stable)', () => {
		// 8 drivers, all filledCount === 1 (each 1 channel) → cap 6 drops input rows 7,8.
		const drivers = Array.from({ length: 8 }, (_, i) => mkDriver(`D${i}`));
		const edges = drivers.map((d) => mkEdge(d.id, 'revenue', 'template'));
		const rows = buildExposureMatrixRows(drivers, drivers, edges, CHANNELS);
		expect(rows.map((r) => r.driver.id)).toEqual(['D0', 'D1', 'D2', 'D3', 'D4', 'D5']);
		// 한 driver가 2채널(filledCount 2)이면 정렬 상단으로 올라온다.
		const edges2 = [...edges, mkEdge('D7', 'margin', 'template')];
		const rows2 = buildExposureMatrixRows(drivers, drivers, edges2, CHANNELS);
		expect(rows2[0].driver.id).toBe('D7');
		expect(rows2[0].filledCount).toBe(2);
	});

	it('keeps same-channel multiple drivers as separate rows (valuation stack)', () => {
		const drivers = [mkDriver('HY'), mkDriver('DGS10')];
		const edges = [mkEdge('HY', 'valuation', 'observed'), mkEdge('DGS10', 'valuation', 'template')];
		const rows = buildExposureMatrixRows(drivers, drivers, edges, CHANNELS);
		expect(rows).toHaveLength(2);
		expect(rows.every((r) => r.cells[CHANNELS.indexOf('valuation')] != null)).toBe(true);
	});

	it('does not throw and does not surface quantCandidate as a first-screen row (silent-drop guard)', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture({
				macroExposure: {
					exposureQuality: {
						status: 'quantCandidate', reason: '', blockedReason: '', missingEvidence: [],
						sourceRef: 'test', nObs: 30, rSquared: 0.4, window: '2018-2026', frequency: 'monthly',
						lagMonths: 1, coverage: 'company', minObs: 24, method: 'ols', modelVersion: 't', targetMetric: 'sales'
					},
					selected: []
				}
			} as unknown as Partial<Company>),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		expect(() => buildExposureMatrixRows(snapshot.drivers, snapshot.topPressures, snapshot.transmissionEdges, CHANNELS)).not.toThrow();
		const rows = buildExposureMatrixRows(snapshot.drivers, snapshot.topPressures, snapshot.transmissionEdges, CHANNELS);
		// 행은 driver 키이며 어떤 셀도 exposureQuality status를 노출하지 않는다(근거 탭 전용).
		const json = JSON.stringify(rows);
		expect(json).not.toContain('quantCandidate');
	});
});

describe('pickFocusCell — observed priority, channel tie-break, determinism', () => {
	const rowsOf = (edges: MacroTransmissionEdgeView[]): MacroExposureMatrixRow[] => {
		const byDriver = new Map<string, MacroTransmissionEdgeView[]>();
		for (const e of edges) {
			if (!byDriver.has(e.driverId)) byDriver.set(e.driverId, []);
			byDriver.get(e.driverId)!.push(e);
		}
		return [...byDriver.entries()].map(([driverId, es]) => ({
			driver: mkDriver(driverId),
			cells: CHANNELS.map((ch) => es.find((e) => e.channel === ch) ?? null),
			filledCount: es.length
		}));
	};

	it('prefers observed over template', () => {
		const focus = pickFocusCell(rowsOf([mkEdge('A', 'margin', 'template'), mkEdge('B', 'valuation', 'observed')]));
		expect(focus?.edge.driverId).toBe('B');
	});

	it('breaks ties by channel priority (revenue > margin > valuation), not by change/lag', () => {
		// 3 observed edges all medium confidence — 채널 우선순위로 revenue(EXPORT)가 초점.
		const focus = pickFocusCell(rowsOf([
			mkEdge('PPI_SEMI', 'margin', 'observed', 'medium'),
			mkEdge('EXPORT', 'revenue', 'observed', 'medium'),
			mkEdge('BAMLH0A0HYM2', 'valuation', 'observed', 'medium')
		]));
		expect(focus?.edge.driverId).toBe('EXPORT');
		expect(focus?.channel).toBe('revenue');
	});

	it('is deterministic across repeated calls on identical input', () => {
		const edges = [mkEdge('PPI_SEMI', 'margin', 'observed'), mkEdge('EXPORT', 'revenue', 'observed'), mkEdge('BAMLH0A0HYM2', 'valuation', 'observed')];
		const a = pickFocusCell(rowsOf(edges));
		const b = pickFocusCell(rowsOf(edges));
		expect(a?.edge.driverId).toBe(b?.edge.driverId);
	});

	it('returns null when no cell is filled', () => {
		expect(pickFocusCell([{ driver: mkDriver('X'), cells: CHANNELS.map(() => null), filledCount: 0 }])).toBeNull();
	});

	it('handles a lagMonths===null focus edge without throwing (chain renders direct)', () => {
		const focus = pickFocusCell(rowsOf([mkEdge('X', 'revenue', 'observed', 'medium', { lagMonths: null })]));
		expect(focus?.edge.lagMonths).toBeNull();
		expect(focus?.edge.financialLine).toBeTruthy();
		expect(focus?.edge.valuationLever).toBeTruthy();
	});

	it('on real semiconductor data returns a stable non-null focus with chain inputs', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const rows = buildExposureMatrixRows(snapshot.drivers, snapshot.topPressures, snapshot.transmissionEdges, CHANNELS);
		const focus = pickFocusCell(rows);
		expect(focus).not.toBeNull();
		expect(focus!.edge.financialLine).toBeTruthy();
		expect(focus!.edge.valuationLever).toBeTruthy();
		const again = pickFocusCell(rows);
		expect(focus!.edge.driverId).toBe(again!.edge.driverId);
	});
});
