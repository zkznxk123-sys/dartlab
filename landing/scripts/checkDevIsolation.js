// 터미널 격리 가드 — 본진(/terminal 라우트 + $lib/terminal 본 경로)이 $lib/terminal/dev/ 를
// import 하면 빌드 실패. dev/ 의 WIP 가 어떤 푸시에 실려도 본진 번들에 묶이지 않음을 기계 보증
// (공개 터미널 무중단 — memory feedback_ui_rules #10). prebuild 체인에서 실행.
import { readFileSync, readdirSync, statSync } from 'fs';
import { resolve, dirname, join, sep } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = resolve(__dirname, '..', 'src');

// 검사 대상 = 본진 트리. dev/ 자신과 /lab/terminal-dev 라우트는 제외 (그쪽만 dev import 허용).
const targets = [join(src, 'lib', 'terminal'), join(src, 'routes', 'terminal')];
const devDir = join(src, 'lib', 'terminal', 'dev') + sep;

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
			// $lib alias·상대경로 모두 — 경로 어딘가에 terminal/dev 세그먼트가 있으면 위반
			if (/(^|\/)terminal\/dev(\/|$)/.test(spec) || /(^|\/)dev\/DevTerminal/.test(spec) || (/(^|\/)dev(\/|$)/.test(spec) && file.includes(join('lib', 'terminal')))) {
				violations.push(`${file.slice(src.length + 1)} -> ${spec}`);
			}
		}
	}
}

if (violations.length) {
	console.error('[dev-isolation] 본진이 $lib/terminal/dev/ 를 import 한다 — 격리 위반, 빌드 차단:');
	for (const v of violations) console.error('  - ' + v);
	process.exit(1);
}
console.log('[dev-isolation] OK — 본진 ↛ terminal/dev import 0');
