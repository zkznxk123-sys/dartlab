// 비정기(수시)공시 — dart/allFilings/recent.parquet (HF, 전 이력 통합 1파일) 을 stock_code
// 필터로 단건 읽기. 일자 date-scan(휴일 404 콘솔오염) 폐기 — 통합파일은 stock_code 정렬이라
// filter pushdown 이 회사 row-group 만 읽음. content_raw 없음(빌드시 메타만). per-code 캐시.
// 통합파일 생성: .github/scripts/sync/buildAllFilingsRecent.py (정기보고서는 이미 제외됨).
// 타입 정본 = contracts (NonRegularFiling 승격 완료 — 중복 정의 금지).
import type { MarketFiling, NonRegularFiling } from '@dartlab/ui-contracts';
import type { DataCore } from '../../../data/fetch/request';

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

export async function loadCompanyNonRegularFilings(core: DataCore, stockCode: string): Promise<NonRegularFiling[]> {
	const code = stockCode.trim();
	if (!/^\d{6}$/.test(code)) return [];
	try {
		const rows = await core.requestParquetRows<RecentRow>({
			origin: 'hfRange',
			path: 'dart/allFilings/recent.parquet',
			columns: COLS,
			filter: { stock_code: { $in: [code] } },
			cacheKey: `allFilings.recent:one:${code}`,
			cache: { scope: 'memory', ttlMs: 10 * 60_000, maxEntries: 256 } // 신선도 — 짧은 TTL, 자체 Map 폐기
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
		return result; // 전 이력 — slice 캡 없음(레일/우측패널 완결성). 캐시/dedup 은 코어.
	} catch {
		return [];
	}
}

// 워치 신선도 — 여러 종목을 한 read 로 ($in:[codes]). 단일판과 동일 HF 파일·정규화, code→목록 그룹핑.
// 공개/로컬 공통배선(둘 다 이 함수 호출 → 백엔드 0). 캐시·dedup 은 fetch 코어(data/fetch) 담당 —
// 신선도 데이터라 짧은 TTL(10분). 자체 batchCache Map 폐기(데이터 워크벤치 SSOT 이관 P1).
export async function loadRecentFilingsForCodes(
	core: DataCore,
	codes: string[]
): Promise<Record<string, NonRegularFiling[]>> {
	const valid = [...new Set(codes.map((c) => String(c).trim()).filter((c) => /^\d{6}$/.test(c)))];
	if (!valid.length) return {};
	try {
		const rows = await core.requestParquetRows<RecentRow>({
			origin: 'hfRange',
			path: 'dart/allFilings/recent.parquet',
			columns: COLS,
			filter: { stock_code: { $in: valid } },
			cacheKey: `allFilings.recent:${valid.slice().sort().join(',')}`,
			cache: { scope: 'memory', ttlMs: 10 * 60_000, maxEntries: 32 }
		});
		const wanted = new Set(valid);
		const out: Record<string, NonRegularFiling[]> = {};
		const seen = new Set<string>(); // code:rceptNo 중복 제거
		for (const r of rows) {
			const code = String(r.stock_code ?? '').trim();
			if (!wanted.has(code)) continue;
			const rceptNo = String(r.rcept_no ?? '').trim();
			const reportNm = String(r.report_nm ?? '').trim();
			const dk = code + ':' + rceptNo;
			if (!rceptNo || seen.has(dk) || REGULAR.some((n) => reportNm.includes(n))) continue;
			seen.add(dk);
			(out[code] ??= []).push({
				rceptNo,
				reportNm,
				rceptDate: fmtDate(String(r.rcept_dt ?? '')),
				filer: String(r.flr_nm ?? '').trim(),
				url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`
			});
		}
		for (const arr of Object.values(out)) arr.sort((a, b) => b.rceptDate.localeCompare(a.rceptDate) || b.rceptNo.localeCompare(a.rceptNo));
		return out;
	} catch {
		return {};
	}
}

// 시장 공시 피드(좌측 터미널) — 전상장사 최근 3개월 수시공시 시간순. 우측 단일기업 경로(stock_code
// 필터 row-group)와 *경로 분리*: 이건 전체시장이라 필터가 없고, 전용 bake 파일(market_recent.parquet,
// rcept_dt 내림차순·~656KB)을 통파일 1 GET 으로 읽는다(govRecent 동형). recent.parquet 은 stock_code
// 정렬이라 날짜순을 못 뽑으므로 재사용 금지. category 는 UI 가 report_nm 으로 분류(여기선 원본만).
const FEED_COLS = ['stock_code', 'corp_name', 'rcept_dt', 'report_nm', 'rcept_no', 'flr_nm'];
interface FeedRow extends RecentRow {
	corp_name?: unknown;
}

export async function loadMarketFeed(core: DataCore): Promise<MarketFiling[]> {
	try {
		const rows = await core.requestParquetWholeFile<FeedRow>({
			origin: 'hf',
			path: 'dart/allFilings/market_recent.parquet',
			columns: FEED_COLS,
			cacheKey: 'allFilings.marketFeed',
			cache: { scope: 'memory', ttlMs: 10 * 60_000, maxEntries: 2 } // 일일 cron 갱신 — 신선도 우선 10분 TTL(worker 엣지 600s 와 일치)
		});
		if (!rows) return [];
		const seen = new Set<string>();
		const result: MarketFiling[] = [];
		for (const r of rows) {
			const rceptNo = String(r.rcept_no ?? '').trim();
			const stockCode = String(r.stock_code ?? '').trim();
			const reportNm = String(r.report_nm ?? '').trim();
			// bake 가 정기보고서·dedup 을 이미 했으나 belt-and-suspenders
			if (!rceptNo || !stockCode || seen.has(rceptNo) || REGULAR.some((n) => reportNm.includes(n))) continue;
			seen.add(rceptNo);
			result.push({
				rceptNo,
				rceptDate: fmtDate(String(r.rcept_dt ?? '')),
				stockCode,
				corpName: String(r.corp_name ?? '').trim(),
				reportNm,
				filer: String(r.flr_nm ?? '').trim(),
				url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`
			});
		}
		return result; // 파일이 이미 rcept_dt 내림차순(bake) — 재정렬 불필요. 캐시·dedup 은 코어/위.
	} catch {
		return [];
	}
}
