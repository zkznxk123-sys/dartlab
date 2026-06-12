import type { ViewerSearchHit } from './searchIndex';

type EvidenceTopicId = 'dividend' | 'debt' | 'legal' | 'audit' | 'capital' | 'workforce' | 'generic';

interface TopicRule {
	id: EvidenceTopicId;
	label: string;
	terms: string[];
	amountLabels: string[];
}

interface EvidenceLine {
	period: string;
	path: string;
	text: string;
	amounts: string[];
}

export interface EvidenceSkillAnswer {
	topic: EvidenceTopicId;
	label: string;
	confidence: 'high' | 'medium' | 'low';
	lines: EvidenceLine[];
	amounts: Array<{ period: string; value: string; source: string }>;
}

const TOPIC_RULES: TopicRule[] = [
	{
		id: 'dividend',
		label: '배당 근거',
		terms: ['배당', '배당금', '현금배당', '배당성향', '배당수익률', 'dps', '주주환원'],
		amountLabels: ['배당금', 'DPS', '환원'],
	},
	{
		id: 'debt',
		label: '부채 · 차입 근거',
		terms: ['부채', '차입', '사채', '채무', '우발부채', '지급보증', '리스부채'],
		amountLabels: ['부채', '차입', '사채'],
	},
	{
		id: 'legal',
		label: '소송 · 분쟁 근거',
		terms: ['소송', '분쟁', '피소', '제소', '손해배상', '계류', '제재'],
		amountLabels: ['청구', '손해배상'],
	},
	{
		id: 'audit',
		label: '감사 · 내부통제 근거',
		terms: ['감사', '감사의견', '내부회계', '외부감사', '감사인'],
		amountLabels: ['감사'],
	},
	{
		id: 'capital',
		label: '자본거래 근거',
		terms: ['자사주', '자기주식', '증자', '전환사채', '신주인수권', '교환사채'],
		amountLabels: ['자기주식', '증자', '전환사채'],
	},
	{
		id: 'workforce',
		label: '인력 · 보수 근거',
		terms: ['직원', '임직원', '급여', '보수', '주식매수선택권', '스톡옵션'],
		amountLabels: ['급여', '보수'],
	},
];

const KRW_AMOUNT_RE =
	/(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(조|억)\s*(?:원|(?:\d{1,3}(?:,\d{3})*)\s*억\s*원?)?/g;

function normalize(text: string): string {
	return text.toLowerCase();
}

function hitHaystack(hit: ViewerSearchHit): string {
	return normalize(`${hit.chapter} ${hit.section} ${hit.block} ${hit.snippet}`);
}

function detectTopic(question: string, hits: ViewerSearchHit[]): TopicRule {
	const hay = normalize(`${question} ${hits.slice(0, 3).map(hitHaystack).join(' ')}`);
	let best: { rule: TopicRule; score: number } | null = null;
	for (const rule of TOPIC_RULES) {
		const score = rule.terms.reduce((sum, term) => (hay.includes(normalize(term)) ? sum + 1 : sum), 0);
		if (score > 0 && (!best || score > best.score)) best = { rule, score };
	}
	return best?.rule ?? { id: 'generic', label: '공시 근거', terms: [], amountLabels: [] };
}

function sourcePath(hit: ViewerSearchHit): string {
	return `${hit.chapter} > ${hit.section}${hit.block ? ` > ${hit.block}` : ''}`;
}

function compactText(text: string): string {
	return text.replace(/\s+/g, ' ').trim();
}

function pickFragment(hit: ViewerSearchHit, terms: string[]): string {
	const text = compactText(hit.snippet);
	if (!terms.length) return text.slice(0, 180);
	const lower = normalize(text);
	const at = terms
		.map((term) => lower.indexOf(normalize(term)))
		.filter((pos) => pos >= 0)
		.sort((a, b) => a - b)[0];
	if (at == null) return text.slice(0, 180);
	return text.slice(Math.max(0, at - 36), Math.min(text.length, at + 156));
}

function extractAmounts(text: string): string[] {
	const amounts = new Set<string>();
	KRW_AMOUNT_RE.lastIndex = 0;
	let match: RegExpExecArray | null;
	while ((match = KRW_AMOUNT_RE.exec(text)) !== null) {
		const value = match[0].replace(/\s+/g, ' ').trim();
		if (value.length >= 3) amounts.add(value);
		if (amounts.size >= 3) break;
	}
	return [...amounts];
}

function confidenceFor(rule: TopicRule, hits: ViewerSearchHit[]): EvidenceSkillAnswer['confidence'] {
	if (!hits.length) return 'low';
	if (rule.id === 'generic') return 'medium';
	const topHay = hitHaystack(hits[0]);
	if (rule.terms.some((term) => topHay.includes(normalize(term)))) return 'high';
	return 'medium';
}

function hitKey(hit: ViewerSearchHit): string {
	return `${hit.sectionKey}\u0000${hit.rowIndex}\u0000${hit.period}\u0000${hit.block}`;
}

export function prioritizeEvidenceSkillHits(question: string, hits: ViewerSearchHit[]): ViewerSearchHit[] {
	if (!hits.length) return hits;
	const rule = detectTopic(question, hits);
	if (rule.id === 'generic') return hits;
	const topicHits = hits.filter((hit) => rule.terms.some((term) => hitHaystack(hit).includes(normalize(term))));
	if (!topicHits.length) return hits;
	const topicKeys = new Set(topicHits.map(hitKey));
	return [...topicHits, ...hits.filter((hit) => !topicKeys.has(hitKey(hit)))];
}

export function buildEvidenceSkillAnswer(question: string, hits: ViewerSearchHit[]): EvidenceSkillAnswer | null {
	if (!hits.length) return null;
	const rule = detectTopic(question, hits);
	const topicHits =
		rule.id === 'generic'
			? hits
			: hits.filter((hit) => rule.terms.some((term) => hitHaystack(hit).includes(normalize(term))));
	const sourceHits = topicHits.length ? topicHits : hits;
	const lines = sourceHits.slice(0, 5).map((hit) => {
		const text = pickFragment(hit, rule.terms);
		return {
			period: hit.period,
			path: sourcePath(hit),
			text,
			amounts: extractAmounts(text),
		};
	});
	const amounts = lines.flatMap((line) =>
		line.amounts.map((value) => ({
			period: line.period,
			value,
			source: line.path,
		})),
	);
	return {
		topic: rule.id,
		label: rule.label,
		confidence: confidenceFor(rule, hits),
		lines,
		amounts: amounts.slice(0, 6),
	};
}

export function formatEvidenceSkillAnswer(question: string, hits: ViewerSearchHit[]): string {
	const answer = buildEvidenceSkillAnswer(question, hits);
	if (!answer) {
		return `'${question}' 관련 근거를 현재 공시 색인에서 찾지 못했습니다. 회사/기간 또는 핵심어를 좁혀 다시 질문하세요.`;
	}
	const header = `근거 스킬 · ${answer.label} · 신뢰도 ${answer.confidence}`;
	const amountLines = answer.amounts.length
		? ['확인된 숫자', ...answer.amounts.slice(0, 4).map((item) => `- ${item.period} · ${item.value} · ${item.source}`)]
		: [];
	const evidenceLines = [
		`근거 ${answer.lines.length}건`,
		...answer.lines.map((line, i) => `- ${i + 1}. ${line.period} · ${line.path}\n  ${line.text}`),
	];
	return [header, ...amountLines, ...evidenceLines].join('\n');
}
