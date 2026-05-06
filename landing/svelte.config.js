import adapter from '@sveltejs/adapter-static';
import { mdsvex } from 'mdsvex';
import { createHighlighter } from 'shiki';
import { visit } from 'unist-util-visit';
import { readdirSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

const basePath = process.env.BASE_PATH || '';

// 산업지도: static/map/companies/*.json 이 있으면 해당 경로 prerender
const mapCompaniesDir = resolve('./static/map/companies');
const companyEntries = existsSync(mapCompaniesDir)
	? readdirSync(mapCompaniesDir)
			.filter((f) => f.endsWith('.json'))
			.map((f) => `/company/${f.replace('.json', '')}`)
	: [];

const mapIndustriesDir = resolve('./static/map/industries');
const industryEntries = existsSync(mapIndustriesDir)
	? readdirSync(mapIndustriesDir)
			.filter((f) => f.endsWith('.json'))
			.map((f) => `/industry/${f.replace('.json', '')}`)
	: [];

function rehypeBaseUrl() {
	return (tree, file) => {
		// 호출 컨텍스트 식별: skill 본문이면 ./assets/foo → /skills/assets/foo,
		// 블로그(또는 그 외) 이면 /blog/assets/foo (기존 동작).
		const filePath = file?.path ?? file?.history?.[0] ?? '';
		const isSkillFile =
			filePath.includes('/skills/specs/') || filePath.includes('\\skills\\specs\\');
		const assetsBase = isSkillFile ? '/skills/assets/' : '/blog/assets/';

		visit(tree, 'element', (node) => {
			if (node.tagName === 'img' && node.properties?.src) {
				const src = node.properties.src;
				// 1) 본문의 ./assets/foo.svg|webp|png 상대경로 →
				//    평면 구조 (skills 본문은 /skills/assets/, 그 외는 /blog/assets/) 로 변환.
				if (src.startsWith('./assets/')) {
					const fileName = src.slice('./assets/'.length);
					node.properties.src = `${basePath}${assetsBase}${fileName}`;
					return;
				}
				// 2) 절대경로 (/avatar.png 등) → basePath 접두
				if (src.startsWith('/')) {
					node.properties.src = basePath + src;
				}
			}
			if (node.tagName === 'a' && node.properties?.href?.startsWith('/')) {
				node.properties.href = basePath + node.properties.href;
			}
		});
	};
}

const highlighter = await createHighlighter({
	themes: ['github-dark'],
	langs: ['python', 'bash', 'powershell', 'json', 'yaml', 'toml', 'javascript', 'typescript', 'svelte', 'markdown', 'text']
});

/** @type {import('@sveltejs/kit').Config} */
const config = {
	extensions: ['.svelte', '.md'],
	preprocess: [
		mdsvex({
			extensions: ['.md'],
			rehypePlugins: [rehypeBaseUrl],
			highlight: {
				highlighter: (code, lang) => {
					const supported = highlighter.getLoadedLanguages();
					const safeLang = supported.includes(lang) ? lang : 'text';
					const html = highlighter.codeToHtml(code, {
						lang: safeLang,
						theme: 'github-dark'
					});
					return `{@html \`${html.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`}`;
				}
			}
		})
	],
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: '404.html',
			precompress: false,
			strict: false
		}),
		prerender: {
			entries: ['*', '/docs/', '/blog/', '/cheatsheet', ...companyEntries, ...industryEntries],
			handleHttpError: ({ path, referrer, message }) => {
				// basePath prefix 제거 후 검사 (CI에서 path는 /dartlab/... 형태)
				const stripped = basePath && path.startsWith(basePath) ? path.slice(basePath.length) : path;
				// /industry/ 는 아직 구현 전 — 무시
				if (stripped.startsWith('/industry/')) {
					return;
				}
				// /company/ 중 top 200에 없는 회사 링크 + JSON fetch 실패는 무시
				if (stripped.startsWith('/company/') || stripped.startsWith('/map/companies/')) {
					return;
				}
				// /feed/ RSS/iCal 링크 — 정적 파일이라 prerender 불필요
				if (stripped.startsWith('/feed/')) {
					return;
				}
				// app.html icon 링크. static/favicon.ico 는 build assets 로 복사되므로 prerender 방문 불필요.
				if (stripped === '/favicon.ico') {
					return;
				}
				throw new Error(`${message} (linked from ${referrer})`);
			}
		},
		paths: {
			base: process.env.BASE_PATH || ''
		},
		alias: {
			$pyodide: '../pyodide',
			$chart: '../ui/shared/chart',
			$skills: '../src/dartlab/skills'
		}
	}
};

export default config;
