import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, type ViteDevServer } from 'vite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const blogDir = path.resolve(__dirname, '..', 'blog');
const skillsDir = path.resolve(__dirname, '..', 'src', 'dartlab', 'skills');
const pyodideDir = path.resolve(__dirname, '..', 'pyodide');
const sharedChartDir = path.resolve(__dirname, '..', 'ui', 'shared', 'chart');

function contentType(filePath: string): string {
	const ext = path.extname(filePath).toLowerCase();
	if (ext === '.svg') return 'image/svg+xml';
	if (ext === '.png') return 'image/png';
	if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
	if (ext === '.webp') return 'image/webp';
	return 'application/octet-stream';
}

function collectBlogAssets(dir: string, result = new Map<string, string>()) {
	for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
		const fullPath = path.resolve(dir, entry.name);
		if (entry.isDirectory()) {
			if (entry.name === 'assets') {
				for (const asset of fs.readdirSync(fullPath, { withFileTypes: true })) {
					if (!asset.isFile()) continue;
					const assetPath = path.resolve(fullPath, asset.name);
					const duplicate = result.get(asset.name);
					if (duplicate) {
						throw new Error(`Duplicate blog asset filename detected: ${asset.name}\n- ${duplicate}\n- ${assetPath}`);
					}
					result.set(asset.name, assetPath);
				}
				continue;
			}
			collectBlogAssets(fullPath, result);
		}
	}
	return result;
}

function blogAssetsPlugin() {
	return {
		name: 'blog-assets-plugin',
		configureServer(server: ViteDevServer) {
			const assetMap = collectBlogAssets(blogDir);
			server.middlewares.use('/blog/assets', (req, res, next) => {
				const rawPath = req.url?.split('?')[0] ?? '/';
				const fileName = path.basename(rawPath);
				const filePath = assetMap.get(fileName);
				if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
					next();
					return;
				}
				res.setHeader('Content-Type', contentType(filePath));
				fs.createReadStream(filePath).pipe(res);
			});
		}
	};
}

function skillCatalogPlugin() {
	return {
		name: 'skill-catalog-plugin',
		configureServer(server: ViteDevServer) {
			server.middlewares.use('/__dartlab_skills', (req, res, next) => {
				const rawPath = req.url?.split('?')[0] ?? '/';
				const fileName = path.basename(rawPath);
				if (!['index.json', 'pyodide.json'].includes(fileName)) {
					next();
					return;
				}
				const filePath = path.resolve(skillsDir, fileName);
				if (!filePath.startsWith(skillsDir + path.sep) || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
					next();
					return;
				}
				res.setHeader('Content-Type', 'application/json; charset=utf-8');
				fs.createReadStream(filePath).pipe(res);
			});
		}
	};
}

export default defineConfig({
	plugins: [tailwindcss(), blogAssetsPlugin(), skillCatalogPlugin(), sveltekit()],
	worker: {
		format: 'es'
	},
	build: {
		emptyOutDir: true
	},
	resolve: {
		alias: {
			'@blog': blogDir,
			'$chart': sharedChartDir,
			'$skills': skillsDir,
			// ui/shared/chart 의 svelte 컴포넌트가 d3 모듈을 import. ui/ 트리에는 node_modules 가 없어
			// rollup module resolution 이 landing/node_modules 까지 도달 못 하는 케이스 (CI npm ci 환경) —
			// landing/node_modules 의 절대 경로를 alias 로 강제.
			'd3-scale': path.resolve(__dirname, 'node_modules/d3-scale'),
			'd3-selection': path.resolve(__dirname, 'node_modules/d3-selection'),
			'd3-shape': path.resolve(__dirname, 'node_modules/d3-shape'),
			'd3-array': path.resolve(__dirname, 'node_modules/d3-array')
		}
	},
	ssr: {
		noExternal: [/^d3-/]
	},
	optimizeDeps: {
		include: ['d3-scale', 'd3-selection', 'd3-shape', 'd3-array']
	},
	server: {
		host: '127.0.0.1',
		port: 5173,
		strictPort: true,
		fs: {
			allow: [
				blogDir,
				pyodideDir,
				sharedChartDir,
				skillsDir
			]
		}
	}
});
