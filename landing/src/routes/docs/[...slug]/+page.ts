import type { EntryGenerator } from './$types';

// docs 라우트는 /skills 와 /samples 로 흡수됐다. 이 catch-all 은 redirect 만 처리한다.
// 외부 인용 (`/dartlab/docs/...`) 보존이 목적이고 mdsvex 본문 렌더는 더 이상 없다.

const sampleCodes = [
	'000270',
	'000660',
	'004020',
	'005930',
	'017670',
	'034730',
	'036570',
	'042660',
	'051910',
	'055550',
	'090430'
];

const redirectSlugs = [
	'getting-started/installation',
	'getting-started/quickstart',
	'getting-started/cli-maintenance',
	'getting-started/sections',
	'tutorials',
	'about',
	'stability',
	'methodology',
	...sampleCodes.map((code) => `samples/${code}`)
];

export const prerender = true;

export const entries: EntryGenerator = () => redirectSlugs.map((slug) => ({ slug }));

export function load({ params }: { params: { slug: string } }) {
	const slug = params.slug;
	return { slug, isRedirect: redirectSlugs.includes(slug) };
}
