/**
 * Scan Studio METRICS catalog — SSOT.
 *
 * raw scan 엔진 출력 (계정 + 비율 + 등급 + 거버넌스 + 인적) 을 그대로 노출.
 * 가격·valuation·공시변경은 source='prices'|'valuation'|'changes' 로 표시 후
 * DuckDB-WASM 으로 lazy populate (PR-B 이후).
 *
 * MetricKey 와 MetricGroup 은 이 catalog 에서 도출 — 다른 곳에서 정의 금지.
 */

import { fmtKrw, fmtKrwFromEok, fmtPrice } from '$lib/format/krw';
import { fmtPct, fmtMul } from '$lib/format/pct';
import type { MetricDef } from './types';

export type MetricGroup =
	| 'identity'
	| 'income'
	| 'health'
	| 'governance'
	| 'quality'
	| 'workforce'
	| 'changes'
	| 'price'
	| 'valuation'
	| 'disclosure';

/** 그룹별 한국어 라벨 + 대표 색. ColumnGroupBar UI 에 사용. */
export const GROUP_META: Record<MetricGroup, { label: string; color: string }> = {
	identity: { label: '식별', color: '#94a3b8' },
	income: { label: '손익', color: '#60a5fa' },
	health: { label: '재무건전성', color: '#22c55e' },
	governance: { label: '거버넌스', color: '#a78bfa' },
	quality: { label: '이익질', color: '#fbbf24' },
	workforce: { label: '인적', color: '#f472b6' },
	changes: { label: '변화 (Δ)', color: '#fb923c' },
	price: { label: '주가', color: '#ea4647' },
	valuation: { label: 'Valuation', color: '#10b981' },
	disclosure: { label: '공시 변경', color: '#c084fc' }
};

/** 메트릭 정의 catalog — 사용자에게 노출할 raw scan 컬럼들 */
export const METRICS_DEF = [
	// ── identity (식별) ─────────────────────────────────
	{
		key: 'label',
		label: '회사명',
		group: 'identity',
		type: 'text',
		definition: '회사명 (DART 정식 명칭). 클릭 시 회사 대시보드 진입.',
		source: 'ecosystem'
	},
	{
		key: 'industryName',
		label: '산업',
		group: 'identity',
		type: 'enum',
		definition: 'dartlab 자체 산업 분류 (40+ 산업).',
		source: 'ecosystem'
	},
	{
		key: 'stageName',
		label: '단계',
		group: 'identity',
		type: 'enum',
		definition: '제조·도매·소매·서비스 등 산업 가치사슬 단계.',
		source: 'ecosystem'
	},
	{
		key: 'role',
		label: '역할',
		group: 'identity',
		type: 'text',
		definition: '산업 내 역할 (대표·중견·소·신생 등).',
		source: 'ecosystem'
	},
	{
		key: 'marketShare',
		label: '점유율',
		group: 'identity',
		type: 'number',
		unit: '%',
		definition: '산업 내 매출 점유율. 클수록 산업 내 영향력 큼.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},
	{
		key: 'industryRank',
		label: '산업 순위',
		group: 'identity',
		type: 'number',
		unit: '위',
		definition: '산업 내 매출 순위 (1 = 1위). 작을수록 좋음.',
		higherBetter: false,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? `${v}위` : '—')
	},

	// ── income (손익) ──────────────────────────────────
	{
		key: 'revenue',
		label: '매출액',
		group: 'income',
		type: 'number',
		unit: '원',
		definition: '직전 사업연도 매출액. 회사 규모의 기본 척도.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtKrw(v) : '—'),
		distribution: 'log'
	},
	{
		key: 'opMargin',
		label: '영업이익률',
		group: 'income',
		type: 'number',
		unit: '%',
		definition: '영업이익 ÷ 매출액. 본업 수익성. 5%↑ 양호, 10%↑ 우수.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},
	{
		key: 'roe',
		label: 'ROE',
		group: 'income',
		type: 'number',
		unit: '%',
		definition: '당기순이익 ÷ 자본총계. 자기자본 수익률. 10%↑ 양호, 15%↑ 우수.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},
	{
		key: 'revenueYoyPct',
		label: '매출 YoY',
		group: 'income',
		type: 'number',
		unit: '%',
		definition: '직전 사업연도 매출 YoY 성장률. 양수 = 성장.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true }) : '—')
	},
	{
		key: 'revCagr',
		label: '매출 CAGR',
		group: 'income',
		type: 'number',
		unit: '%',
		definition: '5년 매출 연평균 성장률. 장기 성장 추세.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true }) : '—')
	},

	// ── health (재무건전성) ──────────────────────────────
	{
		key: 'debtRatio',
		label: '부채비율',
		group: 'health',
		type: 'number',
		unit: '%',
		definition: '부채총계 ÷ 자본총계. 100%↓ 안전, 200%↑ 위험.',
		higherBetter: false,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},
	{
		key: 'icr',
		label: '이자보상배율',
		group: 'health',
		type: 'number',
		unit: '배',
		definition: '영업이익 ÷ 이자비용. 1↓ = 영업으로 이자도 못 갚음. 5↑ 양호.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtMul(v, 1) : '—')
	},
	{
		key: 'profGrade',
		label: '수익성 등급',
		group: 'health',
		type: 'enum',
		definition: 'scan 엔진 수익성 종합 등급. 우수 / 양호 / 보통 / 저수익 / 적자.',
		values: ['우수', '양호', '보통', '저수익', '적자'],
		higherBetter: true,
		source: 'ecosystem'
	},
	{
		key: 'debtGrade',
		label: '부채 등급',
		group: 'health',
		type: 'enum',
		definition: 'scan 엔진 부채 위험 등급. 안전 / 관찰 / 주의 / 고위험.',
		values: ['안전', '관찰', '주의', '고위험'],
		higherBetter: true,
		source: 'ecosystem'
	},
	{
		key: 'growthGrade',
		label: '성장 등급',
		group: 'health',
		type: 'enum',
		definition: 'scan 엔진 성장성 등급. 고성장 / 성장 / 정체 / 역성장.',
		values: ['고성장', '성장', '정체', '역성장'],
		higherBetter: true,
		source: 'ecosystem'
	},

	// ── governance (거버넌스) ────────────────────────────
	{
		key: 'govGrade',
		label: '거버넌스 등급',
		group: 'governance',
		type: 'enum',
		definition: '대주주·이사회·내부거래 등 5 지표 종합. A / B / C / D / E.',
		values: ['A', 'B', 'C', 'D', 'E'],
		higherBetter: true,
		source: 'ecosystem'
	},
	{
		key: 'holderPct',
		label: '대주주 지분',
		group: 'governance',
		type: 'number',
		unit: '%',
		definition: '최대주주 + 특수관계인 합산 지분율.',
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},
	{
		key: 'holderChange',
		label: '지분 변화',
		group: 'governance',
		type: 'number',
		unit: '%p',
		definition: '직전 1년 대주주 지분 변화 (%포인트).',
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true, suffix: '%p' }) : '—')
	},
	{
		key: 'stability',
		label: '경영 안정성',
		group: 'governance',
		type: 'enum',
		definition: '경영진 변동·내부거래 패턴 종합. 안정 / 보통 / 불안정.',
		values: ['안정', '보통', '불안정'],
		higherBetter: true,
		source: 'ecosystem'
	},

	// ── quality (이익질·현금흐름) ────────────────────────
	{
		key: 'qualGrade',
		label: '이익질 등급',
		group: 'quality',
		type: 'enum',
		definition: '발생주의·현금흐름 일치도. 우수 / 양호 / 보통 / 주의 / 위험.',
		values: ['우수', '양호', '보통', '주의', '위험'],
		higherBetter: true,
		source: 'ecosystem'
	},
	{
		key: 'liqGrade',
		label: '유동성 등급',
		group: 'quality',
		type: 'enum',
		definition: '단기 부채 상환 능력. 우수 / 양호 / 보통 / 주의 / 위험.',
		values: ['우수', '양호', '보통', '주의', '위험'],
		higherBetter: true,
		source: 'ecosystem'
	},
	{
		key: 'cfPattern',
		label: '현금흐름 패턴',
		group: 'quality',
		type: 'enum',
		definition: 'OCF / ICF / FCF 부호 조합 패턴. 환원형·건전형·공격성장형 등.',
		source: 'ecosystem'
	},
	{
		key: 'auditRisk',
		label: '감사 위험',
		group: 'quality',
		type: 'enum',
		definition: '감사인 변경·한정의견·재무재작성 등 회계 신호. 저위험 / 중위험 / 고위험.',
		values: ['저위험', '중위험', '고위험'],
		higherBetter: false,
		source: 'ecosystem'
	},
	{
		key: 'capClass',
		label: '자본 분류',
		group: 'quality',
		type: 'enum',
		definition: '자본 운용 패턴. A (환원형) / B (성장형) / C (단순형).',
		source: 'ecosystem'
	},

	// ── workforce (인적) ───────────────────────────────
	{
		key: 'empCount',
		label: '임직원',
		group: 'workforce',
		type: 'number',
		unit: '명',
		definition: '직전 사업연도 평균 임직원 수.',
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? `${v.toLocaleString('ko-KR')}명` : '—'),
		distribution: 'log'
	},

	// ── changes (변화 Δ) ──────────────────────────────
	{
		key: 'roeDelta',
		label: 'ROE Δ',
		group: 'changes',
		type: 'number',
		unit: '%p',
		definition: '직전 사업연도 ROE 변화 (%포인트). +3 이상 = 개선 신호.',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true, suffix: '%p' }) : '—')
	},
	{
		key: 'opMarginDelta',
		label: '영업이익률 Δ',
		group: 'changes',
		type: 'number',
		unit: '%p',
		definition: '직전 사업연도 영업이익률 변화 (%포인트).',
		higherBetter: true,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true, suffix: '%p' }) : '—')
	},
	{
		key: 'debtRatioDelta',
		label: '부채비율 Δ',
		group: 'changes',
		type: 'number',
		unit: '%p',
		definition: '직전 사업연도 부채비율 변화 (%포인트). 음수 = 개선.',
		higherBetter: false,
		source: 'ecosystem',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true, suffix: '%p' }) : '—')
	},

	// ── price (주가, PR-B 에서 활성) ─────────────────────
	{
		key: 'currentPrice',
		label: '현재가',
		group: 'price',
		type: 'number',
		unit: '원',
		definition: '직전 거래일 종가 (KRX). PR-B 에서 DuckDB lazy 활성.',
		source: 'prices',
		format: (v: unknown) => (typeof v === 'number' ? fmtPrice(v) : '—')
	},
	{
		key: 'marketCap',
		label: '시가총액',
		group: 'price',
		type: 'number',
		unit: '원',
		definition: '직전 거래일 시가총액 (KRX). PR-B 에서 DuckDB lazy 활성.',
		higherBetter: true,
		source: 'prices',
		format: (v: unknown) => (typeof v === 'number' ? fmtKrw(v) : '—'),
		distribution: 'log'
	},
	{
		key: 'return1y',
		label: '1Y 수익률',
		group: 'price',
		type: 'number',
		unit: '%',
		definition: '직전 1년 주가 수익률. PR-B 에서 활성.',
		higherBetter: true,
		source: 'prices',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v, { withSign: true }) : '—')
	},
	{
		key: 'volatility1y',
		label: '1Y 변동성',
		group: 'price',
		type: 'number',
		unit: '%',
		definition: '직전 1년 일별 수익률 연환산 표준편차. PR-B 활성.',
		higherBetter: false,
		source: 'prices',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},
	{
		key: 'spark',
		label: '60일 차트',
		group: 'price',
		type: 'text',
		definition: '직전 60거래일 종가 추이 (4일 다운샘플). 셀 hover 시 큰 차트.',
		source: 'prices'
	},

	// ── valuation (PR-B 활성) ──────────────────────────
	{
		key: 'per',
		label: 'PER',
		group: 'valuation',
		type: 'number',
		unit: '배',
		definition: '주가 ÷ 주당순이익. 낮을수록 저평가. PR-B 활성.',
		higherBetter: false,
		source: 'valuation',
		format: (v: unknown) => (typeof v === 'number' ? fmtMul(v, 1) : '—')
	},
	{
		key: 'pbr',
		label: 'PBR',
		group: 'valuation',
		type: 'number',
		unit: '배',
		definition: '주가 ÷ 주당순자산. 1↓ = 청산가치 미만. PR-B 활성.',
		higherBetter: false,
		source: 'valuation',
		format: (v: unknown) => (typeof v === 'number' ? fmtMul(v, 2) : '—')
	},
	{
		key: 'dividendYield',
		label: '배당수익률',
		group: 'valuation',
		type: 'number',
		unit: '%',
		definition: '주당 배당금 ÷ 주가. PR-B 에서 활성.',
		higherBetter: true,
		source: 'valuation',
		format: (v: unknown) => (typeof v === 'number' ? fmtPct(v) : '—')
	},

	// ── disclosure (공시 변경, PR-B 활성) ─────────────────
	{
		key: 'numericChanges1y',
		label: '재무 변경',
		group: 'disclosure',
		type: 'number',
		unit: '건',
		definition: '직전 1년 재무 정정·변경 건수. 활발할수록 회계 활동 큼. PR-B 활성.',
		source: 'changes',
		format: (v: unknown) => (typeof v === 'number' ? `${v}건` : '—')
	},
	{
		key: 'structuralChanges1y',
		label: '구조 변경',
		group: 'disclosure',
		type: 'number',
		unit: '건',
		definition: '직전 1년 사업구조 변경 건수. PR-B 활성.',
		source: 'changes',
		format: (v: unknown) => (typeof v === 'number' ? `${v}건` : '—')
	}
] as const;

/** 모든 가능한 메트릭 키. catalog 에서 도출 가능하지만 cross-file 호환성을
 * 위해 string 으로 둔다 (FilterCond/SortKey 와 일치). 자동완성용 union 은
 * `MetricKeyLiteral` 로 별도 export. */
export type MetricKey = string;
export type MetricKeyLiteral = (typeof METRICS_DEF)[number]['key'];

/** 빠른 lookup. lookup 키는 string — caller 에서 narrow. */
export const METRICS_BY_KEY: Record<string, MetricDef> = Object.fromEntries(
	(METRICS_DEF as readonly MetricDef[]).map((m) => [m.key, m])
);

/** 그룹별 메트릭 목록 */
export const METRICS_BY_GROUP: Record<string, MetricDef[]> = (
	METRICS_DEF as readonly MetricDef[]
).reduce(
	(acc, m) => {
		(acc[m.group] ||= []).push(m);
		return acc;
	},
	{} as Record<string, MetricDef[]>
);

/** 첫 진입 default 컬럼 (10) — sticky 첫 컬럼 + 핵심 지표 + sparkline */
export const DEFAULT_COLUMNS: string[] = [
	'label',
	'industryName',
	'marketCap',
	'per',
	'roe',
	'opMargin',
	'debtRatio',
	'qualGrade',
	'return1y',
	'spark'
];

/** "회사명·산업" 은 sticky — 절대 toggle 못 끔 */
export const PINNED_COLUMNS: string[] = ['label', 'industryName'];
