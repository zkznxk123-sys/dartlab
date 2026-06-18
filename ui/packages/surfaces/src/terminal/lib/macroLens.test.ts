import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CURRENT_MACRO_EDGE_SECTOR_KEYS, EDGE_SECTOR_TO_TAILWIND } from './macroMappings';
import { buildMacroGlanceView, buildMacroPath, buildRegimeQuadrant } from './macroLens';
import type { MacroFile } from './types';

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
});
