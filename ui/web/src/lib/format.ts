// 단위 보존 숫자 포맷 — 차트 axis · Tooltip · 표 셀 · KPI 타일 모두 단일 호출.
// 단위 (원/%/회/일/배) 에 따라 자동 분기. opts.precise=true 시 한 자리 더.

export function formatValue(
	v: number | null | undefined,
	unit?: string,
	opts?: { precise?: boolean },
): string {
	if (v == null || !Number.isFinite(v)) return '–';
	if (unit === '%') return v.toFixed(opts?.precise ? 2 : 1) + '%';
	if (unit === '회') return v.toFixed(2);
	if (unit === '일') return Math.round(v).toLocaleString();
	if (unit === '배') return v.toFixed(2);
	// 큰 숫자 (원·기타 절대값)
	const abs = Math.abs(v);
	if (abs >= 1e12) return (v / 1e12).toFixed(1) + '조';
	if (abs >= 1e8) return (v / 1e8).toFixed(0) + '억';
	if (abs >= 1e4) return (v / 1e4).toFixed(0) + '만';
	if (abs >= 1000) return v.toLocaleString();
	if (Number.isInteger(v)) return v.toString();
	return v.toFixed(2);
}

// 차트 axis 용 더 짧은 라벨 — 1단위 자리수 줄임.
export function formatAxisTick(v: unknown, unit?: string): string {
	if (typeof v !== 'number' || !Number.isFinite(v)) return '–';
	if (unit === '%') return v.toFixed(0) + '%';
	if (unit === '회') return v.toFixed(1);
	if (unit === '일') return Math.round(v).toString();
	const abs = Math.abs(v);
	if (abs >= 1e12) return (v / 1e12).toFixed(1) + '조';
	if (abs >= 1e8) return (v / 1e8).toFixed(0) + '억';
	if (abs >= 1e4) return (v / 1e4).toFixed(0) + '만';
	if (abs >= 1000) return v.toLocaleString();
	return v.toFixed(0);
}

// 단위 + delta % 동시 표시 — DiffView/KpiTile 보조 라인.
export function formatDelta(deltaPct: number | null | undefined): string {
	if (deltaPct == null || !Number.isFinite(deltaPct)) return '';
	return (deltaPct > 0 ? '+' : '') + deltaPct.toFixed(1) + '%';
}
