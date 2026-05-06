import skillIndex from '$skills/index.json';

export interface RuntimeEntry {
	status?: string;
	notes?: string[];
	limitations?: string[];
	dataSources?: string[];
}

export interface SkillDoc {
	id: string;
	title: string;
	category: string;
	categoryTitle?: string;
	status: string;
	purpose: string;
	whenToUse?: string[];
	inputs?: string[];
	requiredInputs?: string[];
	outputs?: string[];
	apiRefs?: string[];
	toolRefs?: string[];
	datasetRefs?: string[];
	knowledgeRefs?: string[];
	sourceRefs?: string[];
	procedure?: string[];
	requiredEvidence?: string[];
	expectedOutputs?: string[];
	visualGuidance?: string[];
	failureModes?: string[];
	forbidden?: string[];
	examples?: string[];
	runtimeCompatibility?: Record<string, RuntimeEntry>;
}

export interface SkillIndexMeta {
	entrySkillId?: string;
	canonicalSurface?: string;
	skillCount?: number;
	categories?: Array<{ id: string; title: string; description?: string; count: number }>;
	sourcePolicy?: string;
}

type SkillModule = {
	default: ConstructorOfATypedSvelteComponent;
	metadata?: Record<string, unknown>;
};

const components = import.meta.glob('$skills/specs/**/*.md', { eager: true }) as Record<string, SkillModule>;
const rawSources = import.meta.glob('$skills/specs/**/*.md', { eager: true, query: '?raw', import: 'default' }) as Record<string, string>;

function extractFrontmatterId(raw: string): string | undefined {
	if (!raw.startsWith('---')) return undefined;
	const end = raw.indexOf('\n---', 3);
	if (end < 0) return undefined;
	const block = raw.slice(3, end);
	const match = block.match(/^id:\s*(.+)$/m);
	if (!match) return undefined;
	return match[1].trim().replace(/^["']|["']$/g, '');
}

const componentsById = new Map<string, ConstructorOfATypedSvelteComponent>();
const rawById = new Map<string, string>();
const sourcePathById = new Map<string, string>();

for (const [path, raw] of Object.entries(rawSources)) {
	const id = extractFrontmatterId(raw);
	if (!id) continue;
	rawById.set(id, raw);
	sourcePathById.set(id, path);
	const mod = components[path];
	if (mod?.default) componentsById.set(id, mod.default);
}

export const skillsMeta: SkillIndexMeta = (skillIndex as { meta?: SkillIndexMeta }).meta ?? {};
export const skills: SkillDoc[] = ((skillIndex as { skills?: SkillDoc[] }).skills ?? []).filter(
	(skill) => skill.category !== 'capability'
);

const skillById = new Map<string, SkillDoc>(skills.map((skill) => [skill.id, skill]));

export function getSkillMeta(id: string): SkillDoc | undefined {
	return skillById.get(id);
}

export function getSkillComponent(id: string): ConstructorOfATypedSvelteComponent | undefined {
	return componentsById.get(id);
}

export function getSkillRaw(id: string): string | undefined {
	return rawById.get(id);
}

export function getSkillSourcePath(id: string): string | undefined {
	return sourcePathById.get(id);
}

export function allSkillIds(): string[] {
	return skills.map((skill) => skill.id);
}

export function findRelatedSkills(id: string, limit = 6): SkillDoc[] {
	const current = skillById.get(id);
	if (!current) return [];
	return skills
		.filter((skill) => skill.id !== id && skill.category === current.category)
		.slice(0, limit);
}

export function isCatalogSkillId(value: string): boolean {
	return skillById.has(value);
}
