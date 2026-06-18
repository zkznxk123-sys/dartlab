import type { Tone } from './types';

export interface EdgeSectorMapEntry {
	industryId: string | null;
	tailwindKey: string | null;
	kr: string;
	en: string;
}

// Terminal industry id -> macro.sectorTailwind key.
export const INDUSTRY_TAILWIND_MAP: Record<string, string> = {
	auto: 'automotive',
	pharma: 'biotech',
	chemical: 'chemicals',
	construction: 'construction',
	electronics: 'display',
	energy: 'energy',
	finance: 'finance',
	software: 'it_software',
	retail: 'retail',
	semiconductor: 'semiconductor',
	shipbuilding: 'shipbuilding',
	steel: 'steel',
	battery: 'chemicals',
	telecom: 'it_software'
};

// Current v19 transmission sector key coverage. Weak semantic joins are explicit nulls.
export const EDGE_SECTOR_TO_TAILWIND: Record<string, EdgeSectorMapEntry> = {
	semiconductor: { industryId: 'semiconductor', tailwindKey: 'semiconductor', kr: '반도체', en: 'Semiconductors' },
	auto: { industryId: 'auto', tailwindKey: 'automotive', kr: '자동차', en: 'Automobile' },
	shipbuilding: { industryId: 'shipbuilding', tailwindKey: 'shipbuilding', kr: '조선', en: 'Shipbuilding' },
	chemical: { industryId: 'chemical', tailwindKey: 'chemicals', kr: '화학', en: 'Chemicals' },
	battery: { industryId: 'battery', tailwindKey: 'chemicals', kr: '2차전지', en: 'Batteries' },
	logistics: { industryId: 'logistics', tailwindKey: null, kr: '물류', en: 'Logistics' },
	finance: { industryId: 'finance', tailwindKey: 'finance', kr: '금융', en: 'Financials' },
	bank: { industryId: 'finance', tailwindKey: 'finance', kr: '은행', en: 'Banks' },
	food: { industryId: 'food', tailwindKey: 'retail', kr: '음식료', en: 'Food & Bev' },
	energy: { industryId: 'energy', tailwindKey: 'energy', kr: '에너지', en: 'Energy' },
	utility: { industryId: null, tailwindKey: null, kr: '유틸리티', en: 'Utilities' },
	retail: { industryId: 'retail', tailwindKey: 'retail', kr: '유통', en: 'Retail' },
	all: { industryId: null, tailwindKey: null, kr: '전 섹터', en: 'All sectors' }
};

export const CURRENT_MACRO_EDGE_SECTOR_KEYS = Object.freeze(Object.keys(EDGE_SECTOR_TO_TAILWIND));

export type TailwindBucket = 'tailwind' | 'weakTailwind' | 'neutral' | 'headwind';

export interface TailwindClass {
	bucket: TailwindBucket;
	labelKr: string;
	labelEn: string;
	tone: Tone;
}

export function classifyTailwind(blended: number): TailwindClass {
	if (blended < 0) return { bucket: 'headwind', labelKr: '역풍', labelEn: 'headwind', tone: 'down' };
	if (blended >= 0.4) return { bucket: 'tailwind', labelKr: '순풍', labelEn: 'tailwind', tone: 'up' };
	if (blended > 0) return { bucket: 'weakTailwind', labelKr: '상대 약순풍', labelEn: 'relative weak tailwind', tone: 'good' };
	return { bucket: 'neutral', labelKr: '중립', labelEn: 'neutral', tone: 'neutral' };
}

export function hasNegativeTailwind(rows: { blended: number }[]): boolean {
	return rows.some((row) => row.blended < 0);
}
