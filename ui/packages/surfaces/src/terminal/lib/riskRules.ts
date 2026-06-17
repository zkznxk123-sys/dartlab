// 리스크 경고등 규칙 SSOT — riskFlagsOf(글랜스 평가) + RiskFlagsDialog(설명 카탈로그) *공동 소비*.
// 평가 로직은 각 규칙의 evaluate 클로저 한 곳에만 존재(임계·라벨·설명은 선언) → 두 표면 사이 로직 중복 0.
//
// 정직 가드(forensic.ts·gradeGuide.ts 와 정합):
//  · 결정론 — evaluate 는 순수 임계 비교만(LLM 추론 0).
//  · 글랜스 패널은 점등(red/yellow)만 표시 / 다이얼로그만 clear·na 전체 카탈로그 표시(역할 분리).
//  · 완결성 점검 아님 · 매수/매도/목표가 신호 아님 · 인과 단정 금지.
//  · null = 판정불가(데이터 부재 등) — green 으로도 red 로도 흘리지 않음. "—"=공시 부재(0 대체 금지).
//
// 단위 주의(engine.ts mk 확인): icr = 배수(<1.0배), currentRatio = 백분율(<100%), debtRatio·opMargin = %.
import type { EcoNode, RiskCatalogItem } from './types';

export type RiskLevel = 'red' | 'yellow';

/** 평가 컨텍스트 — 회사 EcoNode + 업종 중앙값 조회(industryStats, 없으면 null). */
export interface RiskRuleCtx {
	e: EcoNode;
	median: (field: keyof EcoNode) => number | null;
}

/** 점등(red/yellow) — 글랜스 패널 표시. kr/en = *조건별* 라벨(영업적자/저수익 등, 차원명 아님). */
export interface RiskHit {
	lv: RiskLevel;
	kr: string;
	en: string;
	d: string; // detail (실측 수치 + 맥락)
}
/** evaluate 반환: 점등(RiskHit) · 임계 미달(clear+실제값, 다이얼로그 '통과') · 판정불가(null). */
export type RiskEval = RiskHit | { lv: 'clear'; d: string } | null;

export interface RiskRule {
	id: string;
	kr: string; // 차원명(다이얼로그 카탈로그 행) — 조건별 라벨과 다름
	en: string;
	axis: string | null; // GradeExplainDialog 교차링크 키(COMPOSITE_AXES): prof|growth|audit|qual|debt|liq|stab — 없으면 null
	whatKr: string; // "무엇을 보나"
	whatEn: string;
	thresholdKr: string; // 켜지는 조건(다이얼로그 표기 SSOT)
	thresholdEn: string;
	source: string; // dataSource 필드 표기
	hard: boolean; // 절대수치 위반(정렬 우선) vs 등급라벨 신호
	evaluate: (c: RiskRuleCtx) => RiskEval;
}

// (RiskCatalogItem 타입은 types.ts — 순환 import 회피 위해 데이터 타입은 그곳이 SSOT)

// detail 포맷 헬퍼 — 단위 명시(거짓정밀 방지: 배수/백분율 혼동 차단).
const x1 = (v: number): string => v.toFixed(1) + '배';
const pct0 = (v: number): string => v.toFixed(0) + '%';
const pct1 = (v: number): string => v.toFixed(1) + '%';
const medTail = (med: number | null, fmt: (n: number) => string): string => (med != null ? ' · 업종중앙 ' + fmt(med) : '');

export const RISK_RULES: RiskRule[] = [
	{
		id: 'profitability',
		kr: '수익성',
		en: 'Profitability',
		axis: 'prof',
		whatKr: '본업에서 돈을 버는가 — 영업이익률',
		whatEn: 'Does the core business make money — OP margin',
		thresholdKr: '영업이익률 < 0% 또는 수익성 등급 "적자" → red · 등급 "저수익" → yellow',
		thresholdEn: 'OP margin < 0% or profitability grade "loss" → red · grade "low" → yellow',
		source: 'EcoNode.opMargin / profGrade',
		hard: true,
		evaluate: ({ e }) => {
			const om = e.opMargin;
			// red = 영업적자 (수치 우선, 수치 부재 시 등급 라벨로 보강 — red 손실 방지)
			if ((om != null && om < 0) || e.profGrade === '적자') return { lv: 'red', kr: '영업적자', en: 'Operating loss', d: om != null ? pct1(om) : '' };
			if (e.profGrade === '저수익') return { lv: 'yellow', kr: '저수익', en: 'Low margin', d: om != null ? pct1(om) : '' };
			if (om != null) return { lv: 'clear', d: pct1(om) };
			return null;
		}
	},
	{
		id: 'growth',
		kr: '성장성',
		en: 'Growth',
		axis: 'growth',
		whatKr: '외형이 자라는가 — 매출 추세',
		whatEn: 'Is the top line growing — revenue trend',
		thresholdKr: '성장 등급 "급감" → red · "역성장" → yellow',
		thresholdEn: 'Growth grade "collapse" → red · "decline" → yellow',
		source: 'EcoNode.growthGrade (detail: revCagr)',
		hard: false,
		evaluate: ({ e }) => {
			const d = e.revCagr != null ? pct0(e.revCagr) : '';
			if (e.growthGrade === '급감') return { lv: 'red', kr: '매출 급감', en: 'Revenue collapse', d };
			if (e.growthGrade === '역성장') return { lv: 'yellow', kr: '매출 역성장', en: 'Revenue decline', d };
			if (e.growthGrade != null) return { lv: 'clear', d };
			return null;
		}
	},
	{
		id: 'audit',
		kr: '감사',
		en: 'Audit',
		axis: 'audit',
		whatKr: '감사의견·감사인 교체 등 회계 경고 신호',
		whatEn: 'Audit opinion / auditor-change warning signals',
		thresholdKr: '감사위험 등급 "고위험" → red · "주의" → yellow',
		thresholdEn: 'Audit-risk grade "high" → red · "watch" → yellow',
		source: 'EcoNode.auditRisk',
		hard: false,
		evaluate: ({ e }) => {
			if (e.auditRisk === '고위험') return { lv: 'red', kr: '감사 고위험', en: 'Audit high risk', d: '' };
			if (e.auditRisk === '주의') return { lv: 'yellow', kr: '감사 주의', en: 'Audit watch', d: '' };
			if (e.auditRisk != null) return { lv: 'clear', d: e.auditRisk };
			return null;
		}
	},
	{
		id: 'earningsQuality',
		kr: '이익질',
		en: 'Earnings quality',
		axis: 'qual',
		whatKr: '이익이 현금·본업으로 뒷받침되는가 — 발생액·현금화',
		whatEn: 'Is profit cash- and core-backed — accruals / cash conversion',
		thresholdKr: '이익질 등급 "위험" → red · "주의" → yellow (detail: 발생액비율)',
		thresholdEn: 'Earnings-quality grade "risk" → red · "watch" → yellow (detail: accrual ratio)',
		source: 'EcoNode.qualGrade (detail: accrualRatio)',
		hard: false,
		evaluate: ({ e }) => {
			const d = e.accrualRatio != null ? '발생액 ' + e.accrualRatio.toFixed(2) : '';
			if (e.qualGrade === '위험') return { lv: 'red', kr: '이익질 위험', en: 'Earnings quality risk', d };
			if (e.qualGrade === '주의') return { lv: 'yellow', kr: '이익질 주의', en: 'Earnings quality watch', d };
			if (e.qualGrade != null) return { lv: 'clear', d };
			return null;
		}
	},
	{
		id: 'icr',
		kr: '이자보상배율',
		en: 'Interest coverage',
		axis: 'debt',
		whatKr: '영업이익으로 이자를 감당하는가 (ICR = 영업이익 ÷ 이자비용)',
		whatEn: 'Can operating profit cover interest (ICR = OP income ÷ interest)',
		thresholdKr: 'ICR < 1.0배(영업이익 < 이자) → red · 1.0~1.5배 → yellow · 영업적자(ICR<0)는 수익성에 양보(판정 제외)',
		thresholdEn: 'ICR < 1.0× (OP income < interest) → red · 1.0–1.5× → yellow · operating loss (ICR<0) deferred to profitability',
		source: 'EcoNode.icr',
		hard: true,
		evaluate: ({ e, median }) => {
			const v = e.icr;
			if (v == null || v < 0) return null; // 영업적자/부재 = 무판정(수익성 규칙 소관)
			const tail = medTail(median('icr'), x1);
			if (v < 1.0) return { lv: 'red', kr: '이자보상 1배 미만', en: 'ICR below 1×', d: x1(v) + tail };
			if (v < 1.5) return { lv: 'yellow', kr: '이자보상 취약', en: 'Thin interest coverage', d: x1(v) + tail };
			return { lv: 'clear', d: x1(v) + tail };
		}
	},
	{
		id: 'liquidity',
		kr: '유동성',
		en: 'Liquidity',
		axis: 'liq',
		whatKr: '1년 내 갚을 빚을 1년 내 현금화 자산으로 덮는가 — 유동비율',
		whatEn: 'Do near-term assets cover near-term liabilities — current ratio',
		thresholdKr: '유동비율 < 100%(유동부채 > 유동자산) → red · 100~120% → yellow',
		thresholdEn: 'Current ratio < 100% → red · 100–120% → yellow',
		source: 'EcoNode.currentRatio',
		hard: true,
		evaluate: ({ e, median }) => {
			const v = e.currentRatio;
			if (v == null) return null;
			const tail = medTail(median('currentRatio'), pct0);
			if (v < 100) return { lv: 'red', kr: '유동비율 100% 미만', en: 'Current ratio < 100%', d: pct0(v) + tail };
			if (v < 120) return { lv: 'yellow', kr: '유동비율 취약', en: 'Thin current ratio', d: pct0(v) + tail };
			return { lv: 'clear', d: pct0(v) + tail };
		}
	},
	{
		id: 'controlStability',
		kr: '경영권 안정',
		en: 'Control stability',
		axis: 'stab',
		whatKr: '지배구조가 흔들리는가 — 최대주주 지분 안정성',
		whatEn: 'Is control shaky — controlling-shareholder stability',
		thresholdKr: '경영권 등급 "경고"·"위험" → red · "취약" → yellow',
		thresholdEn: 'Control grade "alert"·"risk" → red · "fragile" → yellow',
		source: 'EcoNode.stability',
		hard: false,
		evaluate: ({ e }) => {
			if (e.stability === '경고' || e.stability === '위험') return { lv: 'red', kr: '경영 불안정', en: 'Unstable', d: e.stability };
			if (e.stability === '취약') return { lv: 'yellow', kr: '경영 취약', en: 'Fragile', d: e.stability };
			if (e.stability != null) return { lv: 'clear', d: e.stability };
			return null;
		}
	},
	{
		id: 'ownerStakeDrop',
		kr: '대주주 지분',
		en: 'Owner stake',
		axis: 'stab',
		whatKr: '최대주주 지분이 급감했는가 (증자·분할 등 거짓양성 가능 → yellow 한정)',
		whatEn: 'Did the controlling stake drop sharply (issuance/spin-off can false-positive → yellow only)',
		thresholdKr: '대주주 지분 변화 < −3%p → yellow (경영권 안정 점등 시 중복 억제)',
		thresholdEn: 'Owner stake change < −3%p → yellow (suppressed if control-stability already lit)',
		source: 'EcoNode.holderChange (detail: holderPct)',
		hard: false,
		evaluate: ({ e }) => {
			const c = e.holderChange;
			if (c == null) return null;
			const cur = e.holderPct != null ? ' · 현재 ' + pct0(e.holderPct) : '';
			if (c < -3) return { lv: 'yellow', kr: '대주주 지분 급감', en: 'Owner stake drop', d: c.toFixed(1) + '%p' + cur };
			return { lv: 'clear', d: c.toFixed(1) + '%p' + cur };
		}
	},
	{
		id: 'debtRatioSpike',
		kr: '부채비율 변화',
		en: 'Debt-ratio change',
		axis: 'debt',
		whatKr: '부채비율이 전년 대비 급증했는가 (자본잠식 거짓양성 차단: 업종중앙 초과 게이트)',
		whatEn: 'Did debt ratio spike YoY (equity-erosion false-positive gated by above-median check)',
		thresholdKr: '부채비율 Δ > +30%p AND 부채비율 > 업종중앙 → yellow (분포 부재 시 Δ 단독)',
		thresholdEn: 'Debt-ratio Δ > +30%p AND debt ratio > industry median → yellow (Δ-only if no distribution)',
		source: 'EcoNode.debtRatioDelta / debtRatio (gate: industryStats median)',
		hard: false,
		evaluate: ({ e, median }) => {
			const dd = e.debtRatioDelta;
			if (dd == null) return null;
			const dr = e.debtRatio;
			const med = median('debtRatio');
			const gated = med != null ? dr != null && dr > med : true; // 분포 부재(local) = 게이트 통과
			const yr = e.deltaYear ? ' (' + e.deltaYear + ')' : '';
			const d = '+' + dd.toFixed(0) + '%p' + (dr != null ? ' → 부채비율 ' + pct0(dr) : '') + yr;
			if (dd > 30 && gated) return { lv: 'yellow', kr: '부채비율 급증', en: 'Debt spike', d };
			return { lv: 'clear', d };
		}
	}
];

/** 다이얼로그용 — 전체 차원 카탈로그 + 이 회사 현상태(점등/통과/판정불가). 억제·정렬 없음(교육 목적 전체 표시). */
export function evalRiskCatalog(ctx: RiskRuleCtx): RiskCatalogItem[] {
	return RISK_RULES.map((r) => {
		const ev = r.evaluate(ctx);
		return {
			id: r.id,
			kr: r.kr,
			en: r.en,
			axis: r.axis,
			whatKr: r.whatKr,
			whatEn: r.whatEn,
			thresholdKr: r.thresholdKr,
			thresholdEn: r.thresholdEn,
			source: r.source,
			status: ev == null ? 'na' : ev.lv,
			d: ev == null ? '' : ev.d
		};
	});
}
