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
export interface TerminalFinance {
	periods: string[]; // 표시용 압축 라벨 (예: '23Q4')
	freq: 'quarter' | 'annual';
	cards: FinCard[];
}

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

const cache = new Map<string, TerminalFinance | null>();

export async function loadTerminalFinance(stockCode: string): Promise<TerminalFinance | null> {
	if (!browser) return null;
	const code = stockCode.trim();
	if (cache.has(code)) return cache.get(code) ?? null;
	try {
		const { rows } = await readParquetRows<RawRow>(`dart/finance/${code}.parquet`, { columns: FINANCE_COLUMNS });
		const built = buildFinance(rows);
		cache.set(code, built);
		return built;
	} catch (e) {
		console.warn('[terminal/finance] load failed', code, e);
		cache.set(code, null);
		return null;
	}
}

function buildFinance(rows: RawRow[]): TerminalFinance | null {
	// fs_div 선호: CFS(연결) → 없으면 OFS(별도)
	const hasCfs = rows.some((r) => (r.fs_div || '') === 'CFS');
	const fs = hasCfs ? 'CFS' : 'OFS';
	const parsed: Parsed[] = [];
	for (const r of rows) {
		if ((r.fs_div || '') !== fs) continue;
		const q = Q_BY_CODE[String(r.reprt_code || '')];
		const year = Number(r.bsns_year);
		const amt = num(r.thstrm_amount);
		if (!q || !Number.isFinite(year) || amt == null) continue;
		parsed.push({
			sj: String(r.sj_div || ''),
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

	// 분기 데이터가 충분한가? (Q1~Q3 존재) → 분기 TTM, 아니면 annual(Q4만)
	const hasInterim = allPk.some((p) => p.q !== 4);
	const freq: 'quarter' | 'annual' = hasInterim ? 'quarter' : 'annual';

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

	// 표시 기간: 분기면 마지막 16, annual 이면 마지막 8
	const keepN = freq === 'quarter' ? 16 : 8;
	const used = (freq === 'quarter' ? allPk : allPk.filter((p) => p.q === 4)).slice(-keepN);
	// 최신 분기가 명백한 이상치(매출 standalone > 직전 4분기 중앙값 1.6×)면 제외 — 예비/오류 공시 방어
	while (freq === 'quarter' && used.length >= 5) {
		const li = used.length - 1;
		const lastRev = standalone('revenue', used[li].y, used[li].q);
		const prior = used.slice(li - 4, li).map((p) => standalone('revenue', p.y, p.q)).filter((v): v is number => v != null);
		if (lastRev == null || prior.length < 3) break;
		const med = [...prior].sort((a, b) => a - b)[Math.floor(prior.length / 2)];
		if (med > 0 && lastRev > med * 1.5) used.pop();
		else break;
	}
	const periods = used.map((p) => `${String(p.y).slice(2)}Q${p.q}`);

	// 값: BS 시점 / IS·CF flow = TTM(직전 4 분기 standalone 합). annual freq = 연간 standalone.
	const valAtIdx = (key: string, i: number): Num => {
		const p = used[i];
		if (isStock(key)) return rawV(key, p.y, p.q);
		if (freq === 'annual') return standalone(key, p.y, 4);
		let s = 0;
		for (let k = 0; k < 4; k++) {
			const j = i - k;
			if (j < 0) return null;
			const v = standalone(key, used[j].y, used[j].q);
			if (v == null) return null;
			s += v;
		}
		return s;
	};

	// 계정 시리즈 — 조 KRW 환산 (BS 시점, IS/CF TTM)
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
		const lag = freq === 'quarter' ? 4 : 1; // TTM YoY = 4 분기(=1년) 전 대비
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

	// ── 핵심 10 카드 (viz/catalog/finance.py FINANCE_DASHBOARD_KEYS 핵심) ──
	const cards: FinCard[] = [];

	// 1. 손익구조 — 매출 막대 + 영업/순이익 선
	cards.push({ key: 'incomeBreakdown', title: '손익', unit: '조', series: [
		{ name: '매출', data: ser('revenue'), color: C.rev, type: 'bar' },
		{ name: '영업익', data: ser('operatingIncome'), color: C.op, type: 'line' },
		{ name: '순익', data: ser('netIncome'), color: C.net, type: 'line' }
	] });

	// 2. 이익률 — GPM/OPM/NPM
	cards.push({ key: 'marginTrend', title: '이익률', unit: '%', series: [
		{ name: 'GPM', data: gpRatio(), color: C.warn, type: 'line' },
		{ name: 'OPM', data: ratio('operatingIncome', 'revenue'), color: C.op, type: 'line' },
		{ name: 'NPM', data: ratio('netIncome', 'revenue'), color: C.net, type: 'line' }
	] });

	// 3. 수익성 — ROE/ROA (평균자본 분모)
	cards.push({ key: 'returnTrend', title: 'ROE · ROA', unit: '%', series: [
		{ name: 'ROE', data: ratio('netIncome', 'equity', 100, true), color: C.net, type: 'line' },
		{ name: 'ROA', data: ratio('netIncome', 'assets', 100, true), color: C.blue, type: 'line' }
	] });

	// 4. 자산구조 — 자산 stacked (현금/매출채권/재고/기타) 시점
	cards.push({ key: 'assetComposition', title: '자산구조', unit: '조', stacked: true, series: [
		{ name: '현금', data: ser('cash'), color: C.good, type: 'bar' },
		{ name: '매출채권', data: ser('receivables'), color: C.blue, type: 'bar' },
		{ name: '재고', data: ser('inventories'), color: C.warn, type: 'bar' },
		{ name: '기타', data: compose(['assets', 1], ['cash', -1], ['receivables', -1], ['inventories', -1]), color: C.dim, type: 'bar' }
	] });

	// 5. 레버리지 — 부채비율 bar + 유동비율 line(우축)
	cards.push({ key: 'leverageTrend', title: '레버리지·유동', unit: '%', series: [
		{ name: '부채비율', data: ratio('liabilities', 'equity'), color: C.red, type: 'bar' },
		{ name: '유동비율', data: ratio('currentAssets', 'currentLiabilities'), color: C.blue, type: 'line', axis: 'r' }
	], refLines: [100] });

	// 6. 순차입금 — netDebt signed bar + 차입금/자본 line
	cards.push({ key: 'netDebt', title: '순차입금', unit: '조', signed: true, series: [
		{ name: '순차입', data: compose(['shortDebt', 1], ['longDebt', 1], ['cash', -1]), color: C.red, type: 'bar' },
		{ name: 'D/E', data: ratio('liabilities', 'equity'), color: C.purple, type: 'line', axis: 'r' }
	] });

	// 7. 현금흐름 — CFO/CFI/CFF signed + 순증감 line
	cards.push({ key: 'cashflowSigned', title: '현금흐름', unit: '조', signed: true, series: [
		{ name: '영업', data: ser('cfOperating'), color: C.good, type: 'bar' },
		{ name: '투자', data: ser('cfInvesting'), color: C.blue, type: 'bar' },
		{ name: '재무', data: ser('cfFinancing'), color: C.op, type: 'bar' }
	] });

	// 8. 잉여현금흐름 — FCF line(헤더값) + CFO/capex bar
	cards.push({ key: 'fcfTrend', title: 'FCF', unit: '조', signed: true, series: [
		{ name: 'FCF', data: compose(['cfOperating', 1], ['capex', -1]), color: C.warn, type: 'line' },
		{ name: '영업CF', data: ser('cfOperating'), color: C.good, type: 'bar' },
		{ name: 'CAPEX', data: compose(['capex', -1]), color: C.dim, type: 'bar' }
	] });

	// 9. 이익 품질 — CFO/순이익(배, 1.0 기준), CFO/매출 line
	cards.push({ key: 'earningsQuality', title: '이익품질', unit: '배', series: [
		{ name: 'CFO/NI', data: ratio('cfOperating', 'netIncome', 1), color: C.cyan, type: 'bar' },
		{ name: 'CFO/매출', data: ratio('cfOperating', 'revenue'), color: C.good, type: 'line', axis: 'r' }
	], refLines: [1] });

	// 10. 성장성 — 매출/영업익/순익 YoY
	cards.push({ key: 'growthYoy', title: '성장 YoY', unit: '%', signed: true, series: [
		{ name: '매출', data: yoy('revenue'), color: C.rev, type: 'bar' },
		{ name: '영업익', data: yoy('operatingIncome'), color: C.op, type: 'line' },
		{ name: '순익', data: yoy('netIncome'), color: C.net, type: 'line' }
	] });

	// null-only 카드 제거 (데이터 없는 회사 방어)
	const live = cards.filter((c) => c.series.some((s) => s.data.some((v) => v != null)));
	if (live.length === 0) return null;
	return { periods, freq, cards: live };
}
