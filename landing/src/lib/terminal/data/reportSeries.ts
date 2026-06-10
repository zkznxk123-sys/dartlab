// 정기보고서 시계열 — dart/scan/report/{employee,investedCompany,dividend,treasuryStock}.parquet 을
// hyparquet 직독 (stockCode 정렬 + 컬럼 projection + row-group pruning, 4파일 병렬).
// DuckDB-WASM 경유 금지 — 단일 워커 직렬 큐에 묶여 첫 표시가 수십 초로 밀린다(실측 40s → 수 초).
// 버틀러식 인력·생산성 / 주주환원 / 타법인출자 패널의 데이터층. 수치는 콤마 문자열('-'=결측).
// 실측 구조: employee 는 fo_bbm='성별합계' 행이 성별 합계+급여 보유, treasuryStock 은 acqs_mth1='총계' 행이 총계.
import { browser } from '$app/environment';
import { readParquetRows } from '$lib/data/hfRange';

export type Num = number | null;

export interface WorkforceYear {
	year: string;
	total: Num;
	male: Num;
	female: Num;
	regular: Num;
	contract: Num;
	avgSalary: Num; // 원/인 (급여총액/총원)
	totalSalary: Num; // 원
	tenure: Num; // 평균 근속연수
}
export interface InvestmentRow {
	name: string;
	purpose: string;
	stakePct: Num;
	bookValue: Num; // 원
	acquiredAmt: Num; // 원 (최초취득)
	targetNet: Num; // 피출자사 당기순이익 (원)
}
export interface InvestmentsView {
	year: string;
	rows: InvestmentRow[]; // 장부가액 top 12
	moreCount: number;
	moreBook: number; // top 밖 장부가액 합 (원)
}
export interface ShareholderReturnYear {
	year: string;
	dps: Num; // 주당 현금배당금 (원, 보통주)
	totalDividend: Num; // 원 (백만원 → 환산)
	payoutPct: Num; // (연결)현금배당성향
	yieldPct: Num; // 현금배당수익률
	buybackQty: Num; // 자사주 취득 (주, 보통주 총계)
	disposalQty: Num;
	treasuryEnd: Num; // 기말 보유 (주)
}
// 패널 3종은 독립 로더 — Promise.all 로 묶으면 가장 무거운 investedCompany(16MB)가
// 가벼운 인력·배당 패널까지 지연시킨다. 각자 캐시·각자 스트림-인.

const num = (v: unknown): Num => {
	if (typeof v === 'number') return Number.isFinite(v) ? v : null;
	if (typeof v === 'bigint') return Number(v);
	if (typeof v === 'string' && v.trim() && v !== '-') {
		const n = Number(v.replace(/,/g, ''));
		return Number.isFinite(n) ? n : null;
	}
	return null;
};
const str = (v: unknown): string => (v == null ? '' : String(v));
// 같은 연도에 4분기(사업보고서) 우선, 없으면 반기·분기 — 연도축 1행 확정용.
const qRank = (q: unknown): number => (str(q) === '4분기' ? 4 : str(q) === '3분기' ? 3 : str(q) === '2분기' ? 2 : 1);

type Row = Record<string, unknown>;
function read(path: string, code: string, columns: string[]): Promise<Row[]> {
	return readParquetRows<Row>(`dart/scan/report/${path}.parquet`, {
		columns: ['stockCode', 'year', 'quarter', ...columns],
		filter: { stockCode: { $eq: code } }
	}).then((r) => r.rows);
}

// 연도별 최우선 분기만 남긴다 (사업보고서 > 반기 > 분기). bestQ 도 함께 반환 — 급여처럼
// 연간 누적값은 사업보고서(4분기)에서만 유효한 필드의 게이트로 쓴다.
function bestQuarterRows(rows: Row[]): Map<string, { q: number; rows: Row[] }> {
	const bestQ = new Map<string, number>();
	for (const r of rows) {
		const y = str(r.year);
		const q = qRank(r.quarter);
		if (q > (bestQ.get(y) ?? 0)) bestQ.set(y, q);
	}
	const out = new Map<string, { q: number; rows: Row[] }>();
	for (const r of rows) {
		const y = str(r.year);
		const q = bestQ.get(y) ?? 0;
		if (qRank(r.quarter) !== q) continue;
		let e = out.get(y);
		if (!e) out.set(y, (e = { q, rows: [] }));
		e.rows.push(r);
	}
	return out;
}

function cached<T>(store: Map<string, Promise<T | null>>, code: string, fn: (c: string) => Promise<T | null>): Promise<T | null> {
	if (!browser) return Promise.resolve(null);
	const c = code.trim();
	const hit = store.get(c);
	if (hit) return hit;
	const p = fn(c).catch((err) => {
		console.warn('[terminal] report series fallback:', c, err);
		return null;
	});
	store.set(c, p);
	return p;
}

const wfCache = new Map<string, Promise<WorkforceYear[] | null>>();
const invCache = new Map<string, Promise<InvestmentsView | null>>();
const srCache = new Map<string, Promise<ShareholderReturnYear[] | null>>();

/** 인력·생산성 연도 시계열 (employee.parquet 단독 — 가볍고 먼저 도착). */
export function loadWorkforce(stockCode: string): Promise<WorkforceYear[] | null> {
	return cached(wfCache, stockCode, buildWorkforce);
}
/** 타법인출자 최신 연도 top 12 (investedCompany.parquet — 가장 무거움). */
export function loadInvestments(stockCode: string): Promise<InvestmentsView | null> {
	return cached(invCache, stockCode, buildInvestments);
}
/** 주주환원 연도 시계열 (dividend + treasuryStock). */
export function loadShareholderReturn(stockCode: string): Promise<ShareholderReturnYear[] | null> {
	return cached(srCache, stockCode, buildShareholderReturn);
}

async function buildWorkforce(code: string): Promise<WorkforceYear[] | null> {
	const emp = await read('employee', code, ['fo_bbm', 'sexdstn', 'rgllbr_co', 'cnttk_co', 'sm', 'avrg_cnwk_sdytrn', 'fyer_salary_totamt']);
	// ── workforce: 성별합계 행 우선, 없으면(기아 등 단일부문 공시) 부문×성별 행 합산 → 연도 1행 ──
	const workforce: WorkforceYear[] = [];
	const sexTotals = emp.filter((r) => str(r.fo_bbm).includes('성별합계') && str(r.sexdstn));
	const empByYear = bestQuarterRows(sexTotals.length ? sexTotals : emp.filter((r) => str(r.sexdstn)));
	for (const [year, { q, rows }] of empByYear) {
		const w: WorkforceYear = { year, total: null, male: null, female: null, regular: null, contract: null, avgSalary: null, totalSalary: null, tenure: null };
		let tenureSum = 0;
		let tenureN = 0;
		for (const r of rows) {
			const sm = num(r.sm);
			if (sm != null && str(r.sexdstn) === '남') w.male = (w.male ?? 0) + sm;
			else if (sm != null && str(r.sexdstn) === '여') w.female = (w.female ?? 0) + sm;
			const reg = num(r.rgllbr_co);
			if (reg != null) w.regular = (w.regular ?? 0) + reg;
			const con = num(r.cnttk_co);
			if (con != null) w.contract = (w.contract ?? 0) + con;
			const sal = num(r.fyer_salary_totamt);
			if (sal != null) w.totalSalary = (w.totalSalary ?? 0) + sal;
			const t = num(r.avrg_cnwk_sdytrn);
			if (t != null) { tenureSum += t; tenureN++; }
		}
		w.total = (w.male ?? 0) + (w.female ?? 0) || null;
		w.tenure = tenureN ? +(tenureSum / tenureN).toFixed(1) : null;
		// 급여총액은 연간 누적 — 사업보고서(4분기) 아닌 해는 부분연도라 표시하면 왜곡 → null
		if (q !== 4) w.totalSalary = null;
		w.avgSalary = w.total && w.totalSalary ? w.totalSalary / w.total : null;
		if (w.total != null) workforce.push(w);
	}
	workforce.sort((a, b) => a.year.localeCompare(b.year));
	return workforce.length ? workforce : null;
}

async function buildInvestments(code: string): Promise<InvestmentsView | null> {
	const inv = await read('investedCompany', code, ['inv_prm', 'invstmnt_purps', 'frst_acqs_amount', 'trmend_blce_qota_rt', 'trmend_blce_acntbk_amount', 'recent_bsns_year_fnnr_sttus_thstrm_ntpf']);
	// ── investments: 최신 유효 (year, quarter) 의 장부가액 top 12 ──
	let investments: InvestmentsView | null = null;
	const invValid = inv.filter((r) => {
		const nm = str(r.inv_prm);
		return nm && nm !== '-' && !nm.replace(/\s/g, '').includes('합계') && num(r.trmend_blce_acntbk_amount) != null;
	});
	if (invValid.length) {
		let bestYear = '';
		let bestQ = 0;
		for (const r of invValid) {
			const y = str(r.year);
			const q = qRank(r.quarter);
			if (y > bestYear || (y === bestYear && q > bestQ)) { bestYear = y; bestQ = q; }
		}
		const rows = invValid
			.filter((r) => str(r.year) === bestYear && qRank(r.quarter) === bestQ)
			.map((r) => ({
				name: str(r.inv_prm),
				purpose: str(r.invstmnt_purps) === '-' ? '' : str(r.invstmnt_purps),
				stakePct: num(r.trmend_blce_qota_rt),
				bookValue: num(r.trmend_blce_acntbk_amount),
				acquiredAmt: num(r.frst_acqs_amount),
				targetNet: num(r.recent_bsns_year_fnnr_sttus_thstrm_ntpf)
			}))
			.sort((a, b) => (b.bookValue ?? 0) - (a.bookValue ?? 0));
		const top = rows.slice(0, 12);
		const rest = rows.slice(12);
		investments = { year: bestYear, rows: top, moreCount: rest.length, moreBook: rest.reduce((a, r) => a + (r.bookValue ?? 0), 0) };
	}
	return investments;
}

async function buildShareholderReturn(code: string): Promise<ShareholderReturnYear[] | null> {
	const [div, tre] = await Promise.all([
		read('dividend', code, ['se', 'stock_knd', 'thstrm']),
		read('treasuryStock', code, ['acqs_mth1', 'stock_knd', 'change_qy_acqs', 'change_qy_dsps', 'trmend_qy'])
	]);
	// ── shareholderReturn: dividend 피벗(사업보고서) + treasury(보통주 총계) 연도 join ──
	const srByYear = new Map<string, ShareholderReturnYear>();
	const sr = (year: string): ShareholderReturnYear => {
		let s = srByYear.get(year);
		if (!s) { s = { year, dps: null, totalDividend: null, payoutPct: null, yieldPct: null, buybackQty: null, disposalQty: null, treasuryEnd: null }; srByYear.set(year, s); }
		return s;
	};
	for (const r of div) {
		if (str(r.quarter) !== '4분기' || str(r.stock_knd).includes('우선')) continue;
		const v = num(r.thstrm);
		if (v == null) continue;
		const se = str(r.se);
		const s = sr(str(r.year));
		if (se.includes('주당 현금배당금')) s.dps = Math.max(s.dps ?? 0, v);
		else if (se.includes('현금배당금총액')) s.totalDividend = v * 1e6; // 백만원 → 원
		else if (se.includes('현금배당성향')) s.payoutPct = v;
		else if (se.includes('현금배당수익률')) s.yieldPct = Math.max(s.yieldPct ?? 0, v);
	}
	const treByYear = bestQuarterRows(tre.filter((r) => str(r.acqs_mth1).includes('총계') && str(r.stock_knd).includes('보통')));
	for (const [year, { rows }] of treByYear) {
		const s = sr(year);
		for (const r of rows) {
			const buy = num(r.change_qy_acqs);
			if (buy != null) s.buybackQty = (s.buybackQty ?? 0) + buy;
			const sell = num(r.change_qy_dsps);
			if (sell != null) s.disposalQty = (s.disposalQty ?? 0) + sell;
			const end = num(r.trmend_qy);
			if (end != null) s.treasuryEnd = (s.treasuryEnd ?? 0) + end;
		}
	}
	const shareholderReturn = [...srByYear.values()]
		.filter((s) => s.dps != null || s.totalDividend != null || s.treasuryEnd != null)
		.sort((a, b) => a.year.localeCompare(b.year));
	return shareholderReturn.length ? shareholderReturn : null;
}
