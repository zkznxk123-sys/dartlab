import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// 워크스페이스 패키지 소스(@dartlab/ui-*)는 ui/packages 아래 심볼릭링크 — dev fs.allow 로 읽기 허용.
const uiPackagesDir = path.resolve(__dirname, '..', '..', 'packages');

// dev: 로컬 Python API 서버(`dartlab ai`) 기본 포트 8400(HF Spaces 7860). SvelteKit dev 가 /api → 서버로 프록시.
// 빌드(정적 SPA)에서는 같은 오리진(Python 서버 서빙)이라 apiBase='' — 프록시는 dev 전용.
const apiTarget = process.env.DARTLAB_API_BASE || 'http://127.0.0.1:8400';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '127.0.0.1',
		port: 5174,
		strictPort: true,
		proxy: {
			'/api': { target: apiTarget, changeOrigin: true }
		},
		fs: {
			allow: [uiPackagesDir]
		}
	},
	optimizeDeps: {
		// 터미널 surface 가 동적 import 하는 무거운 dep 를 시작 시 미리 최적화(landing 동일 — 뒤늦은 재최적화 504 churn 회피).
		include: ['klinecharts']
	}
});
