// Theme store — dark | light | auto. localStorage 영속.
// document.documentElement.dataset.theme 에 setattr.
// default: dark (값 없음). light: 강제 light. auto: prefers-color-scheme 따라감.

const LS_KEY = "dartlab-theme";

function loadInitial() {
	if (typeof localStorage === "undefined") return "dark";
	const v = localStorage.getItem(LS_KEY);
	if (v === "light" || v === "dark" || v === "auto") return v;
	return "dark";
}

function applyToRoot(t) {
	if (typeof document === "undefined") return;
	const root = document.documentElement;
	if (t === "dark") {
		delete root.dataset.theme;
	} else {
		root.dataset.theme = t;
	}
}

let _instance = null;

export function getTheme() {
	if (_instance) return _instance;
	let theme = $state(loadInitial());
	applyToRoot(theme);

	_instance = {
		get value() {
			return theme;
		},
		setTheme(t) {
			if (t !== "dark" && t !== "light" && t !== "auto") return;
			theme = t;
			applyToRoot(t);
			if (typeof localStorage !== "undefined") {
				localStorage.setItem(LS_KEY, t);
			}
		},
		cycle() {
			const next = theme === "dark" ? "light" : theme === "light" ? "auto" : "dark";
			this.setTheme(next);
		},
	};
	return _instance;
}
