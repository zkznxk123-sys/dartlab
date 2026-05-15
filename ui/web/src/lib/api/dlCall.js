// Master API client — POST /api/dl/call wrapper.
// 모든 dashboard data fetch 의 단일 진입점. capability registry 화이트리스트
// 위에서 reflection dispatch 되므로 dartlab 새 capability 추가 시 자동 따라감.

const CALL_ENDPOINT = "/api/dl/call";
const CAPS_ENDPOINT = "/api/dl/capabilities";

/**
 * dartlab capability 호출.
 * @param {string} apiRef "Company.show" / "Company.analysis" / "macro.rates" 등
 * @param {{ target?: string, args?: any[], kwargs?: object, signal?: AbortSignal }} opts
 * @returns {Promise<{ ok: boolean, apiRef: string, target: string|null, message: string, data: any, refs: any[] }>}
 */
export async function dlCall(apiRef, opts = {}) {
	const { target, args = [], kwargs = {}, signal } = opts;

	const body = { apiRef };
	if (target) body.target = target;
	if (args && args.length) body.args = args;
	if (kwargs && Object.keys(kwargs).length) body.kwargs = kwargs;

	const res = await fetch(CALL_ENDPOINT, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
		signal,
	});

	if (!res.ok) {
		let msg = `dlCall ${apiRef} failed: ${res.status}`;
		try {
			const err = await res.json();
			const detail = err.detail || err;
			msg += ` — ${detail.message || detail.error || JSON.stringify(detail)}`;
		} catch {
			/* JSON parse 실패 — status 만으로 throw */
		}
		throw new Error(msg);
	}

	return res.json();
}

/**
 * Capability catalogue — registry 전체 public capability 목록.
 * dashboard 메뉴 구성 + 진단용. dartlab 코드 변경 시 자동 따라감.
 */
export async function dlCapabilities(opts = {}) {
	const res = await fetch(CAPS_ENDPOINT, { signal: opts.signal });
	if (!res.ok) throw new Error(`dlCapabilities failed: ${res.status}`);
	return res.json();
}
