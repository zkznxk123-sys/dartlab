// 지수 계약 — 메인 주가차트에 KR gov 지수(OHLCV 캔들) + US FRED 지수(종가 라인)를 subject 로 그리는 포트.
// (terminal-chart-suite/01). 회사 무관 시리즈라 PricePort 오염 방지 차원에서 별도 포트(MacroPort 와 동형 결정).
// KR = gov/indices 완전체 OHLCV(ohlc:'candle') · US = FRED 종가 1컬럼(ohlc:'line', degenerate candle o=h=l=c).
import type { Candle } from './price';

/** 'US' = FRED markets 그룹(종가 전용). KR 3종 = gov/indices MARKET_GROUP(OHLCV 완전체). */
export type IndexMarket = 'KOSPI' | 'KOSDAQ' | 'KRX' | 'US';

export interface IndexRef {
	market: IndexMarket;
	/** KR=gov IDX_NM 원어('코스피 200') · US=한글 라벨('S&P 500'). */
	name: string;
	/** subject 식별자 = `idx:${market}/${seriesKey}`. KR seriesKey=IDX_NM · US seriesKey=FRED seriesId. */
	code: string;
	/** US 전용 — FRED 시리즈 ID(SP500/NASDAQCOM/DJIA/VIXCLS). KR 은 undefined. */
	seriesId?: string;
	/** 렌더 힌트 — 'candle'=OHLCV(KR) · 'line'=종가전용(US, 고저 부재). */
	ohlc?: 'candle' | 'line';
}

export interface IndexPort {
	/** 큐레이트 화이트리스트(상시 노출). KR 5종 + US 4종 = 9종. 전체 dump 아님. */
	catalog(): Promise<IndexRef[]>;
	/** 부분일치 검색. KR=gov IDX_NM universe 스캔 · US=US_INDEX_PRESETS 라벨/ID 매칭(확장 0). */
	search(query: string, limit?: number): Promise<IndexRef[]>;
	/** 일별 시계열 — 구조적 Candle 오름차순. KR=OHLCV · US=종가(o=h=l=c=value, v=0). null=미존재. */
	series(ref: IndexRef): Promise<Candle[] | null>;
}

// KR 큐레이트 5종 — gov/indices 실측 (MARKET_GROUP·IDX_NM 정확 일치 확인). 자체 OHLCV 완전체.
export const KR_INDEX_PRESETS: IndexRef[] = [
	{ market: 'KOSPI', name: '코스피', code: 'idx:KOSPI/코스피', ohlc: 'candle' },
	{ market: 'KOSPI', name: '코스피 200', code: 'idx:KOSPI/코스피 200', ohlc: 'candle' },
	{ market: 'KOSDAQ', name: '코스닥', code: 'idx:KOSDAQ/코스닥', ohlc: 'candle' },
	{ market: 'KOSDAQ', name: '코스닥 150', code: 'idx:KOSDAQ/코스닥 150', ohlc: 'candle' },
	{ market: 'KRX', name: 'KRX 300', code: 'idx:KRX/KRX 300', ohlc: 'candle' }
];

// US 큐레이트 4종 — FRED markets 그룹 중 '주가지수'(unit=Index)만. 원자재/환율/암호화폐는 시장지수 아니라 제외.
// VIXCLS 는 가격 아닌 변동성 지수 → 라벨 'VIX(변동성)' 로 가격 오인 차단.
export const US_INDEX_PRESETS: IndexRef[] = [
	{ market: 'US', name: 'S&P 500', code: 'idx:US/SP500', seriesId: 'SP500', ohlc: 'line' },
	{ market: 'US', name: 'NASDAQ 종합', code: 'idx:US/NASDAQCOM', seriesId: 'NASDAQCOM', ohlc: 'line' },
	{ market: 'US', name: '다우존스', code: 'idx:US/DJIA', seriesId: 'DJIA', ohlc: 'line' },
	{ market: 'US', name: 'VIX(변동성)', code: 'idx:US/VIXCLS', seriesId: 'VIXCLS', ohlc: 'line' }
];

export const INDEX_PRESETS: IndexRef[] = [...KR_INDEX_PRESETS, ...US_INDEX_PRESETS];
