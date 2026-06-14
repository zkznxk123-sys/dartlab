// 타법인 출자 관계 진단 — 순수 계산 모듈 (렌더 0). HoldingsDialog 가 소비.
// 관계를 "정확히 이해"하는 3축: ① 성격·위계(tier·intent) ② 가치(marketStake·gapRatio) ③ 효율(equityEarn·investROIC).
// 단위 규약(엄수): bookValue·acquiredAmt·targetNet·marketStake·equityEarn = 원.
//   parentNet·parentMktcap 도 원 — 본체 재무는 조 단위라 호출측에서 *1e12 환산 후 주입(자릿수 함정 가드).
// 정직 한계: equityEarn 은 지분법 *근사*(내부거래·공정가치 미반영), marketStake 는 상장 해소된 피출자사만,
//   targetNet 은 최근 1기 단일값. 미해소·null 은 0 으로 뭉개지 않고 분리 카운트.
import type { InvestmentRow } from '@dartlab/ui-contracts';
import type { Num } from './types';

export type HoldingTier = 'consolidated' | 'equity' | 'simple' | 'unknown';

export type ListedLookup = (name: string) => { code: string; marketCap: number; net: number | null } | null;

export interface HoldingsRow extends InvestmentRow {
	tier: HoldingTier; // 지분율 회계 경계 (≥50 연결 / 20~50 지분법 / <20 단순 / null 분류불가)
	intent: boolean; // purpose 에 '경영참여' 포함 = 영향력 의사
	code: string | null; // 상장 해소 시 종목코드 (클릭 이동·시가 환산)
	marketStake: Num; // 원 — 보유지분 시가 (stakePct% × 피출자 시총). 비상장/미해소 = null
	equityEarn: Num; // 원 — 지분법 근사 이익기여 (stakePct% × targetNet, 부호 보존)
	investROIC: Num; // 소수 (×100 = %) — equityEarn / bookValue
	gapRatio: Num; // 시가/장부 (>1 숨은가치, <1 잠재손상) — 상장만
	markRatio: Num; // 장부/취득 (>1 평가이익 누적, <1 손상 가능) — acquiredAmt 있을 때만
}

export interface HoldingsCounts {
	consolidated: number;
	equity: number;
	simple: number;
	unknown: number;
	listed: number; // 상장 해소 성공
	unlisted: number; // 비상장/미해소
	loss: number; // targetNet < 0 (적자 피출자사)
	nullStake: number; // 지분율 미공시
}

export interface HoldingsModel {
	year: string;
	rows: HoldingsRow[]; // 장부가 desc (reportSource 정렬 유지)
	counts: HoldingsCounts;
	listedStakeSum: number; // 원 — 상장 보유지분 시가 합
	pctOfParentCap: Num; // % — listedStakeSum / parentMktcap (본체 시총 중 상장지분 비중)
	sumEquityEarn: number; // 원 — 이익기여 합 (부호 보존)
	contribShare: Num; // % — sumEquityEarn / parentNet (참고·하한, parentNet>0 일 때만)
	bookTotal: number; // 원 — rows 장부가 합
	maxBook: number; // 원 — 노드 크기·스케일 정규화용
}

export function classifyTier(stakePct: Num): HoldingTier {
	if (stakePct == null) return 'unknown';
	if (stakePct >= 50) return 'consolidated';
	if (stakePct >= 20) return 'equity';
	return 'simple';
}

export function enrichHoldingRow(r: InvestmentRow, lookupListed: ListedLookup): HoldingsRow {
	const listed = lookupListed(r.name);
	const code = listed ? listed.code : null;
	const marketStake = listed && r.stakePct != null ? (r.stakePct / 100) * listed.marketCap : null;
	const equityEarn = r.stakePct != null && r.targetNet != null ? (r.stakePct / 100) * r.targetNet : null;
	const investROIC = equityEarn != null && r.bookValue ? equityEarn / r.bookValue : null;
	const gapRatio = marketStake != null && r.bookValue ? marketStake / r.bookValue : null;
	const markRatio = r.bookValue != null && r.acquiredAmt ? r.bookValue / r.acquiredAmt : null;
	return {
		...r,
		tier: classifyTier(r.stakePct),
		intent: (r.purpose || '').includes('경영참여'),
		code,
		marketStake,
		equityEarn,
		investROIC,
		gapRatio,
		markRatio
	};
}

export function buildHoldingsModel(
	year: string,
	rows: InvestmentRow[],
	lookupListed: ListedLookup,
	parentMktcap: number | null,
	parentNet: number | null
): HoldingsModel {
	const er = rows.map((r) => enrichHoldingRow(r, lookupListed));
	const counts: HoldingsCounts = {
		consolidated: 0,
		equity: 0,
		simple: 0,
		unknown: 0,
		listed: 0,
		unlisted: 0,
		loss: 0,
		nullStake: 0
	};
	let listedStakeSum = 0;
	let sumEquityEarn = 0;
	let bookTotal = 0;
	let maxBook = 0;
	for (const h of er) {
		counts[h.tier]++;
		if (h.code) counts.listed++;
		else counts.unlisted++;
		if (h.targetNet != null && h.targetNet < 0) counts.loss++;
		if (h.stakePct == null) counts.nullStake++;
		if (h.marketStake != null) listedStakeSum += h.marketStake;
		if (h.equityEarn != null) sumEquityEarn += h.equityEarn;
		if (h.bookValue != null) {
			bookTotal += h.bookValue;
			if (h.bookValue > maxBook) maxBook = h.bookValue;
		}
	}
	const pctOfParentCap = parentMktcap && parentMktcap > 0 ? (listedStakeSum / parentMktcap) * 100 : null;
	// 본체 적자(parentNet<=0)면 비중 의미 모호 → 산출 안 함(정직).
	const contribShare = parentNet && parentNet > 0 ? (sumEquityEarn / parentNet) * 100 : null;
	return { year, rows: er, counts, listedStakeSum, pctOfParentCap, sumEquityEarn, contribShare, bookTotal, maxBook };
}
