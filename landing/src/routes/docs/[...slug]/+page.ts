import type { EntryGenerator } from './$types';

// docs 라우트는 /skills 로 흡수됐다. 두 가지 경우:
//   1. 알려진 slug → redirect (skills 또는 /about 으로).
//   2. samples / macro-reports 처럼 흡수되지 않은 본문은 mdsvex 그대로 렌더 (외부 인용 보존).

// macro-reports 는 자동 발간 산출물에 mdsvex 비호환 텍스트 (예: ICR<1) 이 포함될 수 있어
// 별도 escape 처리 전까지 import 제외. 외부 인용은 임시로 깨질 수 있다.
const modules = import.meta.glob(
	['@docs/samples/*.md', '!@docs/**/STATUS.md', '!@docs/index.md'],
	{ eager: true }
) as Record<
	string,
	{ default: ConstructorOfATypedSvelteComponent; metadata?: Record<string, string> }
>;

const rawModules = import.meta.glob(
	['@docs/samples/*.md', '!@docs/**/STATUS.md', '!@docs/index.md'],
	{ eager: true, query: '?raw', import: 'default' }
) as Record<string, string>;

function normalizePath(rawPath: string): string {
	return rawPath
		.replace(/^.*?\/docs\//, '')
		.replace(/\/\d+_/g, '/')
		.replace(/\.md$/, '')
		.replace(/\/index$/, '');
}

const slugMap = new Map<
	string,
	{
		component: ConstructorOfATypedSvelteComponent;
		metadata?: Record<string, string>;
		rawMarkdown: string;
	}
>();

for (const [path, mod] of Object.entries(modules)) {
	const slug = normalizePath(path);
	slugMap.set(slug, {
		component: mod.default,
		metadata: mod.metadata,
		rawMarkdown: rawModules[path] ?? ''
	});
}

const redirectSlugs = [
	'getting-started/installation',
	'getting-started/quickstart',
	'getting-started/cli-maintenance',
	'getting-started/sections',
	'tutorials',
	'about',
	'stability',
	'methodology'
];

export const prerender = true;

export const entries: EntryGenerator = () => {
	const allSlugs = new Set<string>(redirectSlugs);
	for (const slug of slugMap.keys()) allSlugs.add(slug);
	return [...allSlugs].map((slug) => ({ slug }));
};

export function load({ params }: { params: { slug: string } }) {
	const slug = params.slug;
	const isRedirect = redirectSlugs.includes(slug);
	const entry = slugMap.get(slug);
	return {
		slug,
		isRedirect,
		component: entry?.component ?? null,
		metadata: entry?.metadata ?? {},
		rawMarkdown: entry?.rawMarkdown ?? ''
	};
}
