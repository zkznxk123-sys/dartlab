// Dashboard data loaders — dlCall master API 위의 의미 단위 래퍼.
// 모든 loader 는 동일 shape 반환: { ok, data, error, raw }
//   data: 정규화된 컴포넌트용 props (or raw rows for tables)
//   error: { message } | null
//   raw: 원본 ToolResult JSON (디버깅용)

import { dlCall } from "$lib/api/dlCall.js";

function unwrapRows(response) {
	// engineCall 이 DataFrame 결과를 ref.payload.rows (head 20) 로 직렬화.
	const ref = response?.refs?.[0];
	if (ref?.payload?.rows && Array.isArray(ref.payload.rows)) {
		return {
			rows: ref.payload.rows,
			columns: ref.payload.columns || [],
			rowCount: ref.payload.rowCount || ref.payload.rows.length,
		};
	}
	return { rows: [], columns: [], rowCount: 0 };
}

function unwrapPreview(response) {
	// DataFrame 이 아닌 일반 객체 결과: refs[0].payload.preview (string)
	const ref = response?.refs?.[0];
	return ref?.payload?.preview || response?.data?.result || "";
}

async function safeCall(apiRef, opts) {
	try {
		const response = await dlCall(apiRef, opts);
		return { ok: true, response, error: null };
	} catch (err) {
		return { ok: false, response: null, error: { message: err?.message || String(err) } };
	}
}

// ── Company.filings — 공시 표 (~57 rows, dispatch 가 head 20) ──
export async function loadFilings(stockCode, opts = {}) {
	const { ok, response, error } = await safeCall("Company.filings", {
		target: stockCode,
		signal: opts.signal,
	});
	if (!ok) return { ok: false, data: null, error, raw: null };
	const { rows, columns, rowCount } = unwrapRows(response);
	return {
		ok: true,
		data: { rows, columns, rowCount, stockCode },
		error: null,
		raw: response,
	};
}

// ── Company.governance — 거버넌스 scorecard (1 row × 16 col) ──
export async function loadGovernance(stockCode, opts = {}) {
	const { ok, response, error } = await safeCall("Company.governance", {
		target: stockCode,
		signal: opts.signal,
	});
	if (!ok) return { ok: false, data: null, error, raw: null };
	const { rows, columns } = unwrapRows(response);
	const row = rows[0] || {};
	return {
		ok: true,
		data: { row, columns, stockCode },
		error: null,
		raw: response,
	};
}

// ── Company.workforce — 임직원 stats ──
export async function loadWorkforce(stockCode, opts = {}) {
	const { ok, response, error } = await safeCall("Company.workforce", {
		target: stockCode,
		signal: opts.signal,
	});
	if (!ok) return { ok: false, data: null, error, raw: null };
	const { rows, columns } = unwrapRows(response);
	return {
		ok: true,
		data: { rows, columns, stockCode },
		error: null,
		raw: response,
	};
}

// ── Company.market — 시장 데이터 (price/cap) ──
export async function loadMarket(stockCode, opts = {}) {
	const { ok, response, error } = await safeCall("Company.market", {
		target: stockCode,
		signal: opts.signal,
	});
	if (!ok) return { ok: false, data: null, error, raw: null };
	const { rows, columns } = unwrapRows(response);
	return {
		ok: true,
		data: { rows, columns, preview: unwrapPreview(response), stockCode },
		error: null,
		raw: response,
	};
}
