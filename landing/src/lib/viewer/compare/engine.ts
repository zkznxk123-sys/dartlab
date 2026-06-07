// Compare module entrypoint for viewer surfaces.
// Routes/components should call this instead of composing branches themselves.
//
// 재무 섹션도 다른 섹션과 동일하게 행 모드로 — 각 회사의 표(재무상태표/손익계산서 등)를 통째로
// 나란히 보여준다(요약재무와 동일). 옛 isFinanceSection→셀(계정별 acode 분해) 분기는 제거:
// 운영자 요청 "계정간 비교 말고 각 회사 표 그대로"(2026-06). compareRows 가 같은 alignKey 의
// 다중 leaf 를 회사별로 통합하므로 재무상태표가 회사당 한 셀(표 통째)로 정렬된다.

import type { PanelBundle } from '../types';
import { compareRows } from './rowCompare';
import type { CompareBoard, FinanceFreq } from './types';

export interface BuildCompareBoardOptions {
	sectionKey: string;
	period: string;
	block?: string | null; // 활성 블록(예: "연결 재무상태표") — 단일 뷰어와 동일하게 그 블록만 비교
	freq?: FinanceFreq;
	scope?: string | null;
}

export function buildCompareBoard(bundles: PanelBundle[], opts: BuildCompareBoardOptions): CompareBoard {
	const row = compareRows(bundles, opts.sectionKey, opts.period, opts.block ?? null);
	return {
		mode: 'row',
		rows: row.rows,
		financeRows: null,
		financeUnits: null,
		diagnostics: row.diagnostics
	};
}
