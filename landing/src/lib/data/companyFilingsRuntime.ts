import { readParquetRows, type FetchLike } from './hfRange';

export interface RegularFiling {
	rceptNo: string;
	rceptDate: string;
	reportType: string;
	year: string;
	url: string;
}

interface DocsRow extends Record<string, unknown> {
	year?: unknown;
	rcept_date?: unknown;
	rcept_no?: unknown;
	report_type?: unknown;
}

const REGULAR_REPORTS = ['사업보고서', '반기보고서', '분기보고서'];

export async function loadCompanyRegularFilings(
	stockCode: string,
	limit = 5,
	fetchFn: FetchLike = fetch
): Promise<RegularFiling[]> {
	const code = stockCode.trim();
	if (!/^\d{6}$/.test(code)) return [];
	const data = await readParquetRows<DocsRow>(`dart/docs/${code}.parquet`, {
		columns: ['year', 'rcept_date', 'rcept_no', 'report_type'],
		fetchFn
	});
	const seen = new Map<string, RegularFiling>();
	for (const row of data.rows) {
		const rceptNo = String(row.rcept_no ?? '').trim();
		const reportType = String(row.report_type ?? '').trim();
		if (!rceptNo || !REGULAR_REPORTS.some((name) => reportType.includes(name))) continue;
		if (seen.has(rceptNo)) continue;
		seen.set(rceptNo, {
			rceptNo,
			rceptDate: String(row.rcept_date ?? ''),
			reportType,
			year: String(row.year ?? ''),
			url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`
		});
	}
	return Array.from(seen.values())
		.sort((a, b) => b.rceptDate.localeCompare(a.rceptDate) || b.rceptNo.localeCompare(a.rceptNo))
		.slice(0, limit);
}
