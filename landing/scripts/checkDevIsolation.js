// 터미널 격리 가드 — 본진(공개 /terminal 라우트 + surface 본 트리)이 dev/ 를 import 하면 빌드 실패.
// dev/ 의 WIP 가 어떤 푸시에 실려도 본진 번들에 묶이지 않음을 기계 보증 (공개 터미널 무중단 —
// memory feedback_ui_rules #10). landing prebuild 체인에서 실행.
//
// 단계-4b: 터미널 surface 가 ui/packages/surfaces 로 승격. export 경로 자체가 분리됐다 —
//   본진 = @dartlab/ui-surfaces/terminal (terminal/index.ts, dev 미도달)
//   dev  = @dartlab/ui-surfaces/terminal/dev (terminal/dev/index.ts, /lab/terminal-dev 전용)
// 가드 대상 = ① surface 본 트리(surfaces/src/terminal, dev/ 제외) ② 공개 라우트(routes/terminal).
// 이들이 terminal/dev 서브패스 또는 내부 ./dev/ 를 import 하면 위반.
import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { resolve, dirname, join, sep } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, '..', '..');

const surfaceTerminal = join(repoRoot, 'ui', 'packages', 'surfaces', 'src', 'terminal');
const landingTermRoute = join(repoRoot, 'landing', 'src', 'routes', 'terminal');
const devDir = join(surfaceTerminal, 'dev') + sep;

// 본진 트리 = surface terminal(dev/ 제외) + 공개 라우트. /lab/terminal-dev 라우트는 비대상(dev import 허용).
const targets = [surfaceTerminal, landingTermRoute].filter((p) => existsSync(p));

function walk(dir, out = []) {
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) {
			if ((p + sep).startsWith(devDir)) continue; // dev/ 폴더 자신은 제외
			walk(p, out);
		} else if (/\.(svelte|ts|js)$/.test(name)) {
			out.push(p);
		}
	}
	return out;
}

const importRe = /(?:from\s+|import\s*\(\s*)['"]([^'"]*)['"]/g;
const violations = [];
for (const root of targets) {
	for (const file of walk(root)) {
		const body = readFileSync(file, 'utf8');
		for (const m of body.matchAll(importRe)) {
			const spec = m[1];
			// 패키지 서브패스(@dartlab/ui-surfaces/terminal/dev)·상대경로(./dev/, ../dev/) 모두 위반.
			const subpathHit = /(^|\/)terminal\/dev(\/|$)/.test(spec);
			const devFileHit = /(^|\/)dev\/DevTerminal/.test(spec);
			const relDevHit = /(^|\/)dev(\/|$)/.test(spec) && file.startsWith(surfaceTerminal + sep);
			if (subpathHit || devFileHit || relDevHit) {
				violations.push(`${file.slice(repoRoot.length + 1)} -> ${spec}`);
			}
		}
	}
}

if (violations.length) {
	console.error('[dev-isolation] 본진이 terminal/dev 를 import 한다 — 격리 위반, 빌드 차단:');
	for (const v of violations) console.error('  - ' + v);
	process.exit(1);
}
console.log('[dev-isolation] OK — 본진 ↛ terminal/dev import 0');
