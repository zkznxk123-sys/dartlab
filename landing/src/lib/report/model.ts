// 리얼타임 기업분석보고서 모델 — 정적 bake JSON 폐기, 데이터 작업대에서 조회 시점 조립.
// 블록 스키마는 기존 렌더러(+page.svelte)와 1:1 호환 (heading/text/metrics/table/flags).
import type { Num } from '@dartlab/ui-contracts';

export type ReportBlock =
	| { type: 'heading'; title: string }
	| { type: 'text'; text: string }
	| { type: 'metrics'; metrics: { label: string; value: string }[] }
	// unit = 표 우측상단 단위 배지(%·억원 등). 셀은 단위 없는 숫자만 — 칸 폭 절약 + 숫자 줄바뀜 방지.
	| { type: 'table'; label?: string; data: Record<string, string>[]; snapshot?: boolean; unit?: string }
	| { type: 'flags'; kind: 'warning' | 'opportunity'; flags: string[] }
	// ── 차트 블록(이미 로드한 데이터의 시각화 — 발명 없음) ──
	// 수평 막대: 값 크기 비교(채무 만기 사다리 등). value=정렬·스케일용 숫자, display=표시 문자열.
	| { type: 'bars'; label?: string; rows: { label: string; value: number; display: string; tone?: 'neg' }[] }
	// 라인: 시계열(주가 궤적 등). series=정규화 전 원값, markers=수평 기준선(52주 고저 등).
	| { type: 'line'; label?: string; series: number[]; xLabels?: [string, string]; markers?: { label: string; v: number }[]; valueFmt?: 'won' }
	// 100% 누적 점유: 연도별 구성비(소유 집중도 등). segs 합 100 가정(나머지는 호출부에서 '기타'로).
	| { type: 'share'; label?: string; rows: { year: string; segs: { label: string; pct: number; key: string }[] }[]; legend: { label: string; key: string }[] };

export type ReportSourceEngine = 'analysis' | 'credit' | 'quant' | 'industry' | 'macro' | 'story';

export interface ReportSection {
	key: string;
	title: string; // "{도메인} -- {질문}"
	sourceEngine: ReportSourceEngine;
	blocks: ReportBlock[];
	emph?: boolean;
}

export interface ReportKpi {
	label: string;
	value: string;
}
export interface ReportFinding {
	key: string;
	finding: string;
	sourceEngine: ReportSourceEngine;
}
export interface ReportClosing {
	label: string;
	engine: ReportSourceEngine;
	line: string;
}
export interface ReportProvenance {
	engines: Record<string, { label: string; sections: number; blocks: number }>;
	note: string;
}

export interface ReportModel {
	stockCode: string;
	corpName: string;
	asOf: string; // 데이터 기준(최근 접수일 또는 최신 회계연도)
	dataBasis: string; // 예: 'FY2025 (연간)'
	industry?: string;
	perspectiveKey: string;
	perspectiveLabel: string;
	conclusion: string;
	headlineKpis: ReportKpi[];
	narrativeOverview: string;
	keyFindings: ReportFinding[];
	sections: ReportSection[];
	closing: ReportClosing[];
	provenance: ReportProvenance;
	assumptionsNote: string;
	qualityLabel: 'verified' | 'conditional';
	focusQuestions: string[];
	pending?: boolean; // 미구현 관점(다음 사이클) — 정직 표기
}

// 5관점 통합 리드 — 보고서를 한 몸으로 묶는 thesis + 관점별 한 줄 요지(권장 읽기 순서).
export interface OverviewTake {
	key: string;
	label: string;
	line: string;
	engine: ReportSourceEngine;
}
export interface OverviewModel {
	corpName: string;
	stockCode: string;
	asOf: string;
	dataBasis: string;
	industry?: string;
	thesis: string; // 관점을 교차해 꿴 한 문단(긴장의 서술 — 종합점수·매수의견 아님)
	takes: OverviewTake[];
}

export interface ReportSkipped {
	skipped: true;
	stockCode: string;
	reason: string;
}

export type ReportResult = ReportModel | ReportSkipped;

export function isSkipped(r: ReportResult): r is ReportSkipped {
	return (r as ReportSkipped).skipped === true;
}

// 행 헬퍼 — Num[] 에서 마지막 유효값
export function lastNonNull(values: Num[]): Num {
	for (let i = values.length - 1; i >= 0; i--) {
		const v = values[i];
		if (v != null && Number.isFinite(v)) return v;
	}
	return null;
}
