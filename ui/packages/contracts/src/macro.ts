// 거시 계약 — landing macroSeries.ts 승격 (census A-5, 단계-0 결정: MacroPort 신설 — 회사 무관 시리즈라 PricePort 오염 방지).

export interface MacroPoint {
	d: string; // YYYYMMDD
	v: number;
}

export interface MacroSeriesDef {
	id: string;
	src: 'fred' | 'ecos';
	kr: string;
	en: string;
	unit: string; // '원' | '%' | '%p' | 'yoy%' | '$/t' | 'pt'
	yoy?: boolean; // true = 12개월 전 대비 % 변환 표시
	digits?: number; // 최신값 표시 소수 자리
}

export interface MacroLatest {
	def: MacroSeriesDef;
	v: number;
	d: string; // YYYYMMDD
	chg: number | null; // 직전 관측 대비 변화 (단위 동일)
	spark: number[]; // 최근 ~1년 추세 (≤40점 다운샘플)
}

/** 화이트리스트 — 주가와 비교 가치가 큰 핵심 지표만 (덕지덕지 방지). MacroPort.listSeries() 의 정본 카탈로그. */
export const MACRO_SERIES: MacroSeriesDef[] = [
	{ id: 'USDKRW', src: 'ecos', kr: '원/달러', en: 'USD/KRW', unit: '원', digits: 0 },
	{ id: 'BASE_RATE', src: 'ecos', kr: '한은 기준금리', en: 'BOK rate', unit: '%', digits: 2 },
	{ id: 'CPI', src: 'ecos', kr: '소비자물가 YoY', en: 'KR CPI YoY', unit: '%', yoy: true, digits: 1 },
	{ id: 'EXPORT', src: 'ecos', kr: '수출 YoY', en: 'Exports YoY', unit: '%', yoy: true, digits: 1 },
	{ id: 'CLI', src: 'ecos', kr: '경기선행지수', en: 'KR CLI', unit: 'pt', digits: 1 },
	{ id: 'DGS10', src: 'fred', kr: '미국 10Y 금리', en: 'US 10Y', unit: '%', digits: 2 },
	{ id: 'FEDFUNDS', src: 'fred', kr: '연준 기준금리', en: 'Fed funds', unit: '%', digits: 2 },
	{ id: 'T10Y2Y', src: 'fred', kr: '미 장단기차(10Y-2Y)', en: 'US 10Y-2Y', unit: '%p', digits: 2 },
	{ id: 'CPIAUCSL', src: 'fred', kr: '미 CPI YoY', en: 'US CPI YoY', unit: '%', yoy: true, digits: 1 },
	{ id: 'PCOPPUSDM', src: 'fred', kr: '구리 가격', en: 'Copper', unit: '$/t', digits: 0 }
];

/** 출처표시 — 거시 시계열을 표시하는 surface 가 노출해야 하는 계약 상수. */
export const MACRO_ATTRIBUTION = '출처: 한국은행 ECOS · FRED (St. Louis Fed)';

export interface MacroPort {
	/** 화이트리스트 시리즈 정의 (출처 attribution 포함 메타). */
	listSeries(): Promise<MacroSeriesDef[]>;
	getSeries(id: string): Promise<MacroPoint[] | null>;
	getLatest(): Promise<MacroLatest[]>;
}
