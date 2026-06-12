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

export interface MacroPort {
	/** 화이트리스트 시리즈 정의 (출처 attribution 포함 메타). */
	listSeries(): Promise<MacroSeriesDef[]>;
	getSeries(id: string): Promise<MacroPoint[] | null>;
	getLatest(): Promise<MacroLatest[]>;
}
