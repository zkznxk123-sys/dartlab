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
	panelToc(code: string): Promise<PanelTocResponse | null>;
	panelInit(code: string): Promise<PanelInitResponse | null>;
	panelGrid(code: string, sectionKey: string): Promise<PanelGridResponse | null>;
}
