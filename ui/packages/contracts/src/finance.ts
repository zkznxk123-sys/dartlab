// 재무 계약 — landing/src/lib/terminal/data/terminalFinance.ts 실타입 승격 (census A-2).
// DART OpenAPI raw 행(sj_div 등 snake 원어)은 어댑터 내부 — 계약은 정규화 표면만.
import type { Num } from './runtime';

export interface FinSeries {
	name: string;
	data: Num[];
	color: string;
	type: 'bar' | 'line';
	axis?: 'r'; // 우측 축 (비율 등)
}

export interface FinCard {
	key: string;
	title: string;
	unit: '조' | '%' | '배' | '일' | string; // 표시 단위 — KR 리터럴은 표시 계층 어휘 (census D-3)
	series: FinSeries[];
	refLines?: number[];
	stacked?: boolean;
	signed?: boolean; // stacked 와 조합: 양수 0 위 · 음수 0 아래 부호별 누적
	kind?: 'waterfall' | 'heatmap'; // 지정 시 series/periods 무시
	steps?: { name: string; value: number | null; total?: boolean }[]; // waterfall 전용
	heat?: { rows: string[]; cols: string[]; vals: Num[][]; yoy: Num[][] }; // heatmap 전용
	logLeft?: boolean; // 좌축 로그 눈금 — 지수(=100) 다중 시계열처럼 시리즈 간 자릿수 차가 큰 경우 (같은 기울기=같은 성장률)
}

export interface StmtRow {
	key: string;
	kr: string;
	en: string;
	values: Num[]; // 기간별 조 KRW (비율 표는 % · 배)
	unit?: string;
}

export type StmtKind = 'IS' | 'BS' | 'CF';
export type FinMode = 'annual' | 'quarter' | 'ttm';
export type FinScope = 'CFS' | 'OFS'; // 연결(CFS) / 별도(OFS)

export interface TerminalFinance {
	periods: string[]; // 압축 라벨 ('23Q4' · 'FY23')
	freq: 'quarter' | 'annual' | 'ttm';
	cards: FinCard[];
	tabCards: { profitability: FinCard[]; cashflow: FinCard[]; debt: FinCard[]; shareholder: FinCard[] };
	revYoy: Num[];
	opYoy: Num[];
	cashQuality: Num[]; // 영업CF / 순이익 배수 (순이익>0 일 때만)
	statements: Record<StmtKind, StmtRow[]>;
	ratios: StmtRow[];
}

export interface TerminalFinanceBundle {
	scope: FinScope; // 이 번들이 담은 범위 (연결/별도)
	availScopes: FinScope[]; // 회사가 실제 보고한 범위 — 2개면 연결/별도 토글 노출
	modes: FinMode[]; // 데이터상 가능한 모드 (분기 없으면 annual 만)
	views: Record<FinMode, TerminalFinance | null>;
	defaultMode: FinMode;
	filedDates: Record<string, string>; // `${year}-${q}` → 접수일 YYYYMMDD (정정 중 최초)
}

export interface FinancePort {
	/** 재무 번들 — 미존재 회사/무데이터는 null. scope 미지정 = 최신 데이터가 있는 범위 자동 선택. */
	bundle(code: string, scope?: FinScope): Promise<TerminalFinanceBundle | null>;
}
