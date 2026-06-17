// 회사 계약 — productIndexRuntime·relations·companyLive 실타입 승격 (census A-4·A-6·A-9).
// parquet 한글 원어 컬럼(종목코드 등)은 어댑터에서 camel 정규화 — 계약은 정규화 표면만.
// recent/pin 류 워크스페이스 상태는 CompanyPort 가 아니라 storage 네임스페이스 키 (storage.ts).

export interface ProductIndexItem {
	product: string;
	productRaw: string;
	latestPeriod: string;
	homepage?: string;
	industry?: string;
	ceo?: string;
	fiscalMonth?: string; // 예: '12월'
	listedDate?: string; // YYYY-MM-DD
	region?: string; // 예: '경기도'
}

export interface RelEdge {
	stockCode: string;
	corpName: string;
	product?: string;
	ratio?: number | null;
	amount?: number | null;
	confidence?: number | null;
}

export interface BlogVerdict {
	verdict?: string;
	direction?: string;
	confidence?: string;
	strengths?: string[];
	weaknesses?: string[];
}

export interface CompanyRelations {
	suppliers: RelEdge[]; // top 8
	customers: RelEdge[]; // top 8
	peers: RelEdge[]; // top 6
	neighborCount: number;
	blog: BlogVerdict | null;
}

export interface LiveCompanyReportFact {
	key: 'dividend' | 'treasuryStock' | 'executive' | 'auditOpinion' | 'majorHolder' | 'corporateBond';
	label: string;
	value: string;
	detail: string;
	source: string;
}

/** profit-pool 격자 원자료 — map/industries/{id}.json 의 stages[].nodes[] (rollup 은 surface 책임). */
export interface ProfitPoolNodeRaw {
	revenue?: number | null;
	opMargin?: number | null;
}
export interface ProfitPoolStageRaw {
	key?: string;
	name?: string;
	stream?: string | null;
	nodes?: ProfitPoolNodeRaw[];
}

export interface CompanyPort {
	/** 단일 회사 제품/프로필 항목 — 미존재는 null. */
	products(code: string): Promise<ProductIndexItem | null>;
	/** 전 종목 인덱스 (Map 금지 — JSON-safe). 미지원은 null. */
	productIndex(): Promise<Record<string, ProductIndexItem> | null>;
	relations(code: string): Promise<CompanyRelations | null>;
	/** 라이브 보고서 팩트 6종 — 해당 없음은 []. */
	reportFacts(code: string): Promise<LiveCompanyReportFact[]>;
	/** 산업 profit-pool stage 원자료 (map/industries/{id}.json) — 미존재/미지원은 null. rollup 은 소비 surface. */
	industryProfitPool(industryId: string): Promise<ProfitPoolStageRaw[] | null>;
}
