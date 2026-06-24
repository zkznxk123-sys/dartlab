import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const brandPath = resolve(__dirname, '..', 'src', 'lib', 'brand.ts');
const pyprojectPath = resolve(__dirname, '..', '..', 'pyproject.toml');

const pyproject = readFileSync(pyprojectPath, 'utf-8');
const versionMatch = pyproject.match(/^version\s*=\s*"([^"]+)"/m);
if (!versionMatch) { console.error('pyproject.toml version not found'); process.exit(1); }
const version = versionMatch[1];

let brandSrc = readFileSync(brandPath, 'utf-8');
const oldVersion = brandSrc.match(/version:\s*'([^']+)'/)?.[1];
if (oldVersion !== version) {
	brandSrc = brandSrc.replace(/version:\s*'[^']+'/, `version: '${version}'`);
	writeFileSync(brandPath, brandSrc);
	console.log(`  -> brand.ts version: ${oldVersion} -> ${version}`);
} else {
	console.log(`  -> brand.ts version: ${version} (unchanged)`);
}

// 색 SSOT = ui/packages/design/src/styles/tokens.css 한 곳. app.css 는 손수 소유하는 @theme inline 브리지로,
// 더 이상 brand.ts hex 에서 생성하지 않는다(옛 생성기가 오렌지 accent #fb923c 를 찍어 SSOT 발산 원인이었음).
// 본 스크립트는 pyproject 버전을 brand.ts 에 동기화하는 책임만 남긴다.
console.log('Brand version synced (색은 tokens.css SSOT — app.css 생성 안 함).');
