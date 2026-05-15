// Dashboard state store — section / company / axis / period + snapshot 캡처.
// Phase 8 에서 AskPanel 로 첨부하는 artifact 의 source.

const LS_KEY = "dartlab-dashboard-state";

const DEFAULT = {
	section: "company.profile",
	stockCode: "035720", // 카카오 default
	axis: null,
	period: "TTM",
};

function loadInitial() {
	if (typeof localStorage === "undefined") return DEFAULT;
	try {
		const raw = localStorage.getItem(LS_KEY);
		if (!raw) return DEFAULT;
		const parsed = JSON.parse(raw);
		return {
			section: parsed.section || DEFAULT.section,
			stockCode: parsed.stockCode || DEFAULT.stockCode,
			axis: parsed.axis || null,
			period: parsed.period || DEFAULT.period,
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
	let axis = $state(saved.axis);
	let period = $state(saved.period);
	let visibleKpis = $state([]);
	let pendingSnapshot = $state(null);

	function persist() {
		if (typeof localStorage === "undefined") return;
		try {
			localStorage.setItem(
				LS_KEY,
				JSON.stringify({ section, stockCode, axis, period })
			);
		} catch {
			/* localStorage 가득 차도 무시 — 영속 실패가 작업 차단하면 안됨 */
		}
	}

	_instance = {
		get section() {
			return section;
		},
		get stockCode() {
			return stockCode;
		},
		get axis() {
			return axis;
		},
		get period() {
			return period;
		},
		get visibleKpis() {
			return visibleKpis;
		},
		get pendingSnapshot() {
			return pendingSnapshot;
		},

		setSection(s) {
			section = s;
			axis = null; // section 바뀌면 axis 리셋
			persist();
		},
		setStockCode(c) {
			stockCode = c;
			persist();
		},
		setAxis(a) {
			axis = a;
			persist();
		},
		setPeriod(p) {
			period = p;
			persist();
		},
		setVisibleKpis(k) {
			visibleKpis = Array.isArray(k) ? k : [];
		},
		setPendingSnapshot(s) {
			pendingSnapshot = s;
		},
		clearPendingSnapshot() {
			pendingSnapshot = null;
		},

		/** Phase 8 artifact 첨부 페이로드. */
		snapshot() {
			return {
				dashboardView: section,
				stockCode,
				axis,
				period,
				visibleKpis: [...visibleKpis],
			};
		},
	};
	return _instance;
}
