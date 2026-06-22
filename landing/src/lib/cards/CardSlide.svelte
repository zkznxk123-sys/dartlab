<script lang="ts">
	// 한 슬라이드 렌더 — CarouselCard 종류별 분기. 차트는 $lib/report/render 순수 SVG 헬퍼로 그려
	// klinecharts·백테스트 0 의존(백본). finChart 만 MiniFinChart(finance.bundle) 로 재무 추이 재현.
	import type { DartLabRuntime, FinCard } from '@dartlab/ui-contracts';
	import { MiniFinChart } from '@dartlab/ui-surfaces/terminal';
	import { cellTone, verdictTone, TXT_COLS, spark, isTimeSeries, lineGeo, wonLabel } from '$lib/report/render';
	import type { CarouselCard } from './model';

	let { card, rt }: { card: CarouselCard; rt: DartLabRuntime } = $props();

	// finChart — finance.bundle 의 첫 1~2 카드를 MiniFinChart 로(없으면 정직 폴백).
	let finCards = $state<{ card: FinCard; periods: string[] } | null>(null);
	let finState = $state<'idle' | 'loading' | 'ready' | 'empty'>('idle');
	$effect(() => {
		if (card.kind !== 'finChart') return;
		finState = 'loading';
		const code = card.stockCode;
		rt.finance
			.bundle(code)
			.then((b) => {
				const view = b?.views?.annual ?? Object.values(b?.views ?? {}).find(Boolean);
				const c = view?.cards?.[0];
				if (c && view) {
					finCards = { card: c, periods: view.periods };
					finState = 'ready';
				} else finState = 'empty';
			})
			.catch(() => (finState = 'empty'));
	});

	// line/bars/share 기하 — report 와 동일 헬퍼.
	const line = $derived(card.kind === 'line' ? lineGeo(card.series, card.markers ?? []) : null);
	const barMax = $derived(card.kind === 'bars' ? Math.max(1, ...card.rows.map((r) => Math.abs(r.value))) : 1);
	const SHARE_C = ['#5b9bf0', '#34d399', '#fbbf24', '#a78bfa', '#f0616f', '#22d3ee', '#64748b'];
	function shareColor(i: number) {
		return SHARE_C[i % SHARE_C.length];
	}
</script>

<article class="slide kind-{card.kind}" aria-roledescription="slide">
	{#if card.heading}
		<header class="sHead">
			<h3>{card.heading}</h3>
			{#if card.sub}<p class="sSub">{card.sub}</p>{/if}
		</header>
	{/if}

	{#if card.kind === 'cover'}
		<div class="cover" class:hasHero={!!card.heroUrl}>
			{#if card.heroUrl}
				<img class="hero" src={card.heroUrl} alt={card.corpName} loading="lazy" />
			{/if}
			<div class="coverBody">
				<p class="cPersp">{card.perspectiveLabel}</p>
				<h2 class="cName">{card.corpName}</h2>
				<p class="cCode">{card.stockCode} · {card.dataBasis}</p>
				<p class="cConcl">{card.conclusion}</p>
			</div>
		</div>
	{:else if card.kind === 'kpis'}
		<div class="kpis">
			{#each card.metrics as m (m.label)}
				<div class="kpi">
					<span class="kLabel">{m.label}</span>
					<span class="kVal {cellTone(m.value)}">{m.value}</span>
				</div>
			{/each}
		</div>
	{:else if card.kind === 'narrative'}
		<p class="narr">{card.text}</p>
	{:else if card.kind === 'flags'}
		<ul class="flags {card.tone}">
			{#each card.items as f}<li>{f}</li>{/each}
		</ul>
	{:else if card.kind === 'line' && line}
		<div class="chart">
			<svg viewBox="0 0 100 30" preserveAspectRatio="none" class="lineChart">
				<polygon points={line.area} class="lArea" />
				<polyline points={line.pts} class="lLine" />
				{#each line.mk as m}
					<line x1="0" x2="100" y1={m.y} y2={m.y} class="lMark" />
				{/each}
				<circle cx={line.lastX} cy={line.lastY} r="0.9" class="lDot" />
			</svg>
			{#if card.markers?.length}
				<div class="lMarkers">
					{#each card.markers as m}<span>{m.label} {card.valueFmt === 'won' ? wonLabel(m.v) : m.v}</span>{/each}
				</div>
			{/if}
		</div>
	{:else if card.kind === 'bars'}
		<div class="bars">
			{#each card.rows as r (r.label)}
				<div class="bar">
					<span class="bLabel">{r.label}</span>
					<span class="bTrack"><span class="bFill" class:neg={r.tone === 'neg'} style="width:{(Math.abs(r.value) / barMax) * 100}%"></span></span>
					<span class="bVal">{r.display}</span>
				</div>
			{/each}
		</div>
	{:else if card.kind === 'share'}
		<div class="share">
			{#each card.rows as row (row.year)}
				<div class="shRow">
					<span class="shYear">{row.year}</span>
					<span class="shBar">
						{#each row.segs as s (s.key)}
							<span class="shSeg" style="width:{s.pct}%;background:{shareColor(card.legend.findIndex((l) => l.key === s.key))}" title="{s.label} {s.pct}%"></span>
						{/each}
					</span>
				</div>
			{/each}
			<div class="shLegend">
				{#each card.legend as l, i (l.key)}<span class="shLi"><i style="background:{shareColor(i)}"></i>{l.label}</span>{/each}
			</div>
		</div>
	{:else if card.kind === 'table'}
		<div class="tableWrap">
			<table class="cTable">
				<thead><tr>{#each card.cols as c}<th class:num={c !== card.cols[0]}>{c}</th>{/each}{#if isTimeSeries(card.cols)}<th class="num">추이</th>{/if}</tr></thead>
				<tbody>
					{#each card.data as row}
						{@const sp = spark(row, card.cols.slice(1))}
						<tr>
							{#each card.cols as c, ci}
								<td class:num={ci !== 0} class="{ci === 0 || TXT_COLS.has(c) ? verdictTone(row[c]) : cellTone(row[c])}">{row[c] ?? '-'}</td>
							{/each}
							{#if isTimeSeries(card.cols)}
								<td class="num spk">
									{#if sp}
										<svg viewBox="0 0 64 22" class="spark"><polygon points={sp.area} class="spkArea" /><polyline points={sp.points} class="spkLine" /></svg>
									{/if}
								</td>
							{/if}
						</tr>
					{/each}
				</tbody>
			</table>
			{#if card.unit}<p class="tUnit">단위: {card.unit}</p>{/if}
		</div>
	{:else if card.kind === 'finChart'}
		<div class="finWrap">
			{#if finState === 'ready' && finCards}
				<MiniFinChart card={finCards.card} periods={finCards.periods} h={220} />
			{:else if finState === 'loading'}
				<p class="muted">재무 추이 불러오는 중…</p>
			{:else}
				<p class="muted">재무 추이 데이터가 아직 없습니다.</p>
			{/if}
		</div>
	{:else if card.kind === 'closing'}
		<blockquote class="closing">{card.thesis}</blockquote>
	{:else if card.kind === 'empty'}
		<div class="empty">
			<p>{card.reason}</p>
		</div>
	{/if}
</article>

<style>
	.slide {
		display: flex;
		flex-direction: column;
		gap: 14px;
		width: 100%;
		height: 100%;
		padding: 28px 26px;
		box-sizing: border-box;
		color: #e7ecf3;
		overflow: hidden;
	}
	.sHead h3 {
		margin: 0;
		font-size: 13px;
		letter-spacing: 0.04em;
		color: #9fb0c4;
		text-transform: uppercase;
	}
	.sSub {
		margin: 2px 0 0;
		font-size: 17px;
		font-weight: 600;
		color: #f1f5f9;
	}
	/* cover */
	.cover {
		position: relative;
		flex: 1;
		display: flex;
		align-items: flex-end;
		border-radius: 14px;
		overflow: hidden;
		background: linear-gradient(160deg, #1a2535, #0e1722);
	}
	.cover .hero {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0.9;
	}
	.coverBody {
		position: relative;
		z-index: 1;
		padding: 24px;
		width: 100%;
		background: linear-gradient(0deg, rgba(8, 12, 18, 0.88) 30%, rgba(8, 12, 18, 0) 100%);
	}
	.hasHero .coverBody {
		padding-top: 64px;
	}
	.cPersp {
		margin: 0;
		font-size: 12px;
		color: #7dd3fc;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.cName {
		margin: 4px 0 2px;
		font-size: 30px;
		font-weight: 700;
		line-height: 1.1;
	}
	.cCode {
		margin: 0 0 10px;
		font-size: 12px;
		color: #94a3b8;
	}
	.cConcl {
		margin: 0;
		font-size: 16px;
		line-height: 1.5;
		color: #dbe4ee;
	}
	/* kpis */
	.kpis {
		flex: 1;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
		align-content: center;
	}
	.kpi {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 16px;
		background: #121b27;
		border: 1px solid #1e2a3a;
		border-radius: 12px;
	}
	.kLabel {
		font-size: 12px;
		color: #93a4b8;
	}
	.kVal {
		font-size: 24px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.kVal.neg {
		color: #f0616f;
	}
	.kVal.pos {
		color: #34d399;
	}
	/* narrative */
	.narr {
		flex: 1;
		display: flex;
		align-items: center;
		margin: 0;
		font-size: 19px;
		line-height: 1.65;
		color: #e2e8f0;
	}
	/* flags */
	.flags {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 10px;
		justify-content: center;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.flags li {
		padding: 12px 16px;
		border-radius: 10px;
		font-size: 15px;
		border-left: 3px solid;
	}
	.flags.warning li {
		background: rgba(240, 97, 111, 0.08);
		border-color: #f0616f;
	}
	.flags.opportunity li {
		background: rgba(52, 211, 153, 0.08);
		border-color: #34d399;
	}
	/* line */
	.chart {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 8px;
		justify-content: center;
	}
	.lineChart {
		width: 100%;
		height: 180px;
	}
	.lArea {
		fill: rgba(91, 155, 240, 0.16);
	}
	.lLine {
		fill: none;
		stroke: #5b9bf0;
		stroke-width: 0.6;
		vector-effect: non-scaling-stroke;
	}
	.lMark {
		stroke: #475569;
		stroke-width: 0.3;
		stroke-dasharray: 1 1;
		vector-effect: non-scaling-stroke;
	}
	.lDot {
		fill: #5b9bf0;
	}
	.lMarkers {
		display: flex;
		gap: 14px;
		font-size: 12px;
		color: #94a3b8;
	}
	/* bars */
	.bars {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 10px;
		justify-content: center;
	}
	.bar {
		display: grid;
		grid-template-columns: 90px 1fr auto;
		gap: 10px;
		align-items: center;
		font-size: 13px;
	}
	.bTrack {
		height: 16px;
		background: #121b27;
		border-radius: 4px;
		overflow: hidden;
	}
	.bFill {
		display: block;
		height: 100%;
		background: #5b9bf0;
	}
	.bFill.neg {
		background: #f0616f;
	}
	.bVal {
		font-variant-numeric: tabular-nums;
		color: #cbd5e1;
	}
	/* share */
	.share {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 8px;
		justify-content: center;
	}
	.shRow {
		display: grid;
		grid-template-columns: 56px 1fr;
		gap: 10px;
		align-items: center;
	}
	.shYear {
		font-size: 12px;
		color: #94a3b8;
	}
	.shBar {
		display: flex;
		height: 18px;
		border-radius: 4px;
		overflow: hidden;
	}
	.shSeg {
		height: 100%;
	}
	.shLegend {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		font-size: 12px;
		color: #94a3b8;
		margin-top: 4px;
	}
	.shLi {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.shLi i {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	/* table */
	.tableWrap {
		flex: 1;
		overflow: auto;
	}
	.cTable {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}
	.cTable th,
	.cTable td {
		padding: 6px 8px;
		text-align: left;
		border-bottom: 1px solid #1a2533;
		white-space: nowrap;
	}
	.cTable th.num,
	.cTable td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.cTable td.neg {
		color: #f0616f;
	}
	.cTable td.pos {
		color: #34d399;
	}
	.cTable td.ok {
		color: #34d399;
	}
	.cTable td.warn {
		color: #fbbf24;
	}
	.spark {
		width: 64px;
		height: 22px;
	}
	.spkArea {
		fill: rgba(125, 211, 252, 0.18);
	}
	.spkLine {
		fill: none;
		stroke: #7dd3fc;
		stroke-width: 1;
		vector-effect: non-scaling-stroke;
	}
	.tUnit {
		margin: 6px 0 0;
		font-size: 11px;
		color: #64748b;
	}
	/* finChart */
	.finWrap {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.muted {
		color: #64748b;
		font-size: 14px;
	}
	/* closing / empty */
	.closing {
		flex: 1;
		display: flex;
		align-items: center;
		margin: 0;
		padding-left: 16px;
		border-left: 3px solid #5b9bf0;
		font-size: 19px;
		line-height: 1.6;
		color: #e2e8f0;
	}
	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #64748b;
		font-size: 15px;
		text-align: center;
	}
</style>
