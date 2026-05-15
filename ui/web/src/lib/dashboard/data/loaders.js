// Dashboard data loaders — dlCall master API 위의 의미 단위 래퍼.
// 모든 loader 는 동일 shape 반환: { ok, data, error, raw }
//   data: 정규화된 컴포넌트용 props (or raw rows for tables)
//   error: { message } | null
//   raw: 원본 ToolResult JSON (디버깅용)

import { dlCall } from "$lib/api/dlCall.js";

function unwrapRows(response) {
	// dl.py 가 DataFrame 을 {_type:'DataFrame', rowCount, columns, rows} 로 직렬화.
	const d = response?.data;
	if (d && d._type === "DataFrame" && Array.isArray(d.rows)) {
		return {
			rows: d.rows,
			columns: d.columns || [],
			rowCount: d.rowCount || d.rows.length,
		};
	}
	return { rows: [], columns: [], rowCount: 0 };
}

function unwrapData(response) {
	// dict / list 결과는 response.data 가 직접 payload.
	return response?.data ?? null;
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
	const raw = unwrapData(response);
	return {
		ok: true,
		data: { rows, columns, raw, stockCode },
		error: null,
		raw: response,
	};
}

// ── Generic engine axis loader — analysis / quant / credit / industry / macro ──
//    apiRef 별 axis 호출. axis 없으면 catalogue DataFrame, 있으면 axis-specific.
//    응답 shape 는 dl.py 의 _toJsonSafe 가 정규화 (DataFrame envelope 또는 dict).
export async function loadEngineAxis(apiRef, stockCode, axis, opts = {}) {
	const kwargs = axis ? { axis } : {};
	const { ok, response, error } = await safeCall(apiRef, {
		target: stockCode,
		kwargs,
		signal: opts.signal,
	});
	if (!ok) return { ok: false, data: null, error, raw: null };

	if (axis) {
		return {
			ok: true,
			data: { apiRef, axis, payload: unwrapData(response), stockCode },
			error: null,
			raw: response,
		};
	}
	const { rows, columns } = unwrapRows(response);
	return {
		ok: true,
		data: { apiRef, axis: null, axes: rows, columns, stockCode },
		error: null,
		raw: response,
	};
}

// ── Company.analysis — axis 별 구조화 분석 ──
//    axis 없으면 catalogue DataFrame (22 axes meta) 반환.
//    axis 있으면 dict — { <metricName>: { history: [...], ... } } 구조.
export async function loadAnalysis(stockCode, axis, opts = {}) {
	const kwargs = axis ? { axis } : {};
	const { ok, response, error } = await safeCall("Company.analysis", {
		target: stockCode,
		kwargs,
		signal: opts.signal,
	});
	if (!ok) return { ok: false, data: null, error, raw: null };

	if (axis) {
		// dict shape: { metricKey: { history: [...] } }
		return {
			ok: true,
			data: { axis, payload: unwrapData(response), stockCode },
			error: null,
			raw: response,
		};
	}
	// axis 없음: 22-axis catalogue DataFrame
	const { rows, columns } = unwrapRows(response);
	return {
		ok: true,
		data: { axis: null, axes: rows, columns, stockCode },
		error: null,
		raw: response,
	};
}
