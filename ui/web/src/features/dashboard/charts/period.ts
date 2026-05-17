// period label formatter — 차트 axis · table 헤더 · Tooltip 모두 같은 함수 사용.
// "2024-FY" → 연간만이면 "2024", 분기 섞이면 "'24Q4"
// "2024-HY" → "'24Q2" (HY 표시 금지)

export function makePeriodFormatter(categories: string[]) {
	const hasQuarter = categories.some((c) => /-(Q1|HY|Q3)$/.test(c));
	return (p: string): string => {
		const m = /^(\d{4})-(\w+)$/.exec(p);
		if (!m) return p;
		const [, y, tag] = m;
		if (!hasQuarter && tag === 'FY') return y;
		const shortYear = `'${y.slice(2)}`;
		if (tag === 'Q1') return `${shortYear}Q1`;
		if (tag === 'HY') return `${shortYear}Q2`;
		if (tag === 'Q3') return `${shortYear}Q3`;
		if (tag === 'FY') return `${shortYear}Q4`;
		return p;
	};
}
