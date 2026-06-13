import { readParquetRows, type FetchLike } from '@dartlab/ui-runtime/data/hfRange';

export interface RegularFiling {
	rceptNo: string;
	rceptDate: string;
	reportType: string;
	year: string;
	url: string;
}

interface DocsRow extends Record<string, unknown> {
	period?: unknown;
	rceptNo?: unknown;
}

const REGULAR_REPORTS = ['사업보고서', '반기보고서', '분기보고서'];

export async function loadCompanyRegularFilings(
	stockCode: string,
	limit = 5,
	fetchFn: FetchLike = fetch
): Promise<RegularFiling[]> {
	const code = stockCode.trim();
	if (!/^\d{6}$/.test(code)) return [];
	const data = await readParquetRows<DocsRow>(`dart/panel/${code}.parquet`, {
		columns: ['period', 'rceptNo'],
		fetchFn
	});
	const seen = new Map<string, RegularFiling>();
	for (const row of data.rows) {
		const rceptNo = String(row.rceptNo ?? '').trim();
		const period = String(row.period ?? '').trim();
		const reportType = periodReportType(period);
		if (!rceptNo || !REGULAR_REPORTS.some((name) => reportType.includes(name))) continue;
		if (seen.has(rceptNo)) continue;
		seen.set(rceptNo, {
			rceptNo,
			rceptDate: rceptDateFromNo(rceptNo),
			reportType,
			year: period.slice(0, 4),
			url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`
		});
	}
	return Array.from(seen.values())
		.sort((a, b) => b.rceptDate.localeCompare(a.rceptDate) || b.rceptNo.localeCompare(a.rceptNo))
		.slice(0, limit);
}

function periodReportType(period: string): string {
	const key = period.toUpperCase();
	if (key.endsWith('Q4')) return '사업보고서';
	if (key.endsWith('Q2')) return '반기보고서';
	if (key.endsWith('Q1') || key.endsWith('Q3')) return '분기보고서';
	return '정기보고서';
}

function rceptDateFromNo(rceptNo: string): string {
	const compact = rceptNo.slice(0, 8);
	if (!/^\d{8}$/.test(compact)) return '';
	return `${compact.slice(0, 4)}-${compact.slice(4, 6)}-${compact.slice(6, 8)}`;
}
