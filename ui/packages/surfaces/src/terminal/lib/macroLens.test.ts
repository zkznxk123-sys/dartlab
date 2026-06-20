import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { MACRO_SERIES, type MacroLatest } from '@dartlab/ui-contracts';
import { CURRENT_MACRO_EDGE_SECTOR_KEYS, EDGE_SECTOR_TO_TAILWIND } from './macroMappings';
import {
	agreementOf,
	bucketOf,
	buildExposureMatrixRows,
	buildMacroGlanceView,
	buildMacroLensSnapshot,
	buildMacroPath,
	buildMarketMacroLensSnapshot,
	buildRegimeQuadrant,
	buildRegimeView,
	focusChannelAlignment,
	pickFocusCell,
	transitionFraction,
	type MacroChannel,
	type MacroDriverView,
	type MacroExposureMatrixRow,
	type MacroTransmissionEdgeView
} from './macroLens';
import type { Company, MacroFile, MacroRegimeModel, MacroRegimePayload, MacroSide } from './types';

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

// ───────────────────────── 국면 렌즈 (Regime Lens · 초강화) view-model ─────────────────────────
// 라이브 macro.json 은 regime 키 미보유(prebuild deploy 시 주입). 합성 fixture(실 payload shape)로 검증.

const usModels = (): Record<string, MacroRegimeModel> => ({
	probit: { probability: 0.18, probabilityRounded: 0.2, zone: 'low', zoneLabel: '낮음', spread: 0.4, horizon: '12M', timeKind: 'leading', precisionNote: 'Estrella-Mishkin 고정계수·표준오차 미산출', asOf: '2026-06-15', seriesId: 'T10Y3M', staleAfterDays: 7 },
	sahm: { value: 0.1, triggered: false, zone: 'normal', zoneLabel: '정상', horizon: 'realtime', timeKind: 'trigger(동행)', asOf: '2026-05-01', seriesId: 'UNRATE', staleAfterDays: 45 },
	lei: { signal: 'caution', signalLabel: '경계', mom6m: -1.2, availableComponents: 9, totalComponents: 10, overlapNote: 'term-spread·initial-claims 내포(probit/Sahm 부분 상관)', horizon: '6-9M', timeKind: 'leading', asOf: '2026-05', staleAfterDays: 75 },
	hamilton: { contractionProb: null, converged: false, separation: 0.31, iterations: 50, status: 'EM 미수렴', timeKind: 'retrospective', horizon: '동행', staleAfterDays: 120, revisionLabel: '분기 GDP·수정 대상', asOf: '2026-Q1', seriesId: 'A191RL1Q225SBEA', seriesSource: 'FRED' }
});

const usRegimePayload = (overrides: Partial<MacroRegimePayload> = {}): MacroRegimePayload => ({
	market: 'US',
	computedAt: '2026-06-18T00:00:00Z',
	forecast: { models: usModels(), missing: [] },
	rates: { spread10y3m: 0.4, sign: '+', curveShape: 'flat', curveShapeLabel: '평탄', curveSource: 'NelsonSiegel.interpretation', asOf: '2026-06-15', seriesId: 'T10Y3M', staleAfterDays: 7, missing: [] },
	gar: { gar5: -1.5, gar25: 0.4, median: 2.1, gar75: 3.2, gar95: 4.4, skewness: -0.8, tailRisk: 'elevated', tailRiskLabel: '주의', currentFCI: 0.32, observations: 42, horizon: 4, timeKind: 'forward', seriesNote: 'FCI 조건부 GDP 성장률 분위(점추정 아닌 조건부 분포)', asOf: '2026-Q1', staleAfterDays: 120, revisionLabel: '분기 GDP·수정 대상' },
	regimeBand: { band: [0.05, 0.04, 0.06, 0.09, 0.14, 0.22, 0.31, 0.28, 0.19, 0.12, 0.08], converged: true, separation: 0.74, timeKind: 'retrospective', horizon: '동행', asOf: '2026-Q1', staleAfterDays: 120 },
	...overrides
});

const krRegimePayload = (): MacroRegimePayload => ({
	market: 'KR',
	computedAt: '2026-06-18T00:00:00Z',
	forecast: {
		models: { lei: { cliMomentum: 1.1, cliLevel: 99.8, growthApprox: 1.4, growthLabel: '확장', asOf: '2026-04', staleAfterDays: 75 } },
		missing: [
			{ id: 'probit', status: 'notApplicable', reason: 'US 전용' },
			{ id: 'sahm', status: 'notApplicable', reason: 'US 전용' },
			{ id: 'hamilton', status: '단위 parity 미확정·표시 보류', reason: 'GROWTH↔A191RL1Q225SBEA 단위 동일성 미확정' },
			{ id: 'gar', status: 'notApplicable', reason: 'US 중심(FCI 입력)' }
		]
	},
	rates: { missing: [{ id: 'yieldCurve', status: 'notApplicable', reason: 'US 전용' }] }
});

const macroWithRegime = (us = usRegimePayload(), kr = krRegimePayload()): MacroFile => {
	const m = cloneMacro();
	m.regime = { kr, us };
	return m;
};

describe('macro regime view-model — transitionFraction', () => {
	it('emits an integer fraction triggered/(triggered+pending), never a percent', () => {
		const side = { transition: { from: 'slowdown', to: 'contraction', progress: 33, triggered: ['gold_surging'], pending: ['vix_spiking', 'term_spread_inverted'] } } as unknown as MacroSide;
		const frac = transitionFraction(side);
		expect(frac).not.toBeNull();
		expect(frac!.fraction).toBe('1/3 충족');
		expect(frac!.from).toBe('slowdown');
		expect(frac!.to).toBe('contraction');
		// 백분율·progress 노출 0 (L1757 % 경로 미재현).
		expect(frac!.fraction).not.toContain('%');
		expect(JSON.stringify(frac)).not.toContain('33');
	});
	it('returns null when transition is null (KR) → no fraction rendered', () => {
		expect(transitionFraction({ transition: null } as unknown as MacroSide)).toBeNull();
		expect(transitionFraction(undefined)).toBeNull();
		expect(transitionFraction(null)).toBeNull();
	});
});

describe('macro regime view-model — bucketOf (§3.3 3-step table)', () => {
	it('maps probit moderate → 0 (absorbed) and the full §3.3 table', () => {
		expect(bucketOf({ zone: 'low' })).toBe(0);
		expect(bucketOf({ zone: 'moderate' })).toBe(0); // 흡수
		expect(bucketOf({ zone: 'elevated' })).toBe(1);
		expect(bucketOf({ zone: 'high' })).toBe(2);
		expect(bucketOf({ zone: 'normal' })).toBe(0); // sahm
		expect(bucketOf({ zone: 'warning' })).toBe(1);
		expect(bucketOf({ zone: 'recession' })).toBe(2);
		expect(bucketOf({ signal: 'expansion' })).toBe(0); // lei
		expect(bucketOf({ signal: 'caution' })).toBe(1);
		expect(bucketOf({ signal: 'recession_warning' })).toBe(2);
		expect(bucketOf({ contractionProb: 0.1 })).toBe(0); // hamilton <0.25
		expect(bucketOf({ contractionProb: 0.4 })).toBe(1); // <0.5
		expect(bucketOf({ contractionProb: 0.6 })).toBe(2); // >=0.5
	});
	it('returns null for status-only / null models (excluded from agreement)', () => {
		expect(bucketOf({ status: 'EM 미수렴', contractionProb: null })).toBeNull();
		expect(bucketOf({ status: '데이터부족·표시 보류' })).toBeNull();
		expect(bucketOf(undefined)).toBeNull();
		expect(bucketOf(null)).toBeNull();
	});
});

describe('macro regime view-model — agreementOf (adjacent=agree, names disagreeing, no score)', () => {
	it('returns 교차 불가 with valid count when <2 valid', () => {
		expect(agreementOf([{ model: 'CLI', bucket: null }])).toBe('교차 불가 (유효 0개)');
		expect(agreementOf([{ model: 'probit', bucket: 0 }, { model: 'Sahm', bucket: null }])).toBe('교차 불가 (유효 1개)');
	});
	it('treats adjacent buckets (0-1, 1-2) as agreement', () => {
		const txt = agreementOf([{ model: 'probit', bucket: 0 }, { model: 'LEI', bucket: 1 }]);
		expect(txt).toContain('동의');
		expect(txt).not.toContain('vs');
	});
	it('names the disagreeing models when ≥2 buckets apart', () => {
		const txt = agreementOf([
			{ model: 'probit', bucket: 0 },
			{ model: 'Sahm', bucket: 0 },
			{ model: 'LEI', bucket: 2 }
		]);
		expect(txt).toContain('LEI');
		expect(txt).toContain('침체');
		expect(txt).toContain('vs');
	});
	it('renders no ordinal/score/badge token (verdict backdoor guard)', () => {
		const txt = agreementOf([{ model: 'probit', bucket: 0 }, { model: 'LEI', bucket: 2 }]);
		expect(txt).not.toMatch(/\/100|score|badge|점수/i);
		expect(txt).not.toMatch(/\b[0-2]\b/); // 서수 bucket 숫자 비노출
	});
});

describe('macro regime view-model — focusChannelAlignment (narrative only, no 수혜/sensitivity)', () => {
	const focusOf = (channel: MacroChannel, sign: MacroTransmissionEdgeView['sign']) =>
		({ channel, edge: { sign } });
	it('describes alignment when edge sign positive', () => {
		const txt = focusChannelAlignment({ growth: 'rising', inflation: 'rising' }, focusOf('revenue', 'positive'));
		expect(txt).toContain('정합');
		expect(txt).toContain('성장↑');
		expect(txt).not.toMatch(/수혜|유리|매수/);
		expect(txt).not.toMatch(/\d/); // 민감도 숫자 0
	});
	it('describes 역방향 when edge sign negative', () => {
		const txt = focusChannelAlignment({ growth: 'rising', inflation: 'rising' }, focusOf('balanceSheet', 'negative'));
		expect(txt).toContain('역방향');
		expect(txt).not.toMatch(/수혜|유리/);
	});
	it('returns null when no quadrant or no focusCell', () => {
		expect(focusChannelAlignment(null, focusOf('revenue', 'positive'))).toBeNull();
		expect(focusChannelAlignment({ growth: 'rising' }, null)).toBeNull();
		expect(focusChannelAlignment({ growth: 'stable' }, focusOf('revenue', 'positive'))).toBeNull();
	});
});

describe('macro regime view-model — buildRegimeView (US confluence, KR asymmetry)', () => {
	it('is undefined-safe when macro.regime is absent (renders nothing)', () => {
		const view = buildRegimeView(macro, null);
		expect(view.available).toBe(false);
		expect(view.us).toBeNull();
		expect(view.kr).toBeNull();
		// 전향 분수는 macro.us.transition 라이브라 regime 없어도 시도(라이브 macro 는 transition 부재 → null 가능).
	});
	it('builds 4 US confluence tiles with own horizon/timing, no single 12M frame', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		expect(view.available).toBe(true);
		expect(view.us!.tiles).toHaveLength(4);
		expect(view.us!.totalCount).toBe(4);
		// hamilton status-only → suppressed, validCount=3 (probit/sahm/lei).
		expect(view.us!.validCount).toBe(3);
		const ham = view.us!.tiles.find((t) => t.model === 'hamilton')!;
		expect(ham.suppressed).toBe(true);
		expect(ham.zoneLabel).toBe('표시 보류');
		// 각 타일이 자기 호라이즌 (단일 '12M·확률' 프레임 아님).
		const probit = view.us!.tiles.find((t) => t.model === 'probit')!;
		const sahm = view.us!.tiles.find((t) => t.model === 'sahm')!;
		const lei = view.us!.tiles.find((t) => t.model === 'lei')!;
		expect(probit.horizonLabel).toContain('12M');
		expect(probit.horizonLabel).toContain('leading');
		expect(sahm.horizonLabel).toContain('realtime');
		expect(lei.horizonLabel).toContain('6-9M');
		expect(ham.horizonLabel).toContain('retrospective');
	});
	it('probit zone is primary, probability 5%p rounded is secondary, precisionNote in title', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		const probit = view.us!.tiles.find((t) => t.model === 'probit')!;
		expect(probit.zoneLabel).toBe('낮음'); // zone 주역
		expect(probit.secondary).toBe('~20%'); // probabilityRounded
		expect(probit.note).toContain('표준오차 미산출'); // precisionNote
		// 소수 2자리(0.18) 단독 노출 0.
		expect(probit.secondary).not.toContain('18');
		expect(probit.secondary).not.toContain('0.1');
	});
	it('LEI tile carries overlapNote (partial correlation, not fully independent)', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		const lei = view.us!.tiles.find((t) => t.model === 'lei')!;
		expect(lei.note).toContain('내포');
		expect(lei.note).toMatch(/term-spread|initial-claims/);
	});
	it('yield curve note carries the double-count guard, agreement counts probit once', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		expect(view.us!.yieldCurve).not.toBeNull();
		expect(view.us!.yieldCurve!.note).toContain('동일곡선');
		expect(view.us!.yieldCurve!.note).toContain('독립 신호 아님');
		// agreement 는 텍스트만(점수·badge 0).
		expect(view.us!.agreement).not.toMatch(/\/100|score|badge/i);
	});
	it('GaR renders all 5 quantiles + skewness + tailRisk + 4Q forward (no single-number collapse, fan allowed)', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		const gar = view.us!.gar!;
		expect(gar.available).toBe(true);
		expect(gar.bars.map((b) => b.key)).toEqual(['gar5', 'gar25', 'median', 'gar75', 'gar95']);
		expect(gar.bars.find((b) => b.key === 'median')!.value).toBe(2.1); // median 동반
		expect(gar.skewness).toBe(-0.8);
		expect(gar.tailRiskLabel).toBe('주의');
		expect(gar.horizonLabel).toContain('4Q 전향');
	});
	it('GaR hides when status-only (표본 부족)', () => {
		const view = buildRegimeView(macroWithRegime(usRegimePayload({ gar: { status: '표본 부족·표시 보류' } })), null);
		expect(view.us!.gar).toBeNull();
	});
	it('regime band is a ≤24-point sparkline with 회고적·smoothed caption (not bars/point-est)', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		const band = view.us!.band!;
		expect(band.available).toBe(true);
		expect(band.points.length).toBeLessThanOrEqual(24);
		expect(band.points.length).toBe(11);
		expect(band.caption).toContain('회고적');
		expect(band.caption).toContain('smoothed');
	});
	it('quadrant direction shows growth/inflation labels + assets, raw signals never exposed', () => {
		// 합성 us.quadrant 부착(라이브 macro.us.quadrant 존재 여부 무관 — fixture 명시).
		const m = macroWithRegime();
		m.us = { ...m.us, quadrant: { quadrant: 'reflation', quadrantLabel: '리플레이션', growth: 'rising', inflation: 'rising', growthSignal: 662678, inflationSignal: 26.71, assetImplication: { commodity: 'overweight', bond: 'underweight' }, description: '' } } as unknown as MacroSide;
		const view = buildRegimeView(m, { channel: 'revenue', edge: { sign: 'positive' } });
		const q = view.us!.quadrant!;
		expect(q.growthLabel).toBe('성장↑');
		expect(q.inflationLabel).toBe('물가↑');
		expect(q.alignment).toContain('정합');
		// raw growthSignal/inflationSignal 비노출.
		const json = JSON.stringify(q);
		expect(json).not.toContain('662678');
		expect(json).not.toContain('26.71');
	});
	it('KR confluence is CLI momentum 1 tile; hamilton in missing as 단위 parity 미확정', () => {
		const view = buildRegimeView(macroWithRegime(), null);
		expect(view.kr!.tiles).toHaveLength(1);
		expect(view.kr!.tiles[0].modelName).toBe('CLI momentum');
		// KR 은 yieldCurve/GaR/band 없음(US 중심).
		expect(view.kr!.yieldCurve).toBeNull();
		expect(view.kr!.gar).toBeNull();
		expect(view.kr!.band).toBeNull();
		// hamilton/probit/sahm/gar 은 빈 셀 아닌 명시 라벨.
		const ham = view.kr!.notApplicable.find((n) => n.id === 'hamilton')!;
		expect(ham.reason).toContain('단위');
		const probit = view.kr!.notApplicable.find((n) => n.id === 'probit')!;
		expect(probit.reason).toContain('US 전용');
		// CLI 1타일뿐이라 교차 불가.
		expect(view.kr!.agreement).toContain('교차 불가');
	});
	it('snapshot.regime is wired and undefined-safe on the live (regime-less) macro.json', () => {
		const snapshot = buildMarketMacroLensSnapshot({ macro, macroLatest: macroLatest(), sectorTailwinds: sectorTailwinds() });
		expect(snapshot.regime).toBeDefined();
		expect(snapshot.regime!.available).toBe(false); // 라이브 macro 는 regime 미보유.
		const withRegime = buildMarketMacroLensSnapshot({ macro: macroWithRegime(), macroLatest: macroLatest(), sectorTailwinds: sectorTailwinds() });
		expect(withRegime.regime!.available).toBe(true);
		expect(withRegime.regime!.us!.tiles).toHaveLength(4);
	});
});
