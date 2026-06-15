<script lang="ts">
	// 타법인 출자 관계 분석 — 전체화면 다이얼로그. 신규 능력 0: 3축 진단은 전부 lib/holdings.ts(렌더 0 계산
	// 모듈) 산물(공동배선 = 퍼블릭·로컬 동일). 모달 크롬은 전역 .scrimWrap/.scrModal/.scrHead 재사용, 표는 finTable.
	// 정직: 매수/매도·목표주가·인과 금지. 결손(null)은 0 으로 뭉개지 않고 '—'/분리. parentNet 미상이면 contribShare 생략.
	import type { Company, Lang } from '../lib/types';
	import type { InvestmentRow, InvestmentTrendYear } from '@dartlab/ui-contracts';
	import { scaleSqrt } from 'd3-scale';
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

	// 위계 맵 packed 레이아웃 — 결정론(physics 0) 레인별 노드 배치. 레인 = 회계 경계, 노드 = 출자처.
	let mapW = $state(0);
	const sizeScale = $derived(scaleSqrt().domain([0, Math.max(m.maxBook, 1)]).range([5, 24]));
	const TIER_ORDER: HoldingTier[] = ['consolidated', 'equity', 'simple', 'unknown'];
	const mapLanes = $derived.by(() => {
		const W = mapW;
		if (!W) return { lanes: [] as { key: HoldingTier; count: number; book: number; headerY: number; nodes: { h: HoldingsRow; cx: number; cy: number; r: number }[] }[], totalH: 0 };
		const headerH = 22;
		const pad = 9;
		const gap = 6;
		let y = 0;
		const lanes = [];
		for (const key of TIER_ORDER) {
			const items = m.rows.filter((h) => h.tier === key);
			if (!items.length) continue;
			const headerY = y;
			y += headerH;
			let x = pad;
			let rowMax = 0;
			let top = y;
			const nodes = [];
			for (const h of items) {
				const r = sizeScale(h.bookValue ?? 0);
				const d = r * 2;
				if (x + d + pad > W) {
					x = pad;
					top += rowMax + gap;
					rowMax = 0;
				}
				nodes.push({ h, cx: x + r, cy: top + r, r });
				x += d + gap;
				if (d > rowMax) rowMax = d;
			}
			y = top + rowMax + pad;
			lanes.push({ key, count: items.length, book: items.reduce((a, h) => a + (h.bookValue ?? 0), 0), headerY, nodes });
			y += gap;
		}
		return { lanes, totalH: y };
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

			<!-- 지배력 위계 맵 — 관계 구조 시각화(radial 폐기, 결정론 레인 packed). 아래 표 = 정밀 수치. -->
			<div class="hdMapSec">
				<div class="hdMapTitle dim">{T('지배력 위계 맵 — 크기=장부가 · 색=이익기여(녹 흑자 / 적 적자 / 회 미상) · 실선=상장(클릭 이동) · ★굵은테두리=경영참여', 'Control hierarchy — size=book · color=earnings(green/red) · solid ring=listed(click) · bold ring=intent')}</div>
				<div class="hdMapCanvas" bind:clientWidth={mapW}>
					{#if mapW}
						<svg width={mapW} height={mapLanes.totalH} role="img" aria-label={T('출자 위계 맵', 'holdings hierarchy map')}>
							{#each mapLanes.lanes as lane (lane.key)}
								<text class="hdLaneLab" x="3" y={lane.headerY + 15}>{T(TIER_LABEL[lane.key].kr, TIER_LABEL[lane.key].en)} · {lane.count}{T('사', '')} · {krw(lane.book)}</text>
								{#each lane.nodes as n (n.h.name + '@' + n.cx)}
									{@const tt = n.h.name + ' · ' + (n.h.stakePct != null ? n.h.stakePct.toFixed(1) + '%' : '—') + ' · ' + T('장부', 'book') + ' ' + krw(n.h.bookValue) + (n.h.marketStake != null ? ' · ' + T('시가', 'mkt') + ' ' + krw(n.h.marketStake) : '') + (n.h.equityEarn != null ? ' · ' + T('이익기여', 'earn') + ' ' + (n.h.equityEarn < 0 ? '-' : '') + fmtKRW(Math.abs(n.h.equityEarn)) : '')}
									{#if n.h.code}
										<!-- 상장 해소 노드 = 클릭/키보드로 종목 이동 (role=button·tabindex 정적 보장). -->
										<circle class="hdMapNode click" cx={n.cx} cy={n.cy} r={n.r} fill={signColor(n.h.equityEarn)} fill-opacity="0.9" stroke="var(--txt)" stroke-width={n.h.intent ? 2.2 : 1} role="button" tabindex={0} aria-label={n.h.name} onclick={() => onPick(n.h.code!)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(n.h.code!); } }}><title>{tt}</title></circle>
									{:else}
										<circle class="hdMapNode" cx={n.cx} cy={n.cy} r={n.r} fill={signColor(n.h.equityEarn)} fill-opacity="0.45" stroke="var(--bd)" stroke-width={n.h.intent ? 2.2 : 1} stroke-dasharray="2 2" aria-label={n.h.name}><title>{tt}</title></circle>
									{/if}
									{#if n.r >= 13}<text class="hdMapNodeLab" x={n.cx} y={n.cy + 3} text-anchor="middle">{clip(n.h.name, 6)}</text>{/if}
								{/each}
							{/each}
						</svg>
					{/if}
				</div>
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
							<tr class={h.tier === 'consolidated' ? 'finKey' : ''}>
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
		max-height: 300px;
		overflow-y: auto;
	}
	.hdLaneLab {
		font-size: 10.5px;
		font-weight: 700;
		fill: var(--txt);
	}
	.hdMapNode {
		transition: fill-opacity 0.1s;
	}
	.hdMapNode.click {
		cursor: pointer;
	}
	.hdMapNode.click:hover {
		fill-opacity: 1;
		stroke: var(--amber, #fb923c);
	}
	.hdMapNodeLab {
		font-size: 8px;
		fill: var(--dl-bg-deep, #05070d);
		font-weight: 700;
	}
</style>
