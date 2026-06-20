// 검색 계약 — 회사 검색 인덱스 행 승격 (census A-11 IndexRow).
// 단계-0 실측: /search route 는 블로그 검색(콘텐츠) — 제품 검색의 실체는 terminal LeftRail·map 내장
// 인덱스 + viewer 본문 인덱스 두 갈래. 본 포트는 회사 인덱스 공급 담당 (본문 검색은 viewer surface 내부).
import type { Num } from './runtime';

export interface IndexRow {
	stockCode: string;
	corpName: string;
	industry: string;
	stage?: string;
	revenue: Num;
}

export interface SearchQuery {
	text: string;
	limit?: number;
}

export interface SearchResultPage {
	hits: IndexRow[];
	total: number;
}

/** 공시 본문 검색 결과 1행 — 전역 코퍼스(DART+EDGAR+뉴스) BM25 hit. 행 클릭 = 관련 회사로 점프. */
export interface FilingHit {
	rceptNo: string;
	corpName: string;
	/** 점프 키 — 종목 active 전환·viewer 딥링크. 없으면(뉴스 등) 회사 점프 불가. */
	stockCode: string;
	reportNm: string;
	rceptDt: string;
	snippet: string;
	source: string;
	sourceRef: string;
	score: number;
}

export interface FilingSearchQuery {
	text: string;
	limit?: number;
}

export interface SearchPort {
	/** 전 종목 인덱스 — 회사 검색·유니버스 공용. */
	universe(): Promise<IndexRow[]>;
	query(input: SearchQuery): Promise<SearchResultPage>;
	/** 전역 공시 본문 검색 — 질의어 postings + top-k meta 만 HTTP range fetch(서버리스·exact BM25). */
	queryFilings(input: FilingSearchQuery): Promise<FilingHit[]>;
	/** 검색 인덱스 빌드시점(ISO) — as-of 정직 라벨용. manifest 만 읽어 콜드 stats 강제 안 함. 미존재는 null. */
	indexBuiltAt(): Promise<string | null>;
}
