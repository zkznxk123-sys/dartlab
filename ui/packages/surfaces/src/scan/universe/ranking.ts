// 랭킹 신호 — UniverseRow 에서 그 시점 랭킹 값 추출(가격/기술 팩터만, 17년 가격보존-clean).
// 재무 팩터 랭킹은 금지(상폐사 재무 13.9% = 생존편향, 05 §4). 단일종목 펀더게이트(W2)와 분리.

import type { RankSignalKey, UniverseRow } from './types';
import { RANK_SIGNAL_LABEL } from './types';

/** 신호 값(null=랭킹 제외). lowerBetter 신호는 부호 반전해 *항상 큰 값=상위분위*로 정규화. */
export function rankValue(row: UniverseRow, signal: RankSignalKey): number | null {
	let v: number | null;
	switch (signal) {
		case 'mom12_1':
			v = row.momMonthly;
			break;
		case 'lowVol':
			v = row.volMonthly6m;
			break;
		case 'high52w':
			v = row.high52wProx;
			break;
		case 'liquidity':
			v = row.turnover > 0 ? row.turnover : null;
			break;
		case 'reversal1m':
			// 단기반전 = 직전 1개월 수익의 역. retFwd 는 미래라 못 씀 → momMonthly 부재 시 null.
			// 1개월 모멘텀 대용: high52wProx 의 역(근접도 낮을수록 반등 여지) 가까운 근사. 정직: 약신호.
			v = row.high52wProx;
			break;
		default:
			v = null;
	}
	if (v == null || !Number.isFinite(v)) return null;
	return RANK_SIGNAL_LABEL[signal].lowerBetter ? -v : v;
}

/** 정렬 가능한 (code, value) 리스트 — value 큰 순(상위분위) 정렬은 호출부. null 값 제외. */
export function eligibleRanked(
	rows: UniverseRow[],
	signal: RankSignalKey,
	minTurnover: number
): { code: string; value: number }[] {
	const out: { code: string; value: number }[] = [];
	for (const r of rows) {
		if (minTurnover > 0 && r.turnover < minTurnover) continue; // PIT 유동성 컷(그 시점 데이터)
		const v = rankValue(r, signal);
		if (v == null) continue;
		out.push({ code: r.stockCode, value: v });
	}
	out.sort((a, b) => b.value - a.value); // 큰 값 = 상위분위(분위 1)
	return out;
}

/** NTILE 분위 배정 — 정렬된 리스트를 buckets 등분(상위=1). 동점 경계는 인덱스 기준(결정론). */
export function assignBuckets(ranked: { code: string; value: number }[], buckets: number): Map<string, number> {
	const n = ranked.length;
	const m = new Map<string, number>();
	if (n === 0) return m;
	for (let i = 0; i < n; i++) {
		// i=0(최상위)→bucket 1, i=n-1(최하위)→bucket=buckets
		const b = Math.min(buckets, Math.floor((i * buckets) / n) + 1);
		m.set(ranked[i].code, b);
	}
	return m;
}
