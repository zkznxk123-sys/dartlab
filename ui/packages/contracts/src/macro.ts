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
	group?: string; // 요인군(정적) — 강상관 시리즈 묶음. UI 가 "같은 요인" 오독 차단용 태그로 표시.
}

export interface MacroLatest {
	def: MacroSeriesDef;
	v: number;
	d: string; // YYYYMMDD
	chg: number | null; // 직전 관측 대비 변화 (단위 동일)
	spark: number[]; // 최근 ~1년 추세 (≤40점 다운샘플)
}

/** 카탈로그 — 주가와 비교 가치가 큰 거시 지표 (HF observations 에 데이터가 실재하는 것만 노출).
 *  MacroPort.listSeries() 정본. 한국(ECOS) → 미국(FRED) 순. ECON_MAX(3) 가 동시표시를 막아 카탈로그가 커도 차트는 깨끗. */
export const MACRO_SERIES: MacroSeriesDef[] = [
	// 한국 (ECOS)
	{ id: 'USDKRW', src: 'ecos', kr: '원/달러', en: 'USD/KRW', unit: '원', digits: 0, group: '환율' },
	{ id: 'JPYKRW', src: 'ecos', kr: '원/100엔', en: 'KRW/100JPY', unit: '원', digits: 1, group: '환율' },
	{ id: 'EURKRW', src: 'ecos', kr: '원/유로', en: 'KRW/EUR', unit: '원', digits: 1, group: '환율' },
	{ id: 'BASE_RATE', src: 'ecos', kr: '한은 기준금리', en: 'BOK rate', unit: '%', digits: 2, group: '한국금리' },
	{ id: 'CPI', src: 'ecos', kr: '소비자물가 YoY', en: 'KR CPI YoY', unit: '%', yoy: true, digits: 1, group: '한국물가' },
	{ id: 'EXPORT', src: 'ecos', kr: '수출 YoY', en: 'Exports YoY', unit: '%', yoy: true, digits: 1, group: '수출' },
	{ id: 'EXPORT_PRICE', src: 'ecos', kr: '수출물가 YoY', en: 'Export px YoY', unit: '%', yoy: true, digits: 1, group: '수출' },
	{ id: 'IPI', src: 'ecos', kr: '산업생산 YoY', en: 'KR IP YoY', unit: '%', yoy: true, digits: 1, group: '한국생산' },
	{ id: 'CLI', src: 'ecos', kr: '경기선행지수', en: 'KR CLI', unit: 'pt', digits: 1, group: '경기·심리' },
	{ id: 'CSI', src: 'ecos', kr: '소비자심리', en: 'KR consumer sentiment', unit: 'pt', digits: 1, group: '경기·심리' },
	{ id: 'M2', src: 'ecos', kr: 'M2 YoY', en: 'KR M2 YoY', unit: '%', yoy: true, digits: 1, group: '통화' },
	{ id: 'HOUSE_PRICE', src: 'ecos', kr: '주택가격 YoY', en: 'KR house px YoY', unit: '%', yoy: true, digits: 1, group: '부동산' },
	{ id: 'PPI_SEMI', src: 'ecos', kr: '반도체 PPI YoY', en: 'KR semi PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	// 업종별 생산자물가 (ECOS) — 종목 업종에 따라 가장 직접적인 가격 드라이버
	{ id: 'PPI_MFG', src: 'ecos', kr: '제조업 PPI YoY', en: 'KR mfg PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_CHEM', src: 'ecos', kr: '화학 PPI YoY', en: 'KR chem PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_STEEL', src: 'ecos', kr: '철강 PPI YoY', en: 'KR steel PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_AUTO', src: 'ecos', kr: '자동차 PPI YoY', en: 'KR auto PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_DISPLAY', src: 'ecos', kr: '디스플레이 PPI YoY', en: 'KR display PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_ELEC', src: 'ecos', kr: '전기전자 PPI YoY', en: 'KR electronics PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_MACHINE', src: 'ecos', kr: '기계 PPI YoY', en: 'KR machinery PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	{ id: 'PPI_OIL', src: 'ecos', kr: '석유 PPI YoY', en: 'KR oil PPI YoY', unit: '%', yoy: true, digits: 1, group: '생산자물가' },
	// 미국 (FRED)
	{ id: 'FEDFUNDS', src: 'fred', kr: '연준 기준금리', en: 'Fed funds', unit: '%', digits: 2, group: '미국금리' },
	{ id: 'DGS2', src: 'fred', kr: '미 2년 금리', en: 'US 2Y', unit: '%', digits: 2, group: '미국금리' },
	{ id: 'DGS10', src: 'fred', kr: '미 10년 금리', en: 'US 10Y', unit: '%', digits: 2, group: '미국금리' },
	{ id: 'DGS30', src: 'fred', kr: '미 30년 금리', en: 'US 30Y', unit: '%', digits: 2, group: '미국금리' },
	{ id: 'T10Y2Y', src: 'fred', kr: '미 장단기차(10Y-2Y)', en: 'US 10Y-2Y', unit: '%p', digits: 2, group: '미국금리' },
	{ id: 'T10Y3M', src: 'fred', kr: '미 장단기차(10Y-3M)', en: 'US 10Y-3M', unit: '%p', digits: 2, group: '미국금리' },
	{ id: 'T10YIE', src: 'fred', kr: '미 기대인플레(10Y)', en: 'US 10Y breakeven', unit: '%', digits: 2, group: '미국물가' },
	{ id: 'CPIAUCSL', src: 'fred', kr: '미 CPI YoY', en: 'US CPI YoY', unit: '%', yoy: true, digits: 1, group: '미국물가' },
	{ id: 'CPILFESL', src: 'fred', kr: '미 근원CPI YoY', en: 'US core CPI YoY', unit: '%', yoy: true, digits: 1, group: '미국물가' },
	{ id: 'PCEPI', src: 'fred', kr: '미 PCE YoY', en: 'US PCE YoY', unit: '%', yoy: true, digits: 1, group: '미국물가' },
	{ id: 'UNRATE', src: 'fred', kr: '미 실업률', en: 'US unemployment', unit: '%', digits: 1, group: '미국고용·생산' },
	{ id: 'PAYEMS', src: 'fred', kr: '미 고용 YoY', en: 'US payrolls YoY', unit: '%', yoy: true, digits: 1, group: '미국고용·생산' },
	{ id: 'INDPRO', src: 'fred', kr: '미 산업생산 YoY', en: 'US IP YoY', unit: '%', yoy: true, digits: 1, group: '미국고용·생산' },
	{ id: 'BAMLH0A0HYM2', src: 'fred', kr: '미 하이일드 스프레드', en: 'US HY spread', unit: '%p', digits: 2, group: '미국신용' },
	{ id: 'BAA10Y', src: 'fred', kr: '미 BAA-10Y 스프레드', en: 'US BAA-10Y', unit: '%p', digits: 2, group: '미국신용' },
	{ id: 'NFCI', src: 'fred', kr: '미 금융상황지수', en: 'US NFCI', unit: 'pt', digits: 2, group: '미국신용' },
	{ id: 'DTWEXBGS', src: 'fred', kr: '달러지수', en: 'US dollar index', unit: 'pt', digits: 1, group: '환율' },
	{ id: 'SP500', src: 'fred', kr: 'S&P 500', en: 'S&P 500', unit: 'pt', digits: 0, group: '미국증시' },
	{ id: 'NASDAQCOM', src: 'fred', kr: '나스닥 종합', en: 'Nasdaq Comp', unit: 'pt', digits: 0, group: '미국증시' },
	{ id: 'VIXCLS', src: 'fred', kr: 'VIX 변동성', en: 'VIX', unit: 'pt', digits: 1, group: '미국증시' },
	{ id: 'DCOILWTICO', src: 'fred', kr: 'WTI 유가', en: 'WTI oil', unit: '$', digits: 1, group: '원자재' },
	{ id: 'PCOPPUSDM', src: 'fred', kr: '구리 가격', en: 'Copper', unit: '$/t', digits: 0, group: '원자재' }
];

/** 출처표시 — 거시 시계열을 표시하는 surface 가 노출해야 하는 계약 상수. */
export const MACRO_ATTRIBUTION = '출처: 한국은행 ECOS · FRED (St. Louis Fed)';

export interface MacroPort {
	/** 화이트리스트 시리즈 정의 (출처 attribution 포함 메타). */
	listSeries(): Promise<MacroSeriesDef[]>;
	getSeries(id: string): Promise<MacroPoint[] | null>;
	getLatest(): Promise<MacroLatest[]>;
}
