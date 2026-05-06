#!/usr/bin/env node
/**
 * ui/web 시각 언어 SSOT (visual-language.md) lint.
 *
 * 컴포넌트당 다음 카운트 임계 초과 시 경고:
 *   - rounded-{2xl|xl|sm|full|lg|md} 종류 ≤2
 *   - border-dl-border/N 농도 종류 ≤2
 *   - bg-dl-bg-card/N 농도 종류 ≤2
 *   - <img src="/avatar 출현 ≤1
 *   - lucide-svelte import 종류 ≤4
 *   - 인라인 hex/rgb 색 =0
 *
 * 경고만 — 실패는 안 시킴 (점진 마이그레이션). CI/pre-commit 에서 추적용.
 *
 * Usage:
 *   node scripts/dev/checkVisualLanguage.mjs
 *   node scripts/dev/checkVisualLanguage.mjs --strict   # 임계 초과 시 exit 1
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..", "..");
const TARGET = path.join(ROOT, "ui", "web", "src", "lib", "components");
const STRICT = process.argv.includes("--strict");

const THRESH = {
	roundedKinds: 2,
	borderShades: 2,
	bgShades: 2,
	avatarCount: 1,
	iconImports: 4,
	inlineColors: 0,
};

function walk(dir) {
	const out = [];
	for (const entry of readdirSync(dir)) {
		const full = path.join(dir, entry);
		const st = statSync(full);
		if (st.isDirectory()) out.push(...walk(full));
		else if (entry.endsWith(".svelte")) out.push(full);
	}
	return out;
}

function audit(filePath) {
	const src = readFileSync(filePath, "utf8");

	const roundedKinds = new Set([...src.matchAll(/\brounded-(2xl|xl|lg|md|sm|full)\b/g)].map((m) => m[1]));
	const borderShades = new Set([...src.matchAll(/\bborder-dl-border\/(\d+)/g)].map((m) => m[1]));
	const bgShades = new Set([...src.matchAll(/\bbg-dl-bg-card(?:-hover)?\/(\d+)/g)].map((m) => m[1]));
	const avatarCount = (src.match(/<img[^>]*src=["']\/avatar/g) || []).length;

	let iconImports = 0;
	const lucideImport = src.match(/import\s*\{([^}]+)\}\s*from\s*["']lucide-svelte["']/);
	if (lucideImport) {
		iconImports = lucideImport[1].split(",").map((s) => s.trim()).filter(Boolean).length;
	}

	const scriptOnly = src.replace(/<style[\s\S]*?<\/style>/g, ""); // <style> 안 hex 는 토큰 외부 정의 가능, 제외
	const inlineColors = (scriptOnly.match(/#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]+\)/g) || []).filter(
		(s) => !s.startsWith("#L"), // markdown 링크 anchor 같은 false-positive 제외
	).length;

	return {
		path: path.relative(ROOT, filePath),
		roundedKinds,
		borderShades,
		bgShades,
		avatarCount,
		iconImports,
		inlineColors,
	};
}

function violations(report) {
	const v = [];
	if (report.roundedKinds.size > THRESH.roundedKinds) {
		v.push(`rounded-* 종류 ${report.roundedKinds.size} (임계 ${THRESH.roundedKinds}): ${[...report.roundedKinds].join(", ")}`);
	}
	if (report.borderShades.size > THRESH.borderShades) {
		v.push(`border-dl-border 농도 ${report.borderShades.size} (임계 ${THRESH.borderShades}): /${[...report.borderShades].join(", /")}`);
	}
	if (report.bgShades.size > THRESH.bgShades) {
		v.push(`bg-dl-bg-card 농도 ${report.bgShades.size} (임계 ${THRESH.bgShades}): /${[...report.bgShades].join(", /")}`);
	}
	if (report.avatarCount > THRESH.avatarCount) {
		v.push(`아바타 출현 ${report.avatarCount} (임계 ${THRESH.avatarCount})`);
	}
	if (report.iconImports > THRESH.iconImports) {
		v.push(`lucide-svelte import ${report.iconImports} (임계 ${THRESH.iconImports})`);
	}
	if (report.inlineColors > THRESH.inlineColors) {
		v.push(`인라인 hex/rgb 색 ${report.inlineColors} (임계 ${THRESH.inlineColors})`);
	}
	return v;
}

function main() {
	const files = walk(TARGET);
	let totalViolations = 0;
	const violatingFiles = [];

	for (const f of files) {
		const report = audit(f);
		const v = violations(report);
		if (v.length > 0) {
			totalViolations += v.length;
			violatingFiles.push({ path: report.path, violations: v });
		}
	}

	if (violatingFiles.length === 0) {
		console.log(`[visual-language] OK — ${files.length} 컴포넌트 검사, 위반 0`);
		process.exit(0);
	}

	console.log(`[visual-language] ${files.length} 컴포넌트 검사, 위반 ${totalViolations} 건 / ${violatingFiles.length} 파일\n`);
	for (const { path: p, violations: vs } of violatingFiles) {
		console.log(`  ${p}`);
		for (const v of vs) console.log(`    - ${v}`);
	}
	console.log("\n룰 본문: ui/web/src/lib/styles/visual-language.md");

	process.exit(STRICT ? 1 : 0);
}

main();
