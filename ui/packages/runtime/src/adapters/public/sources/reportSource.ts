// 정기보고서 시계열 — dart/scan/report/{employee,investedCompany,dividend,treasuryStock}.parquet 을
// hyparquet 직독 (stockCode 정렬 + 컬럼 projection + row-group pruning, 4파일 병렬).
// DuckDB-WASM 경유 금지 — 단일 워커 직렬 큐에 묶여 첫 표시가 수십 초로 밀린다(실측 40s → 수 초).
// 버틀러식 인력·생산성 / 주주환원 / 타법인출자 패널의 데이터층. 수치는 콤마 문자열('-'=결측).
// 실측 구조: employee 는 fo_bbm='성별합계' 행이 성별 합계+급여 보유, treasuryStock 은 acqs_mth1='총계' 행이 총계.
// 타입 정본 = contracts (옛 로컬 재정의는 contracts 로 승격 완료 — 중복 정의 금지).
import type {
	AuditFeeYear,
	AuditYear,
	CapitalChangeEvent,
	CapitalChangesBundle,
	DebtLadder,
	DebtProfileBundle,
	DebtProfileYear,
	DilutionYear,
	ExecBoardYear,
	InvestmentsBundle,
	InvestmentsView,
	InvestmentTrendYear,
	Num,
	OwnershipYear,
	ShareholderReturnYear,
	TopExecPay,
	WorkforceYear
} from '@dartlab/ui-contracts';
import { readParquetRows } from '../../../data/hfRange';

const browser = typeof window !== 'undefined';

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
const dpCache = new Map<string, Promise<DebtProfileBundle | null>>();
const ccCache = new Map<string, Promise<CapitalChangesBundle | null>>();
const atCache = new Map<string, Promise<AuditYear[] | null>>();
const tpCache = new Map<string, Promise<TopExecPay | null>>();
const afCache = new Map<string, Promise<AuditFeeYear[] | null>>();

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
/** 사채 잔액 추이 + 전방 만기 사다리 + 초단기물 (corporateBond + shortTermBond + commercialPaper). */
export function loadDebtProfile(stockCode: string): Promise<DebtProfileBundle | null> {
	return cached(dpCache, stockCode, buildDebtProfile);
}
/** 자본금 변동 이벤트 + 연도 합산 (capitalChange) — 희석 이력 카드 · 주가차트 마커 공용. */
export function loadCapitalChanges(stockCode: string): Promise<CapitalChangesBundle | null> {
	return cached(ccCache, stockCode, buildCapitalChanges);
}
/** 감사 이력 연도 시계열 (auditOpinion) — 감사인·의견·특기사항. */
export function loadAuditTrail(stockCode: string): Promise<AuditYear[] | null> {
	return cached(atCache, stockCode, buildAuditTrail);
}
/** 개별 임원 보수 top 8 (executivePayIndividual, 최신 사업보고서). */
export function loadTopExecPay(stockCode: string): Promise<TopExecPay | null> {
	return cached(tpCache, stockCode, buildTopExecPay);
}
/** 감사보수·독립성 연도 시계열 (auditContract + nonAuditContract). */
export function loadAuditFees(stockCode: string): Promise<AuditFeeYear[] | null> {
	return cached(afCache, stockCode, buildAuditFees);
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
		if (!s) { s = { year, dps: null, eps: null, totalDividend: null, payoutPct: null, yieldPct: null, buybackQty: null, disposalQty: null, buybackCancel: null, treasuryEnd: null }; srByYear.set(year, s); }
		return s;
	};
	for (const r of div) {
		if (str(r.quarter) !== '4분기' || str(r.stock_knd).includes('우선')) continue;
		const v = num(r.thstrm);
		if (v == null) continue;
		const se = str(r.se);
		const s = sr(str(r.year));
		if (se.includes('주당 현금배당금')) s.dps = Math.max(s.dps ?? 0, v);
		else if (se.includes('주당순이익')) { if (s.eps == null || se.includes('연결')) s.eps = v; } // (연결) 우선, 별도는 fallback
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
		read('minorityHolder', code, ['se', 'shrholdr_co', 'hold_stock_rate', 'stock_tot_co', 'rcept_no'])
	]);
	const byYear = new Map<string, OwnershipYear>();
	const own = (year: string): OwnershipYear => {
		let o = byYear.get(year);
		if (!o) { o = { year, majorPct: null, minorPct: null, minorCount: null, stockTotal: null }; byYear.set(year, o); }
		return o;
	};
	// majorHolder: 계행(최대주주측 합산)만 — 개별행 합산은 이중계상 위험으로 기각(계행 부재 연도 null 정직 표시).
	// 보통주 우선, 없으면 의결권 있는 주식 ('의결권 없는' 변형 배제). 기초(bsis_*) 금지 — 기말만.
	for (const [year, { rows }] of bestQuarterRows(maj)) {
		const sums = rows.filter((r) => str(r.nm).trim() === '계' && num(r.trmend_posesn_stock_qota_rt) != null);
		const common = sums.filter((r) => str(r.stock_knd).includes('보통'));
		const voting = sums.filter((r) => { const k = str(r.stock_knd); return k.includes('의결권') && !k.includes('없'); });
		const pool = common.length ? common : voting.length ? voting : [];
		const top = latestRcept(pool)[0];
		if (top) own(year).majorPct = num(top.trmend_posesn_stock_qota_rt);
	}
	// minorityHolder: se='소액주주' 행만 (se=null 깡통행 제외). hold_stock_rate 가 진짜 지분율 (shrholdr_rate 는 주주수 비율 — 사용 금지).
	for (const [year, { rows }] of bestQuarterRows(min)) {
		const valid = rows.filter((r) => str(r.se).trim() === '소액주주');
		if (!valid.length) continue;
		const r = latestRcept(valid)[0];
		if (!r) continue;
		const o = own(year);
		o.minorPct = num(r.hold_stock_rate);
		o.minorCount = num(r.shrholdr_co);
		o.stockTotal = num(r.stock_tot_co); // 같은 채택행만 — 분기 혼용 금지 (분할·소각 연중 변동 왜곡 방지)
	}
	const out = [...byYear.values()]
		.filter((o) => o.majorPct != null || o.minorPct != null || o.stockTotal != null)
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
		const only = grp.length === 1 ? grp[0] : undefined;
		if (only) {
			// 단일행 = 공시값 그대로 — jan_avrg_mendng_am 은 연환산 평균인원 기준이라 totamt/nmpr 재계산 금지
			e.execAvgPay = num(only.jan_avrg_mendng_am);
			e.execTotalPay = num(only.mendng_totamt);
			e.execCount = num(only.nmpr);
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

async function buildDebtProfile(code: string): Promise<DebtProfileBundle | null> {
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
	const buckets7 = new Map<string, Num[]>(); // 검산 통과 연도의 7버킷 원본 — 전방 만기 사다리용
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
				buckets7.set(year, [b1, mids[0] ?? null, mids[1] ?? null, mids[2] ?? null, mids[3] ?? null, b510, b10p]);
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
	if (!out.length) return null;
	// 전방 만기 사다리 — 2% 검산 통과한 최신 연도만 발행. 전단채·CP(만기 ≤1y)는 같은 연도 합계.
	let ladder: DebtLadder | null = null;
	const ladderYears = [...buckets7.keys()].sort();
	const latestLadderYear = ladderYears[ladderYears.length - 1];
	if (latestLadderYear) {
		const d = byYear.get(latestLadderYear);
		const shortTerm = d && (d.stb != null || d.cp != null) ? (d.stb ?? 0) + (d.cp ?? 0) : null;
		ladder = { year: latestLadderYear, buckets: buckets7.get(latestLadderYear)!, shortTerm };
	}
	return { years: out, ladder };
}

async function buildCapitalChanges(code: string): Promise<CapitalChangesBundle | null> {
	const rows = await read('capitalChange', code, ['isu_dcrs_de', 'isu_dcrs_stle', 'isu_dcrs_stock_knd', 'isu_dcrs_qy', 'rcept_no']);
	// 같은 이벤트가 여러 분기 보고서에 반복 수록 — (일자, 형태, 수량) 키 dedupe + rcept_no 최신 우선.
	const best = new Map<string, Row>();
	for (const r of rows) {
		const de = str(r.isu_dcrs_de);
		const stle = str(r.isu_dcrs_stle);
		if (!de || de === '-' || !stle || stle === '-') continue;
		const key = `${de}|${stle}|${str(r.isu_dcrs_qy)}`;
		const cur = best.get(key);
		if (!cur || str(r.rcept_no) > str(cur.rcept_no)) best.set(key, r);
	}
	// 유형 분류 — 무상증자·주식배당·주식분할(액면)은 기계적 주식수 변동이라 희석 집계 제외.
	// 상환권행사 등 분류 밖 유형도 제외 (방향 모호 — 추측 집계 금지).
	const kindOf = (stle: string): CapitalChangeEvent['kind'] | null => {
		const s = stle.replace(/\s/g, '');
		if (s.includes('무상증자') || s.includes('주식배당') || s.includes('주식분할') || s.includes('액면')) return null;
		if (s.includes('유상증자') || s.includes('출자전환') || s.includes('현물출자')) return 'paidIn';
		if (s.includes('전환권') || s.includes('신주인수권') || s.includes('주식매수선택권')) return 'conversion';
		if (s.includes('감자') || s.includes('소각')) return 'reduction';
		return null;
	};
	const events: CapitalChangeEvent[] = [];
	for (const r of best.values()) {
		const stle = str(r.isu_dcrs_stle);
		const kind = kindOf(stle);
		if (!kind) continue;
		const qy = num(r.isu_dcrs_qy);
		const ym = str(r.isu_dcrs_de).match(/^(\d{4})/);
		if (qy == null || qy <= 0 || !ym) continue;
		events.push({ date: str(r.isu_dcrs_de), year: Number(ym[1]), kind, type: stle, qty: kind === 'reduction' ? -qy : qy });
	}
	if (!events.length) return null;
	events.sort((a, b) => a.date.localeCompare(b.date));
	const dilByYear = new Map<number, DilutionYear>();
	for (const e of events) {
		let d = dilByYear.get(e.year);
		if (!d) dilByYear.set(e.year, (d = { year: e.year, paidIn: null, conversion: null, reduction: null }));
		d[e.kind] = (d[e.kind] ?? 0) + e.qty;
	}
	return { events, years: [...dilByYear.values()].sort((a, b) => a.year - b.year) };
}

async function buildAuditTrail(code: string): Promise<AuditYear[] | null> {
	const rows = await read('auditOpinion', code, ['adtor', 'adt_opinion', 'adt_reprt_spcmnt_matter', 'rcept_no']);
	// ⚠ auditOpinion 의 year 컬럼은 캘린더 연도가 아니라 공시 원문 기수 라벨('제55기(당기)' 류 — 실측).
	// 신뢰 가능한 캘린더 앵커는 rcept_no(접수일자)뿐: 사업보고서(4분기)는 익년 제출 → 사업연도 = 접수연도 − 1.
	// 한 보고서에 당기·전기·전전기 행이 같이 실리므로 당기 행만 채택 (마커 부재 옛 공시는 기수 최대 행).
	const annual = rows.filter((r) => str(r.quarter) === '4분기' && str(r.rcept_no).length >= 8);
	if (!annual.length) return null;
	const byFy = new Map<number, Row[]>();
	for (const r of annual) {
		const fy = Number(str(r.rcept_no).slice(0, 4)) - 1;
		if (!Number.isFinite(fy) || fy < 1990) continue;
		let arr = byFy.get(fy);
		if (!arr) byFy.set(fy, (arr = []));
		arr.push(r);
	}
	const gisu = (label: string): number => {
		const m = label.match(/제\s*(\d+)\s*기/);
		return m ? Number(m[1]) : -1;
	};
	const normOpinion = (v: string): string | null => {
		if (!v || v === '-') return null;
		if (v.includes('의견거절')) return '의견거절';
		if (v.includes('부적정')) return '부적정';
		if (v.includes('한정')) return '한정';
		if (v.includes('적정')) return '적정';
		return null; // '해당사항 없음' 류 (분기 검토)
	};
	const out: AuditYear[] = [];
	for (const [fy, grp0] of byFy) {
		const grp = latestRcept(grp0); // 같은 연도 정정공시 — 최신 접수만
		const tagged = grp.filter((r) => {
			const l = str(r.year);
			return l.includes('당기') && !l.includes('당분기') && !l.includes('당반기');
		});
		let pick: Row | undefined = tagged[0];
		if (!pick) {
			let bestN = -1;
			for (const r of grp) { const gn = gisu(str(r.year)); if (gn > bestN) { bestN = gn; pick = r; } }
		}
		if (!pick) pick = grp[0];
		if (!pick) continue;
		const auditor = str(pick.adtor).trim();
		if (!auditor || auditor === '-') continue;
		const spRaw = str(pick.adt_reprt_spcmnt_matter).trim();
		const special = !spRaw || spRaw === '-' || spRaw.replace(/\s/g, '').includes('해당사항없음') ? null : spRaw;
		out.push({ year: fy, auditor, opinion: normOpinion(str(pick.adt_opinion)), special });
	}
	out.sort((a, b) => a.year - b.year);
	return out.length ? out : null;
}

async function buildTopExecPay(code: string): Promise<TopExecPay | null> {
	const rows = await read('executivePayIndividual', code, ['nm', 'ofcps', 'mendng_totamt', 'rcept_no']);
	// 보수는 연간 확정값 — 사업보고서(4분기)만. 최신 연도 + 최신 접수(정정 우선) → 보수 내림차순 top 8.
	const annual = rows.filter((r) => str(r.quarter) === '4분기' && num(r.mendng_totamt) != null && str(r.nm).trim() && str(r.nm) !== '-');
	if (!annual.length) return null;
	let year = '';
	for (const r of annual) { const y = str(r.year); if (y > year) year = y; }
	const grp = latestRcept(annual.filter((r) => str(r.year) === year));
	const list = grp
		.map((r) => ({ name: str(r.nm).trim(), title: str(r.ofcps).replace(/\s+/g, ' ').trim(), pay: num(r.mendng_totamt)! }))
		.sort((a, b) => b.pay - a.pay)
		.slice(0, 8);
	if (!list.length) return null;
	const eb = await loadExecBoard(code); // 캐시 공유 — 추가 fetch 없음 (1인평균 배수 병치용)
	const avgPay = eb?.find((e) => e.year === year)?.execAvgPay ?? null;
	return { year, avgPay, rows: list };
}

// 상대 기수 라벨 → 사업연도 offset. 한 보고서에 당기·전기·전전기 3개 연도 표가 같이 실린다.
// ⚠ '전전기' 가 '전기' 를 포함하므로 검사 순서 고정. '당분기/당반기' 도 0 — 감사 계약보수는 연간
// 단일 계약값이라 분기 시점에도 동일 (하이닉스 1분기 2,975 = 4분기 확정 2,975 실측).
const relOffset = (label: string): number | null => {
	const s = label.replace(/\s/g, '');
	if (s.includes('전전기')) return 2;
	if (s.includes('전기')) return 1;
	if (s.includes('당기') || s.includes('당분기') || s.includes('당반기')) return 0;
	return null;
};
// '4,219(주1)' 류 주석 꼬리 제거 후 수치화 (감사시간·보수 필드 실측 오염 패턴)
const numClean = (v: unknown): Num => num(typeof v === 'string' ? v.replace(/\(.*?\)/g, '') : v);

async function buildAuditFees(code: string): Promise<AuditFeeYear[] | null> {
	const [ac, nac] = await Promise.all([
		read('auditContract', code, ['bsns_year', 'stlm_dt', 'mendng', 'adt_cntrct_dtls_mendng', 'rcept_no']),
		read('nonAuditContract', code, ['bsns_year', 'stlm_dt', 'servc_mendng', 'rcept_no'])
	]);
	// 사업연도 = stlm_dt(보고서 결산 기준일) 연도 − 상대기수. 상대 마커 없는 행은 버린다 —
	// 기수 숫자(제N기)는 회사·문서 간 불일치 실측(현대차 59기↔2025 vs 56기↔2023 모순)이라 신뢰 불가.
	// 부정확한 장기 시계열보다 정확한 단기가 정직.
	const fyOf = (r: Row): number | null => {
		const m = str(r.stlm_dt).match(/^(\d{4})/);
		const off = relOffset(str(r.bsns_year));
		if (!m || off == null) return null;
		const fy = Number(m[1]) - off;
		return fy >= 1990 ? fy : null;
	};
	// 감사보수 — 같은 연도가 여러 보고서에 재수록(당기→전기→전전기) → 최신 접수 우선.
	// 신필드(adt_cntrct_dtls_mendng, 2020 신외감법 양식) 우선, 구필드(mendng) 폴백. 단위 백만원 → 원.
	const acBest = new Map<number, { rc: string; fee: number }>();
	for (const r of ac) {
		const fy = fyOf(r);
		if (fy == null) continue;
		const fee = numClean(r.adt_cntrct_dtls_mendng) ?? numClean(r.mendng);
		if (fee == null || fee <= 0) continue;
		const rc = str(r.rcept_no);
		const cur = acBest.get(fy);
		if (!cur || rc > cur.rc) acBest.set(fy, { rc, fee });
	}
	if (!acBest.size) return null;
	// 비감사보수 — 같은 연도 최신 접수 공시 그룹의 용역 행 합산 (분기 반복 수록 dedup).
	// 그룹은 있는데 유효 보수 0 = 비감사용역 없음('-' 행) → 0. 그룹 자체 부재 → null (미공시 구분).
	const nacGrp = new Map<number, Row[]>();
	for (const r of nac) {
		const fy = fyOf(r);
		if (fy == null) continue;
		let arr = nacGrp.get(fy);
		if (!arr) nacGrp.set(fy, (arr = []));
		arr.push(r);
	}
	const out: AuditFeeYear[] = [];
	for (const [fy, { fee }] of acBest) {
		const grp = nacGrp.get(fy);
		let nonAudit: Num = null;
		if (grp) {
			nonAudit = 0;
			for (const r of latestRcept(grp)) {
				const v = numClean(r.servc_mendng);
				if (v != null && v > 0) nonAudit += v;
			}
		}
		out.push({ year: fy, auditFee: fee * 1e6, nonAuditFee: nonAudit != null ? nonAudit * 1e6 : null });
	}
	out.sort((a, b) => a.year - b.year);
	return out;
}
