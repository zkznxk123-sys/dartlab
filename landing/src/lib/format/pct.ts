/**
 * 퍼센트·비율·등락 포맷
 * 한국 관습: 부호 명시 (+/-) · 기본 소수점 1자리 · 0.0% 도 "0.0%" (빈 칸 X)
 */

export type PctOptions = {
	digits?: number;
	withSign?: boolean; // +12.3 / -4.5 식
	suffix?: string; // 기본 '%'
};

export function fmtPct(value: number | null | undefined, opts: PctOptions = {}): string {
	if (value == null || !Number.isFinite(value)) return '—';
	const { digits = 1, withSign = false, suffix = '%' } = opts;
	const sign = withSign && value > 0 ? '+' : '';
	return `${sign}${value.toFixed(digits)}${suffix}`;
}

/** 등락률 — 부호 + 색 toned, 0 이면 flat */
export function pctTone(value: number | null | undefined): 'up' | 'down' | 'flat' | 'unknown' {
	if (value == null || !Number.isFinite(value)) return 'unknown';
	if (value > 0.001) return 'up';
	if (value < -0.001) return 'down';
	return 'flat';
}

/** 배수 (X.Xx) — Altman Z, 이자보상배율 등 */
export function fmtMul(value: number | null | undefined, digits = 2): string {
	if (value == null || !Number.isFinite(value)) return '—';
	return `${value.toFixed(digits)}x`;
}
