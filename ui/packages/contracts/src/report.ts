// 사업보고서 파생 시리즈 계약 — landing reportSeries.ts 10종 승격 (census A-3, 단계-0 결정: ReportPort 분리).
// 빈값 규약: null = 해당 데이터셋 미존재/미공시. 필드 단위 null 의미는 각 주석 (예: AuditFeeYear.nonAuditFee 0=계약 없음 / null=미공시).
import type { Num } from './runtime';

export interface WorkforceYear {
	year: string;
	total: Num;
	male: Num;
	female: Num;
	regular: Num;
	contract: Num;
	avgSalary: Num; // 원/인 (급여총액/총원)
	totalSalary: Num; // 원
	tenure: Num; // 평균 근속연수
}

export interface InvestmentRow {
	name: string;
	purpose: string;
	stakePct: Num;
	bookValue: Num; // 원
	acquiredAmt: Num; // 원 (최초취득)
	targetNet: Num; // 피출자사 당기순이익 (원)
}

export interface InvestmentsView {
	year: string;
	rows: InvestmentRow[]; // 전체 출자사 (장부가 desc) — 인라인 스크롤·출자 다이얼로그 단일 소스
	moreCount: number; // 현재 0 (rows 가 전체) — 계약 호환 유지
	moreBook: number; // 현재 0 (원) — 계약 호환 유지
}

export interface InvestmentTrendYear {
	year: string;
	bookTotal: Num; // 합계행 장부가 (원)
	count: number; // 유효 개별 출자사 수
}

// 기간별 피출자사 스냅샷 — 시간축(연도/분기) 그래프·재생용. latest 와 동일 소스(보고된 (year,quarter)).
export interface InvestmentPeriod {
	year: string;
	quarter: string; // '1분기'|'2분기'|'3분기'|'4분기' (보고서종류; 4분기=사업보고서). 소비처가 year+quarter 로 라벨 포맷
	rows: InvestmentRow[]; // 그 기간 전체 피출자사 (장부가 desc)
}

export interface InvestmentsBundle {
	latest: InvestmentsView;
	trend: InvestmentTrendYear[]; // 연도 오름차순
	periods: InvestmentPeriod[]; // 보고된 (year,quarter) 오름차순 — 시간축. latest/trend 와 동일 소스
}

export interface OwnershipYear {
	year: string;
	majorPct: Num; // 최대주주측 합산 지분율 %
	minorPct: Num; // 소액주주 지분율 %
	minorCount: Num; // 소액주주 수 (명)
	stockTotal: Num; // 총발행주식수 (주)
}

// 최대주주 개별 행 — 역방향 소유("누가 이 회사를 소유하나"). 개인은 개인정보·동명이인 가드로 익명 집계(실명 미노출).
export type ShareholderKind = 'institution' | 'corp' | 'gov' | 'treasury' | 'person';
export interface ShareholderRow {
	name: string; // 기관·법인·정부·자기주식 실명 (개인은 named 에 넣지 않음 — person 집계로)
	relate: string; // canonical 관계 라벨 (원문 자유문자열 정규화). 미상 = ''
	ratio: Num; // 지분율 %
	shares: Num; // 보유 주식수
	kind: ShareholderKind;
	code: string | null; // 법인주주 상장 해소 시 종목코드 (클릭 이동) — 소비처가 lookupListed 로 채움
}
export interface PersonAggregate {
	count: number; // 특수관계인 개인 수
	ratio: Num; // 개인 지분율 합 %
	shares: Num; // 개인 보유주식 합
}
export interface ShareholdersView {
	year: string;
	quarter: string; // '1분기'|'2분기'|'3분기'|'4분기' — year 와 함께 기간키(시간축 매칭). 기존 단일 뷰는 최신기
	named: ShareholderRow[]; // 기관·법인·정부·자기주식 (실명, 지분 desc)
	person: PersonAggregate | null; // 개인 익명 집계 (1줄). 개인 없으면 null
	totalPct: Num; // 최대주주측 합산 지분율 (계행) — 정합 검증용
}

export interface ExecBoardYear {
	year: string;
	execAvgPay: Num; // 이사·감사 1인평균 보수 (원)
	execTotalPay: Num; // 보수총액 (원)
	execCount: Num;
	directors: Num;
	outsideDirectors: Num;
}

export interface DebtProfileYear {
	year: string;
	bond1y: Num; // 사채 잔존만기 1년이하 (원)
	bond1to5: Num;
	bond5to10: Num;
	bond10plus: Num;
	bondTotal: Num;
	stb: Num; // 단기사채 미상환 (원)
	cp: Num; // CP 미상환 (원)
}

export interface DebtLadder {
	year: string; // 2% 검산 통과한 최신 연도
	buckets: Num[]; // 7버킷 (원): ≤1y · 1~2y · 2~3y · 3~4y · 4~5y · 5~10y · 10y+
	shortTerm: Num; // 전단채+CP 합계 (원)
}

export interface DebtProfileBundle {
	years: DebtProfileYear[]; // 연도 오름차순
	ladder: DebtLadder | null; // 검산 통과 연도 없으면 null
}

export interface ShareholderReturnYear {
	year: string;
	dps: Num; // 주당 현금배당금 (원, 보통주)
	eps: Num; // 주당순이익 (원) — (연결) 우선
	totalDividend: Num; // 원
	payoutPct: Num;
	yieldPct: Num;
	buybackQty: Num; // 자사주 취득 (주, 보통주 총계)
	disposalQty: Num;
	buybackCancel: Num; // 소각 (주)
	treasuryEnd: Num; // 기말 보유 (주)
}

export interface CapitalChangeEvent {
	date: string; // 발행(감소)일자 공시 원문 (예: '2025.08.21')
	year: number;
	kind: 'paidIn' | 'conversion' | 'reduction';
	type: string; // 발행(감소)형태 원문
	qty: number; // 주 — 감자·소각은 음수
}

export interface DilutionYear {
	year: number;
	paidIn: Num;
	conversion: Num;
	reduction: Num; // 음수, 주
}

export interface CapitalChangesBundle {
	events: CapitalChangeEvent[]; // 일자 오름차순 — 주가차트 마커 연결용
	years: DilutionYear[]; // 연도 합산 — 희석 이력 카드용
}

export interface AuditYear {
	year: number; // 사업연도 (= 사업보고서 접수연도 − 1)
	auditor: string;
	opinion: string | null; // 적정/한정/부적정/의견거절 표준화 — 미기재 null
	special: string | null;
}

export interface TopExecPayRow {
	name: string;
	title: string;
	pay: number; // 보수총액 (원)
}

export interface TopExecPay {
	year: string;
	avgPay: Num; // 같은 연도 이사·감사 1인평균 보수 (원)
	rows: TopExecPayRow[]; // 보수 내림차순 top 8
}

export interface AuditFeeYear {
	year: number;
	auditFee: Num; // 감사용역 계약보수 (원)
	nonAuditFee: Num; // 비감사용역 보수 합 (원) — 계약 없으면 0, 미공시 null
}

// 밸류에이션 스냅샷 행 — dart/scan/valuation.parquet (네이버 per/pbr, 전 종목 1행/종목, snapshotAt 일 1회).
// 동종업종 밸류에이션 *좌표*용(자기역사 PER 과 정의·시점 분리). null = 적자·미산출(네이버가 결손사 null 처리).
export interface ValuationRow {
	per: Num; // 주가수익비율 (TTM 연결 EPS 기준, 네이버 표준)
	pbr: Num; // 주가순자산비율
	marketCap: Num; // 시가총액(원)
}
// stockCode → ValuationRow. 전 종목 1파일(소형) — 동종 분포·주체 위치를 조회 시점 계산.
export type ValuationSnapshot = Record<string, ValuationRow>;

/** 정기보고서 주석 블록 — panel 파케 본문(contentRaw, DART XML 표/텍스트)을 *그 자리에서* 렌더하는 단위.
 * ↗원문 링크가 아니라 실제 주석 내용을 우측 패널에 표면화(PRD 00 §26 "갇힌 계산을 있는 그대로 표면화").
 * content = raw DART XML/HTML — 소비측(CellContent)이 sanitize·표/텍스트 분리 렌더. 신규 분석 0, 표면화만. */
/** 주석 표 파싱 구성요소 — 항목별 금액·비중%. 비용 성격별·부문 같은 *정형 숫자표*(부분합 닫힌 100%) 파싱 결과. */
export interface CompositionItem {
	name: string; // 항목명 (원문 그대로 — 예 '원재료 및 상품매입액')
	amount: number; // 원 (당기 컬럼)
	pct: number; // % of total (0~100)
}
export interface NoteComposition {
	items: CompositionItem[]; // 금액 desc, 상위 topN + '기타 (N)' 롤업
	total: number; // 원 — 합계(분모)
}

export interface ReportNoteBlock {
	key: string; // 안정 식별자 (disclosureKey + 순서)
	topic: string; // 토픽 id (costNature·segment·contingency·affiliates·relatedParty) — 소비측 평어 라벨 매핑
	title: string; // 주석 제목 (blockLeaf 또는 sectionLeaf) — 원문 그대로(보조 표시)
	section: string; // 상위 섹션 (예 '3. 연결재무제표 주석') — scope(연결/별도) 동적 도출 소스
	content: string; // 본문 raw DART XML/HTML (표·텍스트) — CellContent 가 렌더(서술혼합 폴백)
	composition?: NoteComposition; // 정형 숫자표 파싱 성공 시(비용성격별·부문). 실패=undefined → content 발췌 폴백
	rceptNo: string; // 출처 공시 번호 (↗원문)
	period: string; // 기준 분기 (YYYYQn)
}

// ── 비용의 성격별 분류 시계열 — 매 정기보고서(분기/연간)가 보고한 당기 구성을 전 기간 파싱. snapshot(notes())이
// 단일점이라면 이건 *분기마다 다 있는* 비용 체질의 변화(원재료 비중 ↑ = 원가압박, 감가상각 비중 ↑ = capex 사이클).
// 당기 컬럼만(전기 혼입 방지) · 연결 우선 · 단위(백만원/천원) 원 환산 · 라벨+구조적 총계 제거. 분기는 YTD 누적이라
// 절대액(total)은 사다리꼴(분기리셋); 비중(shares)은 전 기간 비교가능 → 시각화 헤드라인은 100% 적층 믹스. ──
export interface CostNaturePoint {
	period: string; // 'YYYYQn'
	year: string; // 'YYYY'
	quarter: string; // '1분기'..'4분기' (4분기=사업보고서=연간 누적)
	total: number; // 원 — 당기 합계(양수 항목 합)
	shares: number[]; // categories[] 정렬 비중% (합 ~100, 없는 카테고리=0)
}
export interface CostNatureSeries {
	categories: string[]; // 안정 카테고리(표시명) — 전 기간 합계 desc 상위 K + 마지막 '기타'(롤업 있을 때). 색·범례·적층 순서 SSOT
	points: CostNaturePoint[]; // period 오름차순(분기 포함)
}

export interface ReportPort {
	workforce(code: string): Promise<WorkforceYear[] | null>;
	/** 밸류에이션 스냅샷(전 종목 per/pbr/marketCap, dart/scan/valuation.parquet 통파일 직독). 동종 밸류에이션 좌표용. 미존재는 null. */
	valuationSnapshot(): Promise<ValuationSnapshot | null>;
	investments(code: string): Promise<InvestmentsBundle | null>;
	shareholderReturn(code: string): Promise<ShareholderReturnYear[] | null>;
	ownership(code: string): Promise<OwnershipYear[] | null>;
	/** 최대주주 개별 — 역방향 소유("누가 이 회사를 소유하나"). 개인 익명 집계. 미지원/미존재는 null. */
	shareholders(code: string): Promise<ShareholdersView | null>;
	/** 최대주주 기간 시계열 — shareholders() 의 전(全) (year,quarter) 버전(오름차순). shareholders() 는 이 결과의 최신. 미지원은 null. */
	shareholderPeriods(code: string): Promise<ShareholdersView[] | null>;
	execBoard(code: string): Promise<ExecBoardYear[] | null>;
	debtProfile(code: string): Promise<DebtProfileBundle | null>;
	capitalChanges(code: string): Promise<CapitalChangesBundle | null>;
	auditTrail(code: string): Promise<AuditYear[] | null>;
	topExecPay(code: string): Promise<TopExecPay | null>;
	auditFees(code: string): Promise<AuditFeeYear[] | null>;
	/** 정기보고서 주석 본문 — panel 파케에서 고가치 도시에 주석(관계기업·종속기업 투자·특수관계자 거래·우발부채·약정)의
	 * 최신기 본문을 그 자리 렌더용으로. 지연 로드 권장(panel 대용량). 미존재/미지원은 null. */
	notes(code: string): Promise<ReportNoteBlock[] | null>;
	/** 비용의 성격별 분류 *시계열* — 전 기간(분기 포함) 당기 구성 파싱. panel 전 기간 본문을 읽어 무거우니
	 * 상세보기(다이얼로그) 열 때만 지연 호출 권장. 단일점이면(시계열 의미 없음) null. 미존재/미지원도 null. */
	costNatureSeries(code: string): Promise<CostNatureSeries | null>;
}
