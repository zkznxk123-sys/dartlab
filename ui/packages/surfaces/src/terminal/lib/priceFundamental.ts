// 가격↔기초체력 지수 오버레이 — 주가·매출·자본을 같은 시작점(=100)으로 리베이스해 한 차트에 겹친다.
// 신규 데이터 0: 이미 로드된 finance 번들(기간 라벨·접수일) + price 캔들을 조인할 뿐이다.
// ★look-ahead 차단(honesty spine): 각 기간의 주가는 그 기간 *공시 접수일* 종가로 샘플 —
// 사업연도 종료 시점이 아니라 그 숫자가 실제로 공표된 날 (미리보기 가격 금지).
import type { Candle, FinCard, Num, TerminalFinance } from '@dartlab/ui-contracts';

const finite = (v: Num): v is number => typeof v === 'number' && Number.isFinite(v);

// 기간 라벨 → (연도, 분기). 'FY23'→{2023,4} · '23Q4'→{2023,4} · '23Q1'→{2023,1}
function parsePeriod(label: string): { year: number; q: number } | null {
	let m = label.match(/^FY(\d{2})$/);
	if (m) return { year: 2000 + +m[1]!, q: 4 };
	m = label.match(/^(\d{2})Q(\d)$/);
	if (m) return { year: 2000 + +m[1]!, q: +m[2]! };
	return null;
}
const Q_END = ['', '0331', '0630', '0930', '1231']; // 접수일 결측 시 분기말 폴백

// 오름차순 캔들에서 t ≤ dateYmd 인 마지막 종가 (공시 시점 가격 — 그 이후 가격은 미리보기라 금지)
function priceAtOrBefore(candles: Candle[], dateYmd: string): number | null {
	for (let i = candles.length - 1; i >= 0; i--) {
		const cd = candles[i];
		if (cd && cd.t <= dateYmd) return cd.c;
	}
	return null;
}

/**
 * 가격↔기초체력 오버레이 카드를 만든다. 주가·매출·자본 모두 첫 공통 유효 기간을 100 으로 정규화.
 *
 * @param view - 현재 모드(연간/분기/TTM)의 재무 뷰 — periods 라벨·statements 값 제공.
 * @param filedDates - `${year}-${q}` → 접수일(YYYYMMDD). 번들에서 직접.
 * @param candles - gov EOD 캔들(오름차순). null/단일점이면 카드 없음(honest-gap).
 * @returns 3선(=100) FinCard 또는 데이터 부족 시 null (→ 카드 비표시).
 *
 * @example
 *   const card = buildPriceFundamentalCard(finData, bundle.filedDates, candles);
 *   if (card) renderMini(card, finData.periods);
 */
export function buildPriceFundamentalCard(
	view: TerminalFinance,
	filedDates: Record<string, string>,
	candles: Candle[] | null
): FinCard | null {
	if (!candles || candles.length < 2) return null;
	const revRow = view.statements.IS.find((r) => r.key === 'revenue');
	const eqRow = view.statements.BS.find((r) => r.key === 'equity');
	if (!revRow || !eqRow) return null;

	// 각 기간의 공시 접수일(없으면 분기말) 종가
	const priceRaw: Num[] = view.periods.map((label) => {
		const pp = parsePeriod(label);
		if (!pp) return null;
		const filed = filedDates[`${pp.year}-${pp.q}`];
		const date = filed && filed.length === 8 ? filed : `${pp.year}${Q_END[pp.q]}`;
		return priceAtOrBefore(candles, date);
	});
	const rev = revRow.values;
	const eq = eqRow.values;

	// 기준(=100) = 주가·매출·자본 모두 유효한 첫 기간
	let base = -1;
	for (let i = 0; i < view.periods.length; i++) {
		if (finite(priceRaw[i]) && finite(rev[i]) && finite(eq[i])) { base = i; break; }
	}
	if (base < 0) return null;
	const idx = (arr: Num[]): Num[] => {
		const b = arr[base];
		if (!finite(b) || b === 0) return arr.map(() => null);
		return arr.map((v) => (finite(v) ? +((v / b) * 100).toFixed(1) : null));
	};
	const priceIdx = idx(priceRaw);
	if (priceIdx.filter(finite).length < 2) return null; // 단일 가격점 = 추세 무의미

	return {
		key: 'priceVsFundamentals',
		title: '가격 vs 기초체력 (=100)',
		unit: '=100',
		refLines: [100],
		series: [
			{ name: '주가', data: priceIdx, color: '#e879a6', type: 'line' },
			{ name: '매출', data: idx(rev), color: '#5b9bf0', type: 'line' },
			{ name: '자본', data: idx(eq), color: '#34d399', type: 'line' }
		]
	};
}
