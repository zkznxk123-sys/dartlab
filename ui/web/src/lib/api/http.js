import { authHeaders } from "./token.js";

export const BASE = "";

// 기본 timeout — Quick Tunnel + 모바일 LTE 조합에서 fetch가 영원히 pending되는 문제 차단.
// SSE 스트리밍처럼 의도적으로 긴 응답은 init.signal로 따로 처리.
const DEFAULT_TIMEOUT_MS = 15000;

/**
 * 모든 API fetch는 authedFetch를 거친다 — 터널 모드에서 토큰 자동 주입 + timeout.
 *
 * Microsoft DevTunnels anti-phishing 우회:
 *   X-Tunnel-Skip-AntiPhishing-Page-Redirect: true
 */
export async function authedFetch(url, init = {}) {
	const headers = {
		...(init.headers || {}),
		...authHeaders(),
	};
	// 사용자 지정 signal이 있으면 그대로, 없으면 timeout signal 부여
	let signal = init.signal;
	let timeoutId = null;
	if (!signal && typeof AbortController !== "undefined") {
		const controller = new AbortController();
		timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
		signal = controller.signal;
	}
	try {
		return await fetch(url, { ...init, headers, signal });
	} finally {
		if (timeoutId) clearTimeout(timeoutId);
	}
}

/**
 * XMLHttpRequest 기반 fetch 대체 — 일부 모바일 환경에서 fetch promise가
 * 응답을 받았는데도 resolve 안 되는 zombie 케이스 우회.
 * Response-like 객체 반환 (ok / status / json() / text()).
 */
export function xhrFetch(url, init = {}) {
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		const method = (init.method || "GET").toUpperCase();
		xhr.open(method, url, true);
		xhr.timeout = DEFAULT_TIMEOUT_MS;

		// 헤더 주입
		const headers = {
			...(init.headers || {}),
			...authHeaders(),
		};
		for (const [k, v] of Object.entries(headers)) {
			try { xhr.setRequestHeader(k, String(v)); } catch (_) {}
		}

		xhr.onload = () => {
			const status = xhr.status;
			const text = xhr.responseText;
			resolve({
				ok: status >= 200 && status < 300,
				status,
				statusText: xhr.statusText,
				json: async () => {
					try { return JSON.parse(text); } catch (e) { throw new Error("Invalid JSON: " + text.slice(0, 100)); }
				},
				text: async () => text,
				headers: {
					get: (name) => xhr.getResponseHeader(name),
				},
			});
		};
		xhr.onerror = () => reject(new Error("XHR network error"));
		xhr.ontimeout = () => reject(new Error("XHR timeout (" + DEFAULT_TIMEOUT_MS + "ms)"));
		xhr.onabort = () => reject(new Error("XHR aborted"));

		try {
			xhr.send(init.body || null);
		} catch (e) {
			reject(e);
		}
	});
}

export async function fetchPack(url) {
	const res = await authedFetch(url);
	if (!res.ok) throw new Error(`요청 실패: ${res.status}`);
	return res.json();
}
