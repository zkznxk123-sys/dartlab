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

export interface SearchPort {
	/** 전 종목 인덱스 — 회사 검색·유니버스 공용. */
	universe(): Promise<IndexRow[]>;
	query(input: SearchQuery): Promise<SearchResultPage>;
}
