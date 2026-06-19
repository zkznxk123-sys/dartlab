// 공시 계약 — companyFilingsRuntime·companyNonRegularFilings + viewer panel HTTP 표면 승격 (census A-7·A-8·C).
// 시장 고유 식별자 규칙(02 §3): rceptNo 는 DART 네임스페이스 — 이벤트화 시 `dart:${rceptNo}` (EDGAR 는 accessionNo).

export interface RegularFiling {
	rceptNo: string;
	rceptDate: string; // YYYY-MM-DD
	reportType: string; // '사업보고서' | '반기보고서' | '분기보고서' | '정기보고서'
	year: string;
	url: string; // dart.fss.or.kr 뷰어 URL
}

export interface NonRegularFiling {
	rceptNo: string;
	rceptDate: string; // YYYY-MM-DD
	reportNm: string;
	filer: string;
	url: string;
}

// 시장 공시 피드 — 전상장사 수시공시 시간순(market_recent.parquet). 우측 단일기업(NonRegularFiling)과
// 달리 행마다 회사가 바뀌므로 stockCode·corpName 보유(회사명이 피드 1순위 정보). category 는 클라
// 분류(marketFeedCategory, report_nm 기반)라 계약에 두지 않는다 — 원본 reportNm 으로 UI 가 분류.
export interface MarketFiling {
	rceptNo: string;
	rceptDate: string; // YYYY-MM-DD
	stockCode: string;
	corpName: string;
	reportNm: string;
	filer: string;
	url: string;
}

// ── panel (공시뷰어 격자) — ui/web HTTP 판 기준 + leafType superset (landing↔ui/web 발산 1건 해소: 계약은 superset) ──

export interface PanelTocBlock {
	blockLeaf: string;
	leafType: string | null;
	disclosureKey: string | null;
}

export interface PanelTocSection {
	sectionLeaf: string;
	sectionKey: string; // `${chapter}␟${sectionLeaf}`
	blocks: PanelTocBlock[];
}

export interface PanelTocChapter {
	chapter: string;
	sections: PanelTocSection[];
}

export interface PanelTocResponse {
	stockCode: string;
	corpName: string;
	chapters: PanelTocChapter[];
	periods: string[];
}

export interface PanelRow {
	chapter: string;
	sectionLeaf: string;
	blockLeaf: string;
	leafType: string | null;
	disclosureKey: string | null; // null = narrative
	scope: string | null;
	blockType: 'text' | 'table';
	cells: Record<string, string>; // period → raw DART XML (무손실)
}

export interface PanelGridResponse {
	stockCode: string;
	corpName: string;
	chapter: string;
	sectionLeaf: string;
	sectionKey: string;
	periods: string[];
	rows: PanelRow[];
	dartUrlByPeriod?: Record<string, string>;
}

export interface PanelInitResponse {
	stockCode: string;
	corpName: string;
	toc: PanelTocResponse;
	firstChapter: string;
	firstSectionKey: string;
	grid: PanelGridResponse;
}

export interface FilingPort {
	/** 정기공시 목록 — 해당 없음은 []. */
	regular(code: string, limit?: number): Promise<RegularFiling[]>;
	/** 비정기공시 목록 — 해당 없음은 []. */
	nonRegular(code: string, limit?: number): Promise<NonRegularFiling[]>;
	/** 워치 신선도용 — 여러 종목의 수시공시(allFilings)를 한 번에 읽어 code→목록. 공개/로컬 공통배선(HF 직독, 백엔드 0). 미존재는 {}. */
	recentForCodes(codes: string[]): Promise<Record<string, NonRegularFiling[]>>;
	/** 전상장사 시장 공시 피드 — 최근 3개월 수시공시 rcept_dt 내림차순(market_recent.parquet 통파일 1 GET). 공개/로컬 공통배선. 미존재는 []. */
	marketFeed(): Promise<MarketFiling[]>;
	panelToc(code: string): Promise<PanelTocResponse | null>;
	panelInit(code: string): Promise<PanelInitResponse | null>;
	panelGrid(code: string, sectionKey: string): Promise<PanelGridResponse | null>;
}
