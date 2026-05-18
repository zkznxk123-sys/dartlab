#!/usr/bin/env node
/**
 * landing/src/lib/brand.ts ↔ ui/web/src/app.css drift detection.
 *
 * brand.ts 의 color object 가 SSOT. ui/web 의 @theme --color-dl-* 가 일치해야 한다.
 * 일치하지 않으면 drift 보고 + exit 1. CI / pre-commit hook 게이트용.
 *
 * Usage:
 *   node landing/_scripts/syncBrand.mjs           # check only
 *   node landing/_scripts/syncBrand.mjs --apply   # rewrite ui/web/src/app.css to match
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..", "..");
const BRAND_TS = path.join(ROOT, "landing", "src", "lib", "brand.ts");
const APP_CSS = path.join(ROOT, "ui", "web", "src", "app.css");

const APPLY = process.argv.includes("--apply");

const KEY_TO_VAR = {
	primary: "--color-dl-primary",
	primaryDark: "--color-dl-primary-dark",
	primaryLight: "--color-dl-primary-light",
	accent: "--color-dl-accent",
	accentLight: "--color-dl-accent-light",
	bgDark: "--color-dl-bg-dark",
	bgDarker: "--color-dl-bg-darker",
	bgCard: "--color-dl-bg-card",
	bgCardHover: "--color-dl-bg-card-hover",
	text: "--color-dl-text",
	textMuted: "--color-dl-text-muted",
	textDim: "--color-dl-text-dim",
	border: "--color-dl-border",
	success: "--color-dl-success",
	warning: "--color-dl-warning",
};

function parseBrandColors(source) {
	const colorBlock = source.match(/color:\s*\{([\s\S]*?)\}/);
	if (!colorBlock) throw new Error("brand.ts: color block not found");
	const colors = {};
	const re = /(\w+)\s*:\s*'(#[0-9a-fA-F]{3,8})'/g;
	let match;
	while ((match = re.exec(colorBlock[1])) !== null) {
		colors[match[1]] = match[2];
	}
	return colors;
}

function parseCssVars(source) {
	const themeBlock = source.match(/@theme\s*\{([\s\S]*?)^\}/m);
	if (!themeBlock) throw new Error("app.css: @theme block not found");
	const vars = {};
	const re = /(--color-dl-[\w-]+)\s*:\s*([^;]+);/g;
	let match;
	while ((match = re.exec(themeBlock[1])) !== null) {
		vars[match[1]] = match[2].trim();
	}
	return vars;
}

const brandSource = readFileSync(BRAND_TS, "utf8");
const cssSource = readFileSync(APP_CSS, "utf8");
const colors = parseBrandColors(brandSource);
const vars = parseCssVars(cssSource);

const drift = [];
for (const [key, varName] of Object.entries(KEY_TO_VAR)) {
	const expected = colors[key];
	const actual = vars[varName];
	if (!expected) {
		drift.push({ key, varName, kind: "brand-missing", expected, actual });
		continue;
	}
	if (!actual) {
		drift.push({ key, varName, kind: "css-missing", expected, actual });
		continue;
	}
	if (expected.toLowerCase() !== actual.toLowerCase()) {
		drift.push({ key, varName, kind: "value-mismatch", expected, actual });
	}
}

if (drift.length === 0) {
	console.log("✓ brand tokens in sync (15 colors)");
	process.exit(0);
}

console.error(`✗ brand drift detected (${drift.length} entries):`);
for (const d of drift) {
	console.error(`  ${d.varName} [${d.kind}]: expected ${d.expected ?? "—"} actual ${d.actual ?? "—"} (brand.${d.key})`);
}

if (!APPLY) {
	console.error("\nrun with --apply to rewrite ui/web/src/app.css");
	process.exit(1);
}

let nextCss = cssSource;
for (const d of drift) {
	if (d.kind !== "value-mismatch") continue;
	const re = new RegExp(`(${d.varName.replace(/[-]/g, "\\-")}\\s*:\\s*)[^;]+(;)`);
	nextCss = nextCss.replace(re, `$1${d.expected}$2`);
}
writeFileSync(APP_CSS, nextCss, "utf8");
console.log(`✓ rewrote ${path.relative(ROOT, APP_CSS)} (${drift.filter((d) => d.kind === "value-mismatch").length} edits)`);
