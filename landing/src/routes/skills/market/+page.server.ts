import fs from 'node:fs';
import path from 'node:path';
import type { MarketIndex } from '$lib/skills/marketCatalog';

export const prerender = true;

function readMarketIndex(): MarketIndex {
	const filePath = path.resolve(process.cwd(), 'static', 'skills', 'market', 'marketIndex.json');
	try {
		return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as MarketIndex;
	} catch {
		return {
			meta: {
				schemaVersion: '1',
				source: 'local-empty',
				skillCount: 0,
				trustPolicy: 'community market entries are untrusted until curated'
			},
			skills: []
		};
	}
}

export function load() {
	return {
		market: readMarketIndex()
	};
}
