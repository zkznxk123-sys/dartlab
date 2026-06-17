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

// 공개 CF 워커 프록시(secret 아님, 전 환경 동일) 기본값 — 로컬도 공개와 "공통 배선"으로 워커를 쓴다.
// price·macro 와 달리 news 는 HF 직독 fallback 이 없어(private) env 미설정 시 빈 섹션이 됐다.
// deploy-landing 은 step env 로 주입하므로 여기 기본값은 로컬/직접빌드 전용 — ??= 라 operator 명시값이 우선(가역).
const DARTLAB_WORKER = 'https://dartlab-hf-proxy.eddmpython.workers.dev';
process.env.VITE_DARTLAB_HF_RESOLVE ??= `${DARTLAB_WORKER}/hf`;
process.env.VITE_DARTLAB_NAVER_PROXY ??= `${DARTLAB_WORKER}/naver`;
process.env.VITE_DARTLAB_NEWS_PROXY ??= `${DARTLAB_WORKER}/news`;

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
