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

export interface MarketExecutionStep {
	step?: number;
	engine?: string | null;
	purpose?: string;
	inputs?: string[];
	outputs?: string[];
	failureMode?: string | null;
}

export interface MarketSkill {
	id: string;
	title: string;
	summary?: string;
	intent?: string;
	inputs?: string[];
	dataSources?: string[];
	procedure?: string[];
	executionPlan?: MarketExecutionStep[];
	outputs?: string[];
	outputSchema?: string[];
	criteria?: string[];
	forbidden?: string[];
	completionCriteria?: string[];
	canonicalSource?: string;
	itemPath?: string;
	acceptedAt?: string;
	version?: number;
	canonicalUpdatedAt?: string;
	finalizedAt?: string;
	revisionStatus?: string;
	pendingCommentCount?: number;
	pendingCommentUrls?: string[];
	pendingSince?: string | null;
	revisionPolicy?: string;
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
		...(skill.dataSources ?? []),
		...(skill.procedure ?? []),
		...(skill.executionPlan ?? []).flatMap((step) => [
			step.engine ?? '',
			step.purpose ?? '',
			...(step.inputs ?? []),
			...(step.outputs ?? [])
		]),
		...(skill.outputs ?? []),
		...(skill.outputSchema ?? []),
		...(skill.criteria ?? []),
		...(skill.forbidden ?? []),
		...(skill.completionCriteria ?? []),
		...(skill.tags ?? []),
		...(skill.mappedBuiltinSkills ?? [])
	]
		.filter(Boolean)
		.join(' ')
		.toLowerCase();
	return haystack.includes(q);
}
