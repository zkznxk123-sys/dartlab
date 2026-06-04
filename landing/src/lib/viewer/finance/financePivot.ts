// 정량재무제표 순수 로직 — SQL 빌더 + pivot + era-drift 병합. duckdb import 0(순수, parity 테스트 가능).
// financeQuery.ts(IO)가 본 모듈의 buildSql/pivot 을 DuckDB 결과에 적용.

import type { FinanceFreq, FinanceKind, FinanceScope, FinanceStatement, FinanceStmtRow } from './types';

export interface QueryRow {
	period: string;
	acct: string;
	label: string;
	val: number | null;
	ord: number | null;
}

// SQL 문자열 escape (단일 인용 안전) — duckdb.sqlEscape 와 동일, import 격리 위해 로컬.
const esc = (s: string): string => s.replace(/'/g, "''");
const num = (col: string): string => `TRY_CAST(REPLACE(CAST(${col} AS VARCHAR), ',', '') AS DOUBLE)`;
const QUARTER_CASE = `CASE reprt_code WHEN '11013' THEN 'Q1' WHEN '11012' THEN 'Q2' WHEN '11014' THEN 'Q3' WHEN '11011' THEN 'Q4' END`;

// (kind, freq) → {period 표현, 금액식, reprt 필터}. BS=시점, flow=연간/분기단독/누적.
export function freqClause(kind: FinanceKind, freq: FinanceFreq): { period: string; amount: string; reprt: string } {
	const isBs = kind === 'BS';
	if (freq === 'annual') {
		return { period: 'bsns_year', amount: num('thstrm_amount'), reprt: "reprt_code = '11011'" };
	}
	const period = `CONCAT(bsns_year, ${QUARTER_CASE})`;
	if (isBs) {
		// BS 는 시점 잔액 — 분기/누적 구분 없음(thstrm_amount), 연간슬롯(11011)=연말잔액 포함.
		return { period, amount: num('thstrm_amount'), reprt: "reprt_code IN ('11011','11012','11013','11014')" };
	}
	if (freq === 'cumulative') {
		// 누적 — 분기 add_amount, 연간(11011)=full year(=Q4 누적).
		return {
			period,
			amount: `CASE WHEN reprt_code = '11011' THEN ${num('thstrm_amount')} ELSE ${num('thstrm_add_amount')} END`,
			reprt: "reprt_code IN ('11011','11012','11013','11014')"
		};
	}
	// 분기 단독 — 분기보고서 thstrm_amount(당분기). Q4 단독(연간−Q3누적)은 v1 생략.
	return { period, amount: num('thstrm_amount'), reprt: "reprt_code IN ('11012','11013','11014')" };
}

export function buildSql(stockCode: string, kind: FinanceKind, freq: FinanceFreq, scope: FinanceScope): string {
	const code = esc(stockCode);
	const { period, amount, reprt } = freqClause(kind, freq);
	// 같은 (period, account) 중복(요약/세부)은 account_detail='-'(요약) 우선 1행.
	return `
		WITH f AS (
			SELECT ${period} AS period,
			       COALESCE(NULLIF(CAST(account_id AS VARCHAR), ''), account_nm) AS acct,
			       account_nm AS label,
			       ${amount} AS val,
			       TRY_CAST(ord AS INTEGER) AS ord,
			       ROW_NUMBER() OVER (
			           PARTITION BY ${period}, COALESCE(NULLIF(CAST(account_id AS VARCHAR), ''), account_nm)
			           ORDER BY CASE WHEN account_detail = '-' OR account_detail IS NULL THEN 0 ELSE 1 END,
			                    TRY_CAST(ord AS INTEGER) NULLS LAST
			       ) AS rn
			FROM companyFinance
			WHERE stock_code = '${code}' AND sj_div = '${esc(kind)}' AND fs_div = '${esc(scope)}'
			  AND ${reprt} AND account_nm IS NOT NULL AND ${amount} IS NOT NULL
		)
		SELECT period, acct, label, val, ord FROM f WHERE rn = 1 ORDER BY ord NULLS LAST, acct, period
	`;
}

// 계정 depth — account_id(XBRL 개념)의 구조 분류. 총계/소계 개념집합은 회사간 매우 안정(실측 15/15).
// standardAccounts.level 은 커버리지·의미 오류로 부적합. 0=총계(굵게)·1=소계·2=리프(들여쓰기).
const DEPTH0 = new Set([
	'ifrs-full_Assets',
	'ifrs-full_Liabilities',
	'ifrs-full_Equity',
	'ifrs-full_EquityAndLiabilities',
	'ifrs-full_ComprehensiveIncome',
	'ifrs-full_ProfitLoss'
]);
const DEPTH1 = new Set([
	'ifrs-full_CurrentAssets',
	'ifrs-full_NoncurrentAssets',
	'ifrs-full_CurrentLiabilities',
	'ifrs-full_NoncurrentLiabilities',
	'ifrs-full_EquityAttributableToOwnersOfParent',
	'ifrs-full_GrossProfit',
	'dart_OperatingIncomeLoss',
	'ifrs-full_ProfitLossBeforeTax',
	'ifrs-full_OtherComprehensiveIncome'
]);
export function accountDepth(accountId: string): number {
	if (DEPTH0.has(accountId)) return 0;
	if (DEPTH1.has(accountId)) return 1;
	return 2;
}

// 최신좌측 정렬 — "YYYY"/"YYYYQn" 문자열 내림차순.
const sortPeriodsDesc = (ps: string[]): string[] => [...ps].sort((a, b) => (a < b ? 1 : a > b ? -1 : 0));

// 같은 label 의 account_id 변종을 **기간 비충돌**끼리 병합 — era-drift 동의어 태그(매출액 태그가 연도마다 바뀜)는
// 한 행으로, 매 기간 공존하는 동명(BS 의 '기타'×N, 부모 다름)은 분리 유지(기간 겹침). 엔진 snakeId 정규화의
// 경량 근사(as-reported 충실). 충돌(같은 기간 두 값) 시 병합 안 함.
export function mergeDriftVariants(rawRows: FinanceStmtRow[]): FinanceStmtRow[] {
	const byLabel = new Map<string, FinanceStmtRow[]>();
	for (const r of rawRows) {
		const g = byLabel.get(r.label);
		if (g) g.push(r);
		else byLabel.set(r.label, [r]);
	}
	const out: FinanceStmtRow[] = [];
	for (const group of byLabel.values()) {
		const slots: FinanceStmtRow[] = [];
		for (const r of group) {
			const keys = Object.keys(r.values);
			const slot = slots.find((s) => !keys.some((p) => p in s.values)); // 기간 비충돌 슬롯
			if (slot) {
				for (const [p, v] of Object.entries(r.values)) slot.values[p] = v;
				slot.ord = Math.min(slot.ord, r.ord);
			} else {
				slots.push({ ...r, values: { ...r.values } });
			}
		}
		out.push(...slots);
	}
	return out.sort((a, b) => a.ord - b.ord || a.label.localeCompare(b.label, 'ko-KR'));
}

export function pivot(rows: QueryRow[], kind: FinanceKind, scope: FinanceScope, freq: FinanceFreq): FinanceStatement {
	const periods = sortPeriodsDesc([...new Set(rows.map((r) => r.period))]);
	const byAcct = new Map<string, FinanceStmtRow>();
	for (const r of rows) {
		let row = byAcct.get(r.acct);
		if (!row) {
			row = { accountId: r.acct, label: r.label || r.acct, ord: r.ord ?? Number.MAX_SAFE_INTEGER, depth: accountDepth(r.acct), values: {} };
			byAcct.set(r.acct, row);
		}
		row.ord = Math.min(row.ord, r.ord ?? Number.MAX_SAFE_INTEGER);
		row.values[r.period] = r.val;
	}
	return { kind, scope, freq, periods, rows: mergeDriftVariants([...byAcct.values()]), unit: 'KRW' };
}
