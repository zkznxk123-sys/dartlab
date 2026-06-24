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

/** 조 단위 raw 값 → 한국어 표기 (FinCard·재무 데이터가 조 단위라서). 각 값이 제 자연 단위를
 *  고르므로 "0.0조" 붕괴가 원천 차단된다 (0.0864조 → "864억"). 표·KPI·문장 셀별 포맷에 사용. */
export function fmtKrwFromJo(jo: number | null | undefined, opts: KrwOptions = {}): string {
	if (jo == null || !Number.isFinite(jo)) return '—';
	return fmtKrw(jo * 1e12, opts);
}

/** from-단위(조/억/만/원) → 원 환산 계수. 통화 아닌 단위는 매핑 없음(undefined). */
const UNIT_TO_WON: Record<string, number> = { 조: 1e12, 억: 1e8, 만: 1e4, 원: 1 };

/** 시리즈/축 단위 스케일 결정 결과. `fmt(v)` 는 from-단위 값 v 를 표시 단위로 환산·포맷(단위 접미 없음). */
export type KrwScale = { unit: string; scale: number; fmt: (v: number) => string };

/**
 * 시리즈/축 단위 스케일 SSOT — 차트 축·표 헤더처럼 **여러 값이 단위 하나를 공유**해야 할 때 사용.
 * from-단위(기본 '조') 값들의 *최대 절댓값* 으로 표시 단위(조/억/만/원)를 한 번 고른다 (fmtKrw 와
 * 같은 규약: 1조↑=조, 1억↑=억 …). 작은 회사(최대 0.8조)는 전체를 억(8,000억)으로 내려 "0.0조" 범벅을
 * 막고, 큰 회사(최대 50조)는 조 유지. 반환 scale = from→표시 환산계수, fmt = 그 단위로 포맷(접미 없음).
 * 통화 아닌 단위(%·배·일)는 항등(scale 1)으로 통과.
 *
 * 셀마다 단위가 달라도 되는 표/KPI 는 이 함수 대신 per-value `fmtKrwFromJo` 를 써라(0.0 완전 차단).
 */
export function pickKrwUnit(values: ReadonlyArray<number | null | undefined>, opts: { from?: string } = {}): KrwScale {
	const from = opts.from ?? '조';
	const base = UNIT_TO_WON[from];
	if (base == null) return { unit: from, scale: 1, fmt: (v) => fmtUnitValue(v, from) }; // 통화 아님 — 항등

	let maxAbs = 0;
	for (const v of values) if (typeof v === 'number' && Number.isFinite(v)) maxAbs = Math.max(maxAbs, Math.abs(v));
	const maxWon = maxAbs * base;

	let unit = '원';
	let unitWon = 1;
	if (maxWon >= 1e12) { unit = '조'; unitWon = 1e12; }
	else if (maxWon >= 1e8) { unit = '억'; unitWon = 1e8; }
	else if (maxWon >= 1e4) { unit = '만'; unitWon = 1e4; }

	const scale = base / unitWon;
	return { unit, scale, fmt: (v) => fmtUnitValue(v * scale, unit) };
}

/** 표시 단위 값(이미 환산됨) → 적응 정밀도 문자열(단위 접미 없음). 100↑=정수콤마, 1↑=1자리, 그 미만=2자리. */
function fmtUnitValue(v: number, _unit: string): string {
	if (!Number.isFinite(v)) return '–';
	const a = Math.abs(v);
	if (a >= 100) return Math.round(v).toLocaleString('ko-KR');
	if (a >= 1) return trimZero(v.toFixed(1));
	return trimZero(v.toFixed(2));
}

/** 통화 기호 + 천 단위 콤마 (주가 표기) */
export function fmtPrice(value: number | null | undefined): string {
	if (value == null || !Number.isFinite(value) || value <= 0) return '—';
	return `₩${Math.round(value).toLocaleString('ko-KR')}`;
}

function trimZero(s: string): string {
	return s.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
}
