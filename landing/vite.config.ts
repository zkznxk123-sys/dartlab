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
const uiPackagesDir = path.resolve(__dirname, '..', 'ui', 'packages');

const pyprojectText = fs.readFileSync(path.resolve(__dirname, '..', 'pyproject.toml'), 'utf-8');
const versionMatch = pyprojectText.match(/^version\s*=\s*"([^"]+)"/m);
if (!versionMatch) throw new Error('pyproject.toml version not found');
const dartlabVersion = versionMatch[1];

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
				if (!['catalog.json', 'pyodide.json'].includes(fileName)) {
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

// repo 루트 .env 직독 (Vite 는 비-VITE_ 변수를 process.env 에 안 넣음 → dev 미들웨어용으로 직접 파싱).
function readRepoEnv(): Record<string, string> {
	try {
		const txt = fs.readFileSync(path.resolve(__dirname, '..', '.env'), 'utf-8');
		const out: Record<string, string> = {};
		for (const line of txt.split(/\r?\n/)) {
			const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
			if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, '').trim();
		}
		return out;
	} catch {
		return {};
	}
}

// 공공데이터포털 금융위원회_주식시세정보 (디코딩 키 → encodeURIComponent). 전체 이력 → Candle[] 정규화.
const GOV_ENDPOINT = 'https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo';
async function fetchGovCandles(code: string, key: string) {
	const candles: { t: string; o: number; h: number; l: number; c: number; v: number }[] = [];
	const seen = new Set<string>();
	for (let page = 1; page <= 6; page++) {
		const url = `${GOV_ENDPOINT}?serviceKey=${encodeURIComponent(key)}&resultType=json&numOfRows=4000&pageNo=${page}&likeSrtnCd=${encodeURIComponent(code)}`;
		const res = await fetch(url);
		if (!res.ok) throw new Error(`gov api ${res.status}`);
		const j: any = await res.json();
		const item = j?.response?.body?.items?.item;
		const arr = Array.isArray(item) ? item : item ? [item] : [];
		if (!arr.length) break;
		for (const r of arr) {
			if (String(r.srtnCd) !== code) continue; // likeSrtnCd = LIKE → 정확 매칭만 채택
			const t = String(r.basDt);
			const c = Number(r.clpr);
			if (seen.has(t) || !Number.isFinite(c) || c <= 0) continue;
			seen.add(t);
			candles.push({ t, o: Number(r.mkp) || c, h: Number(r.hipr) || c, l: Number(r.lopr) || c, c, v: Number(r.trqu) || 0 });
		}
		const total = Number(j?.response?.body?.totalCount) || 0;
		if (page * 4000 >= total) break;
	}
	candles.sort((a, b) => a.t.localeCompare(b.t));
	return candles;
}

// save-later: 회사별 parquet 영속화를 buildGovData --stock 로 백그라운드 spawn (응답 후, 차트 비차단).
// gov 전체이력 fetch + 기존 parquet merge + HF 업로드를 Python(검증된 생산기)에 위임 — Node parquet 쓰기 회피.
function spawnGovPersist(code: string, server: ViteDevServer): void {
	import('node:child_process')
		.then(({ spawn }) => {
			const child = spawn(
				'uv',
				['run', 'python', '-X', 'utf8', '.github/scripts/sync/buildGovData.py', '--stock', code],
				{ cwd: path.resolve(__dirname, '..'), detached: true, stdio: 'ignore' }
			);
			child.on('error', (e) => server.config.logger.warn(`[gov] parquet 저장 spawn 실패 ${code}: ${e}`));
			child.unref();
		})
		.catch(() => {});
}

// 프론트-먼저 HF 캐시-필 미들웨어 — /__gov?code=XXXXXX (dev only, 토큰 Node 서버측 보관).
// draw-first-save-later: gov fetch → 캔들 즉시 반환(차트 먼저 그림) → 백그라운드 parquet 영속화.
function govPriceDevPlugin() {
	return {
		name: 'gov-price-dev',
		configureServer(server: ViteDevServer) {
			server.middlewares.use('/__gov', async (req, res) => {
				const send = (status: number, obj: unknown) => {
					if (res.writableEnded) return;
					res.statusCode = status;
					res.setHeader('Content-Type', 'application/json; charset=utf-8');
					res.end(JSON.stringify(obj));
				};
				const url = new URL(req.url ?? '', 'http://localhost');
				const code = (url.searchParams.get('code') ?? '').replace(/[^0-9A-Za-z]/g, '');
				if (!code) return send(400, { error: 'code 필요' });
				const env = readRepoEnv();
				if (!env.DATA_GO_KR_KEY) return send(503, { error: 'DATA_GO_KR_KEY 미설정(.env)' });
				let candles: { t: string; o: number; h: number; l: number; c: number; v: number }[] = [];
				try {
					candles = await fetchGovCandles(code, env.DATA_GO_KR_KEY);
				} catch (e) {
					return send(502, { error: String(e) });
				}
				send(200, { source: 'data.go.kr/금융위원회·한국거래소', code, asOf: candles.at(-1)?.t ?? '', candles });
				if (candles.length && env.HF_TOKEN) spawnGovPersist(code, server);
			});
		}
	};
}

export default defineConfig({
	plugins: [tailwindcss(), blogAssetsPlugin(), skillCatalogPlugin(), govPriceDevPlugin(), sveltekit()],
	define: {
		__DARTLAB_VERSION__: JSON.stringify(dartlabVersion)
	},
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
			'$skills': skillsDir
		}
	},
	ssr: {
		noExternal: [/^d3-/]
	},
	optimizeDeps: {
		// d3 + 뷰어가 *동적 import* 하는 무거운 deps 를 시작 시 미리 최적화. 안 넣으면 뷰어 로드 중 뒤늦게 최적화되며
		// "optimized dependencies changed. reloading" → 옛 청크 무효화 → 504(Outdated Optimize Dep) → 빈 화면 churn.
		include: [
			'd3-scale',
			'd3-selection',
			'd3-shape',
			'd3-array',
			'lucide-svelte',
			'hyparquet',
			'hyparquet-compressors',
			'dompurify',
			'@mlc-ai/web-llm',
			'klinecharts'
		]
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
				skillsDir,
				uiPackagesDir
			]
		}
	}
});
