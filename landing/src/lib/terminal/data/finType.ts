// 재무 유형 라벨 SSOT — 좌측 레일·상세검색(ScreenerModal)·데이터 출처(SourcesModal) 3소비처 공유.
// 기준·코드·문서가 이 파일 하나에서 나와 드리프트가 구조적으로 불가능하다 (분기 임계 재보정도 여기 한 곳).
//
// 결정론 규칙 — 고정 임계값 기계 판정. 추정·예측·점수화 아님. 결측(null·빈 문자열) = 그 라벨 미부여(fail-safe).
// 복수 충족 시 배열 순서가 우선순위 체인: 주의형 > 회복형 > 성장형 > 수익형 > 우량형 (첫 매치 1개만 표시 —
// 하방 신호 은폐 비용이 비대칭적으로 커서 주의형 최우선, 상태변화(회복) > 정적 라벨).
//
// ⛔ 기준식 사용 금지 필드 (씨데이터 전수 실측): EcoNode.debtRatio·auditRisk·px.beta·px.foreignPct = 전수 null,
//    revenueYoyPct = 빈티지 오염(YTD/연간 혼합). 부채비율은 반드시 finance.json ratios 에서 읽는다.
// ⚠ JS 코어션 함정: null >= -5 는 true — 모든 수치 비교는 `v != null && v >= 임계` 형태 강제.
import type { EcoNode, FinanceCompany } from './types';

export interface FinTypeDef {
	name: string;
	tone: 'down' | 'up' | 'good' | 'neutral';
	criteriaKr: string; // 데이터 출처 모달에 그대로 노출되는 한 줄 기준 — 임계값 포함
	criteriaEn: string;
}

export const FIN_TYPES: FinTypeDef[] = [
	{
		name: '주의형',
		tone: 'down',
		criteriaKr: '수익성 적자 · 유동성 등급 주의/위험 · 현금흐름 현금위기형 — 3개 신호 중 2개 이상 동시 충족 (결측 신호는 미충족으로 계산)',
		criteriaEn: 'At least 2 of 3 signals: loss-making · liquidity grade caution/risk · cash-crisis CF pattern'
	},
	{
		name: '회복형',
		tone: 'up',
		criteriaKr: 'ROE ≥ 2% 이고 ROE 증감 ≥ +5%p 이며 전기 ROE(= 당기 ROE − 증감) < 0 — 적자에서 흑자로 전환',
		criteriaEn: 'ROE ≥ 2%, ROE delta ≥ +5%p, prior ROE (= ROE − delta) < 0 — loss-to-profit turnaround'
	},
	{
		name: '성장형',
		tone: 'good',
		criteriaKr: '매출 3년 CAGR ≥ 20% 이고 수익성 등급이 적자가 아님',
		criteriaEn: '3Y revenue CAGR ≥ 20% and profitability grade not loss-making'
	},
	{
		name: '수익형',
		tone: 'good',
		criteriaKr: '영업이익률 ≥ 12% 이고 ROE ≥ 0%',
		criteriaEn: 'Operating margin ≥ 12% and ROE ≥ 0%'
	},
	{
		name: '우량형',
		tone: 'neutral',
		criteriaKr: '부채비율 ≤ 50% (최신 연간 재무제표) 이고 유동성 등급 우수·양호 이고 수익성 등급 보통 이상',
		criteriaEn: 'Debt ratio ≤ 50% (latest annual statements), liquidity grade good+, profitability grade fair+'
	}
];

function lastNonNull(arr?: (number | null)[]): number | null {
	if (!arr) return null;
	for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return arr[i];
	return null;
}

export interface FinTypeResult {
	primary: FinTypeDef | null; // 우선순위 체인 첫 매치 — 모든 화면이 이것만 표시 (화면 간 불일치 금지)
	all: FinTypeDef[]; // 전체 만족 집합 — hover title 등 보조 노출용
}

export function finTypeOf(n: EcoNode, fin?: FinanceCompany): FinTypeResult {
	const hits: FinTypeDef[] = [];
	// 주의형 — 2-of-3 합의 (단독 신호 오탐 차단: 현금위기형 단독은 양호 기업도 걸린다)
	const signals = [n.profGrade === '적자', n.liqGrade === '주의' || n.liqGrade === '위험', n.cfPattern === '현금위기형'];
	if (signals.filter(Boolean).length >= 2) hits.push(FIN_TYPES[0]);
	// 회복형 — 전기 ROE 를 roe−roeDelta 로 결정론 복원해 부호 전환(적자→흑자)을 요구
	if (n.roe != null && n.roeDelta != null && n.roe >= 2 && n.roeDelta >= 5 && n.roe - n.roeDelta < 0) hits.push(FIN_TYPES[1]);
	// 성장형 — 적자 가드 (부실 외형성장 차단)
	if (n.revCagr != null && n.revCagr >= 20 && !!n.profGrade && n.profGrade !== '적자') hits.push(FIN_TYPES[2]);
	// 수익형 — opMargin 12 = 유니버스 상위 ~15-18% 컷
	if (n.opMargin != null && n.roe != null && n.opMargin >= 12 && n.roe >= 0) hits.push(FIN_TYPES[3]);
	// 우량형 — 부채비율은 finance.json ratios 최신 비결측 (EcoNode.debtRatio 는 전수 null)
	const d = lastNonNull(fin?.ratios?.debtRatio);
	if (
		d != null && d <= 50 &&
		(n.liqGrade === '우수' || n.liqGrade === '양호') &&
		(n.profGrade === '우수' || n.profGrade === '양호' || n.profGrade === '보통')
	) hits.push(FIN_TYPES[4]);
	return { primary: hits[0] ?? null, all: hits };
}
