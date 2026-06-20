// 표시 포맷 헬퍼 — 재무 값은 모두 조(兆) KRW 단위(StmtRow.values 계약). 단위는 표별 자동 스케일.
import type { Num } from '@dartlab/ui-contracts';

/** 기간 라벨 → 4자리 연도 컬럼 ('FY23' → '2023'). 분기 라벨은 그대로. */
export function pYear(label: string): string {
	const m = /^FY(\d{2})$/.exec(label);
	if (m) return `20${m[1]}`;
	return label;
}

export function fmtPct(v: Num, digits = 1): string {
	if (v == null || !Number.isFinite(v)) return '-';
	return `${(v as number).toFixed(digits)}%`;
}

export function fmtPctSigned(v: Num, digits = 1): string {
	if (v == null || !Number.isFinite(v)) return '-';
	const n = v as number;
	return `${n > 0 ? '+' : ''}${n.toFixed(digits)}%`;
}

export function fmtMult(v: Num, digits = 2): string {
	if (v == null || !Number.isFinite(v)) return '-';
	return `${(v as number).toFixed(digits)}배`;
}

/** 단일 금액(조 단위 값) → 조/억 자동. KPI·문장용. */
export function fmtAmt1(v: Num): string {
	if (v == null || !Number.isFinite(v)) return '-';
	const n = v as number;
	const a = Math.abs(n);
	if (a >= 1) return `${n.toFixed(1)}조`;
	if (a > 0) return `${Math.round(n * 10000).toLocaleString('en-US')}억`;
	return '0';
}

/** 조 단위 값 묶음 → 표 전체 단일 스케일 선택. */
export function scaleAmt(values: Num[]): { unit: string; scale: number } {
	const nums = values.filter((v): v is number => v != null && Number.isFinite(v)).map(Math.abs);
	const maxAbs = nums.length ? Math.max(...nums) : 0;
	if (maxAbs >= 1) return { unit: '조원', scale: 1 };
	if (maxAbs > 0) return { unit: '억원', scale: 10000 };
	return { unit: '조원', scale: 1 };
}

export function fmtScaled(v: Num, scale: number): string {
	if (v == null || !Number.isFinite(v)) return '-';
	return ((v as number) * scale).toFixed(1);
}
