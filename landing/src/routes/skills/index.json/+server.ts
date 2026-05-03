import { error, json } from '@sveltejs/kit';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const prerender = true;

export function GET() {
	try {
		const filePath = resolve(process.cwd(), '..', 'skills', 'index.json');
		return json(JSON.parse(readFileSync(filePath, 'utf-8')));
	} catch {
		throw error(500, 'Skill catalog is missing. Run scripts/build/generateSkills.py.');
	}
}
