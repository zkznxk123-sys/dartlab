import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';
import { allSkillIds, getSkillComponent, getSkillMeta, getSkillRaw, getSkillSourcePath } from '$lib/skills/catalog';

export const prerender = true;

export const entries: EntryGenerator = () => {
	return allSkillIds().map((id) => ({ id }));
};

export function load({ params }: { params: { id: string } }) {
	const meta = getSkillMeta(params.id);
	const component = getSkillComponent(params.id);
	if (!meta || !component) {
		throw error(404, `unknown skill: ${params.id}`);
	}
	return {
		id: params.id,
		meta,
		component,
		raw: getSkillRaw(params.id) ?? '',
		sourcePath: getSkillSourcePath(params.id) ?? ''
	};
}
