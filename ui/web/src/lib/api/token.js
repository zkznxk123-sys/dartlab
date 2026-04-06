/**
 * Tunnel token 관리 — 단일 출처.
 *
 * 동작:
 *   1. SPA가 처음 로드될 때 URL 쿼리스트링 ?token=... 에서 토큰 추출
 *   2. sessionStorage에 저장 (탭 닫으면 사라짐 — XSS 측면에서 localStorage보다 안전)
 *   3. URL에서 토큰 제거 (history.replaceState) — 북마크/스크린샷 노출 방지
 *   4. 모든 fetch에 Authorization: Bearer <token> 헤더 자동 추가
 *   5. SSE/EventSource처럼 헤더를 못 붙이는 경우는 ?token=... 쿼리로 부착
 *
 * 토큰이 없으면(데스크탑 로컬 모드) headers/url을 그대로 둠 — 회귀 없음.
 */

const STORAGE_KEY = "dartlab.tunnelToken";
let _token = null;
let _initialized = false;

function _readFromUrl() {
	if (typeof window === "undefined") return null;
	try {
		const url = new URL(window.location.href);
		return url.searchParams.get("token");
	} catch {
		return null;
	}
}

function _stripFromUrl() {
	if (typeof window === "undefined") return;
	try {
		const url = new URL(window.location.href);
		if (url.searchParams.has("token")) {
			url.searchParams.delete("token");
			window.history.replaceState(null, "", url.toString());
		}
	} catch {
		// noop
	}
}

function _readFromStorage() {
	// sessionStorage → localStorage → cookie 순으로 시도
	if (typeof sessionStorage !== "undefined") {
		try {
			const v = sessionStorage.getItem(STORAGE_KEY);
			if (v) return v;
		} catch {}
	}
	if (typeof localStorage !== "undefined") {
		try {
			const v = localStorage.getItem(STORAGE_KEY);
			if (v) return v;
		} catch {}
	}
	if (typeof document !== "undefined") {
		try {
			const m = document.cookie.match(new RegExp("(?:^|; )" + STORAGE_KEY + "=([^;]*)"));
			if (m) return decodeURIComponent(m[1]);
		} catch {}
	}
	return null;
}

function _writeToStorage(token) {
	let ok = false;
	// sessionStorage 시도
	if (typeof sessionStorage !== "undefined") {
		try {
			sessionStorage.setItem(STORAGE_KEY, token);
			ok = sessionStorage.getItem(STORAGE_KEY) === token;
		} catch {
			ok = false;
		}
	}
	// 추가 폴백: localStorage (iOS Safari의 Private에선 sessionStorage가 막힐 수 있음)
	if (!ok && typeof localStorage !== "undefined") {
		try {
			localStorage.setItem(STORAGE_KEY, token);
			if (localStorage.getItem(STORAGE_KEY) === token) ok = true;
		} catch {}
	}
	// 최종 폴백: cookie (탭간 공유, JS-만접근 가능)
	if (!ok && typeof document !== "undefined") {
		try {
			// SameSite=Strict, Secure (HTTPS만), 1일 만료
			document.cookie = `${STORAGE_KEY}=${encodeURIComponent(token)}; path=/; max-age=86400; SameSite=Strict; Secure`;
			ok = document.cookie.includes(STORAGE_KEY + "=");
		} catch {}
	}
	return ok;
}

/**
 * SPA 부트스트랩에서 1회 호출. URL/storage에서 토큰을 찾아 메모리에 적재.
 *
 * 정책: URL에서 토큰을 절대 제거하지 않는다.
 * - iOS Safari는 페이지 reload/탭 전환/URL 편집 시 sessionStorage를 비우는
 *   케이스가 있어, 한 번 strip하면 토큰을 영영 복구할 방법이 없다.
 * - URL에 token이 보이는 건 미관 손실이지만, 잃어버리는 것보다 훨씬 낫다.
 * - 추가로 sessionStorage / localStorage / cookie 3중 폴백으로 저장 시도.
 *
 * @returns {string|null} 토큰 또는 null
 */
export function initToken() {
	if (_initialized) return _token;
	_initialized = true;

	const fromUrl = _readFromUrl();
	if (fromUrl) {
		_token = fromUrl;
		_writeToStorage(fromUrl); // 베스트 에포트 저장 (실패해도 URL이 있으니 OK)
		return _token;
	}

	const fromStorage = _readFromStorage();
	if (fromStorage) {
		_token = fromStorage;
		return _token;
	}

	return null;
}

/**
 * 현재 토큰 반환. 초기화 안 됐으면 자동 초기화.
 * @returns {string|null}
 */
export function getToken() {
	if (!_initialized) initToken();
	return _token;
}

/**
 * fetch headers에 머지할 인증 헤더 dict. 토큰 없으면 빈 객체.
 * @returns {Record<string,string>}
 */
export function authHeaders() {
	const t = getToken();
	return t ? { Authorization: `Bearer ${t}` } : {};
}

/**
 * 토큰의 현재 출처를 반환 — 디버그용.
 * @returns {"url"|"storage"|"memory"|"none"}
 */
export function getTokenSource() {
	if (_readFromUrl()) return "url";
	if (_token && !_readFromStorage()) return "memory";
	if (_readFromStorage()) return "storage";
	return "none";
}

/**
 * 디버그용 — 현재 토큰 상태 콘솔 출력.
 */
export function debugTokenStatus() {
	if (typeof console !== "undefined") {
		console.log("[dartlab.token]", {
			initialized: _initialized,
			hasMemoryToken: !!_token,
			hasUrlToken: !!_readFromUrl(),
			hasStorageToken: !!_readFromStorage(),
		});
	}
}

/**
 * URL에 토큰을 쿼리스트링으로 부착 (EventSource/SSE/img src 등 헤더 못 쓰는 경우용).
 * 토큰 없으면 원본 URL 그대로.
 * @param {string} url
 * @returns {string}
 */
export function withTokenQuery(url) {
	const t = getToken();
	if (!t) return url;
	try {
		const u = new URL(url, typeof window !== "undefined" ? window.location.origin : "http://localhost");
		if (!u.searchParams.has("token")) u.searchParams.set("token", t);
		return u.toString();
	} catch {
		// 상대 경로 등 URL 파싱 실패 → 단순 결합
		const sep = url.includes("?") ? "&" : "?";
		return `${url}${sep}token=${encodeURIComponent(t)}`;
	}
}

/**
 * 테스트/디버그용 — 토큰 강제 설정.
 * @param {string|null} token
 */
export function _setTokenForTest(token) {
	_token = token;
	_initialized = true;
}

/**
 * 테스트용 — 상태 초기화.
 */
export function _resetForTest() {
	_token = null;
	_initialized = false;
}
