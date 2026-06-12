// 가격 계약 — landing/src/lib/terminal/data/priceSeries.ts 실타입 승격 (단계-0 census A-1).
// KRX raw 행(ISU_CD 등 원어 컬럼)은 어댑터 내부 비밀 — 계약은 정규화 표면만.

export interface Candle {
	t: string; // YYYYMMDD
	o: number;
	h: number;
	l: number;
	c: number;
	v: number;
	r?: number | null; // 기준가 대비 등락률(%) — 수정주가 체이닝용
	tv?: number | null; // 거래대금(원)
}

export interface CompanyPrices {
	candles: Candle[]; // 오름차순 · 일자 dedup
	oldestYear: number; // 현재까지 로드한 가장 오래된 연도
}

export const KRX_MIN_YEAR = 2010;

export interface PricePort {
	/** 초기 로드 — 해당 연도부터 현재까지. 미존재 회사는 null. */
	initial(code: string, year: number): Promise<CompanyPrices | null>;
	/** 과거 연도 추가 로드 — 해당 없음은 []. */
	older(code: string, targetYear: number): Promise<Candle[]>;
	/** 메모리에 로드된 캔들 동기 조회 — 미로드는 []. */
	loaded(code: string): Candle[];
	/** gov 일배치 캔들 — 미지원/미존재는 null. */
	govCandles(code: string): Promise<Candle[] | null>;
	/** 전 종목 최근 캔들 묶음 (Map 금지 — JSON-safe). 미지원은 null. */
	govRecent(): Promise<Record<string, Candle[]> | null>;
	// liveQuote 는 단계-4a 에서 livePrice.ts 포트화와 함께 추가 (표면 미실측 — 발명 금지).
}
