import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, type ViteDevServer } from 'vite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docsDir = path.resolve(__dirname, '..', 'docs');
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
			'@docs': docsDir,
			'@blog': blogDir,
			'$chart': sharedChartDir,
			'$skills': skillsDir
		}
	},
	server: {
		host: '127.0.0.1',
		port: 5173,
		strictPort: true,
		fs: {
			allow: [
				docsDir,
				blogDir,
				pyodideDir,
				sharedChartDir,
				skillsDir
			]
		}
	}
});
