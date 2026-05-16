// Dashboard state store v3 — stockCode + mode 만. (재무제표 4 분류는 FinancialView 내부 Tabs.)

const LS_KEY = "dartlab-dashboard-state-v3";

const DEFAULT = {
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
	let stockCode = $state(saved.stockCode);
	let mode = $state(saved.mode);
	let visibleKpis = $state([]);
	let pendingSnapshot = $state(null);

	function persist() {
		if (typeof localStorage === "undefined") return;
		try {
			localStorage.setItem(LS_KEY, JSON.stringify({ stockCode, mode }));
		} catch {
			/* localStorage 가득 차도 무시 */
		}
	}

	_instance = {
		get stockCode() { return stockCode; },
		get mode() { return mode; },
		get visibleKpis() { return visibleKpis; },
		get pendingSnapshot() { return pendingSnapshot; },

		setStockCode(c) { stockCode = c; persist(); },
		setMode(m) { mode = m; persist(); },
		setVisibleKpis(k) { visibleKpis = Array.isArray(k) ? k : []; },
		setPendingSnapshot(s) { pendingSnapshot = s; },
		clearPendingSnapshot() { pendingSnapshot = null; },

		snapshot() {
			return {
				dashboardView: "financial",
				stockCode,
				mode,
				visibleKpis: [...visibleKpis],
			};
		},
	};
	return _instance;
}
