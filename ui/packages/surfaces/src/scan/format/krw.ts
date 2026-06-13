/**
 * 한국어 숫자 포맷 — "420조 원", "8,500억", "2.1억", "12만"
 *
 * 원칙:
 *  - 만 단위 (10⁴) 기반 — 한국 컨벤션
 *  - 조 (10¹²) > 억 (10⁸) > 만 (10⁴) > 그 미만은 천 단위 콤마
 *  - 기본 소수점 1자리. 0.x 조는 "8500억" 으로 표기 (한국인 직관)
 *
 * SSOT: 다른 곳에서 KRW 포맷 정의 금지. 여기만 import.
 */

export type KrwOptions = {
	/** 단위 (조/억/만) 표시 여부. false 면 콤마만 */
	withUnit?: boolean;
	/** 소수점 자리수. 기본 1 */
	digits?: number;
	/** "원" 접미 표시. 기본 false (UI 에서는 제외) */
	withWon?: boolean;
};

/** 원(₩) 단위 raw 값 → 한국어 표기 */
export function fmtKrw(value: number | null | undefined, opts: KrwOptions = {}): string {
	if (value == null || !Number.isFinite(value)) return '—';
	const { withUnit = true, digits = 1, withWon = false } = opts;

	const abs = Math.abs(value);
	const sign = value < 0 ? '-' : '';
	const won = withWon ? ' 원' : '';

	if (!withUnit) {
		return `${sign}${Math.round(abs).toLocaleString('ko-KR')}${won}`;
	}

	// 1조 이상
	if (abs >= 1e12) {
		const v = abs / 1e12;
		// toFixed 후 trimZero — 그 다음 정수부에 천단위 콤마 (1283.3조 → 1,283.3조)
		const fixed = trimZero(v.toFixed(digits));
		const [intPart, decPart] = fixed.split('.');
		const intWithComma = Number(intPart).toLocaleString('ko-KR');
		const formatted = decPart ? `${intWithComma}.${decPart}` : intWithComma;
		return `${sign}${formatted}조${won}`;
	}
	// 1억 이상 — "0.X 조" 대신 "X,XXX억" 으로 (한국 직관)
	if (abs >= 1e8) {
		const v = abs / 1e8;
		// 1조 미만이면 정수 억 단위
		const rounded = abs >= 1e10 ? Math.round(v) : parseFloat(v.toFixed(digits));
		return `${sign}${rounded.toLocaleString('ko-KR')}억${won}`;
	}
	// 1만 이상
	if (abs >= 1e4) {
		const v = abs / 1e4;
		const rounded = abs >= 1e6 ? Math.round(v) : parseFloat(v.toFixed(digits));
		return `${sign}${rounded.toLocaleString('ko-KR')}만${won}`;
	}
	// 그 미만 — 천 단위 콤마
	return `${sign}${Math.round(abs).toLocaleString('ko-KR')}${won}`;
}

/** 억 단위 raw 값 → 한국어 표기 (scan/ecosystem 데이터가 억 단위라서) */
export function fmtKrwFromEok(eok: number | null | undefined, opts: KrwOptions = {}): string {
	if (eok == null || !Number.isFinite(eok)) return '—';
	return fmtKrw(eok * 1e8, opts);
}

/** 통화 기호 + 천 단위 콤마 (주가 표기) */
export function fmtPrice(value: number | null | undefined): string {
	if (value == null || !Number.isFinite(value) || value <= 0) return '—';
	return `₩${Math.round(value).toLocaleString('ko-KR')}`;
}

function trimZero(s: string): string {
	return s.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
}
