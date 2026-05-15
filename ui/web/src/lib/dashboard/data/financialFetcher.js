// 14 컴포넌트 + prefetch dlCall wrapper.
import { dlCall } from "$lib/api/dlCall.js";

const apiRefMap = {
	is: ["isOverview", "isRevenueTrend", "isMarginTrend", "isCostStructure"],
	bs: ["bsOverview", "bsComposition", "bsLeverage"],
	cf: ["cfOverview", "cfWaterfall", "cfFreeCashFlow"],
	ratios: ["ratiosProfitability", "ratiosStability", "ratiosEfficiency", "ratiosGrowth"],
};

export function refsFor(section) {
	return apiRefMap[section] || [];
}

export async function fetchView(section, stockCode, mode, signal) {
	const refs = refsFor(section);
	const results = await Promise.all(
		refs.map((name) =>
			dlCall(`viz.dashboard.financial.${name}`, {
				target: stockCode,
				kwargs: { mode },
				signal,
			})
		)
	);
	const out = {};
	refs.forEach((name, i) => {
		const r = results[i];
		out[name] = r?.ok ? r.data : { error: r?.message || "unknown" };
	});
	return out;
}

export async function prefetchCompany(stockCode, signal) {
	return dlCall("viz.dashboard.companyCache.prefetch", {
		target: stockCode,
		signal,
	});
}
