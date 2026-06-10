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
export interface InvestmentTrendYear {
	year: string;
	bookTotal: Num; // 합계행 장부가 (원) — 부재 연도만 개별행 합산 fallback
	count: number; // 유효 개별 출자사 수
}
export interface InvestmentsBundle {
	latest: InvestmentsView;
	trend: InvestmentTrendYear[]; // 연도 오름차순
}
export interface OwnershipYear {
	year: string;
	majorPct: Num; // 최대주주측 합산 지분율 % (계행·보통주 우선)
	minorPct: Num; // 소액주주 지분율 %
	minorCount: Num; // 소액주주 수 (명)
}
export interface ExecBoardYear {
	year: string;
	execAvgPay: Num; // 이사·감사 1인평균 보수 (원) — 공시값 우선
	execTotalPay: Num; // 보수총액 (원)
	execCount: Num; // 인원
	directors: Num; // 이사 수
	outsideDirectors: Num; // 사외이사 수
}
export interface DebtProfileYear {
	year: string;
	bond1y: Num; // 사채 잔존만기 1년이하 (원)
	bond1to5: Num;
	bond5to10: Num;
	bond10plus: Num;
	bondTotal: Num; // 사채 미상환 합계 (원)
	stb: Num; // 단기사채 미상환 (원)
	cp: Num; // CP 미상환 (원)
}
export interface ShareholderReturnYear {
	year: string;
	dps: Num; // 주당 현금배당금 (원, 보통주)
	totalDividend: Num; // 원 (백만원 → 환산)
	payoutPct: Num; // (연결)현금배당성향
	yieldPct: Num; // 현금배당수익률
	buybackQty: Num; // 자사주 취득 (주, 보통주 총계)
	disposalQty: Num;
	buybackCancel: Num; // 소각 (주)
	treasuryEnd: Num; // 기말 보유 (주)
}
// 패널 3종은 독립 로더 — Promise.all 로 묶으면 가장 무거운 investedCompany(16MB)가
// 가벼운 인력·배당 패널까지 지연시킨다. 각자 캐시·각자 스트림-인.

const num = (v: unknown): Num => {
	if (typeof v === 'number') return Number.isFinite(v) ? v : null;
	if (typeof v === 'bigint') return Number(v);
	if (typeof v === 'string' && v.trim() && v !== '-') {
		// '%' suffix — minorityHolder.hold_stock_rate ('68.23%') 류. 콤마와 함께 제거.
		const n = Number(v.replace(/[,%]/g, ''));
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
const invCache = new Map<string, Promise<InvestmentsBundle | null>>();
const srCache = new Map<string, Promise<ShareholderReturnYear[] | null>>();
const ownCache = new Map<string, Promise<OwnershipYear[] | null>>();
const ebCache = new Map<string, Promise<ExecBoardYear[] | null>>();
const dpCache = new Map<string, Promise<DebtProfileYear[] | null>>();

/** 인력·생산성 연도 시계열 (employee.parquet 단독 — 가볍고 먼저 도착). */
export function loadWorkforce(stockCode: string): Promise<WorkforceYear[] | null> {
	return cached(wfCache, stockCode, buildWorkforce);
}
/** 타법인출자 — 최신 연도 top 12 + 연도별 장부가 합계 추이 (investedCompany.parquet — 가장 무거움, 단일 패스). */
export function loadInvestments(stockCode: string): Promise<InvestmentsBundle | null> {
	return cached(invCache, stockCode, buildInvestments);
}
/** 주주환원 연도 시계열 (dividend + treasuryStock). */
export function loadShareholderReturn(stockCode: string): Promise<ShareholderReturnYear[] | null> {
	return cached(srCache, stockCode, buildShareholderReturn);
}
/** 소유구조 연도 시계열 (majorHolder 계행 + minorityHolder). */
export function loadOwnership(stockCode: string): Promise<OwnershipYear[] | null> {
	return cached(ownCache, stockCode, buildOwnership);
}
/** 이사·감사 보수 + 이사회 구성 연도 시계열 (executivePayAllTotal + outsideDirector). */
export function loadExecBoard(stockCode: string): Promise<ExecBoardYear[] | null> {
	return cached(ebCache, stockCode, buildExecBoard);
}
/** 사채 만기 사다리 + 초단기물 (corporateBond + shortTermBond + commercialPaper). */
export function loadDebtProfile(stockCode: string): Promise<DebtProfileYear[] | null> {
	return cached(dpCache, stockCode, buildDebtProfile);
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

async function buildInvestments(code: string): Promise<InvestmentsBundle | null> {
	const inv = await read('investedCompany', code, ['inv_prm', 'invstmnt_purps', 'frst_acqs_amount', 'trmend_blce_qota_rt', 'trmend_blce_acntbk_amount', 'recent_bsns_year_fnnr_sttus_thstrm_ntpf']);
	// ── latest: 최신 유효 (year, quarter) 의 장부가액 top 12 ──
	let latest: InvestmentsView | null = null;
	const isSumRow = (r: Row) => str(r.inv_prm).replace(/\s/g, '').includes('합계');
	const invValid = inv.filter((r) => {
		const nm = str(r.inv_prm);
		return nm && nm !== '-' && !isSumRow(r) && num(r.trmend_blce_acntbk_amount) != null;
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
		latest = { year: bestYear, rows: top, moreCount: rest.length, moreBook: rest.reduce((a, r) => a + (r.bookValue ?? 0), 0) };
	}
	if (!latest) return null;
	// ── trend: 연도별 장부가 합계 — 합계행 직접 채택(개별행 '-' 결측에 강건), 부재 연도만 개별 합산 ──
	const trend: InvestmentTrendYear[] = [];
	for (const [year, { rows }] of bestQuarterRows(inv)) {
		const sumRow = rows.find((r) => isSumRow(r) && num(r.trmend_blce_acntbk_amount) != null);
		const valid = rows.filter((r) => {
			const nm = str(r.inv_prm);
			return nm && nm !== '-' && !isSumRow(r) && num(r.trmend_blce_acntbk_amount) != null;
		});
		const bookTotal = sumRow
			? num(sumRow.trmend_blce_acntbk_amount)
			: valid.length
				? valid.reduce((a, r) => a + (num(r.trmend_blce_acntbk_amount) ?? 0), 0)
				: null;
		if (bookTotal != null) trend.push({ year, bookTotal, count: valid.length });
	}
	trend.sort((a, b) => a.year.localeCompare(b.year));
	return { latest, trend };
}

async function buildShareholderReturn(code: string): Promise<ShareholderReturnYear[] | null> {
	const [div, tre] = await Promise.all([
		read('dividend', code, ['se', 'stock_knd', 'thstrm']),
		read('treasuryStock', code, ['acqs_mth1', 'stock_knd', 'change_qy_acqs', 'change_qy_dsps', 'change_qy_incnr', 'trmend_qy'])
	]);
	// ── shareholderReturn: dividend 피벗(사업보고서) + treasury(보통주 총계) 연도 join ──
	const srByYear = new Map<string, ShareholderReturnYear>();
	const sr = (year: string): ShareholderReturnYear => {
		let s = srByYear.get(year);
		if (!s) { s = { year, dps: null, totalDividend: null, payoutPct: null, yieldPct: null, buybackQty: null, disposalQty: null, buybackCancel: null, treasuryEnd: null }; srByYear.set(year, s); }
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
			const cancel = num(r.change_qy_incnr);
			if (cancel != null) s.buybackCancel = (s.buybackCancel ?? 0) + cancel;
			const end = num(r.trmend_qy);
			if (end != null) s.treasuryEnd = (s.treasuryEnd ?? 0) + end;
		}
	}
	const shareholderReturn = [...srByYear.values()]
		.filter((s) => s.dps != null || s.totalDividend != null || s.treasuryEnd != null)
		.sort((a, b) => a.year.localeCompare(b.year));
	return shareholderReturn.length ? shareholderReturn : null;
}

// 연도 그룹에서 rcept_no 최대(=최신 정정공시) 행들만 남긴다.
const latestRcept = (rows: Row[]): Row[] => {
	let best = '';
	for (const r of rows) { const rc = str(r.rcept_no); if (rc > best) best = rc; }
	return best ? rows.filter((r) => str(r.rcept_no) === best) : rows;
};

async function buildOwnership(code: string): Promise<OwnershipYear[] | null> {
	const [maj, min] = await Promise.all([
		read('majorHolder', code, ['nm', 'stock_knd', 'trmend_posesn_stock_qota_rt', 'rcept_no']),
		read('minorityHolder', code, ['se', 'shrholdr_co', 'hold_stock_rate', 'rcept_no'])
	]);
	const byYear = new Map<string, OwnershipYear>();
	const own = (year: string): OwnershipYear => {
		let o = byYear.get(year);
		if (!o) { o = { year, majorPct: null, minorPct: null, minorCount: null }; byYear.set(year, o); }
		return o;
	};
	// majorHolder: 계행(최대주주측 합산)만 — 개별행 합산은 이중계상 위험으로 기각(계행 부재 연도 null 정직 표시).
	// 보통주 우선, 없으면 의결권 있는 주식 ('의결권 없는' 변형 배제). 기초(bsis_*) 금지 — 기말만.
	for (const [year, { rows }] of bestQuarterRows(maj)) {
		const sums = rows.filter((r) => str(r.nm).trim() === '계' && num(r.trmend_posesn_stock_qota_rt) != null);
		const common = sums.filter((r) => str(r.stock_knd).includes('보통'));
		const voting = sums.filter((r) => { const k = str(r.stock_knd); return k.includes('의결권') && !k.includes('없'); });
		const pool = common.length ? common : voting.length ? voting : [];
		if (pool.length) own(year).majorPct = num(latestRcept(pool)[0].trmend_posesn_stock_qota_rt);
	}
	// minorityHolder: se='소액주주' 행만 (se=null 깡통행 제외). hold_stock_rate 가 진짜 지분율 (shrholdr_rate 는 주주수 비율 — 사용 금지).
	for (const [year, { rows }] of bestQuarterRows(min)) {
		const valid = rows.filter((r) => str(r.se).trim() === '소액주주');
		if (!valid.length) continue;
		const r = latestRcept(valid)[0];
		const o = own(year);
		o.minorPct = num(r.hold_stock_rate);
		o.minorCount = num(r.shrholdr_co);
	}
	const out = [...byYear.values()]
		.filter((o) => o.majorPct != null || o.minorPct != null)
		.sort((a, b) => a.year.localeCompare(b.year));
	return out.length ? out : null;
}

async function buildExecBoard(code: string): Promise<ExecBoardYear[] | null> {
	const [pay, od] = await Promise.all([
		read('executivePayAllTotal', code, ['nmpr', 'jan_avrg_mendng_am', 'mendng_totamt', 'rcept_no']),
		read('outsideDirector', code, ['drctr_co', 'otcmp_drctr_co', 'rcept_no'])
	]);
	const byYear = new Map<string, ExecBoardYear>();
	const eb = (year: string): ExecBoardYear => {
		let e = byYear.get(year);
		if (!e) { e = { year, execAvgPay: null, execTotalPay: null, execCount: null, directors: null, outsideDirectors: null }; byYear.set(year, e); }
		return e;
	};
	// 보수는 연중 누적(기아 Q1 604M→Q4 3,335M 실측) — 사업보고서(4분기) 행만. bestQuarterRows 금지.
	const payByYear = new Map<string, Row[]>();
	for (const r of pay) {
		if (str(r.quarter) !== '4분기') continue;
		const y = str(r.year);
		let arr = payByYear.get(y);
		if (!arr) payByYear.set(y, (arr = []));
		arr.push(r);
	}
	for (const [year, rows] of payByYear) {
		const grp = latestRcept(rows);
		const e = eb(year);
		if (grp.length === 1) {
			// 단일행 = 공시값 그대로 — jan_avrg_mendng_am 은 연환산 평균인원 기준이라 totamt/nmpr 재계산 금지
			e.execAvgPay = num(grp[0].jan_avrg_mendng_am);
			e.execTotalPay = num(grp[0].mendng_totamt);
			e.execCount = num(grp[0].nmpr);
		} else {
			// 다행(동일 rcept_no 유형분리, 카테고리 라벨 부재) = 합산만 가능
			let tot = 0, cnt = 0, anyTot = false;
			for (const r of grp) {
				const t = num(r.mendng_totamt);
				if (t != null) { tot += t; anyTot = true; }
				const c = num(r.nmpr);
				if (c != null) cnt += c;
			}
			e.execTotalPay = anyTot ? tot : null;
			e.execCount = cnt || null;
			e.execAvgPay = anyTot && cnt > 0 ? tot / cnt : null;
		}
	}
	// 이사회 구성 — 실질 2·4분기만 공시라 연 축 (bestQuarterRows 4분기 우선)
	for (const [year, { rows }] of bestQuarterRows(od)) {
		const r = latestRcept(rows)[0];
		if (!r) continue;
		const e = eb(year);
		e.directors = num(r.drctr_co);
		e.outsideDirectors = num(r.otcmp_drctr_co);
	}
	const out = [...byYear.values()]
		.filter((e) => e.execAvgPay != null || e.execTotalPay != null || e.directors != null)
		.sort((a, b) => a.year.localeCompare(b.year));
	return out.length ? out : null;
}

async function buildDebtProfile(code: string): Promise<DebtProfileYear[] | null> {
	const [cb, stb, cp] = await Promise.all([
		read('corporateBond', code, ['remndr_exprtn2', 'sm', 'yy1_below', 'yy1_excess_yy2_below', 'yy2_excess_yy3_below', 'yy3_excess_yy4_below', 'yy4_excess_yy5_below', 'yy5_excess_yy10_below', 'yy10_excess']),
		read('shortTermBond', code, ['remndr_exprtn2', 'sm']),
		read('commercialPaper', code, ['remndr_exprtn2', 'sm'])
	]);
	const byYear = new Map<string, DebtProfileYear>();
	const dp = (year: string): DebtProfileYear => {
		let d = byYear.get(year);
		if (!d) { d = { year, bond1y: null, bond1to5: null, bond5to10: null, bond10plus: null, bondTotal: null, stb: null, cp: null }; byYear.set(year, d); }
		return d;
	};
	const isTotal = (r: Row) => str(r.remndr_exprtn2).trim() === '합계';
	// corporateBond: 합계행 우선(공모+사모 공시 오류 36건 자동 방어). 단위 = 원 실측 확정(기아 2.82조 BS 대조).
	for (const [year, { rows }] of bestQuarterRows(cb)) {
		const sumRow = rows.find((r) => isTotal(r) && num(r.sm) != null);
		const d = dp(year);
		if (sumRow) {
			d.bondTotal = num(sumRow.sm);
			const b1 = num(sumRow.yy1_below);
			const mids = [num(sumRow.yy1_excess_yy2_below), num(sumRow.yy2_excess_yy3_below), num(sumRow.yy3_excess_yy4_below), num(sumRow.yy4_excess_yy5_below)];
			const b15 = mids.some((v) => v != null) ? mids.reduce<number>((a, v) => a + (v ?? 0), 0) : null;
			const b510 = num(sumRow.yy5_excess_yy10_below);
			const b10p = num(sumRow.yy10_excess);
			// 검산: 버킷합 vs sm 잔차 >2% → 버킷 전부 null (공시 오류 tail 방어, sm 만 신뢰)
			const bucketSum = (b1 ?? 0) + (b15 ?? 0) + (b510 ?? 0) + (b10p ?? 0);
			if (d.bondTotal != null && d.bondTotal > 0 && Math.abs(bucketSum - d.bondTotal) / d.bondTotal <= 0.02) {
				d.bond1y = b1;
				d.bond1to5 = b15;
				d.bond5to10 = b510;
				d.bond10plus = b10p;
			}
		} else {
			// 합계행 sm 결측 — 공모+사모 행 sm 합산 fallback (버킷 null)
			const parts = rows.filter((r) => !isTotal(r) && num(r.sm) != null);
			if (parts.length) d.bondTotal = parts.reduce((a, r) => a + (num(r.sm) ?? 0), 0);
		}
	}
	for (const [year, { rows }] of bestQuarterRows(stb)) {
		const r = rows.find((x) => isTotal(x) && num(x.sm) != null);
		if (r) dp(year).stb = num(r.sm);
	}
	for (const [year, { rows }] of bestQuarterRows(cp)) {
		const r = rows.find((x) => isTotal(x) && num(x.sm) != null);
		if (r) dp(year).cp = num(r.sm);
	}
	const out = [...byYear.values()]
		.filter((d) => d.bondTotal != null || d.stb != null || d.cp != null)
		.sort((a, b) => a.year.localeCompare(b.year));
	return out.length ? out : null;
}
