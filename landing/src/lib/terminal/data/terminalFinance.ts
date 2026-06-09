// 터미널 재무 데이터층 — dart/finance/{code}.parquet (HF, per-company) 을 hyparquet 로 직독.
// DuckDB-WASM 불필요 (per-company 파일 작음 → 전 row 읽고 JS 정규화). 28 표준계정 매핑은
// src/dartlab/viz/display/finance/accounts.py(_STANDARDS) 포팅. 분기 누적(YTD)→TTM 환산.
// 핵심 10 카드 spec 을 클라이언트에서 계산 (ui/web viz/catalog/finance.py 의 dashboard 핵심).
import { browser } from '$app/environment';
import { readParquetRows } from '$lib/data/hfRange';

export type Num = number | null;

export interface FinSeries {
	name: string;
	data: Num[];
	color: string;
	type: 'bar' | 'line';
	axis?: 'r'; // 우측 축 (비율 등)
}
export interface FinCard {
	key: string;
	title: string;
	unit: string; // '조' | '%' | '배' | '일'
	series: FinSeries[];
	refLines?: number[];
	stacked?: boolean;
	signed?: boolean; // 0 기준선 (음수 가능)
}
export interface StmtRow {
	key: string;
	kr: string;
	en: string;
	values: Num[]; // 기간별 조 KRW (비율 표는 % · 배)
	unit?: string; // 비율 표 단위 표기 ('%' · '배'); 재무제표 본문은 생략(조)
}
export type StmtKind = 'IS' | 'BS' | 'CF';
export interface TerminalFinance {
	periods: string[]; // 표시용 압축 라벨 (예: '23Q4' · 'FY23')
	freq: 'quarter' | 'annual' | 'ttm';
	cards: FinCard[];
	revYoy: Num[]; // 매출 YoY % (분기=4분기전, 연간=전년)
	opYoy: Num[]; // 영업이익 YoY %
	cashQuality: Num[]; // 영업CF / 순이익 배수 (순이익>0 일 때만)
	statements: Record<StmtKind, StmtRow[]>; // 손익·재무상태·현금흐름 — 전 기간 계정×기간 표
	ratios: StmtRow[]; // 핵심 비율 시계열 — 동일 기간 축 (% · 배)
}

// 재무제표 표(손익/재무상태/현금흐름) 행 정의 — STD key + 표시 라벨.
const STMT_DEF: Record<StmtKind, { key: string; kr: string; en: string }[]> = {
	IS: [
		{ key: 'revenue', kr: '매출액', en: 'Revenue' },
		{ key: 'costOfSales', kr: '매출원가', en: 'COGS' },
		{ key: 'grossProfit', kr: '매출총이익', en: 'Gross profit' },
		{ key: 'sga', kr: '판매관리비', en: 'SG&A' },
		{ key: 'operatingIncome', kr: '영업이익', en: 'Operating income' },
		{ key: 'financeIncome', kr: '금융수익', en: 'Finance income' },
		{ key: 'financeCosts', kr: '금융비용', en: 'Finance costs' },
		{ key: 'incomeTax', kr: '법인세비용', en: 'Income tax' },
		{ key: 'netIncome', kr: '당기순이익', en: 'Net income' }
	],
	BS: [
		{ key: 'assets', kr: '자산총계', en: 'Assets' },
		{ key: 'currentAssets', kr: '유동자산', en: 'Current assets' },
		{ key: 'cash', kr: '현금성자산', en: 'Cash' },
		{ key: 'inventories', kr: '재고자산', en: 'Inventories' },
		{ key: 'receivables', kr: '매출채권', en: 'Receivables' },
		{ key: 'liabilities', kr: '부채총계', en: 'Liabilities' },
		{ key: 'currentLiabilities', kr: '유동부채', en: 'Current liab' },
		{ key: 'equity', kr: '자본총계', en: 'Equity' },
		{ key: 'retainedEarnings', kr: '이익잉여금', en: 'Retained earnings' }
	],
	CF: [
		{ key: 'cfOperating', kr: '영업활동현금흐름', en: 'Operating CF' },
		{ key: 'cfInvesting', kr: '투자활동현금흐름', en: 'Investing CF' },
		{ key: 'cfFinancing', kr: '재무활동현금흐름', en: 'Financing CF' },
		{ key: 'capex', kr: '설비투자(CAPEX)', en: 'CapEx' },
		{ key: 'dividendsPaid', kr: '배당금지급', en: 'Dividends paid' }
	]
};

// ── 28 표준계정 (accounts.py _STANDARDS 포팅) ──
interface StdAcct {
	key: string;
	sj: 'IS' | 'BS' | 'CF';
	ids: string[]; // account_id (IFRS) 우선
	kw: string[]; // account_nm 키워드 fallback
}
const STD: StdAcct[] = [
	// IS
	{ key: 'revenue', sj: 'IS', ids: ['ifrs-full_Revenue', 'ifrs_Revenue'], kw: ['매출액', '영업수익', '수익(매출액)'] },
	{ key: 'costOfSales', sj: 'IS', ids: ['ifrs-full_CostOfSales', 'ifrs_CostOfSales'], kw: ['매출원가'] },
	{ key: 'grossProfit', sj: 'IS', ids: [], kw: ['매출총이익'] },
	{ key: 'operatingIncome', sj: 'IS', ids: ['dart_OperatingIncomeLoss', 'ifrs-full_ProfitLossFromOperatingActivities', 'ifrs_OperatingProfitLoss'], kw: ['영업이익', '영업이익(손실)'] },
	{ key: 'netIncome', sj: 'IS', ids: ['ifrs-full_ProfitLoss', 'ifrs_ProfitLoss'], kw: ['당기순이익', '당기순이익(손실)', '순이익'] },
	{ key: 'sga', sj: 'IS', ids: ['dart_TotalSellingGeneralAdministrativeExpenses', 'ifrs-full_SellingGeneralAndAdministrativeExpense'], kw: ['판매비와관리비', '판매관리비'] },
	{ key: 'financeIncome', sj: 'IS', ids: ['ifrs-full_FinanceIncome', 'ifrs_FinanceIncome'], kw: ['금융수익'] },
	{ key: 'financeCosts', sj: 'IS', ids: ['ifrs-full_FinanceCosts', 'ifrs_FinanceCosts'], kw: ['금융비용'] },
	{ key: 'incomeTax', sj: 'IS', ids: ['ifrs-full_IncomeTaxExpenseContinuingOperations', 'ifrs_IncomeTaxExpense'], kw: ['법인세비용'] },
	// BS
	{ key: 'assets', sj: 'BS', ids: ['ifrs-full_Assets', 'ifrs_Assets'], kw: ['자산총계'] },
	{ key: 'currentAssets', sj: 'BS', ids: ['ifrs-full_CurrentAssets', 'ifrs_CurrentAssets'], kw: ['유동자산'] },
	{ key: 'cash', sj: 'BS', ids: ['ifrs-full_CashAndCashEquivalents', 'ifrs_CashAndCashEquivalents'], kw: ['현금및현금성자산', '현금성자산'] },
	{ key: 'inventories', sj: 'BS', ids: ['ifrs-full_Inventories', 'ifrs_Inventories'], kw: ['재고자산'] },
	{ key: 'receivables', sj: 'BS', ids: ['ifrs-full_TradeAndOtherCurrentReceivables', 'dart_ShortTermTradeReceivable'], kw: ['매출채권'] },
	{ key: 'liabilities', sj: 'BS', ids: ['ifrs-full_Liabilities', 'ifrs_Liabilities'], kw: ['부채총계'] },
	{ key: 'currentLiabilities', sj: 'BS', ids: ['ifrs-full_CurrentLiabilities', 'ifrs_CurrentLiabilities'], kw: ['유동부채'] },
	{ key: 'payables', sj: 'BS', ids: ['ifrs-full_TradeAndOtherCurrentPayables', 'dart_ShortTermTradePayables'], kw: ['매입채무'] },
	{ key: 'shortDebt', sj: 'BS', ids: ['ifrs-full_ShorttermBorrowings', 'ifrs_ShorttermBorrowings'], kw: ['단기차입금'] },
	{ key: 'longDebt', sj: 'BS', ids: ['ifrs-full_LongtermBorrowings', 'ifrs_LongtermBorrowings'], kw: ['장기차입금', '사채'] },
	{ key: 'equity', sj: 'BS', ids: ['ifrs-full_Equity', 'ifrs_Equity'], kw: ['자본총계'] },
	{ key: 'capitalStock', sj: 'BS', ids: ['ifrs-full_IssuedCapital', 'ifrs_IssuedCapital', 'dart_IssuedCapital'], kw: ['자본금'] },
	{ key: 'retainedEarnings', sj: 'BS', ids: ['ifrs-full_RetainedEarnings', 'ifrs_RetainedEarnings'], kw: ['이익잉여금'] },
	// CF
	{ key: 'cfOperating', sj: 'CF', ids: ['ifrs-full_CashFlowsFromUsedInOperatingActivities', 'ifrs_CashFlowsFromUsedInOperatingActivities'], kw: ['영업활동현금흐름', '영업활동'] },
	{ key: 'cfInvesting', sj: 'CF', ids: ['ifrs-full_CashFlowsFromUsedInInvestingActivities', 'ifrs_CashFlowsFromUsedInInvestingActivities'], kw: ['투자활동현금흐름', '투자활동'] },
	{ key: 'cfFinancing', sj: 'CF', ids: ['ifrs-full_CashFlowsFromUsedInFinancingActivities', 'ifrs_CashFlowsFromUsedInFinancingActivities'], kw: ['재무활동현금흐름', '재무활동'] },
	{ key: 'capex', sj: 'CF', ids: ['ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities', 'dart_PurchaseOfPropertyPlantAndEquipment'], kw: ['유형자산의취득', '유형자산취득'] },
	{ key: 'dividendsPaid', sj: 'CF', ids: ['ifrs-full_DividendsPaidClassifiedAsFinancingActivities', 'ifrs_DividendsPaid'], kw: ['배당금지급'] }
];
const STD_BY_KEY: Record<string, StdAcct> = Object.fromEntries(STD.map((s) => [s.key, s]));
const isStock = (k: string) => STD_BY_KEY[k]?.sj === 'BS';

const TRILLION = 1e12; // 조 KRW 환산

interface RawRow extends Record<string, unknown> {
	sj_div?: string | null;
	fs_div?: string | null;
	reprt_code?: string | null;
	bsns_year?: string | number | null;
	account_id?: string | null;
	account_nm?: string | null;
	account_detail?: string | null;
	thstrm_amount?: string | number | null;
	ord?: string | number | null;
}
interface Parsed {
	sj: string;
	year: number;
	q: number; // 1..4
	id: string;
	nm: string;
	detail: string;
	ord: number;
	amt: number; // 누적(YTD) for IS/CF, 시점 for BS
}

const Q_BY_CODE: Record<string, number> = { '11013': 1, '11012': 2, '11014': 3, '11011': 4 };

function num(v: unknown): number | null {
	if (typeof v === 'number') return Number.isFinite(v) ? v : null;
	if (typeof v === 'bigint') return Number(v);
	if (typeof v === 'string' && v.trim()) {
		const n = Number(v.replace(/,/g, ''));
		return Number.isFinite(n) ? n : null;
	}
	return null;
}

const FINANCE_COLUMNS = ['sj_div', 'fs_div', 'reprt_code', 'bsns_year', 'account_id', 'account_nm', 'account_detail', 'thstrm_amount', 'ord'];

// 표시 모드: 연간 / 분기(standalone 단일분기) / TTM(직전 4분기 합). 기본 = TTM.
export type FinMode = 'annual' | 'quarter' | 'ttm';
export interface TerminalFinanceBundle {
	modes: FinMode[]; // 데이터상 가능한 모드 (분기 없으면 annual 만)
	views: Record<FinMode, TerminalFinance | null>;
	defaultMode: FinMode;
}

// in-flight Promise 캐시 — CenterStack·RightStack 가 같은 회사 재무를 동시 호출해도
// 다운로드는 1 회만(중복 fetch 경쟁 제거). 해소 후엔 같은 Promise 가 즉시 resolve.
const cache = new Map<string, Promise<TerminalFinanceBundle | null>>();

export function loadTerminalFinance(stockCode: string): Promise<TerminalFinanceBundle | null> {
	if (!browser) return Promise.resolve(null);
	const code = stockCode.trim();
	const hit = cache.get(code);
	if (hit) return hit;
	const p = (async () => {
		try {
			const { rows } = await readParquetRows<RawRow>(`dart/finance/${code}.parquet`, { columns: FINANCE_COLUMNS });
			return buildBundle(rows);
		} catch (e) {
			console.warn('[terminal/finance] load failed', code, e);
			return null;
		}
	})();
	cache.set(code, p);
	return p;
}

function buildBundle(rows: RawRow[]): TerminalFinanceBundle | null {
	// fs_div 선호: CFS(연결) → 없으면 OFS(별도)
	const hasCfs = rows.some((r) => (r.fs_div || '') === 'CFS');
	const fs = hasCfs ? 'CFS' : 'OFS';
	// 손익 출처: IS(별도 손익계산서) 있으면 IS, 없으면 CIS(단일 포괄손익계산서·카카오류) 를 IS 로 채택.
	const incomeSrc = rows.some((r) => (r.fs_div || '') === fs && r.sj_div === 'IS') ? 'IS' : 'CIS';
	const parsed: Parsed[] = [];
	for (const r of rows) {
		if ((r.fs_div || '') !== fs) continue;
		const q = Q_BY_CODE[String(r.reprt_code || '')];
		const year = Number(r.bsns_year);
		const amt = num(r.thstrm_amount);
		if (!q || !Number.isFinite(year) || amt == null) continue;
		const sjRaw = String(r.sj_div || '');
		let sj: string;
		if (sjRaw === 'IS' || sjRaw === 'CIS') {
			if (sjRaw !== incomeSrc) continue; // 채택 안 한 손익표 스킵
			sj = 'IS';
		} else sj = sjRaw; // BS · CF · SCE
		parsed.push({
			sj,
			year,
			q,
			id: String(r.account_id || ''),
			nm: String(r.account_nm || ''),
			detail: String(r.account_detail || ''),
			ord: num(r.ord) ?? Number.MAX_SAFE_INTEGER,
			amt
		});
	}
	if (parsed.length === 0) return null;

	// 표준계정 × (year,q) 매핑 — STD 별 독립 매칭 (row 소비/순서 의존 없음).
	// id 매칭 우선, 없으면 nm 키워드. 같은 셀 다중 후보 시 account_detail='-' 우선·ord 최소.
	type PK = string; // `${year}-${q}`
	const score = (x: Parsed, byId: boolean) => (byId ? 0 : 1000) + (x.detail === '-' || x.detail === '' ? 0 : 100) + Math.min(x.ord, 99);
	const grid: Record<string, Map<PK, Parsed>> = {};
	for (const s of STD) {
		const m = new Map<PK, Parsed>();
		for (const p of parsed) {
			if (p.sj !== s.sj) continue;
			const idHit = s.ids.length > 0 && s.ids.includes(p.id);
			const nmHit = !idHit && s.kw.some((k) => p.nm.includes(k));
			if (!idHit && !nmHit) continue;
			const pk = `${p.year}-${p.q}`;
			const cur = m.get(pk);
			if (!cur || score(p, idHit) < score(cur, s.ids.includes(cur.id))) m.set(pk, p);
		}
		grid[s.key] = m;
	}

	// 사용 가능한 (year,q) 모음 (자산총계 또는 매출 존재 기준) — 분기 우선
	const pkSet = new Set<string>();
	for (const key of ['revenue', 'assets', 'cfOperating', 'netIncome']) {
		for (const pk of grid[key].keys()) pkSet.add(pk);
	}
	const allPk = Array.from(pkSet)
		.map((pk) => { const [y, q] = pk.split('-').map(Number); return { pk, y, q }; })
		.sort((a, b) => a.y - b.y || a.q - b.q);
	if (allPk.length === 0) return null;

	// 분기(Q1~Q3) 존재 여부 → 분기·TTM 모드 가능. annual 은 Q4(연간) 존재 시.
	const hasInterim = allPk.some((p) => p.q !== 4);
	const hasAnnual = allPk.some((p) => p.q === 4);

	const rawV = (key: string, y: number, q: number): Num => grid[key].get(`${y}-${q}`)?.amt ?? null;

	// IS/CF flow standalone(단일분기) — DART 분기 규약 혼합 자동판정.
	// 연도 Σ(Q1..Q3) > annual 이면 YTD 누적(차분), 아니면 standalone(Q4 = annual − Σ).
	const stdCache = new Map<string, Num>();
	const standalone = (key: string, y: number, q: number): Num => {
		const ck = `${key}|${y}|${q}`;
		const hit = stdCache.get(ck);
		if (hit !== undefined) return hit;
		const q1 = rawV(key, y, 1), q2 = rawV(key, y, 2), q3 = rawV(key, y, 3), a = rawV(key, y, 4);
		const allInterim = q1 != null && q2 != null && q3 != null;
		const ytd = allInterim && a != null && q1! + q2! + q3! > a! * 1.05;
		let res: Num;
		if (q === 1) res = q1; // Q1 누적 = Q1 standalone
		else if (q === 4) {
			if (a == null) res = null;
			else if (ytd) res = q3 != null ? a - q3 : null;
			else if (allInterim) res = a - (q1! + q2! + q3!);
			else res = a; // annual-only 연도
		} else {
			const cur = rawV(key, y, q);
			if (cur == null) res = null;
			else if (ytd) { const prev = rawV(key, y, q - 1); res = prev != null ? cur - prev : cur; }
			else res = cur;
		}
		stdCache.set(ck, res);
		return res;
	};

	// ── 모드별(연간/분기/TTM) 뷰 빌드 ──
	const buildMode = (mode: FinMode): TerminalFinance | null => {
		const isAnnual = mode === 'annual';
		const KEEP = isAnnual ? 24 : 48; // 최대한 많은 기간 (막대 얇아도 무방)
		let used: { y: number; q: number; gi: number }[];
		if (isAnnual) {
			used = allPk.filter((p) => p.q === 4).slice(-KEEP).map((p) => ({ y: p.y, q: 4, gi: -1 }));
		} else if (mode === 'ttm') {
			// TTM 은 직전 4분기 필요 → 앞 3분기(gi<3) 제외해 선두 빈칸 방지
			used = allPk.map((p, gi) => ({ y: p.y, q: p.q, gi })).filter((e) => e.gi >= 3).slice(-KEEP);
		} else {
			used = allPk.map((p, gi) => ({ y: p.y, q: p.q, gi })).slice(-KEEP);
		}
		// 접지 원칙: DART 제출 분기는 그대로 노출. 과거의 "최신 이상치 pop" 휴리스틱은
		// 실제 정식 공시(예: 메모리 슈퍼사이클 분기 급증)를 조용히 삭제해 최신 분기가 누락되는
		// 회귀를 일으켰다 — 값 기준 파괴적 삭제는 폐지하고, 원본 공시값을 표시한다.
		if (used.length === 0) return null;
		const periods = used.map((p) => (isAnnual ? `FY${String(p.y).slice(2)}` : `${String(p.y).slice(2)}Q${p.q}`));

		// 값: BS = 시점. flow(IS·CF) = annual 연간 / quarter 단일분기 / ttm 직전 4분기 합.
		const flowAt = (key: string, i: number): Num => {
			const p = used[i];
			if (isAnnual) return standalone(key, p.y, 4);
			if (mode === 'quarter') return standalone(key, p.y, p.q);
			let s = 0;
			for (let k = 0; k < 4; k++) {
				const gi = p.gi - k;
				if (gi < 0) return null;
				const a = allPk[gi];
				const v = standalone(key, a.y, a.q);
				if (v == null) return null;
				s += v;
			}
			return s;
		};
		const valAtIdx = (key: string, i: number): Num => {
			if (isStock(key)) { const p = used[i]; return rawV(key, p.y, p.q); }
			return flowAt(key, i);
		};
		const lag = isAnnual ? 1 : 4; // YoY: 연간 1년 전, 분기/TTM 4분기 전

		// 계정 시리즈 — 조 KRW 환산 (BS 시점, flow 모드별)
		const ser = (key: string): Num[] => used.map((_, i) => { const v = valAtIdx(key, i); return v == null ? null : +(v / TRILLION).toFixed(3); });
		const raw = (key: string): Num[] => used.map((_, i) => valAtIdx(key, i));
		const ratio = (numK: string, denK: string, scale = 100, avgDen = false): Num[] => {
			const n = raw(numK);
			const d = raw(denK);
			return used.map((_, i) => {
				const nn = n[i];
				let dd = d[i];
				if (avgDen && i > 0 && d[i - 1] != null && dd != null) dd = (dd + d[i - 1]!) / 2;
				return nn != null && dd != null && dd !== 0 ? +((nn / dd) * scale).toFixed(1) : null;
			});
		};
		const yoy = (key: string): Num[] => {
			const v = raw(key);
			return used.map((_, i) => {
				const cur = v[i];
				const prev = i >= lag ? v[i - lag] : null;
				return cur != null && prev != null && prev !== 0 ? +(((cur - prev) / Math.abs(prev)) * 100).toFixed(1) : null;
			});
		};
		const compose = (...parts: [string, number][]): Num[] =>
			used.map((_, i) => {
				let s = 0;
				let any = false;
				for (const [k, sign] of parts) { const v = valAtIdx(k, i); if (v != null) { s += sign * v; any = true; } }
				return any ? +(s / TRILLION).toFixed(3) : null;
			});

		// 보조: grossProfit 없으면 revenue - costOfSales
		const grossProfitSer = (): Num[] => {
			const gp = raw('grossProfit');
			const rev = raw('revenue');
			const cogs = raw('costOfSales');
			return used.map((_, i) => {
				const direct = gp[i];
				if (direct != null) return direct;
				return rev[i] != null && cogs[i] != null ? rev[i]! - cogs[i]! : null;
			});
		};
		const gpRatio = (): Num[] => {
			const g = grossProfitSer();
			const rev = raw('revenue');
			return used.map((_, i) => (g[i] != null && rev[i] ? +((g[i]! / rev[i]!) * 100).toFixed(1) : null));
		};

		const C = { rev: '#5b9bf0', op: '#fb923c', net: '#34d399', good: '#34d399', warn: '#fbbf24', purple: '#a78bfa', red: '#f0616f', blue: '#60a5fa', cyan: '#22d3ee', dim: '#64748b' };

		// FCF (원 단위) + raw 시리즈 분모 비율 (CF 마진용)
		const fcfRaw = used.map((_, i) => { const op = valAtIdx('cfOperating', i); const cx = valAtIdx('capex', i); return op != null ? op - (cx ?? 0) : null; });
		const ratioOfSeries = (numRaw: Num[], denKey: string, scale = 100): Num[] => { const d = raw(denKey); return used.map((_, i) => (numRaw[i] != null && d[i] ? +((numRaw[i]! / d[i]!) * scale).toFixed(1) : null)); };

		// ── 재무제표 분석 16 카드 (기본 4 + 세트). universal 계정 위주 → 빈칸 0. ──
		const cards: FinCard[] = [
			// 기본 4 — 자산·조달·손익·현금
			{ key: 'assetComposition', title: '자산구조', unit: '조', stacked: true, series: [
				{ name: '현금', data: ser('cash'), color: C.good, type: 'bar' },
				{ name: '매출채권', data: ser('receivables'), color: C.blue, type: 'bar' },
				{ name: '재고', data: ser('inventories'), color: C.warn, type: 'bar' },
				{ name: '기타', data: compose(['assets', 1], ['cash', -1], ['receivables', -1], ['inventories', -1]), color: C.dim, type: 'bar' }
			] },
			{ key: 'fundingStructure', title: '조달구조', unit: '조', stacked: true, series: [
				{ name: '유동부채', data: ser('currentLiabilities'), color: C.red, type: 'bar' },
				{ name: '비유동부채', data: compose(['liabilities', 1], ['currentLiabilities', -1]), color: C.op, type: 'bar' },
				{ name: '자본', data: ser('equity'), color: C.good, type: 'bar' }
			] },
			{ key: 'incomeBreakdown', title: '손익구조', unit: '조', series: [
				{ name: '매출', data: ser('revenue'), color: C.rev, type: 'bar' },
				{ name: '영업익', data: ser('operatingIncome'), color: C.op, type: 'line', axis: 'r' },
				{ name: '순익', data: ser('netIncome'), color: C.net, type: 'line', axis: 'r' }
			] },
			{ key: 'cashflowSigned', title: '현금흐름', unit: '조', signed: true, series: [
				{ name: '영업', data: ser('cfOperating'), color: C.good, type: 'bar' },
				{ name: '투자', data: ser('cfInvesting'), color: C.blue, type: 'bar' },
				{ name: '재무', data: ser('cfFinancing'), color: C.op, type: 'bar' }
			] },
			// 수익성
			{ key: 'marginTrend', title: '이익률', unit: '%', series: [
				{ name: 'GPM', data: gpRatio(), color: C.warn, type: 'line' },
				{ name: 'OPM', data: ratio('operatingIncome', 'revenue'), color: C.op, type: 'line' },
				{ name: 'NPM', data: ratio('netIncome', 'revenue'), color: C.net, type: 'line' }
			] },
			{ key: 'returnTrend', title: 'ROE·ROA', unit: '%', series: [
				{ name: 'ROE', data: ratio('netIncome', 'equity', 100, true), color: C.net, type: 'line' },
				{ name: 'ROA', data: ratio('netIncome', 'assets', 100, true), color: C.blue, type: 'line' }
			] },
			{ key: 'cfMargin', title: '현금마진', unit: '%', series: [
				{ name: 'CFO/매출', data: ratio('cfOperating', 'revenue'), color: C.good, type: 'line' },
				{ name: 'FCF/매출', data: ratioOfSeries(fcfRaw, 'revenue'), color: C.warn, type: 'line' }
			] },
			// 안정성
			{ key: 'leverageTrend', title: '레버리지·유동', unit: '%', refLines: [100], series: [
				{ name: '부채비율', data: ratio('liabilities', 'equity'), color: C.red, type: 'bar' },
				{ name: '유동비율', data: ratio('currentAssets', 'currentLiabilities'), color: C.blue, type: 'line', axis: 'r' }
			] },
			{ key: 'stability', title: '안정성', unit: '%', series: [
				{ name: '자기자본비율', data: ratio('equity', 'assets'), color: C.good, type: 'bar' },
				{ name: '유동비율', data: ratio('currentAssets', 'currentLiabilities'), color: C.blue, type: 'line', axis: 'r' }
			] },
			{ key: 'netDebt', title: '순차입금', unit: '조', signed: true, series: [
				{ name: '순차입', data: compose(['shortDebt', 1], ['longDebt', 1], ['cash', -1]), color: C.red, type: 'bar' },
				{ name: 'D/E', data: ratio('liabilities', 'equity'), color: C.purple, type: 'line', axis: 'r' }
			] },
			// 현금·효율
			{ key: 'fcfTrend', title: 'FCF', unit: '조', signed: true, series: [
				{ name: 'FCF', data: compose(['cfOperating', 1], ['capex', -1]), color: C.warn, type: 'line' },
				{ name: '영업CF', data: ser('cfOperating'), color: C.good, type: 'bar' },
				{ name: 'CAPEX', data: compose(['capex', -1]), color: C.dim, type: 'bar' }
			] },
			{ key: 'earningsQuality', title: '이익품질', unit: '배', refLines: [1], series: [
				{ name: 'CFO/NI', data: ratio('cfOperating', 'netIncome', 1), color: C.cyan, type: 'bar' },
				{ name: 'CFO/매출', data: ratio('cfOperating', 'revenue'), color: C.good, type: 'line', axis: 'r' }
			] },
			{ key: 'turnover', title: '회전율', unit: '회', series: [
				{ name: '자산회전', data: ratio('revenue', 'assets', 1, true), color: C.blue, type: 'line' },
				{ name: '매출채권', data: ratio('revenue', 'receivables', 1, true), color: C.cyan, type: 'line' }
			] },
			// 성장
			{ key: 'growthYoy', title: '성장 YoY', unit: '%', signed: true, series: [
				{ name: '매출', data: yoy('revenue'), color: C.rev, type: 'bar' },
				{ name: '영업익', data: yoy('operatingIncome'), color: C.op, type: 'line' },
				{ name: '순익', data: yoy('netIncome'), color: C.net, type: 'line' }
			] },
			{ key: 'assetGrowth', title: '자산·자본성장', unit: '%', signed: true, series: [
				{ name: '자산', data: yoy('assets'), color: C.blue, type: 'bar' },
				{ name: '자본', data: yoy('equity'), color: C.good, type: 'line' }
			] },
			{ key: 'scale', title: '규모', unit: '조', series: [
				{ name: '자산', data: ser('assets'), color: C.blue, type: 'line' },
				{ name: '부채', data: ser('liabilities'), color: C.red, type: 'line' },
				{ name: '자본', data: ser('equity'), color: C.good, type: 'line' }
			] }
		];

		// 회사에 데이터 전무(빈 파케이)면 null. 개별 카드 sparse 는 셀 유지 (빈칸 방지).
		if (!cards.some((c) => c.series.some((s) => s.data.some((v) => v != null)))) return null;
		// 파생 인사이트 — 실적 모멘텀(YoY) + 현금흐름 품질(영업CF/순익).
		const revYoy = yoy('revenue');
		const opYoy = yoy('operatingIncome');
		const cashQuality: Num[] = used.map((_, i) => {
			const cf = valAtIdx('cfOperating', i);
			const ni = valAtIdx('netIncome', i);
			return cf != null && ni != null && ni > 0 ? +(cf / ni).toFixed(2) : null;
		});
		// 재무제표 표 — 전 기간 계정×기간 (조 KRW). 손익·재무상태·현금흐름·비용.
		const mkStmt = (defs: { key: string; kr: string; en: string }[]): StmtRow[] => defs.map((d) => ({ key: d.key, kr: d.kr, en: d.en, values: ser(d.key) }));
		const statements: Record<StmtKind, StmtRow[]> = { IS: mkStmt(STMT_DEF.IS), BS: mkStmt(STMT_DEF.BS), CF: mkStmt(STMT_DEF.CF) };
		// 핵심 비율 시계열 — 재무제표와 동일 기간 축. 수익성·안정성·현금. (% · 이익품질만 배)
		const ratios: StmtRow[] = [
			{ key: 'roe', kr: 'ROE', en: 'ROE', unit: '%', values: ratio('netIncome', 'equity', 100, true) },
			{ key: 'roa', kr: 'ROA', en: 'ROA', unit: '%', values: ratio('netIncome', 'assets', 100, true) },
			{ key: 'gpm', kr: '매출총이익률', en: 'Gross margin', unit: '%', values: gpRatio() },
			{ key: 'opm', kr: '영업이익률', en: 'Operating margin', unit: '%', values: ratio('operatingIncome', 'revenue') },
			{ key: 'npm', kr: '순이익률', en: 'Net margin', unit: '%', values: ratio('netIncome', 'revenue') },
			{ key: 'debtRatio', kr: '부채비율', en: 'Debt/Equity', unit: '%', values: ratio('liabilities', 'equity') },
			{ key: 'currentRatio', kr: '유동비율', en: 'Current', unit: '%', values: ratio('currentAssets', 'currentLiabilities') },
			{ key: 'equityRatio', kr: '자기자본비율', en: 'Equity ratio', unit: '%', values: ratio('equity', 'assets') },
			{ key: 'cfoMargin', kr: '영업CF마진', en: 'CFO margin', unit: '%', values: ratio('cfOperating', 'revenue') },
			{ key: 'earningsQuality', kr: '이익품질(CFO/NI)', en: 'Earnings quality', unit: '배', values: ratio('cfOperating', 'netIncome', 1) }
		];
		return { periods, freq: mode, cards, revYoy, opYoy, cashQuality, statements, ratios };
	};

	const views: Record<FinMode, TerminalFinance | null> = {
		annual: hasAnnual ? buildMode('annual') : null,
		quarter: hasInterim ? buildMode('quarter') : null,
		ttm: hasInterim ? buildMode('ttm') : null
	};
	const modes: FinMode[] = [];
	if (views.ttm) modes.push('ttm');
	if (views.quarter) modes.push('quarter');
	if (views.annual) modes.push('annual');
	if (modes.length === 0) return null;
	const defaultMode: FinMode = views.ttm ? 'ttm' : views.annual ? 'annual' : modes[0];
	return { modes, views, defaultMode };
}
