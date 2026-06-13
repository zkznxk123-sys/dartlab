import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// 로컬 앱 = 클라이언트 렌더 SPA. Python 서버(dartlab ai)가 정적 build 를 서빙(전환=단계-10), 데이터는 /api.
// 동적 [code] 라우트는 prerender 불가(전 종목)라 fallback:'index.html' SPA 셸로 200 응답시킨다.
/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html',
			precompress: false,
			strict: false
		})
	}
};

export default config;
