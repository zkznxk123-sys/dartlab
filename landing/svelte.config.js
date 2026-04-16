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
	return (tree) => {
		visit(tree, 'element', (node) => {
			if (node.tagName === 'img' && node.properties?.src) {
				const src = node.properties.src;
				// 1) 블로그 본문의 ./assets/foo.svg|webp|png 상대경로 →
				//    평면 구조(/blog/assets/{filename})로 변환.
				//    syncBlogAssets.js가 모든 블로그 자산을 단일 폴더로 복사함.
				if (src.startsWith('./assets/')) {
					const fileName = src.slice('./assets/'.length);
					node.properties.src = `${basePath}/blog/assets/${fileName}`;
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
			entries: ['*', '/docs/', '/blog/', ...companyEntries, ...industryEntries],
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
				throw new Error(`${message} (linked from ${referrer})`);
			}
		},
		paths: {
			base: process.env.BASE_PATH || ''
		},
		alias: {
			$pyodide: '../pyodide'
		}
	}
};

export default config;
