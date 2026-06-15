// 타법인 출자 관계 진단 — 순수 계산 모듈 (렌더 0). HoldingsDialog 가 소비.
// 관계를 "정확히 이해"하는 3축: ① 성격·위계(tier·intent) ② 가치(marketStake·gapRatio) ③ 효율(equityEarn·investROIC).
// 단위 규약(엄수): bookValue·acquiredAmt·targetNet·marketStake·equityEarn = 원.
//   parentNet·parentMktcap 도 원 — 본체 재무는 조 단위라 호출측에서 *1e12 환산 후 주입(자릿수 함정 가드).
// 정직 한계: equityEarn 은 지분법 *근사*(내부거래·공정가치 미반영), marketStake 는 상장 해소된 피출자사만,
//   targetNet 은 최근 1기 단일값. 미해소·null 은 0 으로 뭉개지 않고 분리 카운트.
import type { InvestmentRow, PersonAggregate, ShareholderRow } from '@dartlab/ui-contracts';
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

// ───────────────────────── 양방향 관계망 좌표 (순수, 렌더 0) ─────────────────────────
// 위=주주(reverse, 누가 나를 소유)·중앙=본체·아래=자회사(forward, tier 레인). 색은 컴포넌트가 입힌다(여기선 좌표·크기·데이터).
export interface NetNode {
	key: string;
	x: number;
	y: number;
	r: number;
	kind: 'reverseNamed' | 'reversePerson' | 'forward';
	h: HoldingsRow | null; // forward 노드
	sh: ShareholderRow | null; // reverse 기관·법인 주주
	person: PersonAggregate | null; // reverse 개인 익명 집계
	code: string | null; // 클릭 이동 (상장 해소)
}
export interface NetEdge {
	key: string;
	x1: number;
	y1: number;
	x2: number;
	y2: number;
	w: number;
	dashed: boolean;
	up: boolean; // true=주주→본체(위), false=본체→자회사(아래)
}
export interface NetCapsule {
	tier: HoldingTier;
	x: number;
	y: number;
	count: number;
	book: number;
}
export interface NetLane {
	tier: HoldingTier;
	y: number; // 레인 라벨 y (상단)
	cy: number; // 노드 중심 y
	count: number;
	book: number;
}
export interface NetLayout {
	focal: { x: number; y: number; r: number };
	nodes: NetNode[];
	edges: NetEdge[];
	capsules: NetCapsule[];
	lanes: NetLane[];
}

const NET_TIERS: HoldingTier[] = ['consolidated', 'equity', 'simple', 'unknown'];

/** 양방향 3-band 결정론 좌표. reverseNamed 의 code 는 호출측이 lookupListed 로 미리 채워 전달. perLane 초과분은 capsule. */
export function buildNetworkLayout(
	rows: HoldingsRow[],
	maxBook: number,
	reverseNamed: ShareholderRow[],
	reversePerson: PersonAggregate | null,
	W: number,
	H: number,
	perLane = 10
): NetLayout {
	const cx = W / 2;
	const focalY = H * 0.36;
	const focal = { x: cx, y: focalY, r: 22 };
	const nodes: NetNode[] = [];
	const edges: NetEdge[] = [];
	const capsules: NetCapsule[] = [];
	const lanes: NetLane[] = [];
	const sqrtR = (v: number, vmax: number, lo: number, hi: number) => (!vmax || v <= 0 ? lo : lo + Math.sqrt(v / vmax) * (hi - lo));
	// 라벨 폭 근사(한글 위주, px) — 노드 슬롯을 회사명 라벨보다 넓게 잡아 라벨이 겹치지 않게 한다(짧은 이름 촘촘·긴 이름 넓게).
	const labelW = (name: string, max: number) => Math.min((name || '').replace(/\(주\)|㈜|주식회사/g, '').trim().length, max) * 8.5 + 14;

	// ── reverse band (위) — 기관·법인 주주 top 7 + 개인 집계 1 ──
	const revItems: { sh: ShareholderRow | null; person: PersonAggregate | null; ratio: number }[] = [
		...reverseNamed.slice(0, 7).map((sh) => ({ sh, person: null, ratio: sh.ratio ?? 0 })),
		...(reversePerson ? [{ sh: null, person: reversePerson, ratio: reversePerson.ratio ?? 0 }] : [])
	];
	if (revItems.length) {
		const maxRatio = Math.max(...revItems.map((r) => r.ratio), 1);
		const gap = 22;
		const rOf = (it: (typeof revItems)[number]) => sqrtR(it.ratio, maxRatio, 9, 20);
		const slotOf = (it: (typeof revItems)[number]) => Math.max(rOf(it) * 2 + gap, labelW(it.sh ? it.sh.name : '개인', 11));
		const totalW = revItems.reduce((a, it) => a + slotOf(it), 0);
		const revY = H * 0.16;
		let x = cx - totalW / 2;
		for (const it of revItems) {
			const r = rOf(it);
			const slot = slotOf(it);
			const nx = x + slot / 2;
			nodes.push({
				key: 'rev:' + (it.sh ? it.sh.name : 'person'),
				x: nx,
				y: revY,
				r,
				kind: it.sh ? 'reverseNamed' : 'reversePerson',
				h: null,
				sh: it.sh,
				person: it.person,
				code: it.sh?.code ?? null
			});
			edges.push({ key: 'reve:' + nx, x1: nx, y1: revY + r, x2: cx, y2: focalY - focal.r, w: Math.max(0.8, (it.ratio / 100) * 5 + 0.8), dashed: !it.sh, up: true });
			x += slot;
		}
	}

	// ── forward band (아래) — tier 레인, 장부가 desc 좌→우, perLane 초과는 capsule ──
	const tiers = NET_TIERS.filter((t) => rows.some((h) => h.tier === t));
	const bandTop = H * 0.47;
	const bandBot = H * 0.93; // 하단 라벨 거터(2줄: 회사명+지분%) — 캔버스 밖 잘림 방지
	const laneSpan = tiers.length ? (bandBot - bandTop) / tiers.length : 0;
	const padL = 96; // 좌측 레인 라벨 공간
	tiers.forEach((tier, li) => {
		const y0 = bandTop + laneSpan * li;
		const cy = y0 + laneSpan / 2;
		const items = rows.filter((h) => h.tier === tier);
		lanes.push({ tier, y: y0 + 4, cy, count: items.length, book: items.reduce((a, h) => a + (h.bookValue ?? 0), 0) });
		const full = items.slice(0, perLane);
		const rest = items.slice(perLane);
		const gap = 16;
		const rOf = (h: HoldingsRow) => sqrtR(h.bookValue ?? 0, maxBook, 9, 22); // 최소 9 — 단순 레인 작은 노드도 또렷이
		const slotOf = (h: HoldingsRow) => Math.max(rOf(h) * 2 + gap, labelW(h.name, 11)); // 라벨 폭만큼 슬롯 확보 → 회사명 안 겹침
		const baseW = full.reduce((a, h) => a + slotOf(h), 0) + (rest.length ? 80 : 0);
		const avail = W - padL - 18;
		const scale = baseW > avail && baseW > 0 ? avail / baseW : 1;
		let x = padL + Math.max(0, (avail - baseW * scale) / 2); // 레인 내 가로 중앙 정렬
		for (const h of full) {
			const slot = slotOf(h) * scale;
			const r = rOf(h) * scale;
			const nx = x + slot / 2;
			nodes.push({ key: 'fwd:' + h.name, x: nx, y: cy, r, kind: 'forward', h, sh: null, person: null, code: h.code });
			edges.push({ key: 'fwde:' + h.name, x1: cx, y1: focalY + focal.r, x2: nx, y2: cy - r, w: Math.max(0.6, ((h.stakePct ?? 0) / 100) * 4 + 0.6), dashed: h.stakePct == null, up: false });
			x += slot;
		}
		if (rest.length) capsules.push({ tier, x: Math.min(x + 6, W - 64), y: cy, count: rest.length, book: rest.reduce((a, h) => a + (h.bookValue ?? 0), 0) });
	});

	return { focal, nodes, edges, capsules, lanes };
}
