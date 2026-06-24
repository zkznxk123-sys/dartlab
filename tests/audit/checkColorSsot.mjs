// 색상 SSOT 가드 — 브랜드색이 토큰을 우회해 하드코딩되는 회귀 차단(baseline-ratchet).
//
// 배경: 색상 SSOT 3계층(tokens.css --p-*/--dl-*) 도입 전엔 토큰 시스템이 둘 공존(v2 --grad-heat 레드→오렌지
//   vs 제품 핑크)해 "버튼 통일성 없음"이 났다. 그 회귀(브랜드색 하드코딩 → 제2 팔레트 재발)를 기계 차단한다.
//
// 가드 규칙: 브랜드 색 리터럴이 **토큰 정의 파일 밖**에 나타나면 위반(var(--dl-*) 로 소비해야 함).
//   - #ff3f6f (현 시그니처 accent) · #fb923c (옛 오렌지 accent 발산 주범) · #ec4899 (옛 핑크) · #ea4647 (브랜드 레드).
//     대소문자 무시. #fb923c 는 의미상 var(--dl-accent)·var(--dl-orange)·var(--dl-cat-engines) 중 하나로 소비.
//   - 토큰 정의 파일(tokens.css·v2-tokens.css·app.css)은 면제(여기서 primitive 를 *정의*).
//   - 정당한 리터럴 정의처(ALLOW_FILES): dev BrandSwitcher 프리셋 정의·카드 SNS PNG export parity 상수.
//   - 데이터-viz 신호색(#34d399 등)은 대상 아님(노이즈 회피).
//   - 별도 assert: app.css @theme 블록은 hex 0 (반드시 var(--dl-*) 브리지) — 오렌지 재발 차단.
//
// baseline 부채원장(colorSsot.baseline.json): 착수 시점 잔존 하드코딩(뷰어·터미널·scan 등 미토큰화 표면)을
//   기록 → 이후 *신규/증가만* fail. 이관 완료 파일은 baseline 에서 줄며 0 으로 수렴(checkUiDataWiring 동일 철학).
//
// 실행: node tests/audit/checkColorSsot.mjs            (스캔 + baseline 대조, 신규 위반 시 exit 1)
//       node tests/audit/checkColorSsot.mjs --write-baseline   (현 위반을 baseline 으로 기록)
//
// exit 0 = 신규 위반 0(통과). exit 1 = 신규/증가(회귀). exit 2 = 도구 오류.

import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';

const SELF_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(SELF_DIR, '..', '..');
const BASELINE_PATH = join(SELF_DIR, 'colorSsot.baseline.json');

// 스캔 대상 — 프론트 색 소비 표면(.svelte·.css·.ts). node_modules·빌드 산출 제외.
// readdirSync 재귀(node 18.17+ portable) — globSync(node 22+) 의존 회피해 CI 어느 node 에서나 동작.
const SCAN_ROOTS = ['landing/src', 'ui/packages/surfaces/src'];
const SCAN_EXTS = ['.svelte', '.css', '.ts'];
// 토큰 *정의* 파일 — 브랜드 리터럴이 정당(primitive 정의). 정확 경로 매칭으로 면제.
const TOKEN_FILES = [
	'ui/packages/design/src/styles/tokens.css',
	'ui/packages/design/src/styles/v2-tokens.css',
	'landing/src/app.css'
];
// 정당한 리터럴 정의처 — dev 색 시도 위젯 프리셋 정의 + 카드 SNS PNG export parity 상수(Remotion 렌더 일치).
const ALLOW_FILES = [
	'ui/packages/surfaces/src/terminal/ui/BrandSwitch.svelte',
	'landing/src/lib/cards/theme.ts'
];
// 브랜드 색 리터럴(이것만 토큰 강제) — 대소문자 무시. 데이터-viz 신호색은 의도적으로 제외.
const BRAND_HEX = [/#ff3f6f\b/gi, /#fb923c\b/gi, /#ec4899\b/gi, /#ea4647\b/gi];

function norm(p) {
	return relative(REPO_ROOT, p).split('\\').join('/');
}

function listFiles(root) {
	const abs = join(REPO_ROOT, root);
	let names = [];
	try {
		names = readdirSync(abs, { recursive: true });
	} catch {
		return [];
	}
	return names
		.filter((n) => SCAN_EXTS.some((x) => String(n).endsWith(x)))
		.map((n) => join(abs, String(n)));
}

function scan() {
	const counts = {};
	for (const root of SCAN_ROOTS) {
		for (const abs of listFiles(root)) {
			const rel = norm(abs);
			if (TOKEN_FILES.includes(rel) || ALLOW_FILES.includes(rel)) continue;
			let txt = '';
			try {
				txt = readFileSync(abs, 'utf8');
			} catch {
				continue;
			}
			let n = 0;
			for (const re of BRAND_HEX) n += (txt.match(re) || []).length;
			if (n > 0) counts[rel] = n;
		}
	}
	return counts;
}

// app.css @theme 불변식 — Tailwind 유틸은 var(--dl-*) 브리지만 허용(hex 0). 오렌지 accent 재발 차단.
const appCssAbs = join(REPO_ROOT, 'landing', 'src', 'app.css');
try {
	const appCss = readFileSync(appCssAbs, 'utf8');
	const themeBlock = appCss.match(/@theme[^{]*\{([\s\S]*?)\}/)?.[1] || '';
	const themeHex = themeBlock.match(/#[0-9a-fA-F]{3,8}\b/g) || [];
	if (themeHex.length) {
		console.error('[colorSsot] ❌ app.css @theme 에 hex 리터럴 — 반드시 var(--dl-*) 브리지여야(오렌지 재발 가드):');
		console.error('  ' + themeHex.join(', '));
		console.error('  @theme inline { --color-dl-*: var(--dl-*); } 형태로 고치세요 (색 SSOT = tokens.css).');
		process.exit(1);
	}
} catch {
	/* app.css 없으면 스킵(다른 앱) */
}

const current = scan();

if (process.argv.includes('--write-baseline')) {
	const out = {
		_comment:
			'색상 SSOT 가드(checkColorSsot.mjs) 부채원장. 브랜드색(#ff3f6f·#fb923c·#ec4899·#ea4647) 토큰 파일 밖 하드코딩 = SSOT 우회. 신규/증가만 fail(0 수렴). 갱신: node tests/audit/checkColorSsot.mjs --write-baseline.',
		brandHex: ['#ff3f6f', '#fb923c', '#ec4899', '#ea4647'],
		counts: current
	};
	writeFileSync(BASELINE_PATH, JSON.stringify(out, null, '\t') + '\n');
	const total = Object.values(current).reduce((a, b) => a + b, 0);
	console.log(`[colorSsot] baseline 기록: ${Object.keys(current).length} 파일, ${total} 위반.`);
	process.exit(0);
}

if (!existsSync(BASELINE_PATH)) {
	console.error('[colorSsot] baseline 없음 — 먼저 `node tests/audit/checkColorSsot.mjs --write-baseline` 실행.');
	process.exit(2);
}

const baseline = JSON.parse(readFileSync(BASELINE_PATH, 'utf8')).counts || {};
const regressions = [];
for (const [file, n] of Object.entries(current)) {
	const base = baseline[file] || 0;
	if (n > base) regressions.push(`${file}: ${base} → ${n} (+${n - base})`);
}

if (regressions.length) {
	console.error('[colorSsot] ❌ 브랜드색 하드코딩 신규/증가 — var(--dl-accent)/var(--dl-red) 로 소비하세요:');
	for (const r of regressions) console.error('  ' + r);
	console.error('  (정당한 추가면 baseline 갱신: node tests/audit/checkColorSsot.mjs --write-baseline)');
	process.exit(1);
}

const total = Object.values(current).reduce((a, b) => a + b, 0);
console.log(`[colorSsot] ✓ 신규 위반 0 (잔존 부채 ${total} — baseline 내).`);
process.exit(0);
