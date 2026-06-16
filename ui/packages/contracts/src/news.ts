// 뉴스 계약 — 종목별 뉴스 헤드라인(제목+스니펫+원문링크). 터미널 우측패널·주가 이벤트레일 소비.
// 빈값 규약(runtime.ts): [] = 조회 성공·해당 없음(예: 시총 상위 외 종목·미배선·프록시 미설정).
// 출처: 네이버 검색 API archive(언론사 저작권·private). 어댑터는 워커 서버사이드 read 로만 표시(재배포 아님).

export interface NewsItem {
	date: string; // YYYY-MM-DD (발행일)
	title: string; // 기사 제목
	source: string; // 언론사/도메인
	url: string; // 원문 링크 (클릭 시 외부 이동)
	description: string; // 스니펫(요약) — 빈 문자열 가능
}

export interface NewsPort {
	/** 종목별 최근 뉴스 (date 내림차순). 해당 없음·미배선·프록시 미설정은 []. */
	forCompany(code: string): Promise<NewsItem[]>;
}
