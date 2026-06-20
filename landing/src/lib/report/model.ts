// 리얼타임 기업분석보고서 모델 — 정적 bake JSON 폐기, 데이터 작업대에서 조회 시점 조립.
// 블록 스키마는 기존 렌더러(+page.svelte)와 1:1 호환 (heading/text/metrics/table/flags).
import type { Num } from '@dartlab/ui-contracts';

export type ReportBlock =
	| { type: 'heading'; title: string }
	| { type: 'text'; text: string }
	| { type: 'metrics'; metrics: { label: string; value: string }[] }
	| { type: 'table'; label?: string; data: Record<string, string>[] }
	| { type: 'flags'; kind: 'warning' | 'opportunity'; flags: string[] };

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
