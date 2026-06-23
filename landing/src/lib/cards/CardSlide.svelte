<script lang="ts">
	// 한 슬라이드 — 인스타 4:5 에디토리얼. 회사 hero 사진을 배경으로 깔고(전 슬라이드), 헤드라인은
	// AccentText(`[[구절]]`=rose-red). 색감·레이아웃은 기존 SNS 캐러셀(colors.ts/PhotoFrame/InsightCard)
	// 재현 — 새로 짓지 않음. 차트는 $lib/report/render 순수 SVG(klinecharts·백테스트 0), finChart 만 MiniFinChart.
	import type { DartLabRuntime, FinCard } from '@dartlab/ui-contracts';
	import { MiniFinChart } from '@dartlab/ui-surfaces/terminal';
	import { CARD, CARD_SERIES, accentParts, stripDots } from './theme';
	import { cellTone, verdictTone, TXT_COLS, spark, isTimeSeries, lineGeo, wonLabel } from '$lib/report/render';
	import type { CarouselCard } from './model';

	let { card, rt }: { card: CarouselCard; rt: DartLabRuntime } = $props();

	// 사진 모드 — 편집 카드=monochrome+강한 하단 그라데이션(기존 SNS editorial), 텍스트=풀, 차트=dim.
	const CHART_KINDS = new Set(['kpis', 'line', 'bars', 'share', 'table', 'finChart']);
	const EDITORIAL_KINDS = new Set(['editorial', 'editorialBeat', 'editorialStat']);
	const photoMode = $derived(
		card.kind === 'cover'
			? 'cover'
			: EDITORIAL_KINDS.has(card.kind)
				? 'editorial'
				: CHART_KINDS.has(card.kind)
					? 'dim'
					: 'full'
	);

	let finCards = $state<{ card: FinCard; periods: string[] } | null>(null);
	let finState = $state<'idle' | 'loading' | 'ready' | 'empty'>('idle');
	$effect(() => {
		if (card.kind !== 'finChart') return;
		finState = 'loading';
		const code = card.stockCode;
		rt.finance
			.bundle(code)
			.then((b) => {
				// 분기 우선(밀도 — 데이터 작업대 기본 결) → 없으면 연간 폴백. FY 표지화 금지.
				const view = b?.views?.quarter ?? b?.views?.annual ?? Object.values(b?.views ?? {}).find(Boolean);
				const c = view?.cards?.[0];
				if (c && view) {
					// 캐러셀 팔레트로 재색(엔진 기본 블루/주황/그린 → 로즈 계열). 데이터·축·구조 불변.
					const recolored = { ...c, series: c.series.map((s, i) => ({ ...s, color: CARD_SERIES[i % CARD_SERIES.length] })) };
					finCards = { card: recolored, periods: view.periods };
					finState = 'ready';
				} else finState = 'empty';
			})
			.catch(() => (finState = 'empty'));
	});

	// 차트 밑에 같이 둘 수치표 — 시리즈(매출·영업이익·순이익…) × 최근 6기간. 정적 카드는 hover 가 없어
	// 차트만으론 정확값을 못 보니 표를 병치(추세=시각, 정확값=표). 우축은 작은 값(예 영업이익)을 큰 매출
	// 막대 옆에 보이게 한 2차 *같은 단위* 스케일이라 % 가 아님 → 단위 접미 없이 원값 그대로(헤더에 단위 1회).
	const finTable = $derived.by(() => {
		if (!finCards) return null;
		const all = finCards.periods;
		const periods = all.slice(-6);
		const off = all.length - periods.length;
		const fmt = (v: unknown): string => {
			if (typeof v !== 'number' || !Number.isFinite(v)) return '–';
			return Math.abs(v) >= 100 ? Math.round(v).toLocaleString() : v.toFixed(1);
		};
		const rows = finCards.card.series.map((s) => ({
			name: s.name,
			values: periods.map((_, i) => fmt(s.data[off + i]))
		}));
		return { unit: finCards.card.unit ?? '', periods, rows };
	});

	const line = $derived(card.kind === 'line' ? lineGeo(card.series, card.markers ?? []) : null);
	const barMax = $derived(card.kind === 'bars' ? Math.max(1, ...card.rows.map((r) => Math.abs(r.value))) : 1);
	// 비중 차트 세그먼트 색 — 캐러셀 팔레트(로즈+그레이)만. 초록/앰버/보라/시안 금지.
	const SHARE_C = ['#ff3f6f', '#ff9ab0', '#d8e2f0', '#9aa7c0', '#6b7794', '#c0cad8', '#7f8aa3'];
	const shareColor = (i: number) => SHARE_C[i % SHARE_C.length];
</script>

{#snippet accent(text: string, cls = '')}
	<span class={cls}>{#each accentParts(stripDots(text)) as p}<span class:hl={p.accent}>{p.text}</span>{/each}</span>
{/snippet}

<article class="slide pm-{photoMode}">
	{#if card.bg}
		<img class="bg" src={card.bg} alt="" loading="lazy" />
		<div class="scrim"></div>
	{/if}

	<div class="content" class:txtSlide={card.kind === 'narrative' || card.kind === 'closing'}>
		{#if card.kind === 'cover'}
			<div class="cover">
				<span class="kicker"><i></i>{card.perspectiveLabel}</span>
				<h2 class="bigName">{card.corpName}</h2>
				<p class="lead">{@render accent(card.conclusion)}</p>
				<p class="mono">{card.stockCode} · {card.dataBasis}</p>
			</div>
		{:else if card.kind === 'editorial' || card.kind === 'editorialBeat'}
			<div class="editorial">
				{#if card.kind === 'editorialBeat' && card.kicker}<span class="eyebrow">{card.kicker}</span>{/if}
				<h2 class="eLine">{@render accent(card.line)}</h2>
				{#if card.sub}<p class="eSub">{stripDots(card.sub)}</p>{/if}
			</div>
		{:else if card.kind === 'editorialStat'}
			<div class="editorial">
				{#if card.kicker}<span class="eyebrow">{card.kicker}</span>{/if}
				<div class="eStat"><span class="eNum">{card.bigNumber}</span>{#if card.unit}<span class="eUnit">{card.unit}</span>{/if}</div>
				{#if card.context}<p class="eSub">{stripDots(card.context)}</p>{/if}
			</div>
		{:else}
			{#if card.heading}
				<header class="sHead">
					<span class="kicker"><i></i>{card.heading}</span>
					{#if card.sub}<p class="sSub">{@render accent(card.sub)}</p>{/if}
				</header>
			{/if}
			{#if card.note}<p class="note">{@render accent(card.note)}</p>{/if}

			{#if card.kind === 'kpis'}
				<div class="kpis">
					{#each card.metrics as m (m.label)}
						<div class="kpi"><span class="kL">{m.label}</span><span class="kV {cellTone(m.value)}">{m.value}</span></div>
					{/each}
				</div>
			{:else if card.kind === 'narrative'}
				<p class="narr">{@render accent(card.text)}</p>
			{:else if card.kind === 'flags'}
				<ul class="flags {card.tone}">{#each card.items as f}<li>{@render accent(f)}</li>{/each}</ul>
			{:else if card.kind === 'line' && line}
				<div class="chart">
					<svg viewBox="0 0 100 30" preserveAspectRatio="none" class="lineChart">
						<polygon points={line.area} class="lArea" />
						<polyline points={line.pts} class="lLine" />
						{#each line.mk as m}<line x1="0" x2="100" y1={m.y} y2={m.y} class="lMark" />{/each}
						<circle cx={line.lastX} cy={line.lastY} r="0.9" class="lDot" />
					</svg>
					{#if card.markers?.length}
						<div class="lMarkers">{#each card.markers as m}<span>{m.label} {card.valueFmt === 'won' ? wonLabel(m.v) : m.v}</span>{/each}</div>
					{/if}
				</div>
			{:else if card.kind === 'bars'}
				<div class="bars">
					{#each card.rows as r (r.label)}
						<div class="bar"><span class="bL">{r.label}</span><span class="bT"><span class="bF" class:neg={r.tone === 'neg'} style="width:{(Math.abs(r.value) / barMax) * 100}%"></span></span><span class="bV">{r.display}</span></div>
					{/each}
				</div>
			{:else if card.kind === 'share'}
				<div class="share">
					{#each card.rows as row (row.year)}
						<div class="shRow"><span class="shY">{row.year}</span><span class="shBar">{#each row.segs as s (s.key)}<span class="shSeg" style="width:{s.pct}%;background:{shareColor(card.legend.findIndex((l) => l.key === s.key))}" title="{s.label} {s.pct}%"></span>{/each}</span></div>
					{/each}
					<div class="shLeg">{#each card.legend as l, i (l.key)}<span class="shLi"><i style="background:{shareColor(i)}"></i>{l.label}</span>{/each}</div>
				</div>
			{:else if card.kind === 'table'}
				<div class="tWrap">
					<table class="cT">
						<thead><tr>{#each card.cols as c}<th class:num={c !== card.cols[0]}>{c}</th>{/each}{#if isTimeSeries(card.cols)}<th class="num">추이</th>{/if}</tr></thead>
						<tbody>
							{#each card.data as row}
								{@const sp = spark(row, card.cols.slice(1))}
								<tr>
									{#each card.cols as c, ci}<td class:num={ci !== 0} class="{ci === 0 || TXT_COLS.has(c) ? verdictTone(row[c]) : cellTone(row[c])}">{row[c] ?? '-'}</td>{/each}
									{#if isTimeSeries(card.cols)}<td class="num">{#if sp}<svg viewBox="0 0 64 22" class="spark"><polygon points={sp.area} class="spkA" /><polyline points={sp.points} class="spkL" /></svg>{/if}</td>{/if}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else if card.kind === 'finChart'}
				<div class="finWrap">
					{#if finState === 'ready' && finCards}
						<MiniFinChart card={finCards.card} periods={finCards.periods} h={190} />
						{#if finTable}
							<table class="cT finT">
								<thead>
									<tr><th class="finUnit">{finTable.unit}</th>{#each finTable.periods as p (p)}<th class="num">{p}</th>{/each}</tr>
								</thead>
								<tbody>
									{#each finTable.rows as r (r.name)}
										<tr><td>{r.name}</td>{#each r.values as v, i (i)}<td class="num">{v}</td>{/each}</tr>
									{/each}
								</tbody>
							</table>
						{/if}
					{:else if finState === 'loading'}<p class="muted">재무 추이 불러오는 중…</p>
					{:else}<p class="muted">재무 추이 데이터가 아직 없습니다.</p>{/if}
				</div>
			{:else if card.kind === 'closing'}
				<blockquote class="closing">{@render accent(card.thesis)}</blockquote>
			{:else if card.kind === 'empty'}
				<div class="empty"><p>{card.reason}</p></div>
			{/if}
		{/if}
	</div>
</article>

<style>
	.slide {
		position: relative;
		width: 100%;
		height: 100%;
		background: #050811;
		color: #f1f5f9;
		overflow: hidden;
		text-align: left; /* 좌측 정렬 못박음 — <button>(CoverThumb) 안에서 text-align:center 상속 차단 */
		container-type: inline-size; /* cqw = 슬라이드 폭 기준 반응형 타이포(인스타 1080 기준 스케일) */
		font-family: 'Pretendard Variable', 'Pretendard', system-ui, sans-serif;
	}
	.bg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.pm-cover .bg {
		opacity: 1;
	}
	.pm-full .bg {
		opacity: 0.74;
	}
	.pm-dim .bg {
		opacity: 0.68; /* 차트 슬라이드도 회사 사진이 또렷이(모든 슬라이드에 이미지) — 차트는 아래 패널로 가독 확보 */
	}
	.scrim {
		position: absolute;
		inset: 0;
	}
	/* 배경 밝게 — 하단만 가독용 어둠, 상·중단은 사진 노출(전체 어둠 금지). */
	.pm-cover .scrim {
		background: linear-gradient(180deg, rgba(5, 8, 17, 0.05) 0%, rgba(5, 8, 17, 0.16) 48%, rgba(5, 8, 17, 0.88) 100%);
	}
	.pm-full .scrim {
		background: linear-gradient(180deg, rgba(5, 8, 17, 0.4) 0%, rgba(5, 8, 17, 0.24) 42%, rgba(5, 8, 17, 0.8) 100%);
	}
	.pm-dim .scrim {
		background: linear-gradient(180deg, rgba(5, 8, 17, 0.36) 0%, rgba(5, 8, 17, 0.24) 45%, rgba(5, 8, 17, 0.58) 100%);
	}
	/* 편집 카드 = 기존 SNS editorial: 사진 monochrome(원본 grayscale) + 하단 그라데이션. 원본 brightness
	   0.48 보다 밝게(사용자 "조금만 밝게") → 1.04. 강조색=로즈. */
	.pm-editorial .bg {
		opacity: 0.96;
		filter: grayscale(0.82) contrast(1.04) brightness(1.04);
	}
	.pm-editorial .scrim {
		background: linear-gradient(180deg, rgba(3, 5, 9, 0.22) 0%, rgba(3, 5, 9, 0.32) 44%, rgba(3, 5, 9, 0.86) 100%);
	}
	.pm-editorial .content {
		--hl: #ff3f6f;
	}
	.content {
		position: relative;
		z-index: 1;
		height: 100%;
		box-sizing: border-box;
		padding: 7% 7.5% 9%;
		display: flex;
		flex-direction: column;
		overflow: hidden; /* 텍스트가 4:5 프레임을 절대 안 넘치게(hook() 단축 + 하드 클립 belt-and-suspenders) */
	}
	/* 다중행 클램프 — 긴 데이터 산문이 카드를 넘치지 않게(인스타 카피는 짧다). 블록 요소만(.narr/.closing
	   는 flex-center 라 .content overflow:hidden + hook() 단축으로 클립). */
	.lead,
	.sSub,
	.note {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.lead {
		-webkit-line-clamp: 3;
	}
	.sSub {
		-webkit-line-clamp: 2;
	}
	.note {
		-webkit-line-clamp: 2;
	}
	/* kicker (accent dot + label) */
	.kicker {
		display: inline-flex;
		align-items: center;
		gap: 0.6em;
		font-size: clamp(11px, 2.4cqw, 17px);
		color: #ff3f6f;
		font-weight: 800;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.kicker i {
		width: 0.55em;
		height: 0.55em;
		border-radius: 999px;
		background: #ff3f6f;
	}
	.hl {
		color: var(--hl, #ff3f6f);
	}
	/* editorial (기존 SNS editorial 재현 — 하단 텍스트 블록) */
	.editorial {
		margin-top: auto;
		display: flex;
		flex-direction: column;
	}
	.eyebrow {
		font-size: clamp(11px, 2.4cqw, 18px);
		font-weight: 800;
		letter-spacing: 0.04em;
		color: #fb3f6c;
		margin-bottom: 0.5em;
	}
	.eLine {
		margin: 0;
		font-size: clamp(26px, 7cqw, 64px);
		font-weight: 900;
		line-height: 1.13;
		letter-spacing: -0.01em;
		color: #f4f6fb;
		white-space: pre-line;
		word-break: keep-all;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 4;
		overflow: hidden;
	}
	.eSub {
		margin: 0.7em 0 0;
		font-size: clamp(13px, 3cqw, 26px);
		font-weight: 500;
		line-height: 1.46;
		color: #a4adba;
		white-space: pre-line;
		word-break: keep-all;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 4;
		overflow: hidden;
	}
	.eStat {
		display: flex;
		align-items: baseline;
		gap: 0.2em;
	}
	.eNum {
		font-size: clamp(56px, 18cqw, 200px);
		font-weight: 900;
		line-height: 0.92;
		color: #fb3f6c;
	}
	.eUnit {
		font-size: clamp(20px, 6cqw, 56px);
		font-weight: 800;
		color: #f4f6fb;
		white-space: nowrap;
	}
	/* cover */
	.cover {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		gap: 0.5em;
	}
	.bigName {
		margin: 0.1em 0 0;
		font-size: clamp(32px, 9cqw, 76px);
		font-weight: 900;
		line-height: 1.05;
		letter-spacing: -0.03em;
	}
	.lead {
		margin: 0.2em 0 0;
		font-size: clamp(16px, 4cqw, 32px);
		font-weight: 600;
		line-height: 1.35;
		color: #e7edf5;
	}
	.mono {
		margin: 0.6em 0 0;
		font-family: Menlo, Consolas, monospace;
		font-size: clamp(11px, 2.4cqw, 18px);
		letter-spacing: 0.12em;
		color: #94a3b8;
	}
	/* section head */
	.sHead {
		margin-bottom: 1.2em;
	}
	.sSub {
		margin: 0.4em 0 0;
		font-size: clamp(20px, 5cqw, 44px);
		font-weight: 800;
		line-height: 1.15;
		letter-spacing: -0.02em;
	}
	.note {
		margin: 0 0 1em;
		font-size: clamp(13px, 2.8cqw, 22px);
		line-height: 1.5;
		color: #cdd9e6;
		border-left: 2px solid #ff3f6f;
		padding-left: 0.7em;
	}
	/* kpis */
	.kpis {
		flex: 1;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 4%;
		align-content: center;
	}
	.kpi {
		display: flex;
		flex-direction: column;
		gap: 0.3em;
		padding: 6%;
		background: rgba(15, 18, 25, 0.72);
		border: 1px solid #1e2433;
		border-radius: 14px;
	}
	.kL {
		font-size: clamp(12px, 2.6cqw, 20px);
		color: #94a3b8;
	}
	.kV {
		font-size: clamp(22px, 6cqw, 50px);
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}
	.kV.neg {
		color: #ea4647;
	}
	.kV.pos {
		color: #d8e2f0;
	}
	/* 텍스트 슬라이드(narrative·closing) = 에디토리얼처럼 좌측 정렬 + 하단 고정(중앙정렬 금지). */
	.content.txtSlide {
		justify-content: flex-end;
	}
	/* narrative */
	.narr {
		margin: 0;
		font-size: clamp(22px, 5.6cqw, 52px);
		font-weight: 800;
		line-height: 1.25;
		letter-spacing: -0.02em;
		white-space: pre-line; /* 손글 줄바꿈(\n) 보존 */
		word-break: keep-all;
	}
	/* flags */
	.flags {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.7em;
		justify-content: center;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.flags li {
		padding: 0.7em 0.9em;
		border-radius: 12px;
		font-size: clamp(15px, 3.4cqw, 28px);
		font-weight: 600;
		border-left: 4px solid;
		background: rgba(5, 8, 17, 0.5);
	}
	.flags.warning li {
		border-color: #ea4647;
	}
	.flags.opportunity li {
		border-color: #d8e2f0;
	}
	/* charts — 사진 위에서도 가독되게 반투명 패널 + 사진 일부 노출 */
	.chart,
	.bars,
	.share,
	.finWrap,
	.tWrap {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 0.7em;
		background: rgba(5, 8, 17, 0.58);
		border: 1px solid rgba(30, 36, 51, 0.7);
		border-radius: 14px;
		padding: 5%;
		box-sizing: border-box;
	}
	/* MiniFinChart 가 패널 폭을 꽉 채우게(.mfc 가 content 폭으로 줄어 작은 정사각으로 뜨던 것 교정).
	   svg 는 width:100%·height:auto(terminal.css) → 폭 = 패널 폭. 차트(h=190) 위 + 수치표 아래 병치. */
	.finWrap {
		justify-content: flex-start;
		gap: 0.5em;
	}
	.finWrap :global(.mfc) {
		width: 100%;
		flex: 0 0 auto;
	}
	/* 차트 밑 수치표 — 시리즈×기간(compact). 시리즈명 열은 auto·좌측, 값은 우측. */
	.finT {
		font-size: clamp(8px, 1.85cqw, 13px);
		flex: 0 0 auto;
	}
	.finT th,
	.finT td {
		padding: 0.3em 0.4em;
	}
	.finT th:first-child,
	.finT td:first-child {
		width: auto;
		white-space: nowrap;
		color: #cdd9e6;
		font-weight: 600;
	}
	.finUnit {
		color: #9aa3ad !important;
		font-weight: 600;
		font-size: 0.9em;
	}
	.lineChart {
		width: 100%;
		height: 40%;
		min-height: 180px;
	}
	.lArea {
		fill: rgba(234, 70, 71, 0.16);
	}
	.lLine {
		fill: none;
		stroke: #ea4647;
		stroke-width: 0.7;
		vector-effect: non-scaling-stroke;
	}
	.lMark {
		stroke: #475569;
		stroke-width: 0.3;
		stroke-dasharray: 1 1;
		vector-effect: non-scaling-stroke;
	}
	.lDot {
		fill: #ea4647;
	}
	.lMarkers {
		display: flex;
		gap: 1.2em;
		font-size: clamp(12px, 2.4cqw, 18px);
		color: #94a3b8;
	}
	.bar {
		display: grid;
		grid-template-columns: 28% 1fr auto;
		gap: 0.7em;
		align-items: center;
		font-size: clamp(13px, 2.8cqw, 22px);
	}
	.bT {
		height: 1.1em;
		background: rgba(15, 18, 25, 0.8);
		border-radius: 4px;
		overflow: hidden;
	}
	.bF {
		display: block;
		height: 100%;
		background: #ff3f6f;
	}
	.bF.neg {
		background: #ea4647;
	}
	.bV {
		font-variant-numeric: tabular-nums;
		color: #cbd5e1;
	}
	.shRow {
		display: grid;
		grid-template-columns: 18% 1fr;
		gap: 0.7em;
		align-items: center;
	}
	.shY {
		font-size: clamp(12px, 2.4cqw, 18px);
		color: #94a3b8;
	}
	.shBar {
		display: flex;
		height: 1.3em;
		border-radius: 4px;
		overflow: hidden;
	}
	.shSeg {
		height: 100%;
	}
	.shLeg {
		display: flex;
		flex-wrap: wrap;
		gap: 1em;
		font-size: clamp(11px, 2.2cqw, 16px);
		color: #94a3b8;
	}
	.shLi {
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
	}
	.shLi i {
		width: 0.7em;
		height: 0.7em;
		border-radius: 2px;
	}
	.cT {
		width: 100%;
		table-layout: fixed; /* 4:5 프레임에 맞게 — 컬럼이 균등 축소(가로 스크롤·넘침 금지) */
		border-collapse: collapse;
		font-size: clamp(9px, 2.1cqw, 15px);
	}
	.cT th,
	.cT td {
		padding: 0.45em 0.4em;
		text-align: left;
		border-bottom: 1px solid rgba(30, 36, 51, 0.9);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.cT th:first-child,
	.cT td:first-child {
		width: 26%; /* 라벨 열 — 좁혀서 기간 열에 폭을 양보(헤더 '24Q1' 절단 방지) */
		white-space: normal;
		word-break: keep-all;
	}
	.cT th.num,
	.cT td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.cT td.neg {
		color: #ea4647;
	}
	.cT td.pos,
	.cT td.ok {
		color: #d8e2f0;
	}
	.cT td.warn {
		color: #ff9ab0;
	}
	.spark {
		width: 64px;
		height: 22px;
	}
	.spkA {
		fill: rgba(255, 63, 111, 0.18);
	}
	.spkL {
		fill: none;
		stroke: #ff3f6f;
		stroke-width: 1;
		vector-effect: non-scaling-stroke;
	}
	.muted {
		color: #64748b;
		font-size: clamp(13px, 2.6cqw, 20px);
	}
	/* closing / empty */
	.closing {
		margin: 0;
		font-size: clamp(20px, 5cqw, 44px);
		font-weight: 700;
		line-height: 1.3;
		white-space: pre-line; /* 손글 줄바꿈 보존 */
		word-break: keep-all;
	}
	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		color: #94a3b8;
		font-size: clamp(14px, 3cqw, 24px);
		text-align: left;
	}
</style>
