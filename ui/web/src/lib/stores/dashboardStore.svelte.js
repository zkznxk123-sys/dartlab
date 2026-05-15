// Dashboard state store v2 — 4 탭 (IS/BS/CF/Ratios) + annual/quarterly mode.
// Phase 8 ask snapshot 첨부 source.

const LS_KEY = "dartlab-dashboard-state-v2";

const DEFAULT = {
	section: "is",
	stockCode: "035720",
	mode: "annual",
};

function loadInitial() {
	if (typeof localStorage === "undefined") return DEFAULT;
	try {
		const raw = localStorage.getItem(LS_KEY);
		if (!raw) return DEFAULT;
		const parsed = JSON.parse(raw);
		return {
			section: ["is", "bs", "cf", "ratios"].includes(parsed.section) ? parsed.section : DEFAULT.section,
			stockCode: parsed.stockCode || DEFAULT.stockCode,
			mode: ["annual", "quarterly"].includes(parsed.mode) ? parsed.mode : DEFAULT.mode,
		};
	} catch {
		return DEFAULT;
	}
}

let _instance = null;

export function getDashboardStore() {
	if (_instance) return _instance;

	const saved = loadInitial();
	let section = $state(saved.section);
	let stockCode = $state(saved.stockCode);
	let mode = $state(saved.mode);
	let visibleKpis = $state([]);
	let pendingSnapshot = $state(null);

	function persist() {
		if (typeof localStorage === "undefined") return;
		try {
			localStorage.setItem(LS_KEY, JSON.stringify({ section, stockCode, mode }));
		} catch {
			/* localStorage 가득 차도 무시 */
		}
	}

	_instance = {
		get section() { return section; },
		get stockCode() { return stockCode; },
		get mode() { return mode; },
		get visibleKpis() { return visibleKpis; },
		get pendingSnapshot() { return pendingSnapshot; },

		setSection(s) { section = s; persist(); },
		setStockCode(c) { stockCode = c; persist(); },
		setMode(m) { mode = m; persist(); },
		setVisibleKpis(k) { visibleKpis = Array.isArray(k) ? k : []; },
		setPendingSnapshot(s) { pendingSnapshot = s; },
		clearPendingSnapshot() { pendingSnapshot = null; },

		snapshot() {
			return {
				dashboardView: section,
				stockCode,
				mode,
				visibleKpis: [...visibleKpis],
			};
		},
	};
	return _instance;
}
