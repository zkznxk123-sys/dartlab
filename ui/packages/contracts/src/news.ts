// 뉴스 계약 — 종목별 뉴스 헤드라인(제목+스니펫+원문링크). 터미널 우측패널·주가 이벤트레일 소비.
// 빈값 규약(runtime.ts): [] = 조회 성공·해당 없음(예: 시총 상위 외 종목·미배선·프록시 미설정).
// 출처: 네이버 검색 API archive(언론사 저작권·private). 어댑터는 워커 서버사이드 read 로만 표시(재배포 아님).

/** 뉴스 트랙 — naver=검색 API(스니펫 O) · gdelt=GDELT DOC API(제목+링크) · google=Google News RSS 라이브
 *  (조회시점 최신 헤드라인, 스니펫 없음). 좌우 분리: gdelt=우(과거), 그 외(naver·google)=좌(최근). */
export type NewsTrack = 'naver' | 'gdelt' | 'google';

export interface NewsItem {
	date: string; // YYYY-MM-DD (발행일)
	title: string; // 기사 제목
	source: string; // 언론사/도메인
	url: string; // 원문 링크 (클릭 시 외부 이동)
	description: string; // 스니펫(요약) — gdelt 는 빈 문자열
	track: NewsTrack; // 소스 트랙 (좌우 분리 키)
}

// 시장 전체(cross) 뉴스 헤드라인 — 좌측 터미널 패널. 종목별(NewsItem, 우측패널)과 정반대 멘탈모델:
// 종목 무관·전 시장 시간순·제목+원문링크만(스니펫 없음·stock_code 없음). 클릭=외부 기사 이동.
// 출처: public rss 아카이브(Google News RSS·재배포 가능). naver(저작권 private)는 우측 라이브 read 전용.
export interface MarketNews {
	date: string; // YYYY-MM-DD (발행일)
	title: string; // 기사 제목
	source: string; // 언론사/도메인
	url: string; // 원문 링크 (클릭 시 외부 이동)
}

export interface NewsPort {
	/** 종목별 최근 뉴스 (date 내림차순). 해당 없음·미배선·프록시 미설정은 [].
	 *  name(회사명) 주입 시 워커가 Google News RSS 라이브 헤드라인을 byCompany 아카이브 위에 머지(조회시점 최신). */
	forCompany(code: string, name?: string): Promise<NewsItem[]>;
	/** 시장 전체 최근 뉴스 (date 내림차순, 제목+링크). 좌측 cross 피드. 미배선·실패는 []. */
	market(): Promise<MarketNews[]>;
}
