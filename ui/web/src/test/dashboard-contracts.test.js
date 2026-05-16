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

		it("tracks stockCode / mode state (v3 — section 폐기)", () => {
			expect(source).toContain("stockCode = $state");
			expect(source).toContain("mode = $state");
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

		it("Sidebar dashboard 모드 = 재무제표 1 항목", () => {
			const source = read("src/lib/components/Sidebar.svelte");
			expect(source).toContain('key: "financial"');
			expect(source).toContain("재무제표");
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
			expect(source).toContain("FinancialView");
		});
	});

	describe("App + Sidebar integration", () => {
		it("App.svelte swaps main area by uiMode", () => {
			const source = read("src/App.svelte");
			expect(source).toContain("getUiMode");
			expect(source).toContain("DashboardShell");
			expect(source).toMatch(/uiMode\.value\s*===\s*"dashboard"/);
		});

		it("Sidebar.svelte hosts ModeToggle + 4 탭 nav + CompanySwitcher", () => {
			const source = read("src/lib/components/Sidebar.svelte");
			expect(source).toContain("ModeToggle");
			expect(source).toContain("FINANCIAL_NAV");
			expect(source).toContain("CompanySwitcher");
			expect(source).toContain("getUiMode");
		});
	});

	describe("shadcn HSL 토큰 layer (Editorial 폐기 후)", () => {
		const source = read("src/app.css");

		it("defines shadcn HSL tokens (light + dark)", () => {
			expect(source).toContain("--background:");
			expect(source).toContain("--card:");
			expect(source).toContain("--primary:");
			expect(source).toContain("--border:");
			expect(source).toContain("--chart-1:");
			expect(source).toContain("--chart-5:");
		});

		it("retains dl-* primitives for Ask/chat surface", () => {
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
