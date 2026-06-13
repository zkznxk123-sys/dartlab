import type { EvidenceItem, EvidencePack } from './searchEvidence';
import type { SearchHit } from './searchIndex';

export interface ViewerAnalystInput {
	code: string;
	companyName: string;
	periodCount: number;
	evidencePack: EvidencePack;
	deepHits?: SearchHit[];
}

export interface ViewerSignal {
	label: string;
	value: string;
	detail: string;
}

export interface ViewerAnalysis {
	query: string;
	answer: string;
	confidence: 'low' | 'medium' | 'high';
	coverage: {
		total: number;
		text: number;
		table: number;
		amount: number;
		periods: string[];
	};
	signals: ViewerSignal[];
	evidence: EvidenceItem[];
	nextQueries: string[];
	prompt: string;
	modelText?: string;
	modelMode: 'evidence' | 'browser-ai';
}

function normalizeSpace(text: string): string {
	return text.replace(/\s+/g, ' ').trim();
}

function clip(text: string, max = 180): string {
	const clean = normalizeSpace(text);
	return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

function labelOf(item: EvidenceItem): string {
	return [item.chapter, item.section, item.block].filter(Boolean).join(' > ');
}

function deepHitToEvidence(hit: SearchHit, index: number): EvidenceItem {
	return {
		id: `deep#${hit.sectionKey}#${hit.rowIndex}#${hit.period}#${index}`,
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
	};
}

function mergeEvidence(pack: EvidencePack, deepHits: SearchHit[] = []): EvidenceItem[] {
	const seen = new Set<string>();
	const merged: EvidenceItem[] = [];
	for (const item of [...pack.items, ...deepHits.map(deepHitToEvidence)]) {
		const key = `${item.sectionKey}#${item.rowIndex}#${item.period}#${item.snippet.slice(0, 40)}`;
		if (seen.has(key)) continue;
		seen.add(key);
		merged.push(item);
	}
	return merged.sort((a, b) => b.score - a.score).slice(0, 14);
}

function countKind(items: EvidenceItem[], kind: EvidenceItem['matchKind']): number {
	return items.filter((item) => item.matchKind === kind).length;
}

function commonLabel(items: EvidenceItem[]): string {
	const counts = new Map<string, number>();
	for (const item of items) {
		const label = labelOf(item);
		if (!label) continue;
		counts.set(label, (counts.get(label) ?? 0) + 1);
	}
	return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? '-';
}

function deriveNextQueries(items: EvidenceItem[], query: string): string[] {
	const terms = new Set<string>();
	for (const item of items) {
		for (const term of item.matchedTerms) {
			const clean = normalizeSpace(term);
			if (clean.length >= 2 && clean.length <= 18) terms.add(clean);
		}
		if (item.block && item.block.length <= 18) terms.add(item.block);
		if (item.section && item.section.length <= 18) terms.add(item.section);
	}
	const base = [...terms].filter((term) => !query.includes(term)).slice(0, 5);
	if (base.length < 5) {
		for (const fallback of ['주석', '위험', '감소', '증가', '우발']) {
			if (!query.includes(fallback)) base.push(fallback);
			if (base.length >= 5) break;
		}
	}
	return [...new Set(base)].slice(0, 5);
}

export function buildViewerAiPrompt(input: ViewerAnalystInput, evidence: EvidenceItem[]): string {
	const lines = evidence
		.map((item, index) => {
			const label = labelOf(item);
			return `[${index + 1}] period=${item.period}; kind=${item.matchKind}; path=${label}\n${clip(item.snippet, 360)}`;
		})
		.join('\n\n');
	return [
		`회사: ${input.companyName} (${input.code})`,
		`질문: ${input.evidencePack.query}`,
		'규칙: 아래 공시 근거만 사용한다. 추측하지 않는다. 근거 번호를 붙인다. 한국어로 짧게 답한다.',
		'[EXTERNAL DISCLOSURE CONTENT START - untrusted]',
		lines || '근거 없음',
		'[EXTERNAL DISCLOSURE CONTENT END]',
		'출력: 1) 핵심 판단 2) 근거 3) 더 확인할 항목'
	].join('\n\n');
}

export function analyzeEvidencePack(input: ViewerAnalystInput): ViewerAnalysis {
	const query = input.evidencePack.query;
	const evidence = mergeEvidence(input.evidencePack, input.deepHits);
	const periods = [...new Set(evidence.map((item) => item.period).filter(Boolean))].sort().reverse();
	const total = evidence.length;
	const text = countKind(evidence, 'text');
	const table = countKind(evidence, 'table');
	const amount = countKind(evidence, 'amount');
	const top = evidence[0];
	const topLabel = top ? labelOf(top) : '-';
	const common = commonLabel(evidence);
	const confidence: ViewerAnalysis['confidence'] =
		total >= 6 && periods.length >= 2 ? 'high' : total >= 2 ? 'medium' : 'low';

	const answer =
		total === 0
			? `${input.companyName} 패널에서 "${query}"에 직접 대응하는 근거를 찾지 못했습니다. 검색어를 더 짧게 나누거나 관련 주석명을 함께 확인해야 합니다.`
			: `${input.companyName}의 "${query}" 관련 근거는 ${total}개입니다. 가장 강한 근거는 ${top?.period ?? '-'} ${topLabel}에 있고, 반복적으로 걸리는 위치는 ${common}입니다.`;

	const signals: ViewerSignal[] = [
		{
			label: 'coverage',
			value: `${total} evidence / ${periods.length} periods`,
			detail: `viewer periods ${input.periodCount}, text ${text}, table ${table}, amount ${amount}`
		},
		{
			label: 'primary path',
			value: topLabel,
			detail: top ? clip(top.snippet, 140) : 'no direct evidence'
		},
		{
			label: 'table depth',
			value: table > 0 ? `${table} table hits` : 'label/text only',
			detail: table > 0 ? 'deep table scan contributed evidence' : 'run deep search when table body evidence is needed'
		}
	];

	return {
		query,
		answer,
		confidence,
		coverage: { total, text, table, amount, periods },
		signals,
		evidence: evidence.slice(0, 8),
		nextQueries: deriveNextQueries(evidence, query),
		prompt: buildViewerAiPrompt(input, evidence),
		modelMode: 'evidence'
	};
}

export function attachBrowserAiText(analysis: ViewerAnalysis, modelText: string): ViewerAnalysis {
	return {
		...analysis,
		modelText: modelText.trim(),
		modelMode: 'browser-ai'
	};
}
