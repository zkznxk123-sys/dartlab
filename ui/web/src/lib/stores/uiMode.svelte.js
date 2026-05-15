// UI mode store — Ask 모드 / Dashboard 모드 토글.
// Svelte 5 runes + localStorage 영속. Singleton (앱 전체에서 하나).

const LS_KEY = "dartlab-ui-mode";

function loadInitial() {
	if (typeof localStorage === "undefined") return "ask";
	const v = localStorage.getItem(LS_KEY);
	return v === "dashboard" ? "dashboard" : "ask";
}

let _instance = null;

export function getUiMode() {
	if (_instance) return _instance;
	let mode = $state(loadInitial());

	_instance = {
		get value() {
			return mode;
		},
		setMode(m) {
			if (m !== "ask" && m !== "dashboard") return;
			mode = m;
			if (typeof localStorage !== "undefined") {
				localStorage.setItem(LS_KEY, m);
			}
		},
		toggle() {
			this.setMode(mode === "ask" ? "dashboard" : "ask");
		},
	};
	return _instance;
}
