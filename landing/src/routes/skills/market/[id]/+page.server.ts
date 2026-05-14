import fs from 'node:fs';
import path from 'node:path';
import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';
import type { MarketIndex, MarketSkill } from '$lib/skills/marketCatalog';

export const prerender = 'auto';

function readMarketIndex(): MarketIndex {
	const filePath = path.resolve(process.cwd(), 'static', 'skills', 'market', 'marketIndex.json');
	try {
		return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as MarketIndex;
	} catch {
		return { skills: [] };
	}
}

function readMarketItem(skill: MarketSkill): MarketSkill {
	if (!skill.itemPath) return skill;
	const filePath = path.resolve(process.cwd(), 'static', 'skills', 'market', skill.itemPath);
	try {
		return { ...skill, ...(JSON.parse(fs.readFileSync(filePath, 'utf-8')) as MarketSkill) };
	} catch {
		return skill;
	}
}

export const entries: EntryGenerator = () => {
	return (readMarketIndex().skills ?? []).map((skill) => ({ id: skill.id }));
};

export function load({ params }: { params: { id: string } }) {
	const skills = (readMarketIndex().skills ?? []) as MarketSkill[];
	const skill = skills.find((item) => item.id === params.id);
	if (!skill) {
		throw error(404, `unknown market skill: ${params.id}`);
	}
	return { skill: readMarketItem(skill) };
}
