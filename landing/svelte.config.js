import adapter from '@sveltejs/adapter-static';
import { mdsvex } from 'mdsvex';
import { createHighlighter } from 'shiki';
import { visit } from 'unist-util-visit';

const basePath = process.env.BASE_PATH || '';

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
			entries: ['*', '/docs/', '/blog/']
		},
		paths: {
			base: process.env.BASE_PATH || ''
		}
	}
};

export default config;
