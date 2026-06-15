<script lang="ts">
	// 타법인 출자 관계 분석 — 전체화면 다이얼로그. 신규 능력 0: 3축 진단은 전부 lib/holdings.ts(렌더 0 계산
	// 모듈) 산물(공동배선 = 퍼블릭·로컬 동일). 모달 크롬은 전역 .scrimWrap/.scrModal/.scrHead 재사용, 표는 finTable.
	// 정직: 매수/매도·목표주가·인과 금지. 결손(null)은 0 으로 뭉개지 않고 '—'/분리. parentNet 미상이면 contribShare 생략.
	import type { Company, Lang } from '../lib/types';
	import type { InvestmentRow, InvestmentTrendYear } from '@dartlab/ui-contracts';
	import { scaleLog } from 'd3-scale';
	import { buildHoldingsModel, type ListedLookup, type HoldingTier, type HoldingsRow } from '../lib/holdings';
	import { fmtKRW } from '../lib/engine';

	interface Props {
		co: Company;
		year: string;
		rows: InvestmentRow[];
		trend: InvestmentTrendYear[];
		lang: Lang;
		lookupListed: ListedLookup;
		onPick: (code: string) => void;
		onClose: () => void;
	}
	let { co, year, rows, trend, lang, lookupListed, onPick, onClose }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	// 본체 재무 주입(원) — 시총 = 캔들 보정 mktcapRaw(원). 순익은 시총/PER 근사(둘 다 원 → 단위 안전).
	// PER null·≤0(적자·미산출)면 parentNet=null → contribShare 자동 생략(정직, 0 대체 금지).
	const parentMktcap = $derived(co.price.mktcapRaw ?? null);
	const parentNet = $derived(co.fundamentals.per && co.fundamentals.per > 0 && co.price.mktcapRaw ? co.price.mktcapRaw / co.fundamentals.per : null);
	const m = $derived(buildHoldingsModel(year, rows, lookupListed, parentMktcap, parentNet));

	const TIER_LABEL: Record<HoldingTier, { kr: string; en: string; cls: string }> = {
		consolidated: { kr: '연결', en: 'CONS', cls: 'tUp' },
		equity: { kr: '지분법', en: 'EQ', cls: 'tGood' },
		simple: { kr: '단순', en: 'SIMPLE', cls: 'tNeu' },
		unknown: { kr: '분류불가', en: 'n/a', cls: 'tNeu' }
	};
	const krw = (v: number | null) => (v == null ? '—' : fmtKRW(v));
	const ratioCls = (r: number | null, mid = 1) => (r == null ? 'tNeu' : r > mid ? 'tUp' : r < mid ? 'tDn' : 'tNeu');
	const trendMax = $derived(Math.max(...trend.map((t) => t.bookTotal ?? 0), 1));
	// 위계 맵 — 이익기여 부호 색(흑자 녹/적자 적/미상 회) + 법인명 축약.
	const signColor = (v: number | null) => (v == null ? 'var(--dim)' : v > 0 ? 'var(--up)' : v < 0 ? 'var(--dn)' : 'var(--dim)');
	const clip = (s: string, n = 6) => {
		const c = (s || '').replace(/\(주\)|㈜|주식회사/g, '').trim();
		return c.length > n ? c.slice(0, n - 1) + '…' : c;
	};

	// 출자 관계망 — 결정론 radial(physics 0, dartwings 구조 복원): 중앙=본체, 동심원 거리=지분 위계,
	// parent→child 엣지(굵기=지분%), 노드 크기=장부가(log — 1000배 편차 변별), 색=이익기여 부호·강도.
	let mapW = $state(0);
	let hoverName = $state<string | null>(null);
	const MAP_H = 620;
	const TIER_ORDER: HoldingTier[] = ['consolidated', 'equity', 'simple', 'unknown'];
	const RING: Record<HoldingTier, number> = { consolidated: 0.4, equity: 0.66, simple: 0.92, unknown: 0.92 };
	const edgeW = (pct: number | null) => (pct == null ? 0.5 : 0.5 + (pct / 100) * 2.5);
	const radial = $derived.by(() => {
		const W = mapW;
		if (!W) return null;
		const H = MAP_H;
		const cx0 = W / 2;
		const cy0 = H / 2;
		const Rbase = Math.min(W, H) / 2 - 56;
		const posBooks = m.rows.map((r) => r.bookValue).filter((v): v is number => v != null && v > 0);
		const bMin = Math.max(posBooks.length ? Math.min(...posBooks) : 1, 1e7);
		const size = scaleLog().domain([bMin, Math.max(m.maxBook, bMin * 10)]).range([5, 30]).clamp(true);
		const maxEarn = Math.max(...m.rows.map((r) => Math.abs(r.equityEarn ?? 0)), 1);
		const nodes: { h: HoldingsRow; cx: number; cy: number; r: number; ei: number; ang: number }[] = [];
		const ringsOut: { key: HoldingTier; R: number }[] = [];
		for (const key of TIER_ORDER) {
			const items = m.rows.filter((h) => h.tier === key); // 이미 장부가 desc
			const n = items.length;
			if (!n) continue;
			const R = RING[key] * Rbase;
			ringsOut.push({ key, R });
			const cap = Math.max(Math.floor((2 * Math.PI * R) / 28), 1); // 균등각 수용량 — 초과시 2겹
			items.forEach((h, i) => {
				const ang = -Math.PI / 2 + (2 * Math.PI * (i + 0.5)) / n;
				const RR = R + (n > cap ? (i % 2) * 22 : 0);
				nodes.push({ h, cx: cx0 + RR * Math.cos(ang), cy: cy0 + RR * Math.sin(ang), r: size(h.bookValue ?? bMin), ei: Math.min(Math.abs(h.equityEarn ?? 0) / maxEarn, 1), ang });
			});
		}
		const labelSet = new Set(m.rows.slice(0, 8).map((h) => h.name)); // 장부가 상위 8 상시 라벨(나머지는 호버)
		return { W, H, cx0, cy0, nodes, ringsOut, labelSet };
	});

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal hdModal" role="dialog" aria-modal="true" aria-label={T('출자 관계 분석', 'holdings analysis')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('출자 관계 분석', 'HOLDINGS — relationship analysis')} · {co.name.kr} · {m.year}</span>
			<span class="hdSub dim">{T('피출자사', 'holdings')} {m.rows.length}{T('개', '')} · {T('장부가 합', 'book')} {krw(m.bookTotal)}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="hdBody">
			<!-- 3축 요약: ① 성격·위계(tier) ② 가치(상장지분 시가·본체비중) ③ 효율(이익기여·본체순익비중) -->
			<div class="hdSummary">
				<div class="hdSumCard">
					<div class="hdSumLbl">{T('성격 · 위계', 'TIER')}</div>
					<div class="hdTierRow">
						{#if m.counts.consolidated}<span class="hdTier tUp">{T('연결', 'cons')} {m.counts.consolidated}</span>{/if}
						{#if m.counts.equity}<span class="hdTier tGood">{T('지분법', 'eq')} {m.counts.equity}</span>{/if}
						{#if m.counts.simple}<span class="hdTier tNeu">{T('단순', 'simple')} {m.counts.simple}</span>{/if}
						{#if m.counts.unknown}<span class="hdTier tNeu">{T('분류불가', 'n/a')} {m.counts.unknown}</span>{/if}
					</div>
					<div class="hdSumSub dim">{T('상장', 'listed')} {m.counts.listed} · {T('비상장', 'unlisted')} {m.counts.unlisted}{m.counts.loss ? ' · ' + T('적자피출자', 'loss') + ' ' + m.counts.loss : ''}</div>
				</div>
				<div class="hdSumCard">
					<div class="hdSumLbl">{T('가치 — 상장 보유지분 시가', 'VALUE — listed stake')}</div>
					<div class="hdSumV mono">{krw(m.listedStakeSum)}</div>
					<div class="hdSumSub dim">{m.pctOfParentCap != null ? T('본체 시총 대비 ', 'of parent cap ') + m.pctOfParentCap.toFixed(1) + '%' : T('본체 시총 대비 — (미산출)', 'parent cap n/a')}</div>
				</div>
				<div class="hdSumCard">
					<div class="hdSumLbl">{T('효율 — 지분법 이익기여(근사)', 'EFFICIENCY — equity earnings (approx)')}</div>
					<div class={'hdSumV mono ' + (m.sumEquityEarn > 0 ? 'tUp' : m.sumEquityEarn < 0 ? 'tDn' : 'tNeu')}>{krw(m.sumEquityEarn)}</div>
					<div class="hdSumSub dim">{m.contribShare != null ? T('본체 순익 대비 ', 'of parent net ') + m.contribShare.toFixed(1) + '%' : T('본체 순익 대비 — (참고·미산출)', 'parent net n/a')}</div>
				</div>
			</div>

			<!-- 출자 관계망 — 중앙 본체 + 방사형 엣지 + 동심원 지분 위계(dartwings 구조, physics 0 결정론). 노드 호버 → 아래 표 해당 행 강조. -->
			<div class="hdMapSec">
				<div class="hdMapTitle dim">{T('출자 관계망 — 중앙=본체 · 거리=지분 위계(안 연결≥50 / 중 지분법 20~50 / 밖 단순<20) · 크기=장부가(log) · 색=이익기여(녹 흑자 / 적 적자 / 회 미상) · 선=지분% · 실선/채움=상장(클릭 이동) · ★=경영참여', 'Holdings network — center=parent · ring=stake tier · size=book(log) · color=equity earnings · edge=stake% · solid=listed(click) · ★=intent')}</div>
				<div class="hdMapCanvas" bind:clientWidth={mapW}>
					{#if radial}
						<svg width={radial.W} height={radial.H} role="img" aria-label={T('출자 관계망', 'holdings network')}>
							{#each radial.ringsOut as ring (ring.key)}
								<circle cx={radial.cx0} cy={radial.cy0} r={ring.R} fill="none" stroke="var(--bd)" stroke-width="1" stroke-dasharray="2 5" opacity="0.45" />
								<text class="hdRingLab" x={radial.cx0} y={radial.cy0 - ring.R - 5} text-anchor="middle">{T(TIER_LABEL[ring.key].kr, TIER_LABEL[ring.key].en)}</text>
							{/each}
							{#each radial.nodes as n (n.h.name + '@e')}
								<line x1={radial.cx0} y1={radial.cy0} x2={n.cx} y2={n.cy} stroke={hoverName === n.h.name ? 'var(--amber)' : 'var(--bd)'} stroke-width={edgeW(n.h.stakePct)} stroke-opacity={hoverName === n.h.name ? 0.95 : hoverName ? 0.1 : 0.3} stroke-dasharray={n.h.stakePct == null ? '2 2' : 'none'} />
							{/each}
							{#each radial.nodes as n (n.h.name + '@n')}
								{@const tt = n.h.name + ' · ' + (n.h.stakePct != null ? n.h.stakePct.toFixed(1) + '%' : '—') + ' · ' + T('장부', 'book') + ' ' + krw(n.h.bookValue) + (n.h.marketStake != null ? ' · ' + T('시가', 'mkt') + ' ' + krw(n.h.marketStake) : '') + (n.h.equityEarn != null ? ' · ' + T('이익기여', 'earn') + ' ' + (n.h.equityEarn < 0 ? '-' : '') + fmtKRW(Math.abs(n.h.equityEarn)) : '')}
								{#if n.h.code}
									<circle class="hdNode click" cx={n.cx} cy={n.cy} r={n.r} fill={signColor(n.h.equityEarn)} fill-opacity={hoverName && hoverName !== n.h.name ? 0.2 : 0.5 + 0.45 * n.ei} stroke="var(--txt)" stroke-width={n.h.intent ? 2.4 : 1} role="button" tabindex={0} aria-label={n.h.name} onmouseenter={() => (hoverName = n.h.name)} onmouseleave={() => (hoverName = null)} onclick={() => onPick(n.h.code!)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(n.h.code!); } }}><title>{tt}</title></circle>
								{:else}
									<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
									<circle class="hdNode" cx={n.cx} cy={n.cy} r={n.r} fill={signColor(n.h.equityEarn)} fill-opacity={hoverName && hoverName !== n.h.name ? 0.15 : 0.4 + 0.4 * n.ei} stroke="var(--bd)" stroke-width={n.h.intent ? 2.4 : 1} stroke-dasharray="2 2" role="img" aria-label={n.h.name} onmouseenter={() => (hoverName = n.h.name)} onmouseleave={() => (hoverName = null)}><title>{tt}</title></circle>
								{/if}
							{/each}
							{#each radial.nodes as n (n.h.name + '@l')}
								{#if radial.labelSet.has(n.h.name) || hoverName === n.h.name}
									<text class={'hdNodeLab' + (hoverName === n.h.name ? ' hl' : '')} x={n.cx + (n.r + 6) * Math.cos(n.ang)} y={n.cy + (n.r + 6) * Math.sin(n.ang) + 3} text-anchor={Math.cos(n.ang) >= 0 ? 'start' : 'end'}>{clip(n.h.name, 9)}</text>
								{/if}
							{/each}
							<circle cx={radial.cx0} cy={radial.cy0} r="26" fill="var(--panel)" stroke="var(--amber)" stroke-width="2" />
							<text class="hdParentLab" x={radial.cx0} y={radial.cy0 + 3} text-anchor="middle">{clip(co.name.kr, 7)}</text>
						</svg>
					{/if}
				</div>
				{#if m.counts.listed === 0}
					<div class="hdMapNote dim">{T('상장 피출자사 0 — 시가 환산·노드 클릭 이동 해당 없음(전부 비상장 종속). 색=이익기여 근사(확정손익 아님).', 'No listed investees — market value & click-through N/A (all unlisted). Color = approx equity earnings (not realized P/L).')}</div>
				{/if}
			</div>

			{#if trend.length > 1}
				<!-- 출자 추이 — 장부가 합 연도별(자본 잠김 방향). 그래프 금지 구역 아님(다이얼로그 = 중앙 확장) -->
				<div class="hdTrend">
					<span class="hdTrendLbl dim">{T('출자 장부가 추이', 'book trend')}</span>
					{#each trend as t (t.year)}
						<div class="hdTrendBar" title={`${t.year} · ${krw(t.bookTotal)} · ${t.count}${T('사', '')}`}>
							<div class="hdTrendFill" style={`height:${Math.round(((t.bookTotal ?? 0) / trendMax) * 100)}%`}></div>
							<span class="hdTrendYr">{t.year.slice(2)}</span>
						</div>
					{/each}
				</div>
			{/if}

			<div class="hdScroll">
				<table class="finTable hdTable">
					<thead>
						<tr>
							<th class="finAcct">{T('법인명', 'COMPANY')}</th>
							<th>{T('성격', 'TIER')}</th>
							<th class="r">{T('지분', 'STAKE')}</th>
							<th class="r">{T('장부가', 'BOOK')}</th>
							<th class="r">{T('시가지분', 'MKT STAKE')}</th>
							<th class="r" title={T('시가/장부 (>1 숨은가치, <1 잠재손상) — 상장만', 'market/book')}>{T('시가/장부', 'M/B')}</th>
							<th class="r" title={T('장부/취득 (>1 평가이익 누적, <1 손상가능)', 'book/cost')}>{T('장부/취득', 'B/C')}</th>
							<th class="r">{T('피출자 순익', 'TGT NET')}</th>
							<th class="r" title={T('지분법 이익기여 근사 (지분% × 피출자순익)', 'equity earnings approx')}>{T('이익기여', 'EQ EARN')}</th>
							<th class="r" title={T('이익기여/장부가', 'eq earn / book')}>{T('투자ROIC', 'iROIC')}</th>
						</tr>
					</thead>
					<tbody>
						{#each m.rows as h, i (h.name + '#' + i)}
							<tr class={(h.tier === 'consolidated' ? 'finKey ' : '') + (hoverName === h.name ? 'hlRow' : '')}>
								<td class="finAcct" title={h.purpose}>
									{#if h.code}
										<button type="button" class="hdLink" onclick={() => onPick(h.code!)}>{h.name}</button>
									{:else}{h.name}{/if}
									{#if h.intent}<span class="hdIntent" title={T('경영참여 의사', 'management intent')}>{T('경영참여', 'intent')}</span>{/if}
								</td>
								<td><span class={'hdTierMini ' + TIER_LABEL[h.tier].cls}>{T(TIER_LABEL[h.tier].kr, TIER_LABEL[h.tier].en)}</span></td>
								<td class="r mono">{h.stakePct != null ? h.stakePct.toFixed(1) + '%' : '—'}</td>
								<td class="r mono">{krw(h.bookValue)}</td>
								<td class="r mono">{krw(h.marketStake)}</td>
								<td class={'r mono ' + ratioCls(h.gapRatio)}>{h.gapRatio != null ? h.gapRatio.toFixed(2) + '×' : '—'}</td>
								<td class={'r mono ' + ratioCls(h.markRatio)}>{h.markRatio != null ? h.markRatio.toFixed(2) + '×' : '—'}</td>
								<td class={'r mono ' + (h.targetNet != null && h.targetNet < 0 ? 'tDn' : '')}>{h.targetNet != null ? (h.targetNet < 0 ? '-' : '') + fmtKRW(Math.abs(h.targetNet)) : '—'}</td>
								<td class={'r mono ' + (h.equityEarn != null && h.equityEarn < 0 ? 'tDn' : h.equityEarn != null && h.equityEarn > 0 ? 'tUp' : '')}>{h.equityEarn != null ? (h.equityEarn < 0 ? '-' : '') + fmtKRW(Math.abs(h.equityEarn)) : '—'}</td>
								<td class={'r mono ' + (h.investROIC != null ? (h.investROIC > 0 ? 'tUp' : h.investROIC < 0 ? 'tDn' : 'tNeu') : 'tNeu')}>{h.investROIC != null ? (h.investROIC * 100).toFixed(1) + '%' : '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<div class="hdNote dim">
				{T(
					'report · 타법인 출자현황. 이익기여는 지분법 근사(내부거래·공정가치 미반영), 시가지분은 상장 해소된 피출자사만, 피출자 순익은 최근 1기 단일값. 미해소·null 은 0 대체 없이 분리 표기. 판정·목표주가 아님.',
					'report · holdings. Equity earnings are an approximation; market stake covers listed holdings only; target net is the latest single period. Nulls are not coerced to zero. Not a verdict or price target.'
				)}
			</div>
		</div>
	</div>
</div>

<style>
	.hdModal {
		width: min(1100px, 96vw);
		max-height: 90vh;
		display: flex;
		flex-direction: column;
	}
	.hdSub {
		font-size: 10px;
		margin-left: auto;
		margin-right: 10px;
	}
	.hdBody {
		overflow: auto;
		padding: 10px 12px 12px;
	}
	.hdSummary {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
		margin-bottom: 10px;
	}
	.hdSumCard {
		border: 1px solid var(--bd);
		border-radius: 3px;
		padding: 7px 9px;
		background: var(--dl-bg-base, rgba(255, 255, 255, 0.02));
	}
	.hdSumLbl {
		font-size: 9px;
		color: var(--dim);
		letter-spacing: 0.4px;
		text-transform: uppercase;
		margin-bottom: 4px;
	}
	.hdSumV {
		font-size: 15px;
		font-weight: 700;
	}
	.hdSumSub {
		font-size: 9.5px;
		margin-top: 2px;
	}
	.hdTierRow {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.hdTier {
		font-size: 11px;
		font-weight: 700;
		border: 1px solid currentColor;
		border-radius: 2px;
		padding: 1px 5px;
	}
	.hdTrend {
		display: flex;
		align-items: flex-end;
		gap: 4px;
		height: 56px;
		margin-bottom: 10px;
		padding-left: 4px;
	}
	.hdTrendLbl {
		font-size: 9px;
		align-self: center;
		writing-mode: horizontal-tb;
		margin-right: 6px;
		white-space: nowrap;
	}
	.hdTrendBar {
		position: relative;
		width: 22px;
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		align-items: center;
	}
	.hdTrendFill {
		width: 14px;
		background: var(--good, #5b9bf0);
		opacity: 0.7;
		border-radius: 1px 1px 0 0;
		min-height: 1px;
	}
	.hdTrendYr {
		font-size: 8px;
		color: var(--dim);
		margin-top: 1px;
	}
	.hdScroll {
		overflow-x: auto;
	}
	.hdTable {
		width: 100%;
		font-size: 11px;
	}
	.hdLink {
		background: none;
		border: none;
		color: var(--accent, #5b9bf0);
		cursor: pointer;
		padding: 0;
		font: inherit;
		text-align: left;
	}
	.hdLink:hover {
		text-decoration: underline;
	}
	.hdIntent {
		font-size: 8px;
		color: var(--amber, #fb923c);
		border: 1px solid rgba(251, 146, 60, 0.4);
		border-radius: 2px;
		padding: 0 3px;
		margin-left: 5px;
		vertical-align: 1px;
	}
	.hdTierMini {
		font-size: 9.5px;
		font-weight: 700;
	}
	.hdNote {
		font-size: 9px;
		line-height: 1.5;
		margin-top: 8px;
		padding-top: 6px;
		border-top: 1px solid var(--bd);
	}
	.hdMapSec {
		margin-bottom: 10px;
	}
	.hdMapTitle {
		font-size: 9px;
		margin-bottom: 5px;
		line-height: 1.35;
	}
	.hdMapCanvas {
		background: var(--dl-bg-base, rgba(255, 255, 255, 0.02));
		border: 1px solid var(--bd);
		border-radius: 3px;
		padding: 2px;
		display: flex;
		justify-content: center;
	}
	.hdNode {
		transition: fill-opacity 0.12s;
	}
	.hdNode.click {
		cursor: pointer;
	}
	.hdNode.click:hover {
		stroke: var(--amber, #fb923c);
	}
	.hdNodeLab {
		font-size: 9px;
		fill: var(--txt);
		paint-order: stroke;
		stroke: var(--dl-bg-base, #05070d);
		stroke-width: 2.5px;
		pointer-events: none;
	}
	.hdNodeLab.hl {
		fill: var(--amber, #fb923c);
		font-weight: 700;
	}
	.hdRingLab {
		font-size: 8.5px;
		fill: var(--dimmer, #6b7280);
		font-weight: 600;
	}
	.hdParentLab {
		font-size: 10px;
		fill: var(--txt);
		font-weight: 700;
		pointer-events: none;
	}
	.hdMapNote {
		font-size: 9px;
		margin-top: 5px;
		line-height: 1.4;
	}
	.hdTable tbody tr.hlRow {
		background: rgba(251, 146, 60, 0.13);
	}
</style>
