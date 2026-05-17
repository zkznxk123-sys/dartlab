import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';

// dartlab UI 빌드 — Python wheel 안에 박혀서 dartlab 서버 (FastAPI) 가 정적 서빙
//   - 빌드 출력: ui/web/build/  ← pyproject hatch include 패턴과 호환
//   - dev mode: localhost:5400, /api 와 /ws 는 8400 (Python 서버) 으로 프록시
//   - SPA fallback 은 Python 서버 (web.py::serveSpa) 가 처리하므로 추가 설정 불필요
export default defineConfig({
	plugins: [
		TanStackRouterVite({ target: 'react', autoCodeSplitting: true }),
		react(),
		tailwindcss(),
	],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, './src'),
		},
	},
	server: {
		port: 5400,
		proxy: {
			'/api': { target: 'http://localhost:8400', changeOrigin: true },
			'/ws': { target: 'ws://localhost:8400', ws: true },
		},
	},
	build: {
		outDir: 'build',
		emptyOutDir: true,
		sourcemap: false,
	},
});
