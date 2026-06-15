// 비정기(수시)공시 — dart/allFilings/recent.parquet (HF, 전 이력 통합 1파일) 을 stock_code
// 필터로 단건 읽기. 일자 date-scan(휴일 404 콘솔오염) 폐기 — 통합파일은 stock_code 정렬이라
// filter pushdown 이 회사 row-group 만 읽음. content_raw 없음(빌드시 메타만). per-code 캐시.
// 통합파일 생성: .github/scripts/sync/buildAllFilingsRecent.py (정기보고서는 이미 제외됨).
// 타입 정본 = contracts (NonRegularFiling 승격 완료 — 중복 정의 금지).
import type { NonRegularFiling } from '@dartlab/ui-contracts';
import { readParquetRows, type FetchLike } from '../../../data/hfRange';

interface RecentRow extends Record<string, unknown> {
	stock_code?: unknown;
	rcept_dt?: unknown;
	report_nm?: unknown;
	rcept_no?: unknown;
	flr_nm?: unknown;
}

const COLS = ['stock_code', 'rcept_dt', 'report_nm', 'rcept_no', 'flr_nm'];
const REGULAR = ['사업보고서', '반기보고서', '분기보고서'];

function fmtDate(s: string): string {
	const c = String(s).replace(/\D/g, '').slice(0, 8);
	return c.length === 8 ? `${c.slice(0, 4)}-${c.slice(4, 6)}-${c.slice(6, 8)}` : String(s);
}

const cache = new Map<string, NonRegularFiling[]>();

export async function loadCompanyNonRegularFilings(
	stockCode: string,
	{ fetchFn = fetch as FetchLike }: { fetchFn?: FetchLike } = {}
): Promise<NonRegularFiling[]> {
	const code = stockCode.trim();
	if (!/^\d{6}$/.test(code)) return [];
	if (cache.has(code)) return cache.get(code) as NonRegularFiling[];
	try {
		const { rows } = await readParquetRows<RecentRow>('dart/allFilings/recent.parquet', {
			columns: COLS,
			filter: { stock_code: { $in: [code] } },
			fetchFn
		});
		const seen = new Set<string>();
		const result: NonRegularFiling[] = [];
		for (const r of rows) {
			const rceptNo = String(r.rcept_no ?? '').trim();
			const reportNm = String(r.report_nm ?? '').trim();
			if (!rceptNo || seen.has(rceptNo) || REGULAR.some((n) => reportNm.includes(n))) continue;
			seen.add(rceptNo);
			result.push({
				rceptNo,
				reportNm,
				rceptDate: fmtDate(String(r.rcept_dt ?? '')),
				filer: String(r.flr_nm ?? '').trim(),
				url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`
			});
		}
		result.sort((a, b) => b.rceptDate.localeCompare(a.rceptDate) || b.rceptNo.localeCompare(a.rceptNo));
		cache.set(code, result); // 전 이력 — slice 캡 없음(레일/우측패널 완결성). 폭주는 PriceChart 가시범위 skip 이 담당.
		return result;
	} catch {
		cache.set(code, []);
		return [];
	}
}
