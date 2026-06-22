// 색상 SSOT 가드 — 브랜드색이 토큰을 우회해 하드코딩되는 회귀 차단(baseline-ratchet).
//
// 배경: 색상 SSOT 3계층(tokens.css --p-*/--dl-*) 도입 전엔 토큰 시스템이 둘 공존(v2 --grad-heat 레드→오렌지
//   vs 제품 핑크)해 "버튼 통일성 없음"이 났다. 그 회귀(브랜드색 하드코딩 → 제2 팔레트 재발)를 기계 차단한다.
//
// 가드 규칙: 브랜드 색 리터럴이 **토큰 정의 파일 밖**에 나타나면 위반(var(--dl-*) 로 소비해야 함).
//   - #ec4899 (시그니처 accent 핑크) · #ea4647 (브랜드 레드) — 대소문자 무시.
//   - 토큰 정의 파일(tokens.css·v2-tokens.css·app.css)은 면제(여기서 primitive 를 *정의*).
//   - 데이터-viz 색(차트 시리즈·신호색 #34d399 등)·레거시 보조색(#fb923c)은 대상 아님(노이즈 회피).
//
// baseline 부채원장(colorSsot.baseline.json): 착수 시점 잔존 하드코딩(뷰어·터미널·scan 등 미토큰화 표면)을
//   기록 → 이후 *신규/증가만* fail. 이관 완료 파일은 baseline 에서 줄며 0 으로 수렴(checkUiDataWiring 동일 철학).
//
// 실행: node tests/audit/checkColorSsot.mjs            (스캔 + baseline 대조, 신규 위반 시 exit 1)
//       node tests/audit/checkColorSsot.mjs --write-baseline   (현 위반을 baseline 으로 기록)
//
// exit 0 = 신규 위반 0(통과). exit 1 = 신규/증가(회귀). exit 2 = 도구 오류.

import { readFileSync, writeFileSync, existsSync, globSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';

const SELF_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(SELF_DIR, '..', '..');
const BASELINE_PATH = join(SELF_DIR, 'colorSsot.baseline.json');

// 스캔 대상 — 프론트 색 소비 표면(.svelte·.css·.ts). node_modules·빌드 산출 제외.
const GLOBS = [
	'landing/src/**/*.{svelte,css,ts}',
	'ui/packages/surfaces/src/**/*.{svelte,css,ts}'
];
// 토큰 *정의* 파일 — 브랜드 리터럴이 정당(primitive 정의). 파일명 끝 매칭으로 면제.
const TOKEN_FILES = [
	'ui/packages/design/src/styles/tokens.css',
	'ui/packages/design/src/styles/v2-tokens.css',
	'landing/src/app.css'
];
// 브랜드 색 리터럴(이것만 토큰 강제) — 대소문자 무시. 데이터색·보조색은 의도적으로 제외.
const BRAND_HEX = [/#ec4899\b/gi, /#ea4647\b/gi];

function norm(p) {
	return relative(REPO_ROOT, p).split('\\').join('/');
}

function scan() {
	const counts = {};
	for (const g of GLOBS) {
		let files = [];
		try {
			files = globSync(g, { cwd: REPO_ROOT }).map((f) => join(REPO_ROOT, f));
		} catch {
			files = [];
		}
		for (const abs of files) {
			const rel = norm(abs);
			if (TOKEN_FILES.some((t) => rel.endsWith(t.split('/').pop()) && rel === t)) continue;
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

const current = scan();

if (process.argv.includes('--write-baseline')) {
	const out = {
		_comment:
			'색상 SSOT 가드(checkColorSsot.mjs) 부채원장. 브랜드색(#ec4899·#ea4647) 토큰 파일 밖 하드코딩 = SSOT 우회. 신규/증가만 fail. 갱신: node tests/audit/checkColorSsot.mjs --write-baseline.',
		brandHex: ['#ec4899', '#ea4647'],
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
