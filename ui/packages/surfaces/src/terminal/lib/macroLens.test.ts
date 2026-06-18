import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { MACRO_SERIES, type MacroLatest } from '@dartlab/ui-contracts';
import { CURRENT_MACRO_EDGE_SECTOR_KEYS, EDGE_SECTOR_TO_TAILWIND } from './macroMappings';
import { buildMacroGlanceView, buildMacroLensSnapshot, buildMacroPath, buildMarketMacroLensSnapshot, buildRegimeQuadrant } from './macroLens';
import type { Company, MacroFile } from './types';

const macro = JSON.parse(
	readFileSync(new URL('../../../../../../landing/static/dashboards/macro.json', import.meta.url), 'utf8')
) as MacroFile;

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

const macroWithSingleMixedEdge = (): MacroFile => {
	const m = cloneMacro();
	const driver = m.transmission!.drivers.find((d) => d.id === 'USDKRW')!;
	const edge = m.transmission!.edges.find((e) => e.driverId === 'USDKRW')!;
	m.transmission = {
		...m.transmission!,
		drivers: [driver],
		edges: [{
			...edge,
			id: 'test-mixed-edge',
			sectorKeys: ['all'],
			sign: 'mixed',
			confidence: 'high',
			evidenceLevel: 'observed',
			sourceRef: 'test:mixed'
		}]
	};
	return m;
};

const macroWithObservedVsTemplate = (): MacroFile => {
	const m = cloneMacro();
	const drivers = ['EXPORT', 'BASE_RATE'].map((id) => m.transmission!.drivers.find((d) => d.id === id)!);
	const edges = [
		m.transmission!.edges.find((e) => e.driverId === 'EXPORT')!,
		m.transmission!.edges.find((e) => e.driverId === 'BASE_RATE' && e.evidenceLevel === 'template')!
	];
	m.transmission = {
		...m.transmission!,
		drivers,
		edges
	};
	return m;
};

describe('macroLens builders — current macro v19 artifact', () => {
	it('builds a 2x2 regime model without leaking raw coordinate signals', () => {
		const view = buildRegimeQuadrant(macro);
		expect(view.cells.map((cell) => cell.key).sort()).toEqual(['deflation', 'goldilocks', 'reflation', 'stagflation']);

		const kr = view.markets.find((market) => market.market === 'KR')!;
		const us = view.markets.find((market) => market.market === 'US')!;
		expect(kr.cellKey).toBe('stagflation');
		expect(kr.phase).toBe('recovery');
		expect(kr.quadrantLabel).toBe('스태그플레이션');
		expect(kr.hasTransitionProgress).toBe(false);
		expect('growthSignal' in kr).toBe(false);
		expect('inflationSignal' in kr).toBe(false);

		expect(us.cellKey).toBe('reflation');
		expect(us.phase).toBe('slowdown');
		expect(us.hasTransitionProgress).toBe(true);
		expect(us.transitionLabel).toContain('33%');
	});

	it('builds the macro transmission rail from macro.transmission without all-sector fanout', () => {
		const path = buildMacroPath(macro.transmission, sectorTailwinds(), { mode: 'full', activeIndustryId: 'logistics' });
		expect(path.mode).toBe('full');
		expect(path.links.length + path.allSectorLinks.length).toBe(macro.transmission!.edges.length);
		expect(path.allSectorLinks).toHaveLength(2);
		for (const link of path.allSectorLinks) {
			expect(link.sectorKeys).toEqual(['all']);
			expect(link.sectorNodes).toHaveLength(1);
			expect(link.allSector).toBe(true);
		}

		expect([...path.coverageKeys].sort()).toEqual([...CURRENT_MACRO_EDGE_SECTOR_KEYS].sort());
		expect(path.hasNegativeTailwind).toBe(false);
		expect(path.captionKr).toContain('절대 역풍 없음');

		const logistics = path.sectorNodes.find((node) => node.key === 'logistics')!;
		expect(logistics).toMatchObject({ industryId: 'logistics', tailwindKey: null, missingTailwind: true, active: true });

		const utility = path.sectorNodes.find((node) => node.key === 'utility')!;
		expect(utility).toMatchObject({ industryId: null, tailwindKey: null, missingTailwind: true, active: false });
	});

	it('builds a market-only glance before a company is selected', () => {
		const view = buildMacroGlanceView(macro, sectorTailwinds(), { mode: 'compact' });
		expect(view.asOf).toBe('2026-06-18');
		expect(view.regime.markets).toHaveLength(2);
		expect(view.path.links.length).toBeGreaterThan(0);
		expect(view.path.allSectorLinks.length).toBeGreaterThan(0);
		expect(view.sectorTailwinds.length).toBeGreaterThan(0);
	});

	it('builds a market-only macro verdict without company claims', () => {
		const snapshot = buildMarketMacroLensSnapshot({
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds()
		});
		expect(snapshot.marketOnly).toBe(true);
		expect(snapshot.verdict.score).toBeGreaterThanOrEqual(0);
		expect(snapshot.verdict.score).toBeLessThanOrEqual(100);
		expect(snapshot.verdict.claimLevel).toBe('marketMap');
		expect(snapshot.verdict.nextActionKr).toContain('종목 선택');
		expect(snapshot.verdict.drivers.length).toBeGreaterThan(0);
		expect(snapshot.verdict.sourceRefs.length).toBeGreaterThan(0);
		expect(snapshot.verdict.directionScore).toBeGreaterThanOrEqual(-100);
		expect(snapshot.verdict.directionScore).toBeLessThanOrEqual(100);
		expect(snapshot.verdict.evidenceScore).toBeGreaterThanOrEqual(0);
		expect(snapshot.verdict.evidenceScore).toBeLessThanOrEqual(100);
		expect(snapshot.verdict.killChain.length).toBeGreaterThan(0);
		expect(snapshot.verdict.flip.status).not.toBeUndefined();
		expect(snapshot.verdict.contest.rows.length).toBeGreaterThan(0);
		expect(snapshot.verdict.actions.some((action) => action.id === 'select-company')).toBe(true);
		expect(snapshot.verdict.contest.supportiveScore + snapshot.verdict.contest.pressureScore + snapshot.verdict.contest.mixedScore + snapshot.verdict.contest.unknownScore).toBeGreaterThan(0);

		const forbidden = [
			snapshot.verdict.titleKr,
			snapshot.verdict.summaryKr,
			snapshot.verdict.nextActionKr,
			snapshot.verdict.primaryChainKr
		].join(' ');
		expect(forbidden).not.toMatch(/매수|매도|목표가|보장|추천|beta|베타/);
	});

	it('locks the verdict when a critical primary macro driver is stale', () => {
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
		expect(snapshot.verdict.direction).toBe('locked');
		expect(snapshot.verdict.directionScore).toBe(0);
		expect(snapshot.verdict.evidenceScore).toBeLessThanOrEqual(44);
		expect(snapshot.verdict.flip.status).toBe('locked');
		expect(snapshot.verdict.score).toBeLessThanOrEqual(44);
	});

	it('preserves transmission edge falsifiers in driver-local kill chains', () => {
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const fxEdge = snapshot.transmissionEdges.find((edge) => edge.driverId === 'USDKRW');
		expect(fxEdge?.falsifiers[0]).toContain('달러 원가');
		const fxDriver = snapshot.verdict.drivers.find((driver) => driver.driverId === 'USDKRW');
		expect(fxDriver?.killChain.some((step) => step.detailKr.includes('달러 원가'))).toBe(true);
		expect(fxDriver?.gates.map((gate) => gate.id)).toEqual(['series', 'path', 'company', 'quant', 'comove']);
	});

	it('does not open companyCandidate when quantCandidate lacks required evidence fields', () => {
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
			}),
			macro,
			macroLatest: macroLatest(),
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		expect(snapshot.verdict.claimLevel).not.toBe('companyCandidate');
		expect(snapshot.evidenceGates.find((g) => g.id === 'quant')?.status).toBe('blocked');
		expect(snapshot.evidenceGates.find((g) => g.id === 'quant')?.blocks.join(' ')).toContain('nObs missing');
	});

	it('hard-locks fallback transmission templates when macro.transmission is missing', () => {
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
		expect(snapshot.verdict.direction).toBe('locked');
		expect(snapshot.verdict.claimLevel).toBe('locked');
		expect(snapshot.verdict.score).toBeLessThanOrEqual(44);
	});

	it('does not label zero-change negative-rate exposure as pressure', () => {
		const flatLatest = macroLatest().map((row) => ({ ...row, chg: 0, spark: [row.v, row.v, row.v] }));
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture({
				industry: 'finance',
				sector: { kr: '금융', en: 'Finance' }
			}),
			macro,
			macroLatest: flatLatest,
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		const baseRate = snapshot.verdict.drivers.find((d) => d.driverId === 'BASE_RATE');
		expect(baseRate?.direction).not.toBe('pressure');
		expect(snapshot.verdict.direction).not.toBe('pressure');
	});

	it('keeps mixed edges mixed even with a large latest move', () => {
		const latest = macroLatest()
			.filter((row) => row.def.id === 'USDKRW')
			.map((row) => ({ ...row, chg: 50, spark: [row.v - 10, row.v, row.v + 50] }));
		const snapshot = buildMarketMacroLensSnapshot({
			macro: macroWithSingleMixedEdge(),
			macroLatest: latest,
			sectorTailwinds: sectorTailwinds()
		});
		expect(snapshot.verdict.direction).toBe('mixed');
		expect(snapshot.verdict.drivers[0]?.direction).toBe('mixed');
		expect(snapshot.verdict.titleKr).not.toMatch(/우호 경로 우세|부담 경로 우세/);
	});

	it('ranks drivers after evidence so a template path cannot beat an observed path on move alone', () => {
		const m = macroWithObservedVsTemplate();
		const latest: MacroLatest[] = ['EXPORT', 'BASE_RATE'].flatMap((id) => {
			const def = MACRO_SERIES.find((series) => series.id === id);
			if (!def) return [];
			return [{
				def,
				v: id === 'BASE_RATE' ? 3 : 100,
				d: '20260618',
				chg: id === 'BASE_RATE' ? 100 : 1,
				spark: id === 'BASE_RATE' ? [2, 3, 4] : [99, 100, 101]
			}];
		});
		const snapshot = buildMacroLensSnapshot({
			co: companyFixture(),
			macro: m,
			macroLatest: latest,
			sectorTailwinds: sectorTailwinds(),
			coMovers: []
		});
		expect(snapshot.verdict.drivers[0]?.driverId).toBe('EXPORT');
		expect(snapshot.verdict.drivers[0]?.evidenceLabel).toBe('OBS');
		const templateDriver = snapshot.verdict.drivers.find((d) => d.driverId === 'BASE_RATE');
		expect(templateDriver?.evidenceLabel).toBe('TPL');
		expect(templateDriver?.score).toBeLessThanOrEqual(42);
		expect(templateDriver?.evidenceScore).toBeLessThanOrEqual(42);
		expect(templateDriver?.gates.find((gate) => gate.id === 'path')?.status).toBe('locked');
		expect(snapshot.verdict.contest.rows[0]?.driverId).toBe('EXPORT');
	});
});
