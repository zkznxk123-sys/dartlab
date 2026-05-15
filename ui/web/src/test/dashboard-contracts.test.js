// Phase 0 Dashboard 골격 contract — store / API client / 컴포넌트 export 확인.
// runtime 호출 없이 source 검사로 회귀 차단 (ui-contracts.test.js 패턴).

import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = process.cwd();

function read(relativePath) {
	return readFileSync(path.join(ROOT, relativePath), "utf8");
}

describe("Dashboard foundation — Phase 0", () => {
	describe("uiMode store (Ask ⇄ Dashboard)", () => {
		const source = read("src/lib/stores/uiMode.svelte.js");

		it("exports getUiMode factory", () => {
			expect(source).toContain("export function getUiMode");
		});

		it("persists to localStorage under 'dartlab-ui-mode'", () => {
			expect(source).toContain('"dartlab-ui-mode"');
			expect(source).toContain("localStorage.setItem");
		});

		it("exposes value/setMode/toggle API", () => {
			expect(source).toContain("get value()");
			expect(source).toContain("setMode(");
			expect(source).toContain("toggle()");
		});

		it("validates mode is 'ask' or 'dashboard' only", () => {
			expect(source).toMatch(/m\s*!==\s*"ask"\s*&&\s*m\s*!==\s*"dashboard"/);
		});
	});

	describe("dashboardStore (section / company / period / snapshot)", () => {
		const source = read("src/lib/stores/dashboardStore.svelte.js");

		it("exports getDashboardStore factory", () => {
			expect(source).toContain("export function getDashboardStore");
		});

		it("tracks section / stockCode / axis / period state", () => {
			expect(source).toContain("section = $state");
			expect(source).toContain("stockCode = $state");
			expect(source).toContain("axis = $state");
			expect(source).toContain("period = $state");
		});

		it("exposes snapshot() for Phase 8 artifact attachment", () => {
			expect(source).toContain("snapshot()");
			expect(source).toContain("dashboardView");
			expect(source).toContain("visibleKpis");
		});

		it("supports pendingSnapshot for Ask 모드 bridge", () => {
			expect(source).toContain("pendingSnapshot");
			expect(source).toContain("setPendingSnapshot");
			expect(source).toContain("clearPendingSnapshot");
		});
	});

	describe("dlCall master API client", () => {
		const source = read("src/lib/api/dlCall.js");

		it("posts to /api/dl/call", () => {
			expect(source).toContain('"/api/dl/call"');
			expect(source).toContain('method: "POST"');
		});

		it("exposes dlCall and dlCapabilities", () => {
			expect(source).toContain("export async function dlCall");
			expect(source).toContain("export async function dlCapabilities");
		});

		it("supports apiRef / target / args / kwargs payload", () => {
			expect(source).toContain("apiRef");
			expect(source).toContain("target");
			expect(source).toContain("args");
			expect(source).toContain("kwargs");
		});

		it("hits /api/dl/capabilities for catalogue", () => {
			expect(source).toContain('"/api/dl/capabilities"');
		});
	});

	describe("dashboard shell components", () => {
		it("ModeToggle exists with Ask/Dashboard buttons", () => {
			const source = read("src/lib/dashboard/ModeToggle.svelte");
			expect(source).toContain("getUiMode");
			expect(source).toMatch(/setMode\("ask"\)/);
			expect(source).toMatch(/setMode\("dashboard"\)/);
		});

		it("EngineNav aligns with dartlab L1.5+L2+L3 taxonomy", () => {
			const source = read("src/lib/dashboard/EngineNav.svelte");
			// L1.5 Company
			expect(source).toContain("company.profile");
			expect(source).toContain("company.governance");
			expect(source).toContain("company.filings");
			// L2 engines
			expect(source).toMatch(/key: "analysis"/);
			expect(source).toMatch(/key: "quant"/);
			expect(source).toMatch(/key: "credit"/);
			expect(source).toMatch(/key: "macro"/);
			expect(source).toMatch(/key: "industry"/);
			// L3 Story
			expect(source).toMatch(/key: "story"/);
		});

		it("CompanySwitcher includes 16 KOSPI seed (Phase E 교체 대상)", () => {
			const source = read("src/lib/dashboard/CompanySwitcher.svelte");
			expect(source).toContain("005930"); // 삼성전자
			expect(source).toContain("035720"); // 카카오
			expect(source).toContain("000660"); // SK하이닉스
			expect(source).toContain("035420"); // NAVER
		});

		it("DashboardShell routes by dashboardStore.section", () => {
			const source = read("src/lib/dashboard/DashboardShell.svelte");
			expect(source).toContain("getDashboardStore");
			expect(source).toContain("SECTION_LABELS");
		});
	});

	describe("App + Sidebar integration", () => {
		it("App.svelte swaps main area by uiMode", () => {
			const source = read("src/App.svelte");
			expect(source).toContain("getUiMode");
			expect(source).toContain("DashboardShell");
			expect(source).toMatch(/uiMode\.value\s*===\s*"dashboard"/);
		});

		it("Sidebar.svelte hosts ModeToggle + EngineNav + CompanySwitcher", () => {
			const source = read("src/lib/components/Sidebar.svelte");
			expect(source).toContain("ModeToggle");
			expect(source).toContain("EngineNav");
			expect(source).toContain("CompanySwitcher");
			expect(source).toContain("getUiMode");
		});
	});

	describe("shadcn token alias (담백한 색감)", () => {
		const source = read("src/app.css");

		it("aliases shadcn standard tokens to dl-* primitives", () => {
			expect(source).toContain("--color-background: var(--color-dl-bg-dark)");
			expect(source).toContain("--color-primary: var(--color-dl-primary)");
			expect(source).toContain("--color-card: var(--color-dl-bg-card)");
			expect(source).toContain("--color-border: var(--color-dl-border)");
		});

		it("retains brand red as primary (single accent)", () => {
			expect(source).toContain("--color-dl-primary: #ea4647");
		});
	});

	describe("17 shadcn primitives 디렉토리 (nova style)", () => {
		const expected = [
			"button",
			"card",
			"dialog",
			"tabs",
			"table",
			"tooltip",
			"badge",
			"dropdown-menu",
			"separator",
			"scroll-area",
			"input",
			"label",
			"sheet",
			"avatar",
			"skeleton",
			"command",
		];
		for (const name of expected) {
			it(`installs ui/${name}/`, () => {
				expect(existsSync(path.join(ROOT, "src/lib/ui", name))).toBe(true);
			});
		}
	});
});
