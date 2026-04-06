/**
 * 모바일 진단용 디버그 모듈.
 *
 * - console.warn / console.error 를 가로채 ring buffer에 저장
 * - URL ?debug=1 또는 sessionStorage 'dartlab.debug=1' 시 활성화
 * - DebugOverlay 컴포넌트가 이걸 읽어서 화면에 표시
 */

const MAX_LOGS = 20;
const _logs = [];
let _enabled = false;

export function isDebugEnabled() {
	if (_enabled) return true;
	try {
		if (typeof window !== "undefined") {
			const url = new URL(window.location.href);
			if (url.searchParams.get("debug") === "1") {
				_enabled = true;
				try { sessionStorage.setItem("dartlab.debug", "1"); } catch {}
				return true;
			}
		}
		if (typeof sessionStorage !== "undefined" && sessionStorage.getItem("dartlab.debug") === "1") {
			_enabled = true;
			return true;
		}
	} catch {
		// ignore
	}
	return false;
}

export function disableDebug() {
	_enabled = false;
	try { sessionStorage.removeItem("dartlab.debug"); } catch {}
}

export function getLogs() {
	return _logs.slice();
}

export function pushLog(level, args) {
	const text = args.map((a) => {
		if (a instanceof Error) return a.message;
		if (typeof a === "object") {
			try { return JSON.stringify(a); } catch { return String(a); }
		}
		return String(a);
	}).join(" ");
	const entry = { ts: new Date().toLocaleTimeString(), level, text };
	_logs.push(entry);
	if (_logs.length > MAX_LOGS) _logs.shift();
}

let _installed = false;

export function installConsoleCapture() {
	if (_installed || typeof console === "undefined") return;
	_installed = true;
	const origWarn = console.warn.bind(console);
	const origError = console.error.bind(console);
	console.warn = (...args) => { pushLog("warn", args); origWarn(...args); };
	console.error = (...args) => { pushLog("error", args); origError(...args); };
}
