import { search, type SearchHit, type SearchIndex } from './searchIndex';

export interface EvidenceItem {
	id: string;
	sectionKey: string;
	rowIndex: number;
	period: string;
	chapter: string;
	section: string;
	block: string;
	scope: string;
	score: number;
	matchKind: SearchHit['matchKind'];
	snippet: string;
	matchedTerms: string[];
}

export interface EvidencePack {
	query: string;
	items: EvidenceItem[];
	addedTerms: string[];
	stats: {
		total: number;
		text: number;
		table: number;
		amount: number;
	};
	contextText: string;
}

export interface EvidenceOpts {
	topK?: number;
	expand?: boolean;
}

function evidenceLabel(item: EvidenceItem): string {
	return [item.chapter, item.section, item.block].filter(Boolean).join(' > ');
}

export function buildEvidencePack(index: SearchIndex, query: string, opts: EvidenceOpts = {}): EvidencePack {
	const { hits, added } = search(index, query, { topK: opts.topK ?? 12, expand: opts.expand ?? true });
	const seen = new Set<string>();
	const items: EvidenceItem[] = [];
	for (const hit of hits) {
		const id = `${hit.sectionKey}#${hit.rowIndex}#${hit.period}`;
		if (seen.has(id)) continue;
		seen.add(id);
		items.push({
			id,
			sectionKey: hit.sectionKey,
			rowIndex: hit.rowIndex,
			period: hit.period,
			chapter: hit.chapter,
			section: hit.section,
			block: hit.block,
			scope: hit.scope,
			score: hit.score,
			matchKind: hit.matchKind,
			snippet: hit.snippet,
			matchedTerms: hit.matchedTerms
		});
	}
	const stats = {
		total: items.length,
		text: items.filter((item) => item.matchKind === 'text').length,
		table: items.filter((item) => item.matchKind === 'table').length,
		amount: items.filter((item) => item.matchKind === 'amount').length
	};
	const contextText = items
		.map((item, i) => {
			const label = evidenceLabel(item);
			return `[${i + 1}] ${item.period} ${label}\n${item.snippet}`;
		})
		.join('\n\n');
	return { query, items, addedTerms: added, stats, contextText };
}

function escapeRegExp(text: string): string {
	return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export interface HighlightPart {
	text: string;
	hit: boolean;
}

export function highlightParts(text: string, terms: string[]): HighlightPart[] {
	const needles = [...new Set(terms.map((term) => term.trim()).filter((term) => term.length >= 2))].sort((a, b) => b.length - a.length);
	if (!text || needles.length === 0) return [{ text, hit: false }];
	const lowered = new Set(needles.map((term) => term.toLowerCase()));
	const re = new RegExp(`(${needles.map(escapeRegExp).join('|')})`, 'gi');
	return text
		.split(re)
		.filter((part) => part.length > 0)
		.map((part) => ({ text: part, hit: lowered.has(part.toLowerCase()) }));
}
