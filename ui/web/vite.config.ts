import fs from 'node:fs';
import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';

const pyprojectPath = path.resolve(__dirname, '../../pyproject.toml');
const pyprojectText = fs.readFileSync(pyprojectPath, 'utf-8');
const versionMatch = pyprojectText.match(/^version\s*=\s*"([^"]+)"/m);
if (!versionMatch) throw new Error(`pyproject.toml version not found: ${pyprojectPath}`);
const dartlabVersion = versionMatch[1];
const repoRoot = path.resolve(__dirname, '../..');
const landingLib = path.resolve(repoRoot, 'landing/src/lib');
const sharedChartDir = path.resolve(repoRoot, 'ui/shared/chart');
const svelteCompatDir = path.resolve(__dirname, './src/svelteKitCompat');

// dartlab UI 빌드 — Python wheel 안에 박혀서 dartlab 서버 (FastAPI) 가 정적 서빙
//   - 빌드 출력: ui/web/build/  ← pyproject hatch include 패턴과 호환
//   - dev mode: localhost:5400, /api 와 /ws 는 8400 (Python 서버) 으로 프록시
//   - SPA fallback 은 Python 서버 (web.py::serveSpa) 가 처리하므로 추가 설정 불필요
export default defineConfig({
	plugins: [
		TanStackRouterVite({ target: 'react', autoCodeSplitting: true }),
		svelte(),
		react(),
		tailwindcss(),
	],
	resolve: {
		alias: {
			'$app/paths': path.resolve(svelteCompatDir, 'paths.ts'),
			'$app/environment': path.resolve(svelteCompatDir, 'environment.ts'),
			// 옛 viewer shim 2종은 4a-3 주입 역전으로 소멸(hosts=null), 데이터 shim 5종은 4a-2 포트화로 소멸
			'$chart': sharedChartDir,
			'$lib': landingLib,
			// 워크스페이스 패키지 — ui/web 은 워크스페이스 밖이라 패키지명 해석 불가, 파일경로 alias 로 소비 (01 §3.4)
			'@dartlab/ui-runtime': path.resolve(repoRoot, 'ui/packages/runtime/src'),
			'@dartlab/ui-design': path.resolve(repoRoot, 'ui/packages/design/src'),
			'@dartlab/ui-contracts': path.resolve(repoRoot, 'ui/packages/contracts/src'),
			'@': path.resolve(__dirname, './src'),
		},
	},
	server: {
		port: 5400,
		fs: {
			allow: [repoRoot],
		},
		proxy: {
			'/api': { target: 'http://localhost:8400', changeOrigin: true },
			'/ws': { target: 'ws://localhost:8400', ws: true },
		},
	},
	define: {
		__DARTLAB_VERSION__: JSON.stringify(dartlabVersion),
	},
	build: {
		outDir: 'build',
		emptyOutDir: true,
		sourcemap: false,
	},
});
