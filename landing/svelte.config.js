import adapter from '@sveltejs/adapter-static';
import { mdsvex } from 'mdsvex';
import { createHighlighter } from 'shiki';
import { visit } from 'unist-util-visit';
import { readdirSync, existsSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';

const basePath = process.env.BASE_PATH || '';
const projectRoot = resolve('..');
const repoBlobBase = 'https://github.com/eddmpython/dartlab/blob/master';

// 산업지도: static/map/companies/*.json 이 있으면 해당 경로 prerender
const mapCompaniesDir = resolve('./static/map/companies');
const companyEntries = existsSync(mapCompaniesDir)
	? readdirSync(mapCompaniesDir)
			.filter((f) => f.endsWith('.json'))
			.map((f) => `/company/${f.replace('.json', '')}`)
	: [];

// 공시뷰어 동적 라우트(/viewer/company/[code]) prerender — 없으면 GitHub Pages 가 404.html(404 status) 로 fallback
// 해 콘솔 404 + 캐시 꼬임(ERR_CACHE) + 로드 실패 유발. 회사별 정적 shell(ssr=false) 로 200 응답.
const viewerEntries = companyEntries.map((p) => `/viewer${p}`);

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
			if (node.tagName === 'a' && node.properties?.href) {
				const href = node.properties.href;
				if (isSkillFile && (href.startsWith('../') || href.startsWith('./'))) {
					const target = resolve(dirname(filePath), href);
					if (target.startsWith(projectRoot)) {
						const rel = relative(projectRoot, target).replace(/\\/g, '/');
						node.properties.href = `${repoBlobBase}/${rel}`;
					}
					return;
				}
				if (
					isSkillFile &&
					(href.startsWith('/tests/') || href.startsWith('/src/') || href.startsWith('/scripts/'))
				) {
					node.properties.href = `${repoBlobBase}${href}`;
					return;
				}
				if (href.startsWith('/')) {
					node.properties.href = basePath + href;
				}
			}
		});
	};
}

function escapeSkillMarkdownForSvelte() {
	const isSkillSpec = (filename) =>
		filename?.endsWith('.md') &&
		(filename.includes('/skills/specs/') || filename.includes('\\skills\\specs\\'));

	const escapeLine = (line) =>
		line
			.replace(/<(?![A-Za-z/!][^>]*>)(?!!--)(?!\?)(?!&[a-zA-Z#0-9]+;)/g, '&lt;')
			.replace(/\{/g, '\uE000')
			.replace(/\}/g, '\uE001')
			.replace(/\uE000/g, '{@html String.fromCharCode(123)}')
			.replace(/\uE001/g, '{@html String.fromCharCode(125)}');

	return {
		name: 'escape-skill-markdown-for-svelte',
		markup({ content, filename }) {
			if (!isSkillSpec(filename)) {
				return;
			}

			const lines = content.split('\n');
			let inFence = false;
			let inFrontmatter = lines[0]?.trim() === '---';
			let frontmatterClosed = false;

			const code = lines
				.map((line, index) => {
					const trimmed = line.trim();
					if (index > 0 && inFrontmatter && trimmed === '---') {
						inFrontmatter = false;
						frontmatterClosed = true;
						return line;
					}
					if (inFrontmatter && !frontmatterClosed) {
						return line;
					}
					if (/^(```|~~~)/.test(trimmed)) {
						inFence = !inFence;
						return line;
					}
					if (inFence) {
						return line;
					}
					return escapeLine(line);
				})
				.join('\n');

			return { code };
		}
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
		escapeSkillMarkdownForSvelte(),
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
			entries: ['*', '/docs/', '/blog/', '/cheatsheet', ...companyEntries, ...viewerEntries, ...industryEntries],
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
				// /skills/ 내부 spec 교차링크 — Skill OS spec 중 공개 페이지(index.json 등재)는 일부. 미등재 내부
				// SSOT spec(operation.* 하위·engines/recipes 깊은 하위 등) 링크는 prerender 페이지가 없어 404 →
				// 무시(공개 skill 은 entries 로 정상 prerender, 깊은 교차참조만 관용). 운영자 index.json 재생성 시 해소.
				if (stripped.startsWith('/skills/')) {
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
