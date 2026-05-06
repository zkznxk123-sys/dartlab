const modules = import.meta.glob('@samples/*.md', { eager: true, query: '?raw', import: 'default' }) as Record<
	string,
	string
>;

interface SampleEntry {
	code: string;
	title: string;
	excerpt: string;
}

const entries: SampleEntry[] = [];
for (const [path, raw] of Object.entries(modules)) {
	const match = path.match(/\/samples\/(\d{6})\.md$/);
	if (!match) continue;
	const titleMatch = raw.match(/^##\s+(.+)$/m);
	const title = titleMatch ? titleMatch[1].trim() : match[1];
	const firstBold = raw.match(/\*\*(.+?)\*\*/);
	const excerpt = firstBold ? firstBold[1].trim() : '';
	entries.push({ code: match[1], title, excerpt });
}
entries.sort((a, b) => a.code.localeCompare(b.code));

export const prerender = true;

export function load() {
	return { entries };
}
