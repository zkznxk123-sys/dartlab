import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';

const modules = import.meta.glob('@samples/*.md', { eager: true }) as Record<
	string,
	{ default: ConstructorOfATypedSvelteComponent; metadata?: Record<string, string> }
>;

const codeMap = new Map<
	string,
	{ component: ConstructorOfATypedSvelteComponent; metadata?: Record<string, string> }
>();

for (const [path, mod] of Object.entries(modules)) {
	const match = path.match(/\/samples\/(\d{6})\.md$/);
	if (!match) continue;
	codeMap.set(match[1], { component: mod.default, metadata: mod.metadata });
}

export const prerender = true;

export const entries: EntryGenerator = () =>
	[...codeMap.keys()].map((code) => ({ code }));

export function load({ params }: { params: { code: string } }) {
	const entry = codeMap.get(params.code);
	if (!entry) {
		throw error(404, `Sample ${params.code} not found`);
	}
	return {
		code: params.code,
		component: entry.component,
		metadata: entry.metadata ?? {}
	};
}
