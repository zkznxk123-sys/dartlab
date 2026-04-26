/**
 * Screener (스크리너) — 공유 타입 정의.
 *
 * /screener 라우트가 ecosystem.json + quarters.json + prices-snapshot.json +
 * industryStats.json + meta.json + movers.json 을 병렬 fetch 후 stockCode 로
 * join 한 통합 노드를 생성한다. 모든 메트릭은 단일 객체 평면 키로 노출되어
 * 필터·정렬이 동일 인터페이스로 작동한다.
 */

export type Op = '>=' | '<=' | '==' | '!=' | 'between';

/** 단일 필터 조건. between 일 때는 value2 도 사용. */
export interface Cond {
	metric: MetricKey;
	op: Op;
	value: number | string;
	value2?: number | string;
}

/** 정렬 키 + 방향. */
export interface SortKey {
	key: MetricKey;
	dir: 'asc' | 'desc';
}

/** 메트릭 그룹 — 셀렉터 카테고라이즈용. */
export type MetricGroup =
	| 'identity'
	| 'income'
	| 'changes'
	| 'health'
	| 'governance'
	| 'quality'
	| 'workforce'
	| 'price'
	| 'derived'
	| 'quarterly'
	| 'composite';

/** 메트릭 정의 — UI 셀렉터 + 포맷터 + 정렬 보조. */
export interface MetricDef {
	key: MetricKey;
	label: string;
	group: MetricGroup;
	/** 'number' = 슬라이더/연산자 가능, 'text' = ==/!= 만, 'enum' = 칩 다중선택. */
	type: 'number' | 'text' | 'enum';
	/** 단위 ('원', '억', '%', '%p', '명', '배', '점' 등). type=number 한정. */
	unit?: string;
	/** enum 값들 (type=enum 한정). */
	values?: readonly string[];
	/** 표시 시 부호 표시 (Δ 메트릭). */
	signed?: boolean;
	/** 큰 값일수록 좋음 (true) / 작을수록 좋음 (false) — 색 코딩용. */
	higherBetter?: boolean;
}

/** 모든 가능한 메트릭 키 (식별 8 + 정량 16 + 정성 9 + 가격 11 + derived 8 + 분기 5 + composite 4 = 50+) */
export type MetricKey =
	// 식별 (필터 가능, text)
	| 'id'
	| 'label'
	| 'industry'
	| 'industryName'
	| 'stage'
	| 'role'
	| 'stream'
	| 'industryRank'
	| 'industryPeerCount'
	// 손익 정량
	| 'revenue'
	| 'opMargin'
	| 'roe'
	| 'revenueYoyPct'
	| 'revCagr'
	// 변화 (Δ)
	| 'roeDelta'
	| 'opMarginDelta'
	| 'debtRatioDelta'
	// 재무건전성
	| 'debtRatio'
	| 'icr'
	| 'profGrade'
	| 'debtGrade'
	| 'growthGrade'
	// 거버넌스
	| 'govGrade'
	| 'holderPct'
	| 'holderChange'
	| 'stability'
	// 이익질·현금흐름
	| 'qualGrade'
	| 'liqGrade'
	| 'cfPattern'
	| 'auditRisk'
	| 'capClass'
	// 인적·점유율
	| 'empCount'
	| 'marketShare'
	| 'confidence'
	// 가격·시총 (prices-snapshot)
	| 'currentPrice'
	| 'marketCap'
	| 'return1m'
	| 'return3m'
	| 'return1y'
	| 'volatility1y'
	| 'week52High'
	| 'week52Low'
	| 'volumeAvg30d'
	| 'foreignPct'
	| 'beta'
	// derived (frontend 계산, PR-2 에서 활성)
	| 'per'
	| 'pbr'
	| 'psr'
	| 'ev'
	| 'earningsYield'
	| 'fcfYield'
	| 'ebitYield'
	| 'roic'
	// 가격 시계열 derived (DuckDB 가 KRX 일별 query — PR-3)
	| 'currentVsMA20'
	| 'drawdown60d'
	| 'recovery60d'
	// 분기 derived (frontend, PR-2)
	| 'qoqRevenueGrowth'
	| 'qoqOpProfitGrowth'
	| 'lastQuartersProfitable'
	| 'revenueAcceleration'
	| 'turnaroundFlag'
	// composite (frontend, PR-2)
	| 'piotroskiF'
	| 'altmanZ'
	| 'beneishM'
	| 'magicFormulaRank';

/** 통합 노드 — ecosystem + prices + quarters 를 join 한 결과. */
export interface ScreenerNode {
	id: string;
	label: string;
	industry: string;
	industryName?: string;
	color?: string;
	[key: string]: unknown;
}

/** 가격 스냅샷 (prices-snapshot.json 의 회사별 항목). */
export interface PriceSnapshot {
	currentPrice: number | null;
	marketCap: number | null;
	return1m: number | null;
	return3m: number | null;
	return1y: number | null;
	volatility1y: number | null;
	week52High: number | null;
	week52Low: number | null;
	volumeAvg30d: number | null;
	foreignPct: number | null;
	beta: number | null;
	priceUpdated: string | null;
}

/** prices-snapshot.json 의 최상위 구조. */
export interface PricesSnapshotFile {
	schemaVersion: number;
	builtAt: string;
	lookbackDays: number;
	count: number;
	data: Record<string, PriceSnapshot>;
}

/** URL 쿼리 직렬화 페이로드. */
export interface QueryPayload {
	/** 산업 ID 다중선택 (OR). */
	i: string[];
	/** 필터 조건 (AND). */
	c: Cond[];
	/** 정렬 (다중). 첫 항목이 1차 정렬. */
	s: SortKey[];
	/** 활성 프리셋 ID (있으면 PresetCard 강조). */
	p?: string;
}
