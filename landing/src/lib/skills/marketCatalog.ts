export const marketTierOrder = [
	'marketCurated',
	'marketRunnable',
	'marketDraft',
	'needsDetail',
	'builtinCandidate',
	'blocked'
] as const;

export const marketTierTitle: Record<string, string> = {
	marketCurated: 'Curated',
	marketRunnable: 'Runnable',
	marketDraft: 'Draft',
	needsDetail: 'Needs Detail',
	builtinCandidate: 'Builtin Candidates',
	blocked: 'Blocked'
};

export interface MarketCredits {
	originator?: string[];
	coAuthor?: string[];
	reviewer?: string[];
	curator?: string[];
	implementer?: string[];
}

export interface MarketSkill {
	id: string;
	title: string;
	summary?: string;
	intent?: string;
	inputs?: string[];
	outputs?: string[];
	criteria?: string[];
	examples?: string[];
	tags?: string[];
	state?: string;
	trustTier?: string;
	missingDetails?: string[];
	warnings?: string[];
	mappedBuiltinSkills?: string[];
	sourceType?: string;
	sourceUrl?: string;
	discussionNumber?: number;
	author?: string;
	createdAt?: string;
	updatedAt?: string;
	credits?: MarketCredits;
}

export interface MarketIndex {
	meta?: {
		schemaVersion?: string;
		source?: string;
		category?: string;
		generatedAt?: string | null;
		skillCount?: number;
		trustPolicy?: string;
		emptyReason?: string;
	};
	skills?: MarketSkill[];
}

export function displayTier(skill: MarketSkill): string {
	if ((skill.missingDetails?.length ?? 0) > 0 && skill.trustTier === 'marketDraft') {
		return 'needsDetail';
	}
	return skill.trustTier || 'marketDraft';
}

export function tierLabel(skill: MarketSkill): string {
	return marketTierTitle[displayTier(skill)] ?? displayTier(skill);
}

export function marketSkillMatches(skill: MarketSkill, query: string): boolean {
	const q = query.trim().toLowerCase();
	if (!q) return true;
	const haystack = [
		skill.id,
		skill.title,
		skill.summary,
		skill.intent,
		...(skill.inputs ?? []),
		...(skill.outputs ?? []),
		...(skill.criteria ?? []),
		...(skill.tags ?? []),
		...(skill.mappedBuiltinSkills ?? [])
	]
		.filter(Boolean)
		.join(' ')
		.toLowerCase();
	return haystack.includes(q);
}
