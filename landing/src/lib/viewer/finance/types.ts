// 정량재무제표 다이얼로그 데이터 계약 — dart/finance(공식 OpenDART) parquet 을 DuckDB-WASM 으로 pivot 한 결과.

export type FinanceKind = 'IS' | 'BS' | 'CF' | 'CIS' | 'SCE'; // 손익·재무상태·현금흐름·포괄손익·자본변동
export type FinanceFreq = 'annual' | 'quarter' | 'cumulative'; // 연간 / 분기(단독) / 누적(YTD)
export type FinanceScope = 'CFS' | 'OFS'; // 연결 / 개별(별도)

export interface FinanceStmtRow {
	accountId: string; // account_id (기간 정합 pivot 키)
	label: string; // account_nm (표시)
	ord: number; // 재무제표 표시순서
	values: Record<string, number | null>; // period → 금액(원). null = 해당기간 미보고
}

export interface FinanceStatement {
	kind: FinanceKind;
	scope: FinanceScope;
	freq: FinanceFreq;
	periods: string[]; // 최신좌측 (YYYY 또는 YYYYQn)
	rows: FinanceStmtRow[];
	unit: string; // 'KRW'(원) / 'USD'
}

// statement 별 가용 빈도 — BS(시점)는 누적 없음, SCE 는 연간 위주.
export const FREQ_BY_KIND: Record<FinanceKind, FinanceFreq[]> = {
	IS: ['annual', 'quarter', 'cumulative'],
	CIS: ['annual', 'quarter', 'cumulative'],
	CF: ['annual', 'cumulative'],
	BS: ['annual', 'quarter'],
	SCE: ['annual', 'cumulative']
};

export const KIND_LABELS: Record<FinanceKind, string> = {
	IS: '손익계산서',
	BS: '재무상태표',
	CF: '현금흐름표',
	CIS: '포괄손익',
	SCE: '자본변동표'
};
export const FREQ_LABELS: Record<FinanceFreq, string> = { annual: '연간', quarter: '분기', cumulative: '누적' };
export const SCOPE_LABELS: Record<FinanceScope, string> = { CFS: '연결', OFS: '개별' };
