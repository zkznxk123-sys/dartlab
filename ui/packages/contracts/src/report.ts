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

export interface InvestmentsBundle {
	latest: InvestmentsView;
	trend: InvestmentTrendYear[]; // 연도 오름차순
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

export interface ReportPort {
	workforce(code: string): Promise<WorkforceYear[] | null>;
	investments(code: string): Promise<InvestmentsBundle | null>;
	shareholderReturn(code: string): Promise<ShareholderReturnYear[] | null>;
	ownership(code: string): Promise<OwnershipYear[] | null>;
	/** 최대주주 개별 — 역방향 소유("누가 이 회사를 소유하나"). 개인 익명 집계. 미지원/미존재는 null. */
	shareholders(code: string): Promise<ShareholdersView | null>;
	execBoard(code: string): Promise<ExecBoardYear[] | null>;
	debtProfile(code: string): Promise<DebtProfileBundle | null>;
	capitalChanges(code: string): Promise<CapitalChangesBundle | null>;
	auditTrail(code: string): Promise<AuditYear[] | null>;
	topExecPay(code: string): Promise<TopExecPay | null>;
	auditFees(code: string): Promise<AuditFeeYear[] | null>;
}
