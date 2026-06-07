// 정량재무제표 순수 로직 — SQL 빌더 + pivot + era-drift 병합. duckdb import 0(순수, parity 테스트 가능).
// financeQuery.ts(IO)가 본 모듈의 buildSql/pivot 을 DuckDB 결과에 적용.

import type {
	FinanceFreq,
	FinanceKind,
	FinanceScope,
	FinanceStatement,
	FinanceStmtRow,
	SceMatrixData,
	SceRow
} from './types';
import {
	FINANCE_ACCOUNT_DEPTH,
	FINANCE_ACCOUNT_ID_ALIAS,
	FINANCE_ACCOUNT_ID_TO_SNAKE,
	FINANCE_ACCOUNT_IS_TOTAL,
	FINANCE_ACCOUNT_LABEL,
	FINANCE_ACCOUNT_NAME_TO_SNAKES,
	FINANCE_ACCOUNT_ORDER,
	type FinanceStatementOrderKey
} from './accountOrder';

type NumberMap = Record<string, number>;
type StringMap = Record<string, string>;
type BoolMap = Record<string, boolean>;
type NameCandidateMap = Record<string, readonly string[]>;

const ACCOUNT_ORDER = FINANCE_ACCOUNT_ORDER as Record<FinanceStatementOrderKey, NumberMap>;
const ACCOUNT_DEPTH = FINANCE_ACCOUNT_DEPTH as Record<FinanceStatementOrderKey, NumberMap>;
const ACCOUNT_IS_TOTAL = FINANCE_ACCOUNT_IS_TOTAL as Record<FinanceStatementOrderKey, BoolMap>;
const ACCOUNT_LABEL = FINANCE_ACCOUNT_LABEL as StringMap;
const ACCOUNT_ID_TO_SNAKE = FINANCE_ACCOUNT_ID_TO_SNAKE as StringMap;
const ACCOUNT_ID_ALIAS = FINANCE_ACCOUNT_ID_ALIAS as StringMap;
const ACCOUNT_NAME_TO_SNAKES = FINANCE_ACCOUNT_NAME_TO_SNAKES as NameCandidateMap;

export interface QueryRow {
	period: string;
	acct: string;
	label: string;
	val: number | null;
	ord: number | null;
}

// SQL 문자열 escape (단일 인용 안전) — duckdb.sqlEscape 와 동일, import 격리 위해 로컬.
const esc = (s: string): string => s.replace(/'/g, "''");
export const num = (col: string): string => `TRY_CAST(REPLACE(CAST(${col} AS VARCHAR), ',', '') AS DOUBLE)`;
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

// 분기 단독 flow(IS/CIS) — Q1~Q3 = 분기보고서 thstrm, Q4 = 연간(11011) − Q3누적(11014 add). 한 쿼리로 4분기.
function buildQuarterStandaloneSql(code: string, kind: FinanceKind, scope: FinanceScope): string {
	const acct = `COALESCE(NULLIF(CAST(account_id AS VARCHAR), ''), account_nm)`;
	return `
		WITH q AS (
			SELECT ${acct} AS acct, account_nm AS label, bsns_year AS yr, MIN(TRY_CAST(ord AS INTEGER)) AS ord,
			       MAX(CASE WHEN reprt_code = '11013' THEN ${num('thstrm_amount')} END) AS q1,
			       MAX(CASE WHEN reprt_code = '11012' THEN ${num('thstrm_amount')} END) AS q2,
			       MAX(CASE WHEN reprt_code = '11014' THEN ${num('thstrm_amount')} END) AS q3,
			       MAX(CASE WHEN reprt_code = '11011' THEN ${num('thstrm_amount')} END) AS yr_amt,
			       MAX(CASE WHEN reprt_code = '11014' THEN ${num('thstrm_add_amount')} END) AS q3cum
			FROM companyFinance
			WHERE stock_code = '${code}' AND sj_div = '${esc(kind)}' AND fs_div = '${esc(scope)}'
			  AND account_nm IS NOT NULL AND (account_detail = '-' OR account_detail IS NULL)
			GROUP BY 1, 2, 3
		)
		SELECT yr || 'Q1' AS period, acct, label, q1 AS val, ord FROM q WHERE q1 IS NOT NULL
		UNION ALL SELECT yr || 'Q2', acct, label, q2, ord FROM q WHERE q2 IS NOT NULL
		UNION ALL SELECT yr || 'Q3', acct, label, q3, ord FROM q WHERE q3 IS NOT NULL
		UNION ALL SELECT yr || 'Q4', acct, label, yr_amt - q3cum, ord FROM q WHERE yr_amt IS NOT NULL AND q3cum IS NOT NULL
		ORDER BY ord NULLS LAST, acct, period
	`;
}

export function buildSql(stockCode: string, kind: FinanceKind, freq: FinanceFreq, scope: FinanceScope): string {
	const code = esc(stockCode);
	if (freq === 'quarter' && kind !== 'BS') return buildQuarterStandaloneSql(code, kind, scope); // Q4 포함 분기단독
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

const ACCOUNT_PREFIX_RE = /^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)/;
const UNKNOWN_ORDER_BASE = 1_000_000;

function statementOrderKey(kind?: FinanceKind): FinanceStatementOrderKey | null {
	if (kind === 'BS' || kind === 'CF') return kind;
	if (kind === 'IS' || kind === 'CIS') return 'IS';
	return null;
}

function stripAccountPrefix(accountId: string): string {
	return accountId.replace(ACCOUNT_PREFIX_RE, '');
}

function orderMap(kind?: FinanceKind): Record<string, number> | null {
	const key = statementOrderKey(kind);
	return key ? ACCOUNT_ORDER[key] : null;
}

function depthMap(kind?: FinanceKind): Record<string, number> | null {
	const key = statementOrderKey(kind);
	return key ? ACCOUNT_DEPTH[key] : null;
}

function accountDepthFromSnake(snake: string, kind?: FinanceKind): number | null {
	return (
		depthMap(kind)?.[snake] ??
		ACCOUNT_DEPTH.BS[snake] ??
		ACCOUNT_DEPTH.IS[snake] ??
		ACCOUNT_DEPTH.CF[snake] ??
		null
	);
}

function isTotalMap(kind?: FinanceKind): Record<string, boolean> | null {
	const key = statementOrderKey(kind);
	return key ? ACCOUNT_IS_TOTAL[key] : null;
}

function accountIsTotalFromSnake(snake: string, kind?: FinanceKind): boolean {
	return (
		isTotalMap(kind)?.[snake] ??
		ACCOUNT_IS_TOTAL.BS[snake] ??
		ACCOUNT_IS_TOTAL.IS[snake] ??
		ACCOUNT_IS_TOTAL.CF[snake] ??
		false
	);
}

function firstOrderedCandidate(candidates: readonly string[] | undefined, order: Record<string, number> | null): string | null {
	if (!candidates?.length) return null;
	if (!order) return candidates[0] ?? null;
	let best: string | null = null;
	let bestOrder = Number.POSITIVE_INFINITY;
	for (const snake of candidates) {
		const candidateOrder = order[snake];
		if (candidateOrder == null || candidateOrder >= bestOrder) continue;
		best = snake;
		bestOrder = candidateOrder;
	}
	return best ?? candidates[0] ?? null;
}

export function accountSnake(accountId: string, label = '', kind?: FinanceKind): string | null {
	const order = orderMap(kind);
	const stripped = stripAccountPrefix(accountId || '');
	const idSnake = stripped ? ACCOUNT_ID_TO_SNAKE[stripped] : undefined;
	if (idSnake && (!order || order[idSnake] != null)) return idSnake;

	const labelSnake = firstOrderedCandidate(ACCOUNT_NAME_TO_SNAKES[label], order);
	if (labelSnake && (!order || order[labelSnake] != null)) return labelSnake;

	// 최저 우선순위 — 직접 id·name 둘 다 실패 시에만 alias-follow(예: Revenue→sales). name 이 맞는
	// 케이스(Equity→자본총계→stockholders_equity)는 이미 위에서 반환되어 여기 도달 안 함.
	const aliasSnake = stripped ? ACCOUNT_ID_ALIAS[stripped] : undefined;
	if (aliasSnake && (!order || order[aliasSnake] != null)) return aliasSnake;

	return idSnake ?? labelSnake ?? aliasSnake ?? null;
}

// 들여쓰기 깊이(순수 구조) — IS 본류(매출액~당기순이익) 균일 1, 리프 2+. 원천은 Python 과 같은 account SSOT mirror.
export function accountDepth(accountId: string, label = '', kind?: FinanceKind): number {
	const snake = accountSnake(accountId, label, kind);
	if (!snake) return 2;
	return accountDepthFromSnake(snake, kind) ?? 2;
}

// 총계 강조(굵게+상단보더) 여부 — depth(들여쓰기)와 분리된 emphasis 신호. snakeId 명시 SSOT mirror.
// IS 당기순이익/총포괄손익은 depth 1 이어도 true, BS 자산·부채·자본총계는 depth 0 + true.
export function accountIsTotal(accountId: string, label = '', kind?: FinanceKind): boolean {
	const snake = accountSnake(accountId, label, kind);
	if (!snake) return false;
	return accountIsTotalFromSnake(snake, kind);
}

// 표시 라벨 — 엔진 panel 과 동일한 표준 한글명(snakeId→korName SSOT mirror). account_id/account_nm 의
// as-reported 표류(수익(매출액)/매출액/영업수익)를 표준명으로 통일. 미해결(매핑 없음)은 as-reported 원문 유지.
export function accountLabel(accountId: string, label = '', kind?: FinanceKind): string {
	const snake = accountSnake(accountId, label, kind);
	const std = snake ? ACCOUNT_LABEL[snake] : undefined;
	return std || label || accountId;
}

export function accountDisplayOrder(accountId: string, label: string, kind: FinanceKind, rawOrd: number | null): number {
	const snake = accountSnake(accountId, label, kind);
	const order = snake ? orderMap(kind)?.[snake] : null;
	if (order != null) return order;
	return UNKNOWN_ORDER_BASE + (rawOrd ?? Number.MAX_SAFE_INTEGER);
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
		const displayOrd = accountDisplayOrder(r.acct, r.label, kind, r.ord);
		if (!row) {
			row = {
				accountId: r.acct,
				label: accountLabel(r.acct, r.label, kind),
				ord: displayOrd,
				depth: accountDepth(r.acct, r.label, kind),
				isTotal: accountIsTotal(r.acct, r.label, kind),
				values: {}
			};
			byAcct.set(r.acct, row);
		}
		row.ord = Math.min(row.ord, displayOrd);
		row.values[r.period] = r.val;
	}
	return { kind, scope, freq, periods, rows: mergeDriftVariants([...byAcct.values()]), unit: 'KRW' };
}

// ── 자본변동표(SCE) matrix ── 변동유형(행) × 자본구성요소(열), 기간별. account_detail 경로 끝 = 자본구성요소.
// '연결재무제표/재무제표 [member]' = 자본총계. account×period 1D 로는 2D 행렬을 표현 못 해 전용.
export function sceComponent(detail: string | null): string {
	if (!detail) return '기타';
	let last = detail.split('|').pop()?.trim() ?? '기타';
	last = last.replace(/\s*\[(구성요소|member)\]\s*$/u, '').trim();
	return last === '연결재무제표' || last === '재무제표' ? '자본총계' : last;
}
const SCE_COL_PRIORITY = [
	'자본금', '신종자본증권', '자본잉여금', '주식발행초과금', '기타불입자본', '기타자본', '기타자본구성요소',
	'기타포괄손익누계액', '이익잉여금', '지배기업의 소유주에게 귀속되는 지분', '비지배지분', '자본총계'
];
export interface SceQueryRow {
	period: string;
	label: string;
	comp: string;
	val: number | null;
	ord: number | null;
}
export function buildSceMatrix(rows: SceQueryRow[], scope: FinanceScope): SceMatrixData {
	const periods = sortPeriodsDesc([...new Set(rows.map((r) => r.period))]);
	const components = [...new Set(rows.map((r) => r.comp))].sort((a, b) => {
		const ia = SCE_COL_PRIORITY.indexOf(a),
			ib = SCE_COL_PRIORITY.indexOf(b);
		return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b, 'ko-KR');
	});
	const byPeriod: Record<string, SceRow[]> = {};
	for (const p of periods) {
		const byLabel = new Map<string, SceRow>();
		for (const r of rows) {
			if (r.period !== p) continue;
			let row = byLabel.get(r.label);
			if (!row) {
				row = { label: r.label, ord: r.ord ?? Number.MAX_SAFE_INTEGER, values: {} };
				byLabel.set(r.label, row);
			}
			row.ord = Math.min(row.ord, r.ord ?? Number.MAX_SAFE_INTEGER);
			row.values[r.comp] = r.val;
		}
		byPeriod[p] = [...byLabel.values()].sort((a, b) => a.ord - b.ord || a.label.localeCompare(b.label, 'ko-KR'));
	}
	return { scope, periods, components, byPeriod, unit: 'KRW' };
}
