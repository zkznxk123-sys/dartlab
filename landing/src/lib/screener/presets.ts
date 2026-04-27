/**
 * 스크리너 프리셋 라이브러리.
 *
 * 각 프리셋은 사용자가 한 클릭으로 conds + sorts 를 자동 입력받게 한다.
 * 자연어 한국어 타이틀 + 학술/실무 부제 + 한 줄 설명.
 *
 * SSOT: 다른 곳에서 프리셋 정의 금지. 추가 시 여기만.
 */

import type { Cond, SortKey } from './types';

export interface Preset {
	/** URL ?preset=ID 로 직접 진입 가능 */
	id: string;
	/** 카드 메인 타이틀 — 자연어 */
	title: string;
	/** 학술/실무 부제 (검증 출처 등) */
	subtitle: string;
	/** 한 줄 설명 */
	desc: string;
	/** 카테고리 — 카드 그룹화 */
	category: 'verified' | 'theme' | 'price';
	/** 자동 입력 조건 */
	conds: Cond[];
	/** 자동 입력 정렬 (다중 가능) */
	sorts: SortKey[];
}

export const PRESETS: Preset[] = [
	// ── 테마 프리셋 (재무 위주) ──
	{
		id: 'real-money-makers',
		title: '진짜 돈 버는 회사',
		subtitle: '4축 흑자 + 수익성 등급',
		desc: '매출 + 영업이익률 + 순이익 + 흑자전환을 모두 만족하는 회사',
		category: 'theme',
		conds: [
			{ metric: 'opMargin', op: '>=', value: 5 },
			{ metric: 'roe', op: '>=', value: 5 },
			{ metric: 'revenueYoyPct', op: '>=', value: 0 },
			{ metric: 'profGrade', op: '!=', value: '적자' }
		],
		sorts: [
			{ key: 'roe', dir: 'desc' },
			{ key: 'opMargin', dir: 'desc' }
		]
	},
	{
		id: 'quality-compounder',
		title: 'Quality Compounder',
		subtitle: '높은 ROE + 안전 부채 + 우량 등급',
		desc: 'ROE 15%↑ + 부채비율 100%↓ + 이익질 양호 이상 + 건전한 현금흐름',
		category: 'theme',
		conds: [
			{ metric: 'roe', op: '>=', value: 15 },
			{ metric: 'debtRatio', op: '<=', value: 100 },
			{ metric: 'qualGrade', op: '!=', value: '주의' },
			{ metric: 'qualGrade', op: '!=', value: '위험' }
		],
		sorts: [{ key: 'roe', dir: 'desc' }]
	},
	{
		id: 'growth-and-safety',
		title: '성장 + 안전',
		subtitle: '매출 성장 + 부채 통제 + YoY 양수',
		desc: 'CAGR 15%↑ + 부채 80%↓ + 매출 YoY 10%↑ — 빠르게 크면서 빚 안 늘리는 회사',
		category: 'theme',
		conds: [
			{ metric: 'revCagr', op: '>=', value: 15 },
			{ metric: 'debtRatio', op: '<=', value: 80 },
			{ metric: 'revenueYoyPct', op: '>=', value: 10 }
		],
		sorts: [{ key: 'revCagr', dir: 'desc' }]
	},
	{
		id: 'turnaround-signals',
		title: '흑자전환 신호',
		subtitle: 'Δ 양호 + 매출 회복',
		desc: 'ROE 와 영업이익률이 작년 대비 개선 + 매출 YoY 양수 — 회복 중인 회사',
		category: 'theme',
		conds: [
			{ metric: 'roeDelta', op: '>=', value: 3 },
			{ metric: 'opMarginDelta', op: '>=', value: 2 },
			{ metric: 'revenueYoyPct', op: '>=', value: 0 }
		],
		sorts: [{ key: 'roeDelta', dir: 'desc' }]
	},
	{
		id: 'qoq-acceleration',
		title: '분기 가속 회사',
		subtitle: '직전 분기 → 당분기 가속',
		desc: '매출 QoQ 10%↑ + 영업이익 QoQ 20%↑ + YoY 매출 양수 — 분기 단위 모멘텀',
		category: 'theme',
		conds: [
			{ metric: 'qoqRevenueGrowth', op: '>=', value: 10 },
			{ metric: 'qoqOpProfitGrowth', op: '>=', value: 20 },
			{ metric: 'yoyRevenueGrowthQ', op: '>=', value: 0 }
		],
		sorts: [{ key: 'qoqOpProfitGrowth', dir: 'desc' }]
	},
	{
		id: 'consecutive-profit',
		title: '연속 흑자 8 분기',
		subtitle: '안정적 영업이익 흐름',
		desc: '직전 8 분기 연속 영업이익 양수 + 매출 YoY 양수 + 부채 안전권 — 검증된 안정 회사',
		category: 'theme',
		conds: [
			{ metric: 'consecutiveProfitableQ', op: '>=', value: 8 },
			{ metric: 'revenueYoyPct', op: '>=', value: 0 },
			{ metric: 'debtRatio', op: '<=', value: 150 }
		],
		sorts: [{ key: 'consecutiveProfitableQ', dir: 'desc' }]
	},
	{
		id: 'risk-watch',
		title: '이상 신호 회사',
		subtitle: '감사·부채·극단 변화',
		desc: '감사 위험 고위험 또는 부채 등급 고위험 또는 ROE 급변 — 주의 필요',
		category: 'theme',
		conds: [{ metric: 'auditRisk', op: '==', value: '고위험' }],
		sorts: [{ key: 'roeDelta', dir: 'asc' }]
	},

	// ── 가격+Scan 결합 프리셋 (PR-3 의 시계열 메트릭 활용) ──
	{
		id: 'momentum-fundamental',
		title: '모멘텀 + 펀더멘털',
		subtitle: '1Y 강세 진행 + 매출 성장 + 흑자',
		desc: '1Y 수익률 30%↑ + 매출 CAGR 10%↑ + 영업이익률 5%↑ — 시장도 알아챈 우량주',
		category: 'price',
		conds: [
			{ metric: 'return1y', op: '>=', value: 30 },
			{ metric: 'revCagr', op: '>=', value: 10 },
			{ metric: 'opMargin', op: '>=', value: 5 }
		],
		sorts: [{ key: 'return1y', dir: 'desc' }]
	},
	{
		id: 'cheap-quality',
		title: '저평가 Quality',
		subtitle: '우량인데 1Y 빠진 회사',
		desc: 'ROE 10%↑ + 이익질 양호↑ + 1Y 수익률 0%↓ — 펀더멘털 좋은데 시장이 외면',
		category: 'price',
		conds: [
			{ metric: 'roe', op: '>=', value: 10 },
			{ metric: 'qualGrade', op: '!=', value: '주의' },
			{ metric: 'qualGrade', op: '!=', value: '위험' },
			{ metric: 'return1y', op: '<=', value: 0 }
		],
		sorts: [
			{ key: 'roe', dir: 'desc' },
			{ key: 'return1y', dir: 'asc' }
		]
	},
	{
		id: 'oversold-quality',
		title: '60일 단기 조정 우량주',
		subtitle: 'drawdown60d -20%↓ + 흑자 + 부채 안전',
		desc: '직전 60일 고점 대비 20%↓ + 영업이익률 5%↑ + 부채 100%↓ — 단기 저점 매수 후보 (DuckDB 시계열 활성 시)',
		category: 'price',
		conds: [
			{ metric: 'drawdown60d', op: '<=', value: -20 },
			{ metric: 'opMargin', op: '>=', value: 5 },
			{ metric: 'debtRatio', op: '<=', value: 100 }
		],
		sorts: [{ key: 'drawdown60d', dir: 'asc' }]
	},
	{
		id: 'new-high-profitable',
		title: '52주 신고가 + 흑자',
		subtitle: 'currentVsMA20 양수 + drawdown60d 0 근접',
		desc: '20일 이평 위 + 60일 고점 -3%↓ 이내 + 영업이익 흑자 — 강세 진행 중 우량주 (DuckDB 시계열 활성 시)',
		category: 'price',
		conds: [
			{ metric: 'currentVsMA20', op: '>=', value: 0 },
			{ metric: 'drawdown60d', op: '>=', value: -3 },
			{ metric: 'opMargin', op: '>=', value: 0 }
		],
		sorts: [{ key: 'return1y', dir: 'desc' }]
	},
	{
		id: 'low-volatility-cashflow',
		title: '저변동성 + 현금흐름 우량',
		subtitle: '1Y 변동성 30%↓ + 건전형 cf',
		desc: '연환산 변동성 30%↓ + 현금흐름 패턴 건전형 + 환원형 — 안정 배당주 후보',
		category: 'price',
		conds: [
			{ metric: 'volatility1y', op: '<=', value: 30 },
			{ metric: 'cfPattern', op: '==', value: '건전형' }
		],
		sorts: [{ key: 'volatility1y', dir: 'asc' }]
	},
	// ── Valuation 프리셋 (PR-14, HF dart/scan/valuation.parquet 활용) ──
	{
		id: 'low-per-quality',
		title: '저PER + Quality',
		subtitle: 'PER 10배 이하 + 우량 등급',
		desc: 'PER 10배↓ + ROE 10%↑ + 이익질 양호 이상 — 저평가 우량주 (Naver API 시총)',
		category: 'price',
		conds: [
			{ metric: 'per', op: 'between', value: 0, value2: 10 },
			{ metric: 'roe', op: '>=', value: 10 },
			{ metric: 'qualGrade', op: '!=', value: '주의' },
			{ metric: 'qualGrade', op: '!=', value: '위험' }
		],
		sorts: [{ key: 'per', dir: 'asc' }]
	},
	{
		id: 'high-dividend-stable',
		title: '고배당 + 안정',
		subtitle: '배당수익률 4%↑ + 부채 안전 + 흑자',
		desc: '배당수익률 4%↑ + 부채비율 100%↓ + 영업이익률 양수 — 안정 고배당주',
		category: 'price',
		conds: [
			{ metric: 'dividendYield', op: '>=', value: 4 },
			{ metric: 'debtRatio', op: '<=', value: 100 },
			{ metric: 'opMargin', op: '>=', value: 0 }
		],
		sorts: [{ key: 'dividendYield', dir: 'desc' }]
	},
	{
		id: 'pbr-below-book',
		title: 'PBR 1배 이하 회사',
		subtitle: '장부가 미만 + 이익 흑자',
		desc: 'PBR 1배 이하 + ROE 양수 + 영업이익 양수 — 청산가치 미만 (가치주 후보)',
		category: 'price',
		conds: [
			{ metric: 'pbr', op: 'between', value: 0, value2: 1 },
			{ metric: 'roe', op: '>=', value: 0 },
			{ metric: 'opMargin', op: '>=', value: 0 }
		],
		sorts: [{ key: 'pbr', dir: 'asc' }]
	}
];

export const PRESETS_BY_ID = new Map(PRESETS.map((p) => [p.id, p]));

export const PRESET_CATEGORIES: { key: Preset['category']; label: string }[] = [
	{ key: 'theme', label: '테마' },
	{ key: 'price', label: '가격+재무' },
	{ key: 'verified', label: '검증 (Piotroski 등 — PR 후속)' }
];
